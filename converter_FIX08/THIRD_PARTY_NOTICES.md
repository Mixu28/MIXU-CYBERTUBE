# FIX08 — Fremdkomponenten

Der Converter ist eine MIXU-Implementierung. MCV1-Reader und Decoder-Adapter unter `native/` sind unveränderte Kopien der FIX06-Quellen; sie ändern keine Gerätefirmware.

`native/lgfx/utility/lgfx_tjpgd.c` und `.h`: TJpgDec R0.01c, Copyright 2019 ChaN, für LGFX modifiziert durch lovyan03. Vollständige Weitergabehinweise stehen unverändert in beiden Quelldateien. Die übergeordnete M5GFX-MIT-Lizenz liegt zusätzlich unter `licenses/M5GFX_MIT.txt`.

`validate_mcv.exe` wurde mit GCC/MinGW-w64 als Windows-x64-Programm mit statischen GCC-/C++-Laufzeitkomponenten gebaut. GCC GPLv3 und GCC Runtime Library Exception liegen unter `licenses/`. Die Executable benötigt Windows-System-/UCRT-DLLs, keine MSYS-Installation. Ihr Quelltext und die verwendeten Decoderquellen liegen unter `native/`.

FFmpeg wird als separat vorhandenes lokales Programm verwendet und ist nicht im ZIP enthalten. Der hier verwendete FFmpeg-9.0.2-Build meldet GPLv3. Dieses Paket lädt FFmpeg oder andere Programme nicht herunter.

Python/Tk wird über die lokale Installation verwendet. Pillow ist nur für die Entwicklungstests erforderlich.

Für den optionalen YouTube-Workflow wird das separat lokal installierte yt-dlp verwendet (Testversion 2026.10.26, Unlicense; gegebenenfalls gelten zusätzliche Hinweise der eigenen Distribution/Abhängigkeiten). yt-dlp, EJS-Komponenten und JavaScript-Laufzeiten werden nicht in diesem Paket weitergegeben oder automatisch heruntergeladen.
