"""Two-part streaming MCV1 writer; phase-aligned cuts preserve every PCM sample."""
import math
import os
from pathlib import Path
import struct
from mcv import Header,BLOCK,MAX_JPEG,check_jpeg,crc,FormatError
from process_control import check_cancel

FPS=15;RATE=16000;PART_LIMIT=2040109000;MAX_SECONDS=9000
ALIGN=FPS//math.gcd(FPS,RATE) # 3 frames = exactly 3200 samples.

def validate_duration(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=MAX_SECONDS:
        raise ValueError('Videolaenge muss bekannt sein und darf 2 Stunden 30 Minuten nicht ueberschreiten')
    return value

def fits(position,payload,limit=PART_LIMIT):
    if not 64<limit<=PART_LIMIT:raise ValueError('Ungueltiges MCV-Teilelimit')
    return position>=64 and payload>=0 and position+payload<=limit

def write_parts(folder,name,jpegs,audio,expected_frames,*,limit=PART_LIMIT,progress=lambda info:None,
                cancel=None,space_check=lambda needed:None):
    if not 0<expected_frames<=FPS*MAX_SECONDS:raise FormatError('Ungueltige Framezahl')
    if 128+expected_frames*32+2*(expected_frames*RATE//FPS)>2*limit:
        raise FormatError('Bereits Audio und Blockheader passen nicht in zwei Dateien')
    paths=[];headers=[];sizes=[];file=None;local=0;maximum=0;global_index=0;group=[]
    folder=Path(folder)
    def open_part(filename):
        nonlocal file,local,maximum
        path=folder/filename;file=path.open('xb+');file.write(bytes(64));paths.append(path);local=0;maximum=0
    def finish():
        nonlocal file
        if not local:raise FormatError('Leerer MCV-Teil')
        header=Header(FPS,RATE,local,local*RATE//FPS,maximum)
        end=file.tell();file.seek(0);file.write(header.pack());file.flush();os.fsync(file.fileno());file.close();file=None
        headers.append(header);sizes.append(end)
    def flush_group():
        nonlocal local,maximum,global_index,group
        check_cancel(cancel)
        payload=sum(32+len(pcm)+len(jpeg) for _,pcm,jpeg in group)
        if not fits(file.tell(),payload,limit):
            if len(paths)==2:raise FormatError('Tatsaechliche Ausgabe ist fuer zwei Dateien zu gross. Keine Dateien veroeffentlicht; Qualitaet wurde nicht veraendert.')
            if not local or global_index%ALIGN:raise FormatError('Framegruppe passt nicht in das Teilelimit')
            finish()
            renamed=folder/(name+'_PART01.mcv');os.rename(paths[0],renamed);paths[0]=renamed
            open_part(name+'_PART02.mcv')
            if not fits(file.tell(),payload,limit):raise FormatError('Framegruppe passt nicht in das Teilelimit')
        space_check(payload)
        for original_index,pcm,jpeg in group:
            count=(local+1)*RATE//FPS-local*RATE//FPS
            if len(pcm)!=count*2:raise FormatError('PCM-Phase am Schnitt stimmt nicht')
            pts=local*RATE//FPS
            block=BLOCK.pack(b'FRM1',local,pts,count,len(jpeg),crc(pcm+jpeg),0)
            file.write(block[:28]+struct.pack('<I',crc(block[:28])));file.write(pcm);file.write(jpeg)
            maximum=max(maximum,len(jpeg));local+=1;global_index=original_index+1
        progress({'fraction':global_index/expected_frames,'part':len(paths),
                  'bytes':[*sizes,file.tell()],'frames':global_index})
        group=[]
    try:
        open_part(name+'.mcv')
        for i,jpeg in enumerate(jpegs):
            check_cancel(cancel)
            if i>=expected_frames:raise FormatError('Zu viele Frames')
            check_jpeg(jpeg)
            if len(jpeg)>MAX_JPEG:raise FormatError('JPEG zu gross')
            count=(i+1)*RATE//FPS-i*RATE//FPS;pcm=audio.read(count*2)
            if len(pcm)!=count*2:raise FormatError('PCM-Datei unvollstaendig; kein stilles Auffuellen')
            group.append((i,pcm,jpeg))
            if len(group)==ALIGN:flush_group()
        if group:flush_group()
        if global_index!=expected_frames:raise FormatError('Videoframes fehlen')
        if audio.read(1):raise FormatError('Ueberzaehlige PCM-Daten')
        finish()
        if sum(h.frames for h in headers)!=expected_frames or sum(h.samples for h in headers)!=expected_frames*RATE//FPS:
            raise FormatError('Gesamtzahl der Frames oder Samples stimmt nicht')
        return [{'path':p,'header':h,'bytes':s} for p,h,s in zip(paths,headers,sizes)]
    finally:
        if file and not file.closed:file.close()
