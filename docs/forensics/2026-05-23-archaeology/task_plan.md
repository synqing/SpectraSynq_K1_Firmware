# SB Waveform/Bloom + S2-S3 Forensic Reconstruction

## Goal

Create a detailed forensic archaeology HTML reconstructing every known Waveform/Bloom repair attempt and the S2-to-S3/K1 hardware migration/refactor work up to the current state.

## Constraints

- Firmware source remains read-only for this task.
- Use repo evidence, git history, docs, current dirty tree, and memory/claude-mem where available.
- Separate committed facts, live-runtime evidence, inferred causes, and unresolved gaps.
- Deploy/reuse SSAs for independent evidence lanes.

## Phases

1. Completed - Establish evidence base and dispatch/reuse SSAs.
2. Completed - Pull memory and git chronology for Bloom/Waveform repair history.
3. Completed - Pull memory and git chronology for S2-S3/K1 hardware migration.
4. Completed - Integrate SSA findings and local source/doc evidence.
5. Completed - Create forensic archaeological HTML.
6. Completed - Validate links, diff, and final artefact.

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| Fresh SSA spawn failed because thread limit was reached. | `spawn_agent` x4 | Reused existing completed SSA threads with `send_input`. |
