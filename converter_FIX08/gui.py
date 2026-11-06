"""User-triggered YouTube/local workflow with bounded UI events and cancellation."""
import argparse
import importlib.util
import os
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog,messagebox,ttk
import engine
from ffmpeg_tools import ffmpeg_path
from youtube import canonical_url

class Converter:
    def __init__(self,root):
        self.root=root;self.events=queue.Queue();self.busy=False;self.cancel_event=threading.Event();self.result=None
        root.title('MIXU CYBERTUBE // FIX08 YouTube Auto-Split');root.geometry('920x710')
        frame=ttk.Frame(root,padding=16);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='MIXU // CYBERTUBE FIX08',font=('Consolas',20,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Max. 2:30 Stunden · 240 x 135 · 15 FPS · JPEG 4:2:0 · PCM mono 16000 Hz').pack(anchor='w',pady=8)
        self.url=tk.StringVar();self.source=tk.StringVar();self.output=tk.StringVar(value=str(Path(__file__).resolve().parent/'output'))
        self.name=tk.StringVar();self.quality=tk.StringVar(value='5');self.preview=tk.BooleanVar(value=False)
        for label,var,action in [('YouTube-Link',self.url,None),('Oder lokale Videodatei',self.source,self.choose_source),
                                 ('Ausgabe-Basisordner',self.output,self.choose_output),('Name (optional)',self.name,None)]:
            row=ttk.Frame(frame);row.pack(fill='x',pady=4)
            ttk.Label(row,text=label,width=25).pack(side='left');ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
            if action:ttk.Button(row,text='Waehlen',command=action).pack(side='right')
        ttk.Label(frame,text='Ein eingetragener YouTube-Link hat Vorrang. Erst Start loest Download/Verarbeitung aus.').pack(anchor='w')
        row=ttk.Frame(frame);row.pack(fill='x',pady=8)
        ttk.Label(row,text='Qualitaetszahl 2..15 (bleibt unveraendert)').pack(side='left')
        ttk.Entry(row,textvariable=self.quality,width=5).pack(side='left',padx=6)
        ttk.Checkbutton(row,text='Nur 5-Minuten-Probe konvertieren',variable=self.preview).pack(side='left')
        self.title=tk.StringVar(value='Noch keine Quelle verarbeitet');ttk.Label(frame,textvariable=self.title,wraplength=875).pack(anchor='w')
        ttk.Label(frame,text='Download').pack(anchor='w');self.download_bar=ttk.Progressbar(frame,maximum=100);self.download_bar.pack(fill='x')
        ttk.Label(frame,text='Konvertierung und Gesamtpruefung').pack(anchor='w');self.bar=ttk.Progressbar(frame,maximum=100);self.bar.pack(fill='x')
        self.sizes=tk.StringVar(value='Automatisch: 1 oder 2 Dateien, maximal 2.040.109.000 Byte je Datei')
        ttk.Label(frame,textvariable=self.sizes).pack(anchor='w',pady=5)
        row=ttk.Frame(frame);row.pack(fill='x',pady=6)
        self.start_button=ttk.Button(row,text='Start: herunterladen / konvertieren',command=self.start);self.start_button.pack(side='left')
        self.cancel_button=ttk.Button(row,text='Abbrechen',command=self.cancel,state='disabled');self.cancel_button.pack(side='left',padx=8)
        self.open_button=ttk.Button(row,text='microSD-Ergebnisordner oeffnen',command=self.open_result,state='disabled');self.open_button.pack(side='left')
        self.files=ttk.Treeview(frame,columns=('name','size'),show='headings',height=3)
        self.files.heading('name',text='Fertige Datei');self.files.heading('size',text='Bytes');self.files.column('name',width=580)
        self.files.pack(fill='x',pady=5)
        self.log=tk.Text(frame,height=9,state='disabled');self.log.pack(fill='both',expand=True)
        root.after(100,self.poll);root.protocol('WM_DELETE_WINDOW',self.close)
    def choose_source(self):
        value=filedialog.askopenfilename(filetypes=[('Lokale Videos','*.mp4 *.mkv *.webm *.mov'),('Alle Dateien','*.*')])
        if value:self.source.set(value);self.url.set('')
    def choose_output(self):
        value=filedialog.askdirectory(title='Basisordner fuer einen neuen microSD-Ergebnisordner')
        if value:self.output.set(value)
    def start(self):
        if self.busy:return
        url=self.url.get().strip();source=self.source.get().strip();output=self.output.get().strip()
        try:
            if url:url=canonical_url(url)
            elif not Path(source).is_file():raise ValueError('YouTube-Link oder vorhandene lokale Videodatei waehlen')
            if not output:raise ValueError('Ausgabe-Basisordner fehlt')
            quality=int(self.quality.get())
            if not 2<=quality<=15:raise ValueError('Qualitaetszahl muss 2 bis 15 sein')
        except Exception as exc:messagebox.showerror('Eingabe',str(exc));return
        name=self.name.get().strip() or None;seconds=300 if self.preview.get() else None
        self.busy=True;self.result=None;self.cancel_event=threading.Event()
        self.start_button.configure(state='disabled');self.cancel_button.configure(state='normal');self.open_button.configure(state='disabled')
        self.bar['value']=0;self.download_bar['value']=0
        for item in self.files.get_children():self.files.delete(item)
        def worker():
            last=[0.0]
            def status(data):
                now=time.monotonic()
                if now-last[0]>=.15 or data['phase'] in ('source','done'):
                    self.events.put(('status',data));last[0]=now
            try:
                function=engine.from_youtube if url else engine.convert
                result=function(url or source,output,name=name,quality=quality,seconds=seconds,
                    cancel=self.cancel_event,log=lambda s:self.events.put(('log',s)),status=status)
                self.events.put(('done',result))
            except Exception as exc:self.events.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    def cancel(self):self.cancel_event.set();self.cancel_button.configure(state='disabled')
    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='status':
                    phase=value['phase'];fraction=value.get('fraction',0)
                    if phase=='source':self.title.set(f'{value["title"]}  |  {value["duration"]/60:.2f} Minuten')
                    elif phase=='download':self.download_bar['value']=fraction*100
                    elif phase=='audio':self.bar['value']=fraction*20
                    elif phase=='video':
                        self.bar['value']=20+fraction*65
                        self.sizes.set(' | '.join(f'Teil {i+1}: {n:,} / 2.040.109.000 Byte' for i,n in enumerate(value['bytes'])))
                    elif phase=='validate':self.bar['value']=85+fraction*15
                    continue
                if kind=='done':
                    self.result=value;self.bar['value']=100
                    if 'download_path' in value:self.download_bar['value']=100
                    self.sizes.set(f'{len(value["files"])} Datei(en) fertig und gemeinsam geprueft')
                    for file in value['files']:self.files.insert('','end',values=(file['name'],f'{file["bytes"]:,}'))
                    value='Ergebnis: '+value['job_dir']
                self.log.configure(state='normal');self.log.insert('end',str(value)+'\n');self.log.see('end')
                if int(self.log.index('end-1c').split('.')[0])>200:self.log.delete('1.0','100.0')
                self.log.configure(state='disabled')
                if kind in ('done','error'):
                    self.busy=False;self.start_button.configure(state='normal');self.cancel_button.configure(state='disabled')
                    self.open_button.configure(state='normal' if self.result else 'disabled')
                    if kind=='error':messagebox.showerror('FIX08',str(value))
        except queue.Empty:pass
        self.root.after(100,self.poll)
    def open_result(self):
        if self.result:os.startfile(self.result['job_dir'])
    def close(self):
        if self.busy:self.cancel();messagebox.showinfo('Abbruch','Abbruch angefordert; bitte die sichere Bereinigung abwarten.');return
        self.root.destroy()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    root=tk.Tk()
    if args.self_test:root.withdraw()
    app=Converter(root)
    if args.self_test:
        root.update();assert not app.busy and app.url.get()=='' and not app.preview.get()
        assert Path(ffmpeg_path()).is_file() and (Path(__file__).parent/'validate_mcv.exe').is_file()
        root.destroy();print('FIX08 GUI/Startskript OK; kein Download ausgefuehrt.');return
    root.mainloop()
if __name__=='__main__':main()
