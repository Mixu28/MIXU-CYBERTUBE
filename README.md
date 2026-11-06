# MIXU CYBERTUBE — source-only edition

**Publication variant A: READY for this exact source-only tree.** Original MIXU code is MIT, Copyright (c) 2026 MIXU. Third-party decoder code and license texts retain their terms. This edition contains no firmware BIN, validator EXE, vendored M5Stack font/picture datasets, screenshots, user media, SDK archive or toolchain.

The Cardputer ADV FIX06 player source is unchanged. UI01/UI02 sources are experimental and offline-tested. All four M5Stack/IRremote dependencies are pinned by upstream commit in each PlatformIO configuration. First setup fetches those dependencies into your local cache; they are not redistributed here. Normal source build: run `pio run -e cardputer_adv` from `firmware/fix06`. No hardware target is authorized by this tree; the build guard blocks upload/erase/monitor/debug targets.

The owner confirms FIX06 installation, video/audio/headphones/navigation and five-minute playback. BLOOD-MOON (1,348,302,886 bytes) started and played; full 2:08-hour completion is not claimed. [Test scope](docs/HARDWARE_TESTS.md).

## Converter source

`converter_FIX08/` contains unchanged FIX08 Python/C/C++ source plus a new deterministic validator build script, but no compiled EXE. Windows x64, Python/Tk and external FFmpeg are required. Optional YouTube uses separately installed yt-dlp; no cookies/dependencies are bundled or automatically installed. Live YouTube compatibility was not tested.

With the recorded GCC/MinGW-w64 UCRT64 tools on PATH or `MINGW_BIN` set, run from `converter_FIX08`:

```powershell
py -3 build_validator.py --output .build-validator
Copy-Item .build-validator/validate_mcv.exe validate_mcv.exe
Start_Converter.cmd
```

Do not commit local EXEs/build outputs into this source-only edition. A separate newly rebuilt converter download is variant C; it is not the legacy FIX08 ZIP.

## Graphics and distribution scope

The original FIX06 ELF hash matches its BIN descriptor. Its only Font0 glyph array matches all 1,280 bytes of the Adafruit BSD table; no optional FreeFont/DejaVu/efont/IPA/picture symbols are present. [Exact evidence](docs/GRAPHICS_PROVENANCE.json). No unclear datasets were copied into this source edition, so no font replacement or player behavior change was required.

**Firmware binary download remains BLOCKED** pending the exact framework/SDK notice/source/relink package described in [distribution decisions](docs/DISTRIBUTION_DECISIONS.md). A successful source build is not a firmware binary-distribution clearance. No claim is made that all externally fetched dependencies are uniformly MIT.

See [license scope and notices](THIRD_PARTY_NOTICES.md). MIXU is the owner-approved provisional project identifier; no personal name or legal entity is invented. No trademark or branding permission is implied. No GitHub publication or hardware action has occurred.

Validation: [all three offline firmware builds](docs/BUILD_VALIDATION.json) passed using exact local dependency trees in a private worker; initial network retrieval from the published pinned URLs was not exercised. [Native validator toolchain/hashes](docs/VALIDATOR_TOOLCHAIN.json).
