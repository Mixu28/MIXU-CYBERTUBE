"""Local FFmpeg and unchanged FIX06 decoder, with cancellable owned processes."""
from collections import deque
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from process_control import managed_process,check_cancel
from split_writer import validate_duration

VIDEO_FILTER='fps=15:start_time=0,scale=240:135:force_original_aspect_ratio=decrease:force_divisible_by=1,format=yuv444p,pad=240:135:(ow-iw)/2:(oh-ih)/2,setsar=1,tpad=stop_mode=clone:stop_duration=1'

def ffmpeg_path():
    explicit=os.environ.get('FFMPEG_EXE')
    if explicit:
        path=Path(explicit).resolve()
        if not path.is_file():raise FileNotFoundError('FFMPEG_EXE existiert nicht')
        return str(path)
    here=Path(__file__).resolve().parent
    candidates=[here/'ffmpeg.exe',here/'tools/ffmpeg.exe']
    candidates+=list((here.parent/'tools/python_packages/imageio_ffmpeg/binaries').glob('ffmpeg*.exe'))
    for path in candidates:
        if path.is_file():return str(path)
    found=shutil.which('ffmpeg')
    if found:return found
    raise FileNotFoundError('Lokales FFmpeg fehlt. FFMPEG_EXE setzen; kein automatischer Download.')

def capture(args,cancel=None):
    with managed_process(args,cancel=cancel,stdout=subprocess.PIPE,stderr=subprocess.STDOUT) as process:
        data=bytearray()
        while True:
            block=process.stdout.read(65536)
            if not block:break
            data.extend(block)
            if len(data)>8*1024*1024:raise ValueError('Metadatenausgabe zu gross')
        code=process.wait()
    return code,data.decode('utf-8','replace')

def source_info(source,cancel=None):
    source=Path(source).resolve()
    if not source.is_file():raise FileNotFoundError('Lokale Videodatei nicht gefunden')
    _,text=capture([ffmpeg_path(),'-hide_banner','-nostdin','-i',source],cancel)
    match=re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)',text)
    if not match or 'Video:' not in text:raise ValueError('Keine lesbare lokale Videodatei mit bekannter Dauer')
    duration=int(match[1])*3600+int(match[2])*60+float(match[3]);validate_duration(duration)
    title=re.search(r'^\s*title\s*:\s*(.+)$',text,re.M)
    title=title[1] if title else source.stem
    title=re.sub(r'[\x00-\x1f]',' ',title)[:200]
    return {'path':str(source),'duration':duration,'has_audio':'Audio:' in text,'bytes':source.stat().st_size,'title':title}

def run(args,*,cancel=None,progress=lambda v:None,duration=None):
    with managed_process(args,cancel=cancel,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         text=True,encoding='utf-8',errors='replace') as process:
        for line in process.stdout:
            check_cancel(cancel)
            if duration and line.startswith('out_time_us='):
                try:progress(min(1,max(0,int(line.split('=')[1])/1e6/duration)))
                except ValueError:pass
        code=process.wait()
    if code:raise RuntimeError(f'FFmpeg-Verarbeitung fehlgeschlagen (Code {code}); Quelle oder freien Speicher pruefen.')

def validate_native(path,cancel=None):
    executable=Path(__file__).resolve().parent/'validate_mcv.exe'
    if not executable.is_file():raise FileNotFoundError('validate_mcv.exe fehlt; vollstaendiges FIX08-Paket verwenden')
    code,text=capture([executable,path],cancel)
    if code:raise ValueError('Cardputer-Decoderpruefung fehlgeschlagen: '+text[:1000])
    return json.loads(text)
