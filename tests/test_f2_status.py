import json

import pytest

from scripts.dual_sync_probe import f2_status


def _pre_payload(case):
    contract = {
        "C1": ("late_join", "off"),
        "C2": ("controlled_cold_coexistence", "powered_and_advertising"),
    }[case]
    payload = {
        "schema_version": 1,
        "kind": "f2_pre_attestation",
        "case": case,
        "scenario": contract[0],
        "captain": "Captain",
        "created_at_utc": "2026-07-28T01:00:00Z",
        "gpio_wiring_confirmed": True,
        "common_ground_confirmed": True,
        "logic_voltage": "3V3",
        "k718_state": contract[1],
        "four_detent_commitment": True,
    }
    if case == "C2":
        payload["controlled_reboot_authorised"] = True
    return payload


def _feedback_payload(case, pre_hash, physical_status):
    observations = {
        "PASS": (True, True),
        "FAIL": (False, True),
        "UNMEASURED": (None, None),
    }[physical_status]
    return {
        "schema_version": 1,
        "kind": "f2_post_run_feedback",
        "case": case,
        "captain": "Captain",
        "created_at_utc": "2026-07-28T01:02:00Z",
        "pre_attestation_sha256": pre_hash,
        "k1_mode_changed": observations[0],
        "k718_confirmation_displayed": observations[1],
        "status": physical_status,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _all_evidence(root):
    records = {}
    for label in f2_status.REQUIRED_EVIDENCE:
        path = root / "evidence" / f"{label}.json"
        _write_json(path, {"label": label})
        records[label] = f2_status.evidence_record(path, root, label)
    return records


def _all_software(value=f2_status.PASS):
    return {case: value for case in f2_status.CASES}


def _physical(c1=f2_status.PASS, c2=f2_status.PASS):
    return {"C1": c1, "C2": c2}


def test_c1_attestation_and_feedback_are_separate_and_hash_bound(tmp_path):
    pre_path = tmp_path / "attestations" / "pre_C1.json"
    _write_json(pre_path, _pre_payload("C1"))
    pre = f2_status.validate_pre_attestation(pre_path, "C1", tmp_path)

    feedback_path = tmp_path / "feedback" / "post_C1.json"
    _write_json(
        feedback_path,
        _feedback_payload("C1", pre["evidence"]["sha256"], "PASS"),
    )
    feedback = f2_status.validate_post_feedback(
        feedback_path, "C1", pre, tmp_path
    )

    assert feedback["physical_status"] == f2_status.PASS
    assert pre["evidence"]["path"] != feedback["evidence"]["path"]
    assert pre["evidence"]["sha256"] != feedback["evidence"]["sha256"]


def test_pre_attestation_rejects_feedback_fields_and_wrong_case_state(tmp_path):
    path = tmp_path / "pre_C1.json"
    payload = _pre_payload("C1")
    payload["status"] = "PASS"
    _write_json(path, payload)
    with pytest.raises(f2_status.F2StatusError, match="extra=.*status"):
        f2_status.validate_pre_attestation(path, "C1", tmp_path)

    path.unlink()
    payload = _pre_payload("C1")
    payload["k718_state"] = "powered_and_advertising"
    _write_json(path, payload)
    with pytest.raises(
        f2_status.F2StatusError, match="k718_state='off'"
    ):
        f2_status.validate_pre_attestation(path, "C1", tmp_path)


def test_c2_feedback_can_be_unmeasured_but_must_bind_pre_hash(tmp_path):
    pre_path = tmp_path / "pre_C2.json"
    _write_json(pre_path, _pre_payload("C2"))
    pre = f2_status.validate_pre_attestation(pre_path, "C2", tmp_path)

    feedback_path = tmp_path / "post_C2.json"
    _write_json(
        feedback_path,
        _feedback_payload("C2", "0" * 64, "UNMEASURED"),
    )
    with pytest.raises(
        f2_status.F2StatusError, match="pre_attestation_sha256"
    ):
        f2_status.validate_post_feedback(
            feedback_path, "C2", pre, tmp_path
        )

    feedback_path.unlink()
    _write_json(
        feedback_path,
        _feedback_payload(
            "C2", pre["evidence"]["sha256"], "UNMEASURED"
        ),
    )
    result = f2_status.validate_post_feedback(
        feedback_path, "C2", pre, tmp_path
    )
    assert result["physical_status"] == f2_status.UNMEASURED


def test_feedback_status_cannot_contradict_physical_observations(tmp_path):
    pre_path = tmp_path / "pre_C1.json"
    _write_json(pre_path, _pre_payload("C1"))
    pre = f2_status.validate_pre_attestation(pre_path, "C1", tmp_path)
    feedback = _feedback_payload(
        "C1", pre["evidence"]["sha256"], "PASS"
    )
    feedback["k718_confirmation_displayed"] = False
    feedback_path = tmp_path / "feedback_C1.json"
    _write_json(feedback_path, feedback)
    with pytest.raises(
        f2_status.F2StatusError,
        match="both physical observations true",
    ):
        f2_status.validate_post_feedback(
            feedback_path, "C1", pre, tmp_path
        )


def test_immutable_json_refuses_overwrite(tmp_path):
    path = tmp_path / "attestations" / "pre_C1.json"
    first = f2_status.write_immutable_json(
        path, _pre_payload("C1"), tmp_path
    )
    with pytest.raises(f2_status.F2StatusError, match="refusing to overwrite"):
        f2_status.write_immutable_json(
            path, _pre_payload("C1"), tmp_path
        )
    assert f2_status.evidence_record(path, tmp_path, "pre") == first


def test_collection_complete_allows_physical_unmeasured(tmp_path):
    result = f2_status.finalise_f2_status(
        software_status=_all_software(),
        physical_status=_physical(c2=f2_status.UNMEASURED),
        evidence=_all_evidence(tmp_path),
        evidence_root=tmp_path,
    )
    assert result["software_status"] == f2_status.PASS
    assert result["physical_status"] == f2_status.UNMEASURED
    assert result["f2_evidence_collection"] == f2_status.COMPLETE
    assert result["f2_acceptance"] == f2_status.PENDING
    assert result["f3_authorised"] is False
    assert result["case_A_software_status"] == f2_status.PASS
    assert result["case_B_software_status"] == f2_status.PASS
    assert result["case_C1_software_status"] == f2_status.PASS
    assert result["case_C2_software_status"] == f2_status.PASS
    assert result["case_C1_physical_feedback"] == f2_status.PASS
    assert (
        result["case_C2_physical_feedback"]
        == f2_status.UNMEASURED
    )


def test_collection_is_incomplete_on_blocked_case_or_missing_feedback(
    tmp_path,
):
    software = _all_software()
    software["C2"] = f2_status.BLOCKED
    evidence = _all_evidence(tmp_path)
    del evidence["c2_post_feedback"]
    result = f2_status.finalise_f2_status(
        software_status=software,
        physical_status=_physical(c2=f2_status.UNMEASURED),
        evidence=evidence,
        evidence_root=tmp_path,
    )
    assert result["software_status"] == f2_status.BLOCKED
    assert result["f2_evidence_collection"] == f2_status.INCOMPLETE
    assert result["missing_evidence"] == ["c2_post_feedback"]
    assert result["f2_acceptance"] == f2_status.PENDING


def test_any_physical_failure_rejects_without_authorising_f3(tmp_path):
    result = f2_status.finalise_f2_status(
        software_status=_all_software(),
        physical_status=_physical(c1=f2_status.FAIL),
        evidence=_all_evidence(tmp_path),
        evidence_root=tmp_path,
    )
    assert result["f2_evidence_collection"] == f2_status.COMPLETE
    assert result["physical_status"] == f2_status.FAIL
    assert result["f2_acceptance"] == f2_status.REJECTED
    assert result["f3_authorised"] is False


def test_stop_is_hashed_non_overwriting_and_decision_is_separate(tmp_path):
    evidence = _all_evidence(tmp_path)
    pending = f2_status.finalise_f2_status(
        software_status=_all_software(),
        physical_status=_physical(),
        evidence=evidence,
        evidence_root=tmp_path,
    )
    stop_path = tmp_path / "CAPTAIN_STOP.md"
    stop = f2_status.write_captain_stop(
        stop_path, pending, evidence, tmp_path
    )
    text = stop_path.read_text()
    assert "f3_authorised: false" in text
    assert "A separate, immutable Captain decision file is required." in text
    for record in evidence.values():
        assert record["sha256"] in text
    with pytest.raises(f2_status.F2StatusError, match="refusing to overwrite"):
        f2_status.write_captain_stop(
            stop_path, pending, evidence, tmp_path
        )

    decision_path = tmp_path / "captain_decision.json"
    decision_payload = {
        "schema_version": 1,
        "kind": "f2_captain_decision",
        "decided_by": "Captain",
        "captain_stop_sha256": stop["sha256"],
        "decision": "PASS",
    }
    f2_status.write_immutable_json(
        decision_path, decision_payload, tmp_path
    )
    decision = f2_status.validate_captain_decision(
        decision_path, stop["sha256"], tmp_path
    )
    evidence["captain_stop"] = stop
    accepted = f2_status.finalise_f2_status(
        software_status=_all_software(),
        physical_status=_physical(),
        evidence=evidence,
        evidence_root=tmp_path,
        captain_decision=decision,
    )
    assert accepted["f2_acceptance"] == f2_status.PASS
    assert accepted["f3_authorised"] is False
    with pytest.raises(
        f2_status.F2StatusError, match="cannot embed Captain acceptance"
    ):
        f2_status.render_captain_stop(accepted, evidence)


def test_captain_pass_cannot_override_incomplete_collection(tmp_path):
    stop_path = tmp_path / "CAPTAIN_STOP.md"
    stop_path.write_text("STOP")
    stop = f2_status.evidence_record(stop_path, tmp_path, "Captain STOP")
    path = tmp_path / "decision.json"
    _write_json(
        path,
        {
            "schema_version": 1,
            "kind": "f2_captain_decision",
            "decided_by": "Captain",
            "captain_stop_sha256": stop["sha256"],
            "decision": "PASS",
        },
    )
    decision = f2_status.validate_captain_decision(
        path, stop["sha256"], tmp_path
    )
    software = _all_software()
    software["B"] = f2_status.FAIL
    evidence = _all_evidence(tmp_path)
    evidence["captain_stop"] = stop
    result = f2_status.finalise_f2_status(
        software_status=software,
        physical_status=_physical(),
        evidence=evidence,
        evidence_root=tmp_path,
        captain_decision=decision,
    )
    assert result["f2_evidence_collection"] == f2_status.INCOMPLETE
    assert result["f2_acceptance"] == f2_status.PENDING
    assert result["f3_authorised"] is False


def test_evidence_and_decisions_reject_symlinks_and_stop_hash_drift(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "pre_C1.json"
    _write_json(target, _pre_payload("C1"))
    link_root = tmp_path / "run"
    link_root.mkdir()
    (link_root / "pre_C1.json").symlink_to(target)
    with pytest.raises(f2_status.F2StatusError, match="symlink"):
        f2_status.validate_pre_attestation(
            link_root / "pre_C1.json", "C1", link_root
        )

    decision_path = tmp_path / "decision.json"
    _write_json(
        decision_path,
        {
            "schema_version": 1,
            "kind": "f2_captain_decision",
            "decided_by": "Captain",
            "captain_stop_sha256": "d" * 64,
            "decision": "PASS",
        },
    )
    with pytest.raises(
        f2_status.F2StatusError, match="captain_stop_sha256"
    ):
        f2_status.validate_captain_decision(
            decision_path, "e" * 64, tmp_path
        )


def test_forged_or_mutated_evidence_cannot_make_collection_complete(tmp_path):
    evidence = _all_evidence(tmp_path)
    record = evidence["case_C2_manifest"]
    (tmp_path / record["path"]).write_text("mutated")
    result = f2_status.finalise_f2_status(
        software_status=_all_software(),
        physical_status=_physical(),
        evidence=evidence,
        evidence_root=tmp_path,
    )
    assert result["f2_evidence_collection"] == f2_status.INCOMPLETE
    assert result["missing_evidence"] == ["case_C2_manifest"]


def test_stop_writer_rejects_forged_complete_status(tmp_path):
    evidence = _all_evidence(tmp_path)
    status = f2_status.finalise_f2_status(
        software_status=_all_software(),
        physical_status=_physical(),
        evidence=evidence,
        evidence_root=tmp_path,
    )
    del evidence["case_C2_manifest"]
    with pytest.raises(f2_status.F2StatusError, match="does not match"):
        f2_status.write_captain_stop(
            tmp_path / "CAPTAIN_STOP.md", status, evidence, tmp_path
        )


def test_finaliser_cli_requires_all_split_authorities_and_feedback():
    parser = f2_status._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--host-execution-sha",
                "b" * 40,
                "--firmware-source-sha",
                "a" * 40,
            ]
        )


def test_stop_inputs_directly_rehash_run_authority_and_every_image(tmp_path):
    authority_path = tmp_path / "authority.md"
    authority_path.write_text("authority")
    image_manifest = tmp_path / "image-set.json"
    image_manifest.write_text("{}")
    ports_pre = tmp_path / "ports_pre_A.json"
    ports_pre.write_text("{}")
    run_manifest = tmp_path / "RUN_MANIFEST.json"
    authority_record = f2_status.evidence_record(
        authority_path, tmp_path, "authority"
    )
    _write_json(
        run_manifest,
        {
            "status": "OPEN",
            "host_execution_sha": "b" * 40,
            "firmware_source_sha": "a" * 40,
            "f3_authorised": False,
            "authority": {
                authority_record["path"]: {
                    "sha256": authority_record["sha256"],
                    "size": authority_record["size"],
                }
            },
            "image_set_manifest": f2_status.evidence_record(
                image_manifest, tmp_path, "image manifest"
            ),
            "ports_pre_A_manifest": f2_status.evidence_record(
                ports_pre, tmp_path, "ports pre A"
            ),
        },
    )
    authority = f2_status._run_authority_evidence(
        run_manifest,
        repo_root=tmp_path,
        host_execution_sha="b" * 40,
        firmware_source_sha="a" * 40,
        image_set_manifest=image_manifest,
    )
    assert set(authority) == {
        "run_manifest",
        "authority:authority.md",
    }

    partition = tmp_path / "partitions.bin"
    partition.write_bytes(b"partition")
    images = {}
    for env in ("leader_sync_only", "leader", "follower"):
        binary = tmp_path / f"{env}.bin"
        elf = tmp_path / f"{env}.elf"
        binary.write_bytes(env.encode())
        elf.write_bytes((env + "-elf").encode())
        images[env] = {"bin_path": binary, "elf_path": elf}
    frozen = f2_status._image_artifact_evidence(
        {
            "partition_table": {"path": partition},
            "images": images,
        },
        repo_root=tmp_path,
    )
    assert set(frozen) == {
        "image:partition_table",
        "image:leader_sync_only:bin",
        "image:leader_sync_only:elf",
        "image:leader:bin",
        "image:leader:elf",
        "image:follower:bin",
        "image:follower:elf",
    }

    authority_path.write_text("mutated")
    with pytest.raises(f2_status.F2StatusError, match="changed after creation"):
        f2_status._run_authority_evidence(
            run_manifest,
            repo_root=tmp_path,
            host_execution_sha="b" * 40,
            firmware_source_sha="a" * 40,
            image_set_manifest=image_manifest,
        )
