---
abstract: "P0 restore-asset hashes. 2 MB pre-probe dump MATCH. Colour Lab factory app SHA is recorded but the 728336 B bin is not in this tree. webflash k1_main_rpl_im69d.bin is a different image."
---

# Product restore assets (acaecaa8)

Named restore: **`k1_main_rpl_im69d` @ `acaecaa8`**
(`acaecaa8f1b4c3bc6f1863344da4808231e4cc7b` — `fix(colour): cap dual-channel WS2816 paint current`).

## Verified this session

| Asset | Size | SHA-256 | Verdict |
|---|---:|---|---|
| `docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/restore-pre-pcm-probe-0x0-2MB.bin` | 2,097,152 | `1e2744256eaaaf170f18600f5daafc39bc33bce1521bd1067f92f48a6a3a3a8e` | **MATCH** recorded `RESTORE_DUMP.sha256`. This is the silicon image taken **before** the PCM probe flash. Primary restore blob. |
| `docs/forensics/colour-lab-rtrace-20260827/rpl_product_firmware.sha256` | 65 B (hash file) | records `4bd481f8356055ff1ab728b93431f226d5361ac9492f397a25cb8965a383fd72` | Hash **recorded**. Matching 728,336 B `firmware.bin` **ABSENT** from this tree. |
| `tools/webflash/firmware/k1_main_rpl_im69d/firmware.bin` | 708,816 | `fc35f45c7a3b802058af97cde40a3e8240bff697a07d7f01e72542e15fc3e85b` | **NOT** the factory Colour Lab image. Do not use as acaecaa8 restore. |

## Restore policy for P12

1. Identity-check `9087A500` / USB `B4:3A:45:A5:87:90`.
2. Prefer the 2 MB dump (`esptool write_flash 0x0 …`) — it is the actual pre-probe silicon, including whatever NVS/cal was live.
3. If an app-only flash of clean `acaecaa8` is required later, **rebuild** `k1_main_rpl_im69d` at that commit; do not invent a missing 728336 B blob.
4. Never treat `tools/webflash/…/firmware.bin` as that restore.

OPEN_RISK: factory 728336 B bin not on disk. Mitigated by the hash-verified 2 MB dump.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | Re-hashed restore dump; recorded missing factory bin. |
