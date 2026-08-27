# K1 Web Flasher

Browser-based flasher for the SpectraSynq K1 (ESP32-S3), modelled on the
projectZero janos_flash tool: esptool-js + Web Serial, manifest-driven, with an
independent serial monitor. Single self-contained page (`index.html`), no build
step.

## Local use (today)

```sh
# 1. Build the curated homes from one git tree
bash scripts/agent/pio-build.sh k1_main_rpl_im69d
bash scripts/agent/pio-build.sh k1_bench_im69d_led150
bash scripts/agent/pio-build.sh k1_unit2_im69d_right

# 2. Generate manifest.json and copy binaries into firmware/<env>/
python3 tools/webflash/make_manifest.py

# 3. Serve the folder (Web Serial works on localhost without HTTPS)
cd tools/webflash && python3 -m http.server 8321
# → open http://localhost:8321 in Chrome or Edge
```

Re-run step 2 after every build you want the page to serve — the manifest
stamps git SHA, build time and per-image MD5s, and the page refuses images
whose MD5 no longer matches the manifest (stale-binary guard).

## Publishing publicly (later)

The folder is transport-agnostic: `manifest.json` uses relative paths only.
To give testers a janos-style URL, copy the whole folder (`index.html`,
`manifest.json`, `assets/`, `firmware/`) into a **public** GitHub repo with
Pages enabled — same origin for page and binaries, so no CORS, no tokens, no
GitHub API. Nothing else in the private firmware repo needs to go public.

A different manifest can also be pointed at with `?manifest=<url>`.

The variant dropdown is a **Captain-ticked shortlist**, not the ~97
`[env:k1_*]` rows in `platformio.ini`. Captain curates
`CURATED_ENVS` in `make_manifest.py` (ruled 2026-08-18; shortlist 2026-08-26).
Today that is the three homes: Main RPL (`k1_main_rpl_im69d`), bench 150-px
(`k1_bench_im69d_led150`), and Bench Unit 2 (`k1_unit2_im69d_right`). The
device-build registry remains canonical for PlatformIO upload;
this page consumes that subset only. ESP32-P4 images are a different chip
family and are not hosted here.

`?mode=simple` ignores the dropdown and always flashes Main RPL, still
MAC-gated to that unit. Advanced mode shows the ticked homes with
device-plain labels (chip + pin fact).

## Identify and boot verification

The firmware's `build` serial command (stamped by `k1_build_provenance.py`)
reports `BUILD: version=… git=… epoch=… env=…`. The flasher uses it twice:

- **Pre-flash identify**: on Connect it probes `build` at 115200 before handing
  the port to esptool. A running K1 reports its installed env/git/version; a
  blank or ROM-mode board simply doesn't answer and the normal flow continues.
- **Post-flash boot verification**: after reset it waits out USB
  re-enumeration, re-probes `build` (up to ~18 s), and compares the reported
  env and git hash against the manifest. `writeFlash()` returning is not
  treated as success — a booted, answering K1 is.

## Simple (customer) mode

`?mode=simple` hides every advanced control (erase, OTA seeding, baud,
variant, serial monitor) and shows a single **Update K1** action that chains
connect → identify → flash → verify, reporting installed vs available git.
The recovery (BOOT+RESET) instructions stay visible.

## CI packaging

`.github/workflows/webflash-release.yml` builds the curated env(s), runs
`make_manifest.py`, and uploads a `k1-webflash-bundle.zip` artifact; pushing a
`webflash-v*` tag additionally attaches it to a GitHub Release. The zip's
contents drop verbatim into a public Pages repo for the public `/flash`
channel.

## Query parameters

- `?variant=<env>` — preselect a firmware variant
- `?auto=1` — flash automatically after a successful connect
- `?manifest=<url>` — load an alternative manifest
- `?mode=simple` — customer mode (single Update action, advanced hidden)

## Flash layout (from the real partition table, default_16MB.csv)

| Image | Offset |
|---|---|
| bootloader.bin | 0x0 |
| partitions.bin | 0x8000 |
| boot_app0.bin (otadata seed → boots ota_0) | 0xE000 |
| firmware.bin (ota_0) | 0x10000 |
| firmware.bin OTA-1 seed (optional checkbox) | 0x650000 |

Offsets are parsed from each env's actual `partitions.bin` by
`make_manifest.py`, never hardcoded. Flash header parameters are written with
`keep`, so the images fly exactly as PlatformIO built them.

## Caveats

- **Erase** wipes the full flash including NVS (persisted K1 config and
  calibration). The page warns about this; it is deliberate.
- After esptool sync the page reads the chip **MAC** and enforces the
  device identity registry (`k1_device_identities.json`, stamped onto
  `manifest.json` by `make_manifest.py`). A known unit cannot take a
  variant that is not in its allowlist (GPIO39 LED-data vs PDM-clock is
  the fatal pair). An unknown or quarantined MAC is refused. This is the
  browser analogue of `k1_upload_guard.py`; PlatformIO upload still uses
  the Python guard.
- `assets/boot_app0.bin` is vendored from arduino-esp32 3.2.0
  (md5 `e6327541e2dc394ca2c3b3280ac0f39f`); the generator prefers the local
  framework copy in `~/.platformio` when present.
- Curated env list lives at the top of `make_manifest.py` (`CURATED_ENVS`).
