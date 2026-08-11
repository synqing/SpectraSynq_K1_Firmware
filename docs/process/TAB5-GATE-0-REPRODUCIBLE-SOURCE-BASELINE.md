---
abstract: "GATE 0 for the Tab5 Deck16 controller — the reproducible-source-baseline gate that now blocks Gates 1-4 (transactionality / RSSI / recovery / production hardening). Captain-frozen 2026-08-11. Holds the six sub-gates, the vendor/ dependency inventory result (5.5 GB is stock+pinnable; the real local surface is ~75 MB esp_hosted_ab plus one hand-edited stock package), and the decisive finding that the vendor tree is NOT self-contained."
status: active
---

# GATE 0 — Reproducible source baseline (Tab5)

**Captain-frozen 2026-08-11.** Inserted *before* the existing Tab5 hardening
programme. Gates 1–4 are **blocked** until Gate 0 closes.

```
GATE 0 — REPRODUCIBLE SOURCE BASELINE
│
├─ 0.1 Known-wrong calibration tombstoned          DONE  1bdf54d
├─ 0.2 vendor/ dependency inventory                DONE  (below)
├─ 0.3 local patches separated from upstream       OPEN
├─ 0.4 project-cold build PASS                     DONE  (73 s, clean)
├─ 0.5 empty-environment clean-clone build PASS    OPEN  ← authoritative
└─ 0.6 Tab5 CI compile job PASS                    OPEN
        │
        ▼
GATES 1–4  transactionality / RSSI / recovery / production hardening
```

**The end-state is not negotiable:** Tab5 is a first-class, pinned,
clean-clone-buildable, CI-compiled product target. "Source-only CI" is not an
acceptable destination. A short escape hatch is permitted if dependency surgery
exposes something genuinely ugly, but it is an exception to be argued, not a
resting place.

## Why this is Gate 0 and not a cleanup task

The current shape is:

```
203 source files + static assertions + a build that depends on
an ignored 5.6 GB local tree  =  working firmware on one workstation
```

Behavioural hardening performed on that base proves something about a
workstation, not about a product. Every Gate 1–4 result would inherit the
ambiguity.

## 0.2 — Inventory result (measured 2026-08-11)

| Bucket | Size | Disposition |
|---|---|---|
| `pio_packages/` — toolchains, frameworks, tools | **5.5 GB** | **STOCK.** Every package carries a standard upstream version string (`toolchain-riscv32-esp`, `framework-arduinoespressif32 3.3.0`, `framework-arduinoespressif32-libs 5.4.0+sha.858a988d6e`, `tool-cmake 3.30.2`, `tool-esptoolpy 2.40900.250804`, …). Replace with pinned `platform_packages` resolution at those exact versions. |
| `framework-espidf.old/` | 408 MB | **DEAD.** Delete from the dependency model — see the finding below. |
| `esp_hosted_ab/` | 75 MB | **GENUINELY LOCAL.** An A/B of ESP-Hosted 1.4.0 with `REVERT.md` and a downloaded `.zip`. This is the real surface needing extraction into an explicit patch set or a small immutable custom package. The `.zip` leaves the dependency model entirely. |
| `pio_platforms/espressif32/` | 26 MB | Stock platform (54.3.21) — pin it. |
| `python/` | 4 KB | Trivial. |

So the "5.6 GB of architectural debt" is **~98.6 % stock content that simply is
not pinned**. The genuinely local surface is ~75 MB. This is far more tractable
than the headline number suggests.

### The decisive finding — the vendor tree is NOT self-contained

`vendor/pio_packages/framework-espidf` **does not exist**. Only
`framework-espidf.old` is present. The build therefore resolves ESP-IDF from the
**global** `~/.platformio/packages/framework-espidf`.

Two consequences:

1. The vendoring never achieved its purpose. "It builds here" was already
   resting on the workstation's global cache, not on the checked-in tree. The
   5.5 GB buys determinism it does not actually deliver.
2. That global package is **not a git checkout**, which is what produced the
   `fatal: not a git repository` error from ESP-IDF's `project.cmake` version
   stamp during a fresh configure. Fix the dependency packaging — do **not** add
   another local workaround.

### One hand-edited stock package

`vendor/pio_packages/framework-arduinoespressif32/idf_component.yml.orig` is
evidence that `idf_component.yml` was edited in place inside a stock package.
That is exactly the "modified upstream content" class: it must become an
explicit, reviewable patch rather than an invisible in-tree divergence.

## 0.4 / 0.5 — the two cold gates

Deleting `.pio` alone is **not** a reproducibility proof: PlatformIO still
consumes packages and toolchains from its global cache.

```
A. PROJECT-COLD        rm -rf tab5_firmware/.pio ; build in the normal dev env
B. ENVIRONMENT-COLD    clean clone + empty PLATFORMIO_CORE_DIR ; resolve all ; build
```

**B is the authoritative gate.** A is evidence only.

- **0.4 PROJECT-COLD — PASS** (2026-08-11, 73 s, no git-stamp error). Note this
  *corrects* an earlier inference that the git-stamp failure was a cold-configure
  problem; it was transient. The failure is real but belongs to environment-cold,
  where the global ESP-IDF package is resolved fresh.
- **0.5 ENVIRONMENT-COLD — NOT RUN.** Run as:
  ```bash
  git clone <repo> /tmp/k1-cold && cd /tmp/k1-cold/tab5_firmware
  PLATFORMIO_CORE_DIR=/tmp/pio-cold pio run -e tab5_p4
  ```
  If the ESP-IDF git-stamp failure reproduces here, that is the packaging defect
  to fix — not a thing to work around locally.

## 0.6 — CI

Target matrix:

```
k1_hardware
k1_prod_im73d
tab5_p4          ← add on Gate 0 closure
```

Normal PR CI may use a dependency cache for speed. A separate release/nightly
job must start from an **empty** package environment. That gives fast CI *and*
proof that the cache is not the product.

## Standing constraints

- Do not blindly delete `vendor/` and point PlatformIO at the internet. Pin
  first, extract local modifications second, delete generated/cache material
  third.
- Every dependency gets an exact version, commit, or hash where practical.
- `tab5_firmware/vendor/` remains gitignored throughout — the fix is to stop
  needing it, not to commit it.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-11 | agent:claude-code | Created on Captain's freeze. Gate 0 inserted before Tab5 Gates 1–4; 0.1 and 0.2 closed, 0.4 PASS recorded (and the earlier cold-configure inference corrected), 0.3/0.5/0.6 left open with the authoritative environment-cold recipe. |
