# User-confirmed hardware tests

Recorded on 2026-11-06 for release preparation. Source: the project owner's explicit report, not a new test performed by the release-preparation agent. The actual test dates, instrument logs, device revision, card/filesystem details and Launcher version were not supplied.

## Confirmed results

| Item | User-confirmed result |
|---|---|
| Device | M5Stack Cardputer ADV |
| Player version | FIX06 successfully installed |
| Video | Video playback works |
| Audio | Audio output works |
| Headphones | Headphone output works |
| Keyboard | Keyboard navigation works |
| Converter | FIX08 successfully used |
| Large file | BLOOD-MOON MCV, **1,348,302,886 bytes**, successfully started and played |
| Five-minute test | A five-minute MCV test file successfully played back |

## Boundaries of this evidence

The complete **2 h 08 min BLOOD-MOON video has NOT been reported as played through to the end**. No end-to-end completion, long-run drift measurement, uninterrupted 2:08-hour stability, frame-rate benchmark, card-wide compatibility or independent lab certification is claimed. The five-minute playback is the confirmed shorter-duration test.

The user identified the tested version as FIX06. The archived v1.0.0 release reference is `MIXU_CYBERTUBE_V1.0_FIX06_CARDPUTER_ADV_APP.bin`, SHA-256 `aeabcb0d77a8dd1710293e774ea05c5f5923b80943cefbe28b2928a2adaa0d7b`. The hash of the actually installed device image was not independently measured or supplied with the report; do not present it as a test-time hash measurement.

UI01 and UI02 retain their documented **offline-only** status. This user confirmation does not extend to their UI, five-second splash or device behavior. Their screenshots are raster previews, not device captures.

No hardware was accessed, flashed or tested during this audit. No BLOOD-MOON file or other user media was opened, copied, converted or bundled.
