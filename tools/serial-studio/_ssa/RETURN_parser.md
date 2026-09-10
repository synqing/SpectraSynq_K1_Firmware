STATUS: VERIFIED (host parse contract; live Serial Studio not in scope)
CLAIM: JS parser returns a 21-slot vector with record_kind + update_mask so held last-known dashboard values cannot be mistaken for new measurements, without inventing device fields.
EVIDENCE: parsers/k1_ap_parser.js var SCHEMA=1.1 slot18=host_parse_seq slot20=kind 1=AP 2=EVENT_STATUS 3=SYSTEM_FPS 4=LED_FPS 5=BUILD(VERSION:) slot21=mask; unknown/malformed/APCAP=[]; no POLL/firmware_sha/run_id; TELEMETRY_SCHEMA.md v1.1 provenance+virtual transforms; node vm fixtures PASS.
COMMAND: none (orchestrator dryRun via Serial Studio API)
METHOD_RISK: datasets 20-21 and host_parse_seq title rename are orchestrator-owned; wrong index mapping would shift Historian columns.
NEXT: orchestrator injects parser, adds record_kind/update_mask datasets, retitles slot 18; scorer must filter by update_mask bits.
