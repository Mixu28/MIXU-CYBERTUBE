# MIXU CYBERTUBE – Windows-Converter FIX08

Für die unveränderte Cardputer-ADV-Firmware FIX06. Neue, getrennte Version; FIX07 und alte Medien bleiben erhalten.

## Voraussetzungen und Start

Windows x64, Python 3.10+ mit Tk, vorhandenes FFmpeg und das beiliegende `validate_mcv.exe`. Für YouTube zusätzlich lokal installiertes yt-dlp (getestet: 2026.10.26). `requirements-youtube.txt` beschreibt diese Abhängigkeit; der Converter installiert oder aktualisiert nichts.

FFmpeg-Suche: `FFMPEG_EXE`, `ffmpeg.exe` neben dem Converter, `tools/ffmpeg.exe` im Paket, vorhandener Projektpfad `../tools/python_packages/imageio_ffmpeg/binaries`, danach PATH. FFmpeg, Python und yt-dlp werden nicht mitgeliefert. Beim separaten Entpacken `FFMPEG_EXE` auf das vorhandene Programm setzen.

YouTube kann zusätzlich eine von yt-dlp unterstützte lokale JavaScript-Laufzeit und passende lokale EJS-Komponenten benötigen. Automatisches Nachladen solcher Komponenten ist mit `--no-remote-components` gesperrt. Keine Browser-Cookies, Kennwörter, Konten oder Konfigurationen werden übernommen (`--ignore-config`). Private/geschützte Videos werden nicht unterstützt. Verfügbarkeit und YouTube-Kompatibilität müssen bei tatsächlicher Nutzung geprüft werden; Entwicklung und Tests erfolgten offline.

`Start_Converter.cmd` doppelklicken. `Start_Converter.cmd --self-test` prüft GUI und lokale Werkzeuge ohne Download.

## GUI-Workflow

1. HTTPS-YouTube-Einzelvideolink einfügen **oder** eine lokale MP4/MKV/WebM/MOV auswählen. Ein eingetragener Link hat Vorrang; die lokale Dateiauswahl leert ihn.
2. Ausgabe-Basisordner und optional einen neuen Namen wählen. Standardqualität 5 bleibt während des gesamten Auftrags unverändert. Kleinere Qualitätszahl bedeutet höhere Qualität.
3. Optional „Nur 5-Minuten-Probe konvertieren“ aktivieren. Dabei wird eine YouTube-Quelle einmal vollständig heruntergeladen, anschließend nur die Probe konvertiert. Ohne Häkchen wird nach Start das Gesamtvideo konvertiert; maximal 2:30 Stunden.
4. **Start** betätigen. Erst jetzt erfolgen Metadatenabfrage und gegebenenfalls Download. Titel/Dauer erscheinen nach der Abfrage. Download- und Konvertierungsfortschritt sowie tatsächliche MCV-Bytes werden angezeigt.
5. Nach Prüfung aller Teile zeigt die GUI Anzahl, endgültige Dateinamen und Bytegrößen. „microSD-Ergebnisordner öffnen“ öffnet den fertigen Ordner. Abbrechen beendet nur eigene Unterprozesse und entfernt unveröffentlichte MCV-Teile.

Downloads werden einmal in einem neuen Unterordner von `downloads/` gespeichert. Keine vorhandenen Downloads werden ersetzt. Bei späterem Konvertierungsfehler bleibt ein bereits geprüfter Download erhalten; über lokale Dateiauswahl kann er erneut verwendet werden. Der Wechsel zu zwei Teilen lädt nichts erneut herunter. Quellen ohne Audiospur werden ausdrücklich abgewiesen, auch wenn erst nach dem Download erkannt.

## Ausgabeverzeichnis und microSD

Um zwei Dateien gemeinsam und erst nach vollständiger Prüfung zu veröffentlichen, wird **ein neuer Ergebnisordner** atomar umbenannt. Es werden keine fertigen MCV-Dateien einzeln in einen bereits vorhandenen Zielordner verschoben.

```text
<Ausgabe-Basisordner>/<VIDEO_NAME>/
    RESULT.json
    MIXU-CYBERTUBE/VIDEOS/
        VIDEO_NAME.mcv
```

Bei Aufteilung stehen dort stattdessen `VIDEO_NAME_PART01.mcv` und `VIDEO_NAME_PART02.mcv`. Den enthaltenen Ordner `MIXU-CYBERTUBE` später auf die microSD übernehmen; die Videos gehören unmittelbar nach `/MIXU-CYBERTUBE/VIDEOS/`. Die bestehende FIX06-Bibliothek erkennt beide Teile ohne Firmwareänderung. Beim manuellen Kopieren vorhandene SD-Dateien nicht ersetzen.

Ein vorhandener Ergebnisordner wird abgewiesen. Neue Namen wählen. Namen werden Windows-konform bereinigt und auf 60 Zeichen begrenzt; reservierte Gerätenamen erhalten ein Präfix. Temporäre Aufträge tragen `.partial` und sind keine fertigen Ergebnisse. Bei normalem Fehler/Abbruch werden nur die eigenen temporären Dateien entfernt. Nach Stromausfall/Prozessabsturz können solche nicht veröffentlichten Ordner verbleiben; es gibt keine Zusicherung gegen physische Datenträgerausfälle.

## Streaming, Größen und Synchronität

Festes Profil: MCV1 unverändert; 240 × 135 einschließlich Zeile 134; 15 FPS; Baseline-JPEG 4:2:0 (22/11/11); PCM S16LE mono 16.000 Hz. Das FIX07-Skalieren verwendet `force_divisible_by=1` und erst am Encoder yuvj420p, damit 135 nicht auf 134 abgerundet wird. Bildseitenverhältnis bleibt mit Balken erhalten.

Pro Datei maximal **2.040.109.000 Byte** einschließlich 64-Byte-Header, 32-Byte-Frameheader, JPEG und PCM. Tatsächliche Ausgabeblöcke werden gezählt, nicht geschätzt. Es entstehen eine oder höchstens zwei Dateien. Passt der nächste Blockverbund nicht, beginnt Teil 2. Passt auch dieser nicht, wird verständlich abgebrochen und **kein Teil veröffentlicht**. Grenzwerte lassen sich nicht in der GUI erhöhen. Keine automatische Qualitätsreduzierung.

Geschnitten wird vor einer Gruppe von drei Frames: 3/15 Sekunden entsprechen exakt 3.200 PCM-Samples. Dadurch stimmen die 1066/1067/1067-Samplephasen auch nach dem Neustart des Zeitstempels überein. Jeder Teil beginnt mit Frameindex und PTS 0; keine Frames/Samples werden ausgelassen oder doppelt geschrieben. Der Schnitt kann bis zu eine Gruppe vor dem Größenlimit liegen. Die Firmware spielt beide Dateien separat; ein nahtloser automatischer Wechsel zwischen Dateien wird nicht versprochen.

Im Python-RAM liegen höchstens drei JPEG/PCM-Paare und begrenzte Rohr-/Metadatenpuffer, keine vollständige JPEG-Sammlung. PCM wird einmal auf Datenträger vorbereitet (bei 2:30 h höchstens 288 MB), danach gestreamt. FFmpeg verarbeitet die Quelle als eigenen Streamingprozess; dessen Codec-/Threadpuffer sind separat. Temporäres PCM plus Download und beide MCV-Dateien benötigen genügend freien Plattenplatz. Platzprüfungen und echte Schreibfehler verhindern die Veröffentlichung unvollständiger Ergebnisse. Zwei Dateien bieten zusammen höchstens 4.080.218.000 Byte, abzüglich beider Header und Schnittreserve. Auch bei zulässiger Laufzeit können komplexe Bilder dieses Limit überschreiten. Einzel-JPEGs bleiben auf den Firmwaregrenzwert 32.768 Byte begrenzt; überschrittene Frames führen zum Fehler, nicht zur Qualitätsänderung.

Beide Teile werden vor Freigabe vollständig mit Python-Struktur-/CRC-Prüfung und dem unveränderten FIX06-Decoder geprüft, einschließlich Bildabdeckung aller 135 Zeilen. Windows-Dateiumbenennung veröffentlicht danach den ganzen Ergebnisordner ohne bestehende Ziele zu ersetzen. Keine Firmware-/SD-/COM-/USB-Funktion ist im Converter enthalten.

## CLI

```powershell
py -3 convert.py "C:\Videos\Quelle.mp4" "C:\Videos\Ergebnisse" --name VIDEO_NAME --preview
py -3 convert.py "https://www.youtube.com/watch?v=VIDEO_ID" "C:\Videos\Ergebnisse" --name VIDEO_NAME
```

Ohne `--preview` wird nach diesem ausdrücklichen Aufruf die gesamte zulässige Quelle verarbeitet. Ein Link muss eine gültige 11-stellige Video-ID haben. Der CLI-Ausgabeparameter ist ein Basisordner, keine `.mcv`-Datei. `--quality 5` ist optional.

## Offline-Nachweise

Siehe Projektbericht `MIXU_CYBERTUBE_FIX08_CONVERTER_REPORT.md`, `tests/fix08_tests.py` und `logs/fix08_*.json`. YouTube-Abfragen und Downloads wurden simuliert; die echte lokale yt-dlp-/FFmpeg-Zusammenführung wurde bei gesperrtem Netzwerk geprüft. Kein echter Download, keine 2-Stunden-Konvertierung, keine Hardwareinstallation.
