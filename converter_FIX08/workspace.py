"""Temporary workspaces compatible with restricted Windows process tokens."""
from contextlib import contextmanager
from pathlib import Path
import os
import shutil
import uuid

@contextmanager
def temporary_directory(prefix='mixu-'):
    parent=(Path(__file__).resolve().parent/'.tmp').resolve()
    parent.mkdir(parents=True,exist_ok=True)
    path=parent/(prefix+uuid.uuid4().hex)
    # Python 3.13+ mkdir(0700) creates a Windows ACL which excludes restricted
    # tokens. Default inherited permissions also let the FFmpeg child write.
    os.mkdir(path,0o777)
    try:
        yield str(path)
    finally:
        if path.parent.resolve()!=parent or path.is_symlink() or getattr(path,'is_junction',lambda:False)():
            raise RuntimeError('Temporary workspace path changed; refusing cleanup')
        shutil.rmtree(path)
