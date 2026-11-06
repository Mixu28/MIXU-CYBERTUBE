# License scope and third-party notices

[LICENSE](LICENSE): MIT for original MIXU player/header/tools/configuration and converter/native adapter/validator source. All existing per-file copyrights remain effective. The root MIT grant does not override third-party code or dependency terms.

Bundled decoder: TJpgDec, Copyright ChaN 2019, LGFX modifications lovyan03 2020. Original .c/.h and [notice](licenses/TJPGDEC_NOTICE.txt) remain intact, with [M5GFX MIT](licenses/M5GFX_MIT.txt). Retain copyright and warranty disclaimer with source and binary redistributions.

M5Cardputer/M5Unified/M5GFX/IRremote are commit-pinned external dependencies, not vendored in this source edition. Their existing MIT and embedded Adafruit BSD texts are supplied for attribution; they do not license every optional font dataset. The verified Font0 notice is [Adafruit BSD](licenses/Adafruit_GFX_BSD.txt). No font dataset or board-picture array is copied here.

The validator build script uses an externally installed GCC/MinGW-w64. If you distribute its rebuilt EXE, preserve [GCC GPLv3](licenses/GCC_GPL3.txt), [GCC Runtime Library Exception](licenses/GCC_RUNTIME_EXCEPTION.txt), and MinGW/winpthreads texts in `licenses/`; the separately approved variant C includes them and exact build provenance. No compiler/runtime DLL is bundled here.

FFmpeg/Python/Tk/yt-dlp/Pillow are externally supplied, not relicensed or bundled. Pillow is optional for Python-only JPEG checks; ordinary converter processing uses external FFmpeg and the native validator.

Only original project code is MIT; no blanket grant for third-party material, artwork or trademarks. Firmware binary redistribution remains separately blocked. Source-only publication is not a claim that a future binary produced by a user has satisfied every framework/SDK condition.
