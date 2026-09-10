#!/usr/bin/env python3
"""Serial Studio Historian → instrument receipt (capture/config/integrity).

Gate identity is SHA-256 of a *closed* SQLite backup. Hashing the live
``.db`` file while WAL is open is a fingerprint only — never snapshot_sha256.

This module does not score experiments. PASS/FAIL thresholds belong in a
later gate receipt keyed by scoring_profile_id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Sequence


INSTRUMENT_SCHEMA = "k1.serial-studio.instrument_receipt.v2"

# Live .db bytes omit WAL pages. Never treat that digest as gate identity.
LIVE_FINGERPRINT_NOTE = (
    "sha256 of live .db file bytes only; WAL pages omitted; NOT final evidence"
)

TOOLS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_DIR = TOOLS_DIR / "captures" / "snapshots"
CANONICAL_SSPROJ = TOOLS_DIR / "K1-Dual-UART-Observability.ssproj"
PROTECTED_RECEIPT_NAME = "latest.receipt.json"

# Dashboard live samples — not project config. Other mismatches stay drift.
_VOLATILE_PROJECT_KEYS = frozenset({"numericValue", "value"})

_HOST_PARSE_SEQ_TITLES = ("host_parse_seq", "parse_seq")
_DEVICE_MS_TITLES = ("device_ms",)

_NOT_AUTHORITY = (
    "dashboard",
    "screenshot",
    "host_uart_arrival_alone",
    "live_db_fingerprint",
    "live_wal_hash",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sqlite_uri(path: Path, *, mode: str = "ro") -> str:
    return path.resolve().as_uri() + f"?mode={mode}"


def connect_read_only(db: Path) -> sqlite3.Connection:
    """Read/query_only connection. Never PRAGMA wal_checkpoint on this handle."""
    conn = sqlite3.connect(sqlite_uri(db, mode="ro"), uri=True, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _historian_root(path: Path) -> Path | None:
    """Serial Studio's Session Databases folder, or None if this is not a live Historian path."""
    parts = path.resolve().parts
    for i, part in enumerate(parts):
        if part == "Session Databases" and i > 0 and parts[i - 1] == "Serial Studio":
            return Path(*parts[: i + 1])
    return None


def _refuse_live_dir_write(path: Path, live_db: Path) -> None:
    dest = path.resolve()
    src = live_db.resolve()
    if dest == src:
        raise ValueError(f"refusing to overwrite the live Historian db: {path}")
    live_root = _historian_root(src)
    if live_root is not None and (dest == live_root or live_root in dest.parents):
        raise ValueError(f"refusing to write into the live Historian directory: {path}")


def _refuse_protected_receipt(path: Path) -> None:
    if path.name == PROTECTED_RECEIPT_NAME:
        raise ValueError(f"refusing to overwrite {PROTECTED_RECEIPT_NAME}")


def _close_destination(dest: Path) -> None:
    """Checkpoint *dest only* so the snapshot is a single closed file."""
    closed = sqlite3.connect(str(dest))
    try:
        closed.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        closed.execute("PRAGMA journal_mode=DELETE")
        closed.commit()
    finally:
        closed.close()
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(dest) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def _open_src(db: Path, *, query_only: bool) -> sqlite3.Connection:
    conn = sqlite3.connect(sqlite_uri(db, mode="ro"), uri=True, timeout=30.0)
    conn.row_factory = sqlite3.Row
    if query_only:
        conn.execute("PRAGMA query_only=ON")
    return conn


def backup_to_closed_sqlite(src_db: Path, dest: Path) -> Path:
    """Copy committed state via sqlite3.Connection.backup(). Does not checkpoint src."""
    dest = dest.resolve()
    _refuse_live_dir_write(dest, src_db)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    last_error: sqlite3.Error | None = None
    # Prefer query_only. Some SQLite builds reject backup() on query_only;
    # retry mode=ro without query_only. Still never wal_checkpoint the source.
    for query_only in (True, False):
        src = _open_src(src_db, query_only=query_only)
        try:
            dst = sqlite3.connect(str(dest))
            try:
                src.backup(dst)
                dst.commit()
                last_error = None
            except sqlite3.OperationalError as exc:
                last_error = exc
            finally:
                dst.close()
        finally:
            src.close()
        if last_error is None:
            break
        if dest.exists():
            dest.unlink()
    if last_error is not None:
        raise last_error
    _close_destination(dest)
    return dest


def table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def _has_table(names: Sequence[str], name: str) -> bool:
    return name in names


def _count(
    conn: sqlite3.Connection, table: str, session_id: int | None, columns: Sequence[str]
) -> int:
    if session_id is not None and "session_id" in columns:
        row = conn.execute(
            f'SELECT COUNT(*) FROM "{table}" WHERE session_id = ?', (session_id,)
        ).fetchone()
    else:
        row = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
    return int(row[0])


def _select_session(
    conn: sqlite3.Connection, names: Sequence[str], session_id: int | None
) -> sqlite3.Row | None:
    if not _has_table(names, "sessions"):
        return None
    cols = table_columns(conn, "sessions")
    if session_id is not None:
        return conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    order = "session_id DESC"
    if "started_at" in cols:
        order = "started_at DESC, session_id DESC"
    return conn.execute(f"SELECT * FROM sessions ORDER BY {order} LIMIT 1").fetchone()


def _row_get(row: sqlite3.Row | None, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def _parse_project_json(blob: str | None) -> dict[str, Any] | None:
    if not blob:
        return None
    try:
        loaded = json.loads(blob)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _strip_volatile(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: _strip_volatile(value)
            for key, value in obj.items()
            if key not in _VOLATILE_PROJECT_KEYS
        }
    if isinstance(obj, list):
        return [_strip_volatile(item) for item in obj]
    return obj


def _canonical_dump(obj: Any) -> str:
    return json.dumps(_strip_volatile(obj), sort_keys=True, separators=(",", ":"))


def config_drift(session_project_json: str | None, canonical_ssproj: Path | None) -> bool | str:
    """True = drift, False = match, 'UNKNOWN' = cannot compare fairly."""
    if canonical_ssproj is None or not canonical_ssproj.is_file():
        return "UNKNOWN"
    session_obj = _parse_project_json(session_project_json)
    try:
        canonical_obj = json.loads(canonical_ssproj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return "UNKNOWN"
    if not isinstance(canonical_obj, dict) or session_obj is None:
        return "UNKNOWN"
    if "groups" not in session_obj or "groups" not in canonical_obj:
        return "UNKNOWN"
    return _canonical_dump(session_obj) != _canonical_dump(canonical_obj)


def _unique_ids_for_titles(
    conn: sqlite3.Connection,
    names: Sequence[str],
    session_id: int | None,
    titles: Iterable[str],
) -> list[int]:
    if not _has_table(names, "columns"):
        return []
    cols = table_columns(conn, "columns")
    if "title" not in cols or "unique_id" not in cols:
        return []
    wanted = tuple(title.casefold() for title in titles)
    sql = "SELECT DISTINCT unique_id FROM columns WHERE lower(title) IN ({})".format(
        ",".join("?" * len(wanted))
    )
    params: list[Any] = list(wanted)
    if session_id is not None and "session_id" in cols:
        sql += " AND session_id = ?"
        params.append(session_id)
    return [int(r[0]) for r in conn.execute(sql, params) if r[0] is not None]


def _numeric_series_from_sql_column(
    conn: sqlite3.Connection,
    session_id: int | None,
    column: str,
    reading_cols: Sequence[str],
) -> list[float]:
    order = "reading_id"
    if "timestamp_ns" in reading_cols:
        order = "timestamp_ns, reading_id"
    where = f'"{column}" IS NOT NULL'
    params: list[Any] = []
    if session_id is not None and "session_id" in reading_cols:
        where += " AND session_id = ?"
        params.append(session_id)
    rows = conn.execute(
        f'SELECT "{column}" FROM readings WHERE {where} ORDER BY {order}',
        params,
    ).fetchall()
    return [float(row[0]) for row in rows if row[0] is not None]


def _numeric_series_from_unique_ids(
    conn: sqlite3.Connection,
    session_id: int | None,
    unique_ids: Sequence[int],
    reading_cols: Sequence[str],
) -> list[float]:
    if not unique_ids or "unique_id" not in reading_cols:
        return []
    value_col = (
        "final_numeric_value"
        if "final_numeric_value" in reading_cols
        else "raw_numeric_value"
        if "raw_numeric_value" in reading_cols
        else None
    )
    if value_col is None:
        return []
    order = "reading_id"
    if "timestamp_ns" in reading_cols:
        order = "timestamp_ns, reading_id"
    placeholders = ",".join("?" * len(unique_ids))
    params: list[Any] = list(unique_ids)
    where = f"unique_id IN ({placeholders}) AND {value_col} IS NOT NULL"
    if session_id is not None and "session_id" in reading_cols:
        where += " AND session_id = ?"
        params.append(session_id)
    rows = conn.execute(
        f"SELECT {value_col} FROM readings WHERE {where} ORDER BY {order}",
        params,
    ).fetchall()
    return [float(r[0]) for r in rows if r[0] is not None]


def _series_for_metric(
    conn: sqlite3.Connection,
    names: Sequence[str],
    session_id: int | None,
    sql_name: str,
    titles: Iterable[str],
) -> list[float] | None:
    """Return values if a readings SQL column or columns.title exists; else None."""
    if not _has_table(names, "readings"):
        return None
    reading_cols = table_columns(conn, "readings")
    if sql_name in reading_cols:
        return _numeric_series_from_sql_column(conn, session_id, sql_name, reading_cols)
    unique_ids = _unique_ids_for_titles(conn, names, session_id, titles)
    if not unique_ids:
        return None
    return _numeric_series_from_unique_ids(conn, session_id, unique_ids, reading_cols)


def _first_last(series: list[float] | None) -> tuple[float | None, float | None]:
    if not series:
        return None, None
    return series[0], series[-1]


def _downward_jumps(series: list[float] | None) -> int:
    if not series or len(series) < 2:
        return 0
    jumps = 0
    prev = series[0]
    for value in series[1:]:
        if value < prev:
            jumps += 1
        prev = value
    return jumps


def _device_ms_reset_count(
    conn: sqlite3.Connection, names: Sequence[str], session_id: int | None
) -> int:
    if not _has_table(names, "readings"):
        return 0
    reading_cols = table_columns(conn, "readings")
    if "device_ms" in reading_cols:
        return _downward_jumps(
            _numeric_series_from_sql_column(conn, session_id, "device_ms", reading_cols)
        )
    unique_ids = _unique_ids_for_titles(conn, names, session_id, _DEVICE_MS_TITLES)
    return sum(
        _downward_jumps(
            _numeric_series_from_unique_ids(conn, session_id, [uid], reading_cols)
        )
        for uid in unique_ids
    )


def _source_ids(
    conn: sqlite3.Connection, names: Sequence[str], session_id: int | None
) -> list[int]:
    if not _has_table(names, "columns"):
        return []
    cols = table_columns(conn, "columns")
    if "source_id" not in cols:
        return []
    sql = "SELECT DISTINCT source_id FROM columns WHERE source_id IS NOT NULL"
    params: list[Any] = []
    if session_id is not None and "session_id" in cols:
        sql += " AND session_id = ?"
        params.append(session_id)
    sql += " ORDER BY 1"
    return [int(r[0]) for r in conn.execute(sql, params)]


def emit_instrument_receipt(
    db: Path,
    *,
    snapshot: bool = True,
    snapshot_dir: Path | None = None,
    canonical_ssproj: Path | None = None,
    session_id: int | None = None,
    out: Path | None = None,
) -> dict[str, Any]:
    """Capture/config/integrity receipt. Never an experiment PASS/FAIL."""
    db = db.expanduser().resolve()
    generated_unix = int(time.time())
    live_fingerprint = sha256_file(db) if db.is_file() else None
    canonical = CANONICAL_SSPROJ if canonical_ssproj is None else Path(canonical_ssproj)

    snapshot_path: Path | None = None
    snapshot_sha: str | None = None
    snapshot_unix: int | None = None
    if snapshot:
        dest_dir = Path(snapshot_dir) if snapshot_dir is not None else DEFAULT_SNAPSHOT_DIR
        dest_dir = dest_dir.resolve()
        _refuse_live_dir_write(dest_dir / "placeholder.sqlite", db)
        sid_label = "none" if session_id is None else str(session_id)
        snapshot_unix = generated_unix
        snapshot_path = dest_dir / f"historian_s{sid_label}_{snapshot_unix}.sqlite"
        backup_to_closed_sqlite(db, snapshot_path)
        snapshot_sha = sha256_file(snapshot_path)

    evidence_class = "SNAPSHOT_SQLITE" if snapshot else "LIVE_DB_FINGERPRINT"
    authority = "closed-sqlite-snapshot" if snapshot else "live-db-file-bytes"

    conn = connect_read_only(snapshot_path if snapshot_path is not None else db)
    try:
        names = table_names(conn)
        session = _select_session(conn, names, session_id)
        selected_id = _row_get(session, "session_id")
        if selected_id is not None:
            selected_id = int(selected_id)
        ended_at = _row_get(session, "ended_at")
        recording_active = ended_at is None or ended_at == ""
        project_title = _row_get(session, "project_title")
        project_json = _row_get(session, "project_json")
        if isinstance(project_json, bytes):
            project_json = project_json.decode("utf-8")
        project_obj = _parse_project_json(project_json if isinstance(project_json, str) else None)
        app_version = None
        if project_obj is not None:
            app_version = project_obj.get("writerVersion") or project_obj.get(
                "writerVersionAtCreation"
            )

        reading_cols = table_columns(conn, "readings") if "readings" in names else []
        raw_cols = table_columns(conn, "raw_bytes") if "raw_bytes" in names else []
        reading_count = (
            _count(conn, "readings", selected_id, reading_cols) if "readings" in names else 0
        )
        raw_bytes_count = (
            _count(conn, "raw_bytes", selected_id, raw_cols) if "raw_bytes" in names else 0
        )

        parse_series = _series_for_metric(
            conn, names, selected_id, "host_parse_seq", _HOST_PARSE_SEQ_TITLES
        )
        device_series = _series_for_metric(
            conn, names, selected_id, "device_ms", _DEVICE_MS_TITLES
        )
        first_parse, last_parse = _first_last(parse_series)
        first_device, last_device = _first_last(device_series)
        # Count wraps per unique_id so dual-UART clocks are not interleaved.
        device_ms_resets = _device_ms_reset_count(conn, names, selected_id)
        drift = config_drift(
            project_json if isinstance(project_json, str) else None, canonical
        )
        source_ids = _source_ids(conn, names, selected_id)
    finally:
        conn.close()

    if snapshot and not recording_active:
        verdict = "INSTRUMENT_ARCHIVED"
    else:
        verdict = "INSTRUMENT_LIVE_SNAPSHOT"

    project_json_sha = (
        sha256_text(project_json) if isinstance(project_json, str) and project_json else None
    )

    receipt: dict[str, Any] = {
        "ok": True,
        "schema": INSTRUMENT_SCHEMA,
        "evidence_class": evidence_class,
        "authority": authority,
        "not_authority": list(_NOT_AUTHORITY),
        "original_db_path": str(db),
        "session_id": selected_id,
        "snapshot_path": str(snapshot_path) if snapshot_path is not None else None,
        "snapshot_sha256": snapshot_sha,
        "snapshot_unix": snapshot_unix,
        "live_db_fingerprint": live_fingerprint,
        "live_db_fingerprint_note": LIVE_FINGERPRINT_NOTE,
        "recording_active": bool(recording_active),
        "app_version": app_version,
        "project_title": project_title,
        "source_ids": source_ids,
        "reading_count": reading_count,
        "raw_bytes_count": raw_bytes_count,
        "project_json_sha256": project_json_sha,
        "first_host_parse_seq": first_parse,
        "last_host_parse_seq": last_parse,
        "first_device_ms": first_device,
        "last_device_ms": last_device,
        "device_ms_resets": device_ms_resets,
        "INSTRUMENT_CONFIG_DRIFT": drift,
        "generated_unix": generated_unix,
        "verdict": verdict,
        "verdict_note": (
            "Instrument capture/config/integrity only. Not an experiment PASS/FAIL. "
            "Gate scoring requires emit_gate_receipt(scoring_profile_id=...)."
        ),
    }
    if snapshot_sha is not None and live_fingerprint is not None:
        receipt["snapshot_sha256_equals_live_fingerprint"] = snapshot_sha == live_fingerprint

    if out is not None:
        out_path = Path(out)
        _refuse_protected_receipt(out_path)
        _refuse_live_dir_write(out_path, db)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(receipt, indent=2) + "\n")
        receipt["receipt_path"] = str(out_path.resolve())
    elif snapshot_path is not None:
        out_path = snapshot_path.with_suffix(".receipt.json")
        _refuse_protected_receipt(out_path)
        out_path.write_text(json.dumps(receipt, indent=2) + "\n")
        receipt["receipt_path"] = str(out_path)

    return receipt


def emit_gate_receipt(
    instrument_receipt: dict[str, Any],
    *,
    scoring_profile_id: str,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Later hook: named scoring profile. Thresholds are not invented here."""
    raise NotImplementedError(
        "gate receipt requires a named scoring_profile_id and agreed thresholds; "
        f"refusing to score {scoring_profile_id!r} from the instrument tool"
        + (
            ""
            if thresholds is None
            else " (thresholds must come from the profile, not this call)"
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit a Serial Studio instrument receipt from Historian SQLite."
    )
    parser.add_argument("--db", required=True, help="Historian .db path")
    parser.add_argument("--out", help="Receipt JSON path (never latest.receipt.json)")
    parser.add_argument(
        "--snapshot",
        dest="snapshot",
        action="store_true",
        default=True,
        help="Backup to a closed .sqlite and hash that file (default)",
    )
    parser.add_argument(
        "--no-snapshot",
        dest="snapshot",
        action="store_false",
        help="Legacy live-fingerprint only; evidence_class=LIVE_DB_FINGERPRINT",
    )
    parser.add_argument("--snapshot-dir", type=Path, default=None)
    parser.add_argument("--canonical-ssproj", type=Path, default=None)
    parser.add_argument("--session-id", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    db = Path(args.db).expanduser()
    if not db.is_file():
        print(json.dumps({"ok": False, "schema": INSTRUMENT_SCHEMA, "error": f"missing {db}"}))
        return 1
    try:
        receipt = emit_instrument_receipt(
            db,
            snapshot=args.snapshot,
            snapshot_dir=args.snapshot_dir,
            canonical_ssproj=args.canonical_ssproj,
            session_id=args.session_id,
            out=Path(args.out) if args.out else None,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema": INSTRUMENT_SCHEMA,
                    "error": str(exc),
                    "verdict": "INSTRUMENT_LIVE_SNAPSHOT",
                }
            )
        )
        return 1
    text = json.dumps(receipt, indent=2)
    print(text)
    if receipt.get("receipt_path"):
        print(f"wrote {receipt['receipt_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
