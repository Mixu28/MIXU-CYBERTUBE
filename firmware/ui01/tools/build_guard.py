Import('env')
from SCons.Script import COMMAND_LINE_TARGETS
# This project is deliberately build-only in the authorized offline phase.
for target in COMMAND_LINE_TARGETS:
    if target.startswith(('upload','erase','monitor','program','debug')):
        raise RuntimeError('MIXU offline phase: hardware target is disabled')

