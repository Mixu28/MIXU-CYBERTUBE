"""Own-process cancellation, including yt-dlp's FFmpeg child on Windows."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import os
import signal
import subprocess
import threading

class Cancelled(RuntimeError):pass
def check_cancel(cancel):
    if cancel is not None and cancel.is_set():raise Cancelled('Abgebrochen. Keine fertigen MCV-Dateien veroeffentlicht.')

class WindowsJob:
    def __init__(self,process):
        self.handle=None;self.lock=threading.Lock()
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);self.kernel=kernel
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];kernel.CreateJobObjectW.restype=wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetInformationJobObject.restype=wintypes.BOOL
        kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE];kernel.AssignProcessToJobObject.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        class Basic(ctypes.Structure):
            _fields_=[('per_process',ctypes.c_longlong),('per_job',ctypes.c_longlong),('flags',wintypes.DWORD),
                ('min_working_set',ctypes.c_size_t),('max_working_set',ctypes.c_size_t),('active',wintypes.DWORD),
                ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):_fields_=[(name,ctypes.c_ulonglong) for name in ('read','write','other','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
                ('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        handle=kernel.CreateJobObjectW(None,None)
        if not handle:raise OSError('Windows-Prozessschutz konnte nicht erzeugt werden')
        self.handle=handle;info=Extended();info.basic.flags=0x2000 # KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            self.close();raise OSError('Windows-Prozessschutz konnte nicht eingerichtet werden')
        if not kernel.AssignProcessToJobObject(handle,wintypes.HANDLE(int(process._handle))) and process.poll() is None:
            self.close();raise OSError('Unterprozess konnte nicht dem Windows-Prozessschutz zugeordnet werden')
    def close(self):
        with self.lock:
            if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None

@contextmanager
def managed_process(args,*,cancel=None,**kwargs):
    check_cancel(cancel)
    env=dict(os.environ);env.update(kwargs.pop('env',{}))
    flags=kwargs.pop('creationflags',0)
    if os.name=='nt':flags|=subprocess.CREATE_NO_WINDOW
    else:kwargs['start_new_session']=True
    process=subprocess.Popen([str(a) for a in args],env=env,creationflags=flags,**kwargs)
    job=None;done=threading.Event();watcher=None
    def kill_owned():
        if job:job.close()
        elif process.poll() is None:
            if os.name=='nt':process.terminate()
            else:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
    try:
        if os.name=='nt':job=WindowsJob(process)
        if cancel is not None:
            def watch():
                while not done.wait(.05):
                    if cancel.is_set():kill_owned();return
            watcher=threading.Thread(target=watch,daemon=True);watcher.start()
        try:
            yield process
            check_cancel(cancel)
        except BaseException:
            kill_owned()
            check_cancel(cancel)
            raise
    finally:
        done.set()
        if watcher:watcher.join(timeout=1)
        kill_owned()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        if process.stdout:process.stdout.close()
        if process.stderr:process.stderr.close()
