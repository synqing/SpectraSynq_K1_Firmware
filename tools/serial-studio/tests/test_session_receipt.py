"""Instrument receipt: closed backup hash is identity; live .db hash is not.

Uses a tiny synthetic Historian. Does not open the live Serial Studio DB.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

SCORER = Path(__file__).resolve().parents[1] / "scorer"
sys.path.insert(0, str(SCORER))

from session_receipt import (  # noqa: E402
    INSTRUMENT_SCHEMA,
    backup_to_closed_sqlite,
    config_drift,
    connect_read_only,
    emit_gate_receipt,
    emit_instrument_receipt,
    main,
    sha256_file,
)


HISTORIAN_DDL = """
CREATE TABLE sessions (
  session_id INTEGER PRIMARY KEY,
  project_title TEXT,
  started_at TEXT,
  ended_at TEXT,
  project_json TEXT,
  notes TEXT
);
CREATE TABLE columns (
  column_id INTEGER PRIMARY KEY,
  session_id INTEGER,
  unique_id INTEGER,
  source_id INTEGER,
  source_title TEXT,
  group_title TEXT,
  title TEXT,
  units TEXT,
  widget TEXT,
  is_virtual INTEGER
);
CREATE TABLE readings (
  reading_id INTEGER PRIMARY KEY,
  session_id INTEGER,
  timestamp_ns INTEGER,
  unique_id INTEGER,
  raw_numeric_value REAL,
  raw_string_value TEXT,
  final_numeric_value REAL,
  final_string_value TEXT,
  is_numeric INTEGER
);
CREATE TABLE raw_bytes (
  raw_id INTEGER PRIMARY KEY,
  session_id INTEGER,
  timestamp_ns INTEGER,
  device_id INTEGER,
  data BLOB
);
CREATE TABLE project_metadata (key TEXT, value TEXT);
CREATE TABLE table_snapshots (id INTEGER PRIMARY KEY);
CREATE TABLE tags (tag_id INTEGER PRIMARY KEY);
CREATE TABLE session_tags (session_id INTEGER, tag_id INTEGER);
"""

PROJECT_A = {
    "writerVersion": "4.0.3",
    "groups": [{"title": "K1 AP", "datasets": []}],
    "title": "K1 Dual UART Observability",
}


def _insert_reading(conn: sqlite3.Connection, **kwargs: object) -> None:
    conn.execute(
        """
        INSERT INTO readings (
          reading_id, session_id, timestamp_ns, unique_id,
          raw_numeric_value, raw_string_value, final_numeric_value,
          final_string_value, is_numeric
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            kwargs["reading_id"],
            kwargs["session_id"],
            kwargs["timestamp_ns"],
            kwargs["unique_id"],
            kwargs.get("raw_numeric_value"),
            kwargs.get("raw_string_value"),
            kwargs.get("final_numeric_value"),
            kwargs.get("final_string_value"),
            kwargs.get("is_numeric", 1),
        ),
    )


def build_historian(path: Path, *, wal: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint=0")
        conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(HISTORIAN_DDL)
    conn.execute(
        """
        INSERT INTO sessions (session_id, project_title, started_at, ended_at, project_json, notes)
        VALUES (1, 'K1 Dual UART Observability', '2026-08-31T00:00:00Z', '2026-08-31T00:10:00Z', ?, 'closed')
        """,
        (json.dumps(PROJECT_A),),
    )
    conn.execute(
        """
        INSERT INTO sessions (session_id, project_title, started_at, ended_at, project_json, notes)
        VALUES (2, 'K1 Dual UART Observability', '2026-08-31T00:20:00Z', NULL, ?, 'live')
        """,
        (json.dumps(PROJECT_A),),
    )
    conn.execute(
        """
        INSERT INTO columns (
          column_id, session_id, unique_id, source_id, source_title,
          group_title, title, units, widget, is_virtual
        ) VALUES
          (1, 2, 18, 0, 'Bench', 'K1 AP', 'host_parse_seq', '', '', 1),
          (2, 2, 16, 0, 'Bench', 'K1 AP', 'device_ms', 'ms', '', 0),
          (3, 1, 18, 0, 'Bench', 'K1 AP', 'host_parse_seq', '', '', 1)
        """
    )
    _insert_reading(
        conn,
        reading_id=1,
        session_id=1,
        timestamp_ns=1,
        unique_id=18,
        raw_numeric_value=1,
        final_numeric_value=1,
    )
    _insert_reading(
        conn,
        reading_id=2,
        session_id=2,
        timestamp_ns=10,
        unique_id=18,
        raw_numeric_value=10,
        final_numeric_value=10,
    )
    _insert_reading(
        conn,
        reading_id=3,
        session_id=2,
        timestamp_ns=20,
        unique_id=18,
        raw_numeric_value=11,
        final_numeric_value=11,
    )
    # device_ms with one downward jump (reset)
    for rid, ts, value in ((4, 10, 100.0), (5, 20, 150.0), (6, 30, 40.0), (7, 40, 60.0)):
        _insert_reading(
            conn,
            reading_id=rid,
            session_id=2,
            timestamp_ns=ts,
            unique_id=16,
            raw_numeric_value=value,
            final_numeric_value=value,
        )
    conn.execute(
        "INSERT INTO raw_bytes (raw_id, session_id, timestamp_ns, device_id, data) VALUES (1, 2, 10, 0, X'00')"
    )
    conn.commit()
    return conn


def test_snapshot_sha256_matches_closed_file_and_differs_from_live_wal(tmp_path: Path) -> None:
    db = tmp_path / "live.db"
    writer = build_historian(db, wal=True)
    wal_path = Path(str(db) + "-wal")
    assert writer.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    writer.execute(
        """
        INSERT INTO readings (
          reading_id, session_id, timestamp_ns, unique_id,
          raw_numeric_value, raw_string_value, final_numeric_value,
          final_string_value, is_numeric
        ) VALUES (100, 2, 999, 18, 99, NULL, 99, NULL, 1)
        """
    )
    writer.commit()
    assert wal_path.exists() and wal_path.stat().st_size > 0
    wal_size_before = wal_path.stat().st_size
    live_hash_while_writer_open = sha256_file(db)

    snaps = tmp_path / "snaps"
    canon = tmp_path / "canon.ssproj"
    canon.write_text(json.dumps(PROJECT_A), encoding="utf-8")
    receipt = emit_instrument_receipt(
        db,
        snapshot=True,
        snapshot_dir=snaps,
        canonical_ssproj=canon,
        session_id=2,
    )

    closed = Path(receipt["snapshot_path"])
    assert closed.is_file()
    assert receipt["schema"] == INSTRUMENT_SCHEMA
    assert receipt["snapshot_sha256"] == sha256_file(closed)
    assert receipt["live_db_fingerprint"] == live_hash_while_writer_open
    assert receipt["snapshot_sha256"] != receipt["live_db_fingerprint"]
    assert receipt["verdict"] in ("INSTRUMENT_ARCHIVED", "INSTRUMENT_LIVE_SNAPSHOT")
    assert receipt["verdict"] not in ("PASS", "FAIL")
    assert receipt["evidence_class"] == "SNAPSHOT_SQLITE"
    assert receipt["recording_active"] is True
    assert receipt["session_id"] == 2
    assert receipt["reading_count"] == 7  # 3 parse_seq (incl. WAL insert) + 4 device_ms
    # writer still holds the extra row; snapshot includes committed row 100
    assert receipt["first_host_parse_seq"] == 10.0
    assert receipt["last_host_parse_seq"] == 99.0
    assert receipt["first_device_ms"] == 100.0
    assert receipt["last_device_ms"] == 60.0
    assert receipt["device_ms_resets"] == 1
    assert receipt["source_ids"] == [0]
    assert receipt["app_version"] == "4.0.3"
    assert receipt["INSTRUMENT_CONFIG_DRIFT"] is False
    # Source WAL was not checkpointed (we do not wal_checkpoint the live file).
    assert wal_path.exists()
    assert wal_path.stat().st_size >= wal_size_before
    writer.close()


def test_no_snapshot_sets_live_fingerprint_evidence_class(tmp_path: Path) -> None:
    db = tmp_path / "live.db"
    conn = build_historian(db, wal=False)
    conn.close()
    out = tmp_path / "fp.receipt.json"
    receipt = emit_instrument_receipt(
        db,
        snapshot=False,
        out=out,
        canonical_ssproj=tmp_path / "missing.ssproj",
    )
    assert "live_db_fingerprint" in receipt
    assert receipt["live_db_fingerprint"] == sha256_file(db)
    assert receipt["evidence_class"] == "LIVE_DB_FINGERPRINT"
    assert receipt["snapshot_sha256"] is None
    assert receipt["snapshot_path"] is None
    assert receipt["verdict"] == "INSTRUMENT_LIVE_SNAPSHOT"
    assert receipt["INSTRUMENT_CONFIG_DRIFT"] == "UNKNOWN"
    loaded = json.loads(out.read_text())
    assert loaded["live_db_fingerprint"] == receipt["live_db_fingerprint"]


def test_cli_no_snapshot_and_refuses_latest_receipt(tmp_path: Path) -> None:
    db = tmp_path / "live.db"
    build_historian(db).close()
    out = tmp_path / "cli.receipt.json"
    rc = main(["--db", str(db), "--no-snapshot", "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["evidence_class"] == "LIVE_DB_FINGERPRINT"
    assert payload["live_db_fingerprint"]

    banned = tmp_path / "latest.receipt.json"
    rc_ban = main(["--db", str(db), "--no-snapshot", "--out", str(banned)])
    assert rc_ban == 1
    assert not banned.exists()


def test_archived_session_verdict(tmp_path: Path) -> None:
    db = tmp_path / "live.db"
    build_historian(db).close()
    canon = tmp_path / "canon.ssproj"
    canon.write_text(json.dumps(PROJECT_A), encoding="utf-8")
    receipt = emit_instrument_receipt(
        db,
        snapshot=True,
        snapshot_dir=tmp_path / "snaps",
        canonical_ssproj=canon,
        session_id=1,
    )
    assert receipt["recording_active"] is False
    assert receipt["verdict"] == "INSTRUMENT_ARCHIVED"
    assert receipt["reading_count"] == 1


def test_config_drift_true_and_unknown(tmp_path: Path) -> None:
    match = {"writerVersion": "4.0.3", "groups": []}
    ssproj = tmp_path / "a.ssproj"
    ssproj.write_text(json.dumps(match), encoding="utf-8")
    assert config_drift(json.dumps(match), ssproj) is False
    drifted = {"writerVersion": "4.0.3", "groups": [{"title": "other"}]}
    assert config_drift(json.dumps(drifted), ssproj) is True
    assert config_drift("{not json", ssproj) == "UNKNOWN"
    assert config_drift(json.dumps(match), tmp_path / "nope.ssproj") == "UNKNOWN"


def test_read_only_connection_rejects_writes(tmp_path: Path) -> None:
    db = tmp_path / "live.db"
    build_historian(db).close()
    conn = connect_read_only(db)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO tags (tag_id) VALUES (1)")
    conn.close()


def test_backup_does_not_write_into_serial_studio_session_databases(tmp_path: Path) -> None:
    live_dir = tmp_path / "Serial Studio" / "Session Databases" / "K1 Dual UART Observability"
    live_dir.mkdir(parents=True)
    db = live_dir / "K1 Dual UART Observability.db"
    build_historian(db).close()
    with pytest.raises(ValueError, match="live Historian"):
        backup_to_closed_sqlite(db, live_dir / "sibling.sqlite")
    dest = tmp_path / "snaps" / "closed.sqlite"
    backup_to_closed_sqlite(db, dest)
    assert dest.is_file()
    assert sha256_file(dest) != ""


def test_gate_receipt_signature_does_not_invent_thresholds() -> None:
    with pytest.raises(NotImplementedError, match="scoring_profile_id"):
        emit_gate_receipt({"schema": INSTRUMENT_SCHEMA}, scoring_profile_id="gate_c")
