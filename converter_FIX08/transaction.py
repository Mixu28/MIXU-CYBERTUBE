"""Publish a whole validated SD layout via one directory rename, never a half set."""
import json
import os
from pathlib import Path
import re
import shutil
import uuid

def safe_name(value):
    value=re.sub(r'[\x00-\x1f<>:"/\\|?*]','_',str(value)).strip(' .')[:60].rstrip(' .')
    if not value:raise ValueError('Videoname fehlt')
    if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',value,re.I):value='VIDEO_'+value
    return value

class OutputGroup:
    def __init__(self,root,name):
        self.root=Path(root).absolute();self.name=safe_name(name)
        self.final=self.root/self.name
        if os.path.lexists(self.final):raise FileExistsError('Ergebnisordner existiert bereits: '+str(self.final))
        self.stage=self.root/('.mixu_'+uuid.uuid4().hex+'.partial')
        self.videos=self.stage/'MIXU-CYBERTUBE/VIDEOS';self.published=False
    def __enter__(self):
        self.root.mkdir(parents=True,exist_ok=True);self.stage.mkdir(exist_ok=False)
        self.videos.mkdir(parents=True);return self
    def publish(self,result):
        if os.name!='nt':raise OSError('Die atomare Ordnerveroeffentlichung dieser Fassung ist fuer Windows implementiert')
        with (self.stage/'RESULT.json').open('x',encoding='utf-8') as f:
            json.dump(result,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
        # Windows rename refuses an existing final path, atomically for the whole set.
        os.rename(self.stage,self.final);self.published=True
    def __exit__(self,*unused):
        if self.published:return
        if self.stage.exists():
            if self.stage.parent.resolve()!=self.root.resolve() or self.stage.is_symlink() or getattr(self.stage,'is_junction',lambda:False)():
                raise RuntimeError('Temporaerer Auftragspfad hat sich geaendert; Bereinigung verweigert')
            shutil.rmtree(self.stage)
