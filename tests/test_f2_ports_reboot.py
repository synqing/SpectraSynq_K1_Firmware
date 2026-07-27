from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.dual_sync_probe import (
    f2_capture,
    f2_image_set,
    f2_ports,
    f2_reboot,
    f2_run,
)


LEADER_USB = "B4:3A:45:A5:87:F8"
FOLLOWER_USB = "B4:3A:45:A5:89:B4"
LEADER_CHIP = "F887A500"
FOLLOWER_CHIP = "B489A500"
HOST_SHA = "1" * 40
FIRMWARE_SHA = "a" * 40


@dataclass(frozen=True)
class ListedPort:
    device: str
    serial_number: str


class FakeSerial:
    def __init__(self, bus: "FakeSerialBus", port: str, baud: int) -> None:
        self.bus = bus
        self.port = port
        self.baud = baud
        self.dtr = True
        self.rts = True
        self._responses: list[bytes] = []
        self.closed = False

    @property
    def in_waiting(self) -> int:
        return int(bool(self._responses))

    def reset_input_buffer(self) -> None:
        self._responses.clear()

    def write(self, payload: bytes) -> int:
        command = payload.decode("ascii").strip()
        self.bus.writes.append((self.port, command))
        if command == ":reset":
            self.bus.reset_ports.add(self.port)
            self._responses.append(b"SBOK\n")
            return len(payload)

        chip_id = self.bus.chip_by_port[self.port]
        if command == ":chip_id":
            self._responses.append(f"{chip_id}\n".encode("ascii"))
        elif command == ":image_id":
            identity_set = (
                self.bus.post_identity
                if len(self.bus.reset_ports) == 2
                else self.bus.pre_identity
            )
            image = identity_set[chip_id]["app_elf_sha256"]
            self._responses.append(
                f"IMAGE_ID: app_elf_sha256={image}\n".encode("ascii")
            )
        elif command == ":runtime_id":
            identity = (
                self.bus.post_identity
                if len(self.bus.reset_ports) == 2
                else self.bus.pre_identity
            )[chip_id]
            self._responses.append(
                (
                    "RUNTIME_ID: "
                    f"boot_nonce={identity['boot_nonce']} "
                    f"uptime_ms={identity['uptime_ms']} "
                    f"reset_reason={identity['reset_reason']}\n"
                ).encode("ascii")
            )
        elif command == ":build":
            environment = (
                "k1_sync_probe_main"
                if chip_id == LEADER_CHIP
                else "k1_sync_probe_bench"
            )
            self._responses.append(
                (
                    "BUILD: version=test git=aaaaaaa epoch=1785168896 "
                    f"env={environment}\n"
                ).encode("ascii")
            )
        else:
            raise AssertionError(f"unexpected command: {command}")
        return len(payload)

    def flush(self) -> None:
        return None

    def readline(self) -> bytes:
        return self._responses.pop(0) if self._responses else b""

    def close(self) -> None:
        self.closed = True


class FakeSerialBus:
    def __init__(
        self,
        *,
        before: dict[str, str],
        after: dict[str, str] | None = None,
        pre_identity: dict[str, dict[str, object]] | None = None,
        post_identity: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.before = before
        self.after = after or before
        self.pre_identity = pre_identity or {
            LEADER_CHIP: {
                "app_elf_sha256": "a" * 64,
                "boot_nonce": "1111111111111111",
                "uptime_ms": 80_500,
                "reset_reason": 1,
            },
            FOLLOWER_CHIP: {
                "app_elf_sha256": "b" * 64,
                "boot_nonce": "2222222222222222",
                "uptime_ms": 79_500,
                "reset_reason": 1,
            },
        }
        self.post_identity = post_identity or {}
        self.writes: list[tuple[str, str]] = []
        self.opens: list[tuple[str, int]] = []
        self.reset_ports: set[str] = set()
        self.chip_by_port = {
            before["leader"]: LEADER_CHIP,
            before["follower"]: FOLLOWER_CHIP,
            self.after["leader"]: LEADER_CHIP,
            self.after["follower"]: FOLLOWER_CHIP,
        }

    def ports(self) -> list[ListedPort]:
        mapping = self.after if len(self.reset_ports) == 2 else self.before
        return [
            ListedPort(mapping["follower"], FOLLOWER_USB),
            ListedPort(mapping["leader"], LEADER_USB),
        ]

    def open(self, port: str, baud: int) -> FakeSerial:
        self.opens.append((port, baud))
        return FakeSerial(self, port, baud)


def bindings(leader_port: str, follower_port: str) -> dict[str, dict[str, str]]:
    return {
        "leader": {
            "usb_serial": LEADER_USB,
            "port": leader_port,
            "chip_id": LEADER_CHIP,
        },
        "follower": {
            "usb_serial": FOLLOWER_USB,
            "port": follower_port,
            "chip_id": FOLLOWER_CHIP,
        },
    }


def write_ports(stage, root, values, prior_manifest=None):
    return f2_ports.write_ports_manifest(
        stage,
        root,
        values,
        host_execution_sha=HOST_SHA,
        firmware_source_sha=FIRMWARE_SHA,
        prior_manifest=prior_manifest,
        created_at_utc="2026-07-28T01:00:00Z",
    )


def c1_identity() -> dict[str, dict[str, object]]:
    return {
        "leader": {
            "chip_id": LEADER_CHIP,
            "app_elf_sha256": "a" * 64,
            "boot_nonce": "1111111111111111",
            "uptime_ms": 80_000,
            "reset_reason": 1,
        },
        "follower": {
            "chip_id": FOLLOWER_CHIP,
            "app_elf_sha256": "b" * 64,
            "boot_nonce": "2222222222222222",
            "uptime_ms": 79_000,
            "reset_reason": 1,
        },
    }


def post_identity() -> dict[str, dict[str, object]]:
    return {
        LEADER_CHIP: {
            "app_elf_sha256": "a" * 64,
            "boot_nonce": "aaaaaaaaaaaaaaaa",
            "uptime_ms": 1_500,
            "reset_reason": 3,
        },
        FOLLOWER_CHIP: {
            "app_elf_sha256": "b" * 64,
            "boot_nonce": "bbbbbbbbbbbbbbbb",
            "uptime_ms": 1_400,
            "reset_reason": 3,
        },
    }


def reboot_evidence(tmp_path: Path) -> dict[str, Path]:
    image_set = tmp_path / "image-set.json"
    image_set.write_text("{}")
    c1_case = tmp_path / "case_C1.json"
    c1_case.write_text(
        json.dumps(
            {
                "case": "C1",
                "case_status": "PASS",
                "host_execution_sha": HOST_SHA,
                "firmware_source_sha": FIRMWARE_SHA,
            }
        )
    )
    flash_b = tmp_path / "flash_B.json"
    flash_b.write_text(
        json.dumps(
            {
                "case": "B",
                "status": "PASS",
                "host_execution_sha": HOST_SHA,
                "firmware_source_sha": FIRMWARE_SHA,
                "uploads": {
                    "leader": {"app_elf_sha256": "a" * 64},
                    "follower": {"app_elf_sha256": "b" * 64},
                },
            }
        )
    )
    pre = tmp_path / "attestations" / "case_C2_pre.json"
    pre.parent.mkdir()
    pre.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "f2_pre_attestation",
                "case": "C2",
                "scenario": "controlled_cold_coexistence",
                "captain": "Captain",
                "created_at_utc": "2026-07-28T01:00:00Z",
                "gpio_wiring_confirmed": True,
                "common_ground_confirmed": True,
                "logic_voltage": "3V3",
                "k718_state": "powered_and_advertising",
                "four_detent_commitment": True,
                "controlled_reboot_authorised": True,
            }
        )
    )
    return {
        "image_set": image_set,
        "c1_case": c1_case,
        "flash_b": flash_b,
        "pre": pre,
    }


def fake_startup_capture(
    bindings,
    *,
    output_dir,
    repo_root,
    serial_factory,
    baud,
    duration_s,
    status_timeout_s,
):
    del bindings, serial_factory, baud, status_timeout_s
    logs = {}
    for role in ("leader", "follower"):
        path = output_dir / f"c2_startup_{role}.log"
        path.write_text(f"{role} cold startup\n")
        logs[role] = f2_capture._evidence_record(path, repo_root)
    return {
        "status": "PASS",
        "duration_s": duration_s,
        "checks": {
            "leader_advertising_ready": True,
            "follower_scan_started": True,
            "follower_uuid_discovered": True,
            "leader_link_ready_snapshot": True,
            "follower_link_ready_snapshot": True,
        },
        "sync_status": {"roles": {}},
        "logs": logs,
    }


def controlled_reboot(tmp_path: Path, bus: FakeSerialBus, **overrides):
    evidence = reboot_evidence(tmp_path)
    arguments = {
        "output_dir": tmp_path,
        "host_execution_sha": HOST_SHA,
        "firmware_source_sha": FIRMWARE_SHA,
        "image_set_manifest": evidence["image_set"],
        "c1_ports_manifest": tmp_path / "ports_C1.json",
        "c1_identity": c1_identity(),
        "c1_case_manifest": evidence["c1_case"],
        "case_b_flash_manifest": evidence["flash_b"],
        "c2_pre_attestation": evidence["pre"],
        "port_provider": bus.ports,
        "serial_factory": bus.open,
        "reboot_settle_s": 0.0,
        "repo_root_override": tmp_path,
        "host_head_reader": lambda _root: HOST_SHA,
        "image_set_loader": lambda _path, repo_root: {
            "firmware_source_sha": FIRMWARE_SHA
        },
        "startup_capture": fake_startup_capture,
    }
    arguments.update(overrides)
    return f2_reboot.controlled_c2_reboot(**arguments)


def test_resolve_bindings_rebinds_by_usb_serial_then_verifies_chip() -> None:
    bus = FakeSerialBus(
        before={"leader": "/dev/cu.new-leader", "follower": "/dev/cu.new-follower"}
    )

    resolved = f2_ports.resolve_bindings(
        port_provider=bus.ports,
        serial_factory=bus.open,
    )

    assert resolved == bindings("/dev/cu.new-leader", "/dev/cu.new-follower")
    assert bus.writes == [
        ("/dev/cu.new-leader", ":chip_id"),
        ("/dev/cu.new-follower", ":chip_id"),
    ]
    assert [port for port, _baud in bus.opens] == [
        "/dev/cu.new-leader",
        "/dev/cu.new-follower",
    ]


def test_c2_cold_start_checks_require_adv_scan_uuid_and_both_link_snapshots():
    leader = (
        "[k1_sync_diag] adv scan_rsp_configured=1 uuid=1 "
        "name=1 start=1 active=1\n"
    )
    follower = (
        "[k1_sync_diag] scan_start ok=1 active=1\n"
        "[k1_sync_diag] discovered uuid=1 name_match=0 scan_stop=1\n"
    )
    checks = f2_reboot._cold_start_checks(
        leader,
        follower,
        {
            "leader": {"linked": True},
            "follower": {"linked": True},
        },
    )
    assert all(checks.values())

    checks = f2_reboot._cold_start_checks(
        leader,
        follower.replace("uuid=1", "uuid=0"),
        {
            "leader": {"linked": True},
            "follower": {"linked": True},
        },
    )
    assert checks["follower_uuid_discovered"] is False


def test_resolve_bindings_rejects_duplicate_usb_serial_before_serial_open() -> None:
    bus = FakeSerialBus(
        before={"leader": "/dev/cu.leader", "follower": "/dev/cu.follower"}
    )

    def duplicate_ports() -> list[ListedPort]:
        return [
            ListedPort("/dev/cu.leader-a", LEADER_USB),
            ListedPort("/dev/cu.leader-b", LEADER_USB),
            ListedPort("/dev/cu.follower", FOLLOWER_USB),
        ]

    with pytest.raises(f2_ports.F2PortsError, match="multiple ports"):
        f2_ports.resolve_bindings(
            port_provider=duplicate_ports,
            serial_factory=bus.open,
        )

    assert bus.opens == []


def test_resolve_bindings_rejects_chip_mismatch() -> None:
    bus = FakeSerialBus(
        before={"leader": "/dev/cu.leader", "follower": "/dev/cu.follower"}
    )
    bus.chip_by_port["/dev/cu.leader"] = FOLLOWER_CHIP

    with pytest.raises(f2_ports.F2PortsError, match="leader chip mismatch"):
        f2_ports.resolve_bindings(
            port_provider=bus.ports,
            serial_factory=bus.open,
        )


def test_ports_manifests_hash_chain_a_to_b_to_c1_and_allow_port_drift(
    tmp_path: Path,
) -> None:
    pre_a = write_ports(
        "pre_A",
        tmp_path,
        bindings("/dev/cu.pre-leader", "/dev/cu.pre-follower"),
    )
    a = write_ports(
        "A", tmp_path, bindings("/dev/cu.a-leader", "/dev/cu.a-follower")
        , prior_manifest=tmp_path / "ports_pre_A.json"
    )
    b = write_ports(
        "B",
        tmp_path,
        bindings("/dev/cu.b-leader", "/dev/cu.b-follower"),
        prior_manifest=tmp_path / "ports_A.json",
    )
    c1 = write_ports(
        "C1",
        tmp_path,
        bindings("/dev/cu.c1-leader", "/dev/cu.c1-follower"),
        prior_manifest=tmp_path / "ports_B.json",
    )

    assert pre_a["previous_manifest_sha256"] is None
    assert a["previous_manifest_sha256"] == f2_ports.sha256_file(
        tmp_path / "ports_pre_A.json"
    )
    assert b["previous_manifest_sha256"] == f2_ports.sha256_file(
        tmp_path / "ports_A.json"
    )
    assert c1["previous_manifest_sha256"] == f2_ports.sha256_file(
        tmp_path / "ports_B.json"
    )
    assert f2_ports.validate_ports_manifest(
        tmp_path / "ports_C1.json", expected_stage="C1"
    ) == c1


def test_ports_manifest_rejects_wrong_predecessor_tampering_and_overwrite(
    tmp_path: Path,
) -> None:
    a_path = tmp_path / "ports_A.json"
    b_path = tmp_path / "ports_B.json"
    write_ports(
        "pre_A", tmp_path, bindings("/dev/pre-l", "/dev/pre-f")
    )
    write_ports(
        "A",
        tmp_path,
        bindings("/dev/a-l", "/dev/a-f"),
        prior_manifest=tmp_path / "ports_pre_A.json",
    )

    with pytest.raises(f2_ports.F2PortsError, match="requires ports_B.json"):
        write_ports(
            "C1",
            tmp_path,
            bindings("/dev/c-l", "/dev/c-f"),
            prior_manifest=a_path,
        )

    original_a = a_path.read_bytes()
    write_ports(
        "B",
        tmp_path,
        bindings("/dev/b-l", "/dev/b-f"),
        prior_manifest=a_path,
    )

    with pytest.raises(f2_ports.F2PortsError, match="already exists"):
        write_ports(
            "A",
            tmp_path,
            bindings("/dev/other-l", "/dev/other-f"),
            prior_manifest=tmp_path / "ports_pre_A.json",
        )
    assert a_path.read_bytes() == original_a

    a_payload = json.loads(a_path.read_text(encoding="utf-8"))
    a_payload["leader"]["port"] = "/dev/tampered"
    a_path.write_text(json.dumps(a_payload), encoding="utf-8")
    with pytest.raises(f2_ports.F2PortsError, match="predecessor hash mismatch"):
        f2_ports.validate_ports_manifest(b_path, expected_stage="B")


def test_controlled_c2_reboot_rebinds_and_proves_same_image_new_nonce(
    tmp_path: Path,
) -> None:
    c1_ports = tmp_path / "ports_C1.json"
    write_ports(
        "pre_A", tmp_path, bindings("/dev/pre-l", "/dev/pre-f")
    )
    write_ports(
        "A", tmp_path, bindings("/dev/a-l", "/dev/a-f")
        , prior_manifest=tmp_path / "ports_pre_A.json"
    )
    write_ports(
        "B",
        tmp_path,
        bindings("/dev/b-l", "/dev/b-f"),
        prior_manifest=tmp_path / "ports_A.json",
    )
    write_ports(
        "C1",
        tmp_path,
        bindings("/dev/old-leader", "/dev/old-follower"),
        prior_manifest=tmp_path / "ports_B.json",
    )
    bus = FakeSerialBus(
        before={"leader": "/dev/old-leader", "follower": "/dev/old-follower"},
        after={"leader": "/dev/new-leader", "follower": "/dev/new-follower"},
        post_identity=post_identity(),
    )

    result = controlled_reboot(
        tmp_path, bus, c1_ports_manifest=c1_ports
    )

    assert [
        item for item in bus.writes if item[1] == ":reset"
    ] == [
        ("/dev/old-leader", ":reset"),
        ("/dev/old-follower", ":reset"),
    ]
    assert result["status"] == "PASS"
    assert result["reset_acknowledgements"]["leader"]["ack"] == "SBOK"
    assert result["roles"]["leader"]["after"]["app_elf_sha256"] == "a" * 64
    assert result["roles"]["leader"]["after"]["boot_nonce"] == "aaaaaaaaaaaaaaaa"
    assert result["cold_start_capture"]["status"] == "PASS"
    assert all(result["cold_start_capture"]["checks"].values())
    c2_ports = f2_ports.validate_ports_manifest(
        tmp_path / "ports_C2.json", expected_stage="C2"
    )
    assert c2_ports["leader"] == bindings(
        "/dev/new-leader", "/dev/new-follower"
    )["leader"]
    assert c2_ports["follower"] == bindings(
        "/dev/new-leader", "/dev/new-follower"
    )["follower"]
    assert c2_ports["previous_manifest_sha256"] == f2_ports.sha256_file(
        tmp_path / "ports_C1.json"
    )
    assert (tmp_path / "reboot_C2.json").is_file()


@pytest.mark.parametrize("failure", ["same_nonce", "changed_image"])
def test_controlled_c2_reboot_fails_closed_on_runtime_or_image_discontinuity(
    tmp_path: Path,
    failure: str,
) -> None:
    write_ports(
        "pre_A", tmp_path, bindings("/dev/pre-l", "/dev/pre-f")
    )
    write_ports(
        "A", tmp_path, bindings("/dev/a-l", "/dev/a-f")
        , prior_manifest=tmp_path / "ports_pre_A.json"
    )
    write_ports(
        "B",
        tmp_path,
        bindings("/dev/b-l", "/dev/b-f"),
        prior_manifest=tmp_path / "ports_A.json",
    )
    write_ports(
        "C1",
        tmp_path,
        bindings("/dev/old-leader", "/dev/old-follower"),
        prior_manifest=tmp_path / "ports_B.json",
    )
    after = post_identity()
    if failure == "same_nonce":
        after[LEADER_CHIP]["boot_nonce"] = "1111111111111111"
    else:
        after[LEADER_CHIP]["app_elf_sha256"] = "c" * 64
    bus = FakeSerialBus(
        before={"leader": "/dev/old-leader", "follower": "/dev/old-follower"},
        after={"leader": "/dev/new-leader", "follower": "/dev/new-follower"},
        post_identity=after,
    )

    with pytest.raises(f2_reboot.F2RebootError):
        controlled_reboot(tmp_path, bus)

    assert not (tmp_path / "ports_C2.json").exists()
    assert not (tmp_path / "reboot_C2.json").exists()


def test_controlled_c2_reboot_requires_cold_start_establishment_capture(
    tmp_path: Path,
) -> None:
    write_ports(
        "pre_A", tmp_path, bindings("/dev/pre-l", "/dev/pre-f")
    )
    write_ports(
        "A",
        tmp_path,
        bindings("/dev/a-l", "/dev/a-f"),
        prior_manifest=tmp_path / "ports_pre_A.json",
    )
    write_ports(
        "B",
        tmp_path,
        bindings("/dev/b-l", "/dev/b-f"),
        prior_manifest=tmp_path / "ports_A.json",
    )
    write_ports(
        "C1",
        tmp_path,
        bindings("/dev/old-leader", "/dev/old-follower"),
        prior_manifest=tmp_path / "ports_B.json",
    )
    bus = FakeSerialBus(
        before={"leader": "/dev/old-leader", "follower": "/dev/old-follower"},
        after={"leader": "/dev/new-leader", "follower": "/dev/new-follower"},
        post_identity=post_identity(),
    )

    def blocked_startup(*_args, **_kwargs):
        raise f2_reboot.F2RebootError(
            "C2 cold-start establishment evidence failed"
        )

    with pytest.raises(
        f2_reboot.F2RebootError, match="cold-start establishment"
    ):
        controlled_reboot(
            tmp_path, bus, startup_capture=blocked_startup
        )
    assert not (tmp_path / "ports_C2.json").exists()
    assert not (tmp_path / "reboot_C2.json").exists()


def test_reboot_cli_routes_raw_run_root_to_tracked_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    raw_root = tmp_path / "_scratch" / "dual_sync_f2_abc_route"
    tracked_root = tmp_path / "tracked" / "route"
    identity = tmp_path / "c1-identity.json"
    identity.write_text("{}\n", encoding="utf-8")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        f2_capture,
        "_run_tracked_root",
        lambda _repo_root, observed: (
            tracked_root
            if Path(observed) == raw_root
            else pytest.fail("unexpected run root")
        ),
    )

    def fake_controlled(**kwargs):
        captured.update(kwargs)
        return {"status": "PASS"}

    monkeypatch.setattr(
        f2_reboot, "controlled_c2_reboot", fake_controlled
    )
    result = f2_reboot.main(
        [
            "--host-execution-sha",
            HOST_SHA,
            "--firmware-source-sha",
            FIRMWARE_SHA,
            "--image-set-manifest",
            str(tmp_path / "image-set.json"),
            "--ports-manifest",
            str(tracked_root / "runtime" / "ports_C1.json"),
            "--run-root",
            str(raw_root),
            "--c1-identity",
            str(identity),
            "--c1-case-manifest",
            str(tmp_path / "case_C1.json"),
            "--case-b-flash-manifest",
            str(tmp_path / "flash_B.json"),
            "--c2-pre-attestation",
            str(tmp_path / "case_C2_pre.json"),
        ]
    )
    assert result == 0
    assert captured["output_dir"] == tracked_root / "runtime"
    assert captured["run_root"] == raw_root
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_ports_cli_routes_raw_run_root_to_tracked_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    raw_root = tmp_path / "_scratch" / "dual_sync_f2_abc_route"
    tracked_root = tmp_path / "tracked" / "route"
    captured: dict[str, object] = {}

    monkeypatch.setattr(f2_capture, "_git_head", lambda _root: HOST_SHA)
    monkeypatch.setattr(
        f2_capture, "_require_run_open", lambda _root, _run: None
    )
    monkeypatch.setattr(
        f2_capture, "_require_clean_host_inputs", lambda _root: None
    )
    monkeypatch.setattr(
        f2_capture,
        "_run_tracked_root",
        lambda _repo_root, observed: (
            tracked_root
            if Path(observed) == raw_root
            else pytest.fail("unexpected run root")
        ),
    )
    monkeypatch.setattr(
        f2_image_set,
        "load",
        lambda *_args, **_kwargs: {
            "firmware_source_sha": FIRMWARE_SHA
        },
    )

    def fake_resolve(stage, output_dir, **kwargs):
        captured.update(
            {"stage": stage, "output_dir": output_dir, **kwargs}
        )
        return {"stage": stage}

    monkeypatch.setattr(
        f2_ports, "resolve_and_write_ports_manifest", fake_resolve
    )
    result = f2_ports.main(
        [
            "--stage",
            "C1",
            "--host-execution-sha",
            HOST_SHA,
            "--firmware-source-sha",
            FIRMWARE_SHA,
            "--image-set-manifest",
            str(tmp_path / "image-set.json"),
            "--ports-manifest",
            str(tracked_root / "runtime" / "ports_B.json"),
            "--run-root",
            str(raw_root),
        ]
    )
    assert result == 0
    assert captured["stage"] == "C1"
    assert captured["output_dir"] == tracked_root / "runtime"
    assert json.loads(capsys.readouterr().out)["stage"] == "C1"


def test_production_c2_failure_closes_run_as_blocked(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "tracked" / "runtime"
    runtime.mkdir(parents=True)

    @f2_reboot._close_run_on_c2_failure
    def fail(**_kwargs):
        raise f2_reboot.F2RebootError("partial controlled reboot")

    with pytest.raises(
        f2_reboot.F2RebootError, match="partial controlled reboot"
    ):
        fail(
            output_dir=runtime,
            run_root=tmp_path / "_scratch" / "dual_sync_f2_abc_fail",
            host_execution_sha=HOST_SHA,
            firmware_source_sha=FIRMWARE_SHA,
        )

    marker = json.loads(
        (runtime.parent / "RUN_BLOCKED.json").read_text(encoding="utf-8")
    )
    assert marker["status"] == "BLOCKED"
    assert marker["reason"] == "c2_controller_failed"
    assert marker["f3_authorised"] is False


def test_controlled_c2_reboot_refuses_existing_output_before_reset(
    tmp_path: Path,
) -> None:
    write_ports(
        "pre_A", tmp_path, bindings("/dev/pre-l", "/dev/pre-f")
    )
    write_ports(
        "A", tmp_path, bindings("/dev/a-l", "/dev/a-f")
        , prior_manifest=tmp_path / "ports_pre_A.json"
    )
    write_ports(
        "B",
        tmp_path,
        bindings("/dev/b-l", "/dev/b-f"),
        prior_manifest=tmp_path / "ports_A.json",
    )
    write_ports(
        "C1",
        tmp_path,
        bindings("/dev/old-leader", "/dev/old-follower"),
        prior_manifest=tmp_path / "ports_B.json",
    )
    (tmp_path / "ports_C2.json").write_text("occupied", encoding="utf-8")
    bus = FakeSerialBus(
        before={"leader": "/dev/old-leader", "follower": "/dev/old-follower"},
        after={"leader": "/dev/new-leader", "follower": "/dev/new-follower"},
        post_identity=post_identity(),
    )

    with pytest.raises(f2_reboot.F2RebootError, match="already exists"):
        controlled_reboot(tmp_path, bus)

    assert bus.writes == []


def test_controlled_c2_reboot_rejects_stale_c1_boot_before_reset(
    tmp_path: Path,
) -> None:
    write_ports(
        "pre_A", tmp_path, bindings("/dev/pre-l", "/dev/pre-f")
    )
    write_ports(
        "A",
        tmp_path,
        bindings("/dev/a-l", "/dev/a-f"),
        prior_manifest=tmp_path / "ports_pre_A.json",
    )
    write_ports(
        "B",
        tmp_path,
        bindings("/dev/b-l", "/dev/b-f"),
        prior_manifest=tmp_path / "ports_A.json",
    )
    write_ports(
        "C1",
        tmp_path,
        bindings("/dev/old-leader", "/dev/old-follower"),
        prior_manifest=tmp_path / "ports_B.json",
    )
    stale = {
        LEADER_CHIP: {
            "app_elf_sha256": "a" * 64,
            "boot_nonce": "cccccccccccccccc",
            "uptime_ms": 500,
            "reset_reason": 3,
        },
        FOLLOWER_CHIP: {
            "app_elf_sha256": "b" * 64,
            "boot_nonce": "2222222222222222",
            "uptime_ms": 79_500,
            "reset_reason": 1,
        },
    }
    bus = FakeSerialBus(
        before={"leader": "/dev/old-leader", "follower": "/dev/old-follower"},
        after={"leader": "/dev/new-leader", "follower": "/dev/new-follower"},
        pre_identity=stale,
        post_identity=post_identity(),
    )

    with pytest.raises(f2_reboot.F2RebootError, match="not the captured C1 boot"):
        controlled_reboot(tmp_path, bus)

    assert all(command != ":reset" for _port, command in bus.writes)


def test_run_creation_rejects_blocked_image_before_device_resolution(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(f2_capture, "_git_head", lambda _root: HOST_SHA)
    monkeypatch.setattr(
        f2_capture, "_require_clean_host_inputs", lambda _root: None
    )
    monkeypatch.setattr(
        f2_image_set,
        "load",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            f2_image_set.F2ImageSetError("reviewed image set is BLOCKED")
        ),
    )
    args = SimpleNamespace(
        host_execution_sha=HOST_SHA,
        firmware_source_sha=FIRMWARE_SHA,
        image_set_manifest=tmp_path / "image-set.json",
        run_root=tmp_path
        / "_scratch"
        / "dual_sync_f2_abc_blocked",
    )
    with pytest.raises(f2_run.F2RunError, match="image set is not ready"):
        f2_run.create_run(
            args,
            repo_root_override=tmp_path,
            bindings_resolver=lambda: pytest.fail(
                "device resolution before image-set PASS"
            ),
        )
    assert not args.run_root.exists()


def test_run_creation_rejects_conflated_host_and_firmware_identity(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(f2_capture, "_git_head", lambda _root: HOST_SHA)
    monkeypatch.setattr(
        f2_capture, "_require_clean_host_inputs", lambda _root: None
    )
    args = SimpleNamespace(
        host_execution_sha=HOST_SHA,
        firmware_source_sha=HOST_SHA,
        image_set_manifest=tmp_path / "image-set.json",
        run_root=tmp_path
        / "_scratch"
        / "dual_sync_f2_abc_conflated",
    )
    with pytest.raises(f2_run.F2RunError, match="must remain distinct"):
        f2_run.create_run(
            args,
            repo_root_override=tmp_path,
            bindings_resolver=lambda: pytest.fail(
                "device resolution after conflated identity"
            ),
        )
    assert not args.run_root.exists()


def test_host_head_drift_closes_started_run_and_cannot_be_reopened(
    tmp_path: Path,
) -> None:
    run_id = "host_drift"
    run_root = (
        tmp_path / "_scratch" / f"dual_sync_f2_abc_{run_id}"
    )
    run_root.mkdir(parents=True)
    tracked_root = tmp_path / f2_capture.TRACKED_F2_REL / run_id
    tracked_root.mkdir(parents=True)

    marker = f2_capture._close_run_for_host_drift(
        tmp_path,
        run_root,
        expected_host_sha=HOST_SHA,
        observed_host_sha="c" * 40,
    )
    assert marker == tracked_root / "RUN_BLOCKED.json"
    payload = json.loads(marker.read_text())
    assert payload["status"] == "BLOCKED"
    assert payload["f3_authorised"] is False
    assert payload["expected_host_execution_sha"] == HOST_SHA
    assert payload["observed_host_execution_sha"] == "c" * 40

    with pytest.raises(
        f2_capture.F2ContractError, match="already closed as BLOCKED"
    ):
        f2_capture._require_run_open(tmp_path, run_root)
    with pytest.raises(
        f2_capture.F2ContractError, match="refusing to overwrite"
    ):
        f2_capture._close_run_for_host_drift(
            tmp_path,
            run_root,
            expected_host_sha=HOST_SHA,
            observed_host_sha="d" * 40,
        )
