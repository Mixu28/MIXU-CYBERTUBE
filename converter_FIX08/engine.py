"""One video encoding pass, measured two-part streaming, whole-set publication."""
import math
import os
from pathlib import Path
import shutil
import subprocess
from ffmpeg_tools import ffmpeg_path,source_info,run,validate_native,VIDEO_FILTER
from jpeg_stream import JpegFrames
from mcv import validate
from process_control import managed_process,check_cancel
from split_writer import FPS,RATE,PART_LIMIT,validate_duration,write_parts
from transaction import OutputGroup,safe_name
from workspace import temporary_directory

def convert(source,output_root,*,name=None,quality=5,seconds=None,limit=PART_LIMIT,title=None,
            cancel=None,log=lambda s:None,status=lambda d:None):
    check_cancel(cancel)
    if not 2<=quality<=15:raise ValueError('Qualitaetszahl muss 2 bis 15 sein; keine automatische Aenderung')
    if seconds is not None and (not math.isfinite(seconds) or seconds<=0):raise ValueError('Ungueltige Probedauer')
    if not 64<limit<=PART_LIMIT:raise ValueError('Ungueltiges Teilelimit')
    info=source_info(source,cancel);validate_duration(info['duration'])
    if title is not None:info['title']=str(title)[:200]
    if not info['has_audio']:raise ValueError('Die Quelle enthaelt keine Audiospur. Keine stille MCV-Ausgabe erzeugt.')
    name=safe_name(name or info['title'])
    group=OutputGroup(output_root,name) # Refuse existing result before encoding.
    duration=min(info['duration'],seconds) if seconds is not None else info['duration']
    frames=math.ceil(duration*FPS-1e-8);samples=frames*RATE//FPS
    if 128+frames*32+samples*2>limit*2:raise ValueError('Audio und Metadaten passen bereits nicht in zwei Dateien')
    if not (Path(__file__).parent/'validate_mcv.exe').is_file():raise FileNotFoundError('validate_mcv.exe fehlt')
    root=Path(output_root).absolute();root.mkdir(parents=True,exist_ok=True)
    def space(needed):
        if shutil.disk_usage(root).free<needed+1024*1024:raise OSError('Nicht genug freier Speicher. Kein Ergebnis veroeffentlicht.')
    space(64*1024*1024)
    status({'phase':'source','title':info['title'],'duration':info['duration']})
    log(f'Lokale Quelle: {duration:g} s, {frames} Frames; 15 FPS / 240x135 / 4:2:0 / PCM 16000 Hz')
    with temporary_directory(prefix='mixu-fix08-') as folder:
        folder=Path(folder);audio=folder/'audio.pcm'
        if shutil.disk_usage(folder).free<samples*2+64*1024*1024:raise OSError('Nicht genug Platz fuer temporaeres PCM')
        base=[ffmpeg_path(),'-hide_banner','-loglevel','error','-nostdin','-i',Path(source).resolve()]
        run([*base,'-map','0:a:0','-vn','-af',f'aresample=16000:async=1:first_pts=0,apad,atrim=end_sample={samples}',
             '-t',f'{samples/RATE:.8f}','-ac','1','-ar','16000','-c:a','pcm_s16le','-f','s16le',
             '-progress','pipe:1',audio],cancel=cancel,duration=samples/RATE,
            progress=lambda v:status({'phase':'audio','fraction':v}))
        if audio.stat().st_size!=samples*2:raise ValueError('PCM-Laenge stimmt nicht; keine stillen Samples ergaenzt')
        with group as output, audio.open('rb') as pcm:
            with (folder/'video_errors.log').open('w+b') as errors:
                with managed_process([*base,'-map','0:v:0','-an','-vf',VIDEO_FILTER,'-frames:v',frames,
                     '-c:v','mjpeg','-pix_fmt','yuvj420p','-q:v',quality,'-threads','1','-f','image2pipe','pipe:1'],
                     cancel=cancel,stdout=subprocess.PIPE,stderr=errors) as process:
                    parts=write_parts(output.videos,name,JpegFrames(process.stdout),pcm,frames,limit=limit,
                        cancel=cancel,space_check=space,
                        progress=lambda data:status({'phase':'video',**data}))
                    if process.wait():raise RuntimeError('FFmpeg-Bildkonvertierung fehlgeschlagen; kein Ergebnis veroeffentlicht')
            result_files=[]
            for i,part in enumerate(parts):
                check_cancel(cancel);status({'phase':'validate','fraction':i/len(parts)})
                validate(part['path']);native=validate_native(part['path'],cancel)
                h=part['header']
                if (native['frames'],native['samples'],native['bytes'])!=(h.frames,h.samples,part['bytes']):
                    raise ValueError('Decoder und MCV-Metadaten stimmen nicht ueberein')
                if part['bytes']>limit:raise ValueError('Teilelimit verletzt')
                relative=part['path'].relative_to(output.stage).as_posix()
                result_files.append({'relative_path':relative,'name':part['path'].name,
                                     'bytes':part['bytes'],'frames':h.frames,'samples':h.samples})
            check_cancel(cancel)
            result={'title':info['title'],'duration_seconds':samples/RATE,'files':result_files,
                    'total_frames':frames,'total_samples':samples,'part_limit_bytes':limit,
                    'quality':quality,'split':len(parts)==2,'all_parts_validated':True}
            output.publish(result)
    result['job_dir']=str(group.final)
    for item in result['files']:item['path']=str(group.final/item['relative_path'])
    status({'phase':'done','fraction':1,'result':result})
    log(f'Fertig: {len(parts)} Datei(en), zusammen {sum(p["bytes"] for p in result_files):,} Byte')
    return result

def from_youtube(url,output_root,*,name=None,quality=5,seconds=None,cancel=None,
                 log=lambda s:None,status=lambda d:None,runner=None,limit=PART_LIMIT):
    # Importing this module never starts network traffic.
    import youtube
    metadata=youtube.inspect_video(url,cancel=cancel,runner=runner)
    base=safe_name(name or (metadata['title']+'_'+metadata['id']))
    OutputGroup(output_root,base) # Existing result: do not download again.
    status({'phase':'source','title':metadata['title'],'duration':metadata['duration']})
    cached=youtube.download(url,metadata=metadata,cancel=cancel,status=status,runner=runner)
    try:
        result=convert(cached['path'],output_root,name=base,quality=quality,seconds=seconds,
                       cancel=cancel,log=log,status=status,limit=limit,title=metadata['title'])
    except BaseException:
        log('Gepruefter Download bleibt fuer lokale Wiederverwendung erhalten: '+cached['path'])
        raise
    result['download_path']=cached['path'];return result
