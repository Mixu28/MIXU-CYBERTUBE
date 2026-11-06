"""User-triggered yt-dlp only; canonical URLs, ignored config and private errors."""
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit,parse_qs
import uuid
from ffmpeg_tools import ffmpeg_path,source_info
from process_control import managed_process,check_cancel
from split_writer import validate_duration

def canonical_url(url):
    try:
        parsed=urlsplit(url.strip())
        if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError()
        host=(parsed.hostname or '').lower()
        if host=='youtu.be':identifier=parsed.path.strip('/')
        elif host in ('youtube.com','www.youtube.com','m.youtube.com'):
            if parsed.path=='/watch':identifier=parse_qs(parsed.query).get('v',[''])[0]
            elif re.fullmatch(r'/(shorts|live|embed)/[^/]+/?',parsed.path):identifier=parsed.path.strip('/').split('/')[1]
            else:raise ValueError()
        else:raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',identifier):raise ValueError()
    except (ValueError,TypeError):raise ValueError('Gueltigen HTTPS-YouTube-Einzelvideolink verwenden; keine Zugangsdaten in der URL') from None
    return 'https://www.youtube.com/watch?v='+identifier

def run_ytdlp(args,*,cancel=None,metadata=False,status=lambda d:None):
    if importlib.util.find_spec('yt_dlp') is None:raise RuntimeError('yt-dlp fehlt lokal. Keine automatische Installation; Hinweise im FIX08-README.')
    output=[];size=0;error_kind='Download oder YouTube-Abfrage fehlgeschlagen; Netzwerk, Verfuegbarkeit und lokale yt-dlp-Version pruefen.'
    with managed_process(args,cancel=cancel,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         text=True,encoding='utf-8',errors='replace') as process:
        while True:
            line=process.stdout.readline(8*1024*1024+1)
            if not line:break
            check_cancel(cancel)
            if len(line)>8*1024*1024:raise ValueError('YouTube-Metadaten zu gross')
            text=line.strip();lower=text.lower()
            if 'no space' in lower or 'disk full' in lower:error_kind='Download abgebrochen: nicht genug freier Speicher.'
            elif 'private video' in lower or 'sign in' in lower or 'login' in lower:error_kind='Video nicht frei verfuegbar. FIX08 verwendet keine Zugangsdaten oder Browser-Cookies.'
            elif 'requested format' in lower:error_kind='Kein herunterladbares Format mit Video und Audio gefunden.'
            if metadata and text.startswith('{'):
                size+=len(text)
                if size>8*1024*1024:raise ValueError('YouTube-Metadaten zu gross')
                output.append(text)
            elif text.startswith('FIX08_PROGRESS:'):
                try:status({'phase':'download','fraction':min(1,max(0,float(text.split(':',1)[1].strip().strip('%'))/100))})
                except ValueError:pass
            elif text.startswith('FIX08_FILE:'):output.append(text)
        code=process.wait()
    if code:raise RuntimeError(error_kind) # Never forward raw yt-dlp output/credentials.
    return '\n'.join(output)

def inspect_video(url,*,cancel=None,runner=None):
    canonical=canonical_url(url);check_cancel(cancel);runner=runner or run_ytdlp
    args=[sys.executable,'-m','yt_dlp','--ignore-config','--no-playlist','--no-cache-dir','--no-remote-components','--color','never',
          '--no-warnings','--skip-download','--dump-single-json','--',canonical]
    text=runner(args,cancel=cancel,metadata=True)
    try:data=json.loads(text)
    except (ValueError,TypeError):raise ValueError('YouTube-Metadaten konnten nicht gelesen werden') from None
    if not isinstance(data,dict):raise ValueError('Ungueltige YouTube-Metadaten')
    if data.get('is_live') or data.get('_type') in ('playlist','multi_video'):
        raise ValueError('Livestreams und Playlists werden nicht verarbeitet')
    duration=validate_duration(data.get('duration'))
    identifier=canonical.split('=')[-1]
    if data.get('id',identifier)!=identifier:raise ValueError('YouTube-ID stimmt nicht ueberein')
    formats=data.get('formats') or []
    if not isinstance(formats,list) or not all(isinstance(f,dict) for f in formats):raise ValueError('Ungueltige Formatliste')
    if formats and not any(f.get('acodec') not in (None,'none') for f in formats):
        raise ValueError('YouTube bietet fuer dieses Video keine Audiospur an')
    identifier=canonical.split('=')[-1]
    title=re.sub(r'[\x00-\x1f]',' ',str(data.get('title') or identifier))[:200]
    return {'id':identifier,'title':title,'duration':duration}

def download(url,*,metadata=None,cancel=None,status=lambda d:None,runner=None):
    canonical=canonical_url(url);runner=runner or run_ytdlp
    metadata=metadata or inspect_video(canonical,cancel=cancel,runner=runner)
    if metadata.get('id')!=canonical.split('=')[-1]:raise ValueError('YouTube-ID stimmt nicht ueberein')
    validate_duration(metadata['duration']);check_cancel(cancel)
    root=Path(__file__).resolve().parent/'downloads';root.mkdir(exist_ok=True)
    unique=metadata['id']+'_'+uuid.uuid4().hex
    stage=root/('.'+unique+'.partial');stage.mkdir(exist_ok=False)
    final=root/unique;published=False
    try:
        if shutil.disk_usage(root).free<64*1024*1024:raise OSError('Nicht genug Platz fuer einen Download')
        args=[sys.executable,'-m','yt_dlp','--ignore-config','--no-playlist','--no-cache-dir','--no-remote-components','--color','never',
              '--no-overwrites','--no-continue','--no-simulate','--newline','--progress',
              '--progress-template','download:FIX08_PROGRESS:%(progress._percent_str)s',
              '--print','after_move:FIX08_FILE:%(filepath)s','--ffmpeg-location',ffmpeg_path(),
              '--merge-output-format','mkv','-f','bv+ba/b','-o',str(stage/'source.%(ext)s'),'--',canonical]
        text=runner(args,cancel=cancel,metadata=False,status=status)
        paths=[line.split(':',1)[1] for line in text.splitlines() if line.startswith('FIX08_FILE:')]
        if len(paths)!=1:raise ValueError('Download meldet keine eindeutige zusammengefuehrte Videodatei')
        source=Path(paths[0]).resolve()
        if not source.is_relative_to(stage.resolve()) or not source.is_file():raise ValueError('Ungueltiger Download-Ausgabepfad')
        info=source_info(source,cancel)
        if not info['has_audio']:raise ValueError('Zusammengefuehrter Download hat keine Audiospur; keine MCV-Dateien erzeugt')
        check_cancel(cancel)
        relative=source.relative_to(stage.resolve())
        with (stage/'DOWNLOAD.json').open('x',encoding='utf-8') as f:json.dump(metadata,f,ensure_ascii=False,indent=2)
        os.rename(stage,final);published=True
        status({'phase':'download','fraction':1})
        return {'path':str(final/relative),'title':metadata['title'],'duration':info['duration']}
    finally:
        if not published and stage.exists():
            if stage.parent.resolve()!=root.resolve() or stage.is_symlink() or getattr(stage,'is_junction',lambda:False)():
                raise RuntimeError('Download-Arbeitspfad geaendert; Bereinigung verweigert')
            shutil.rmtree(stage)
