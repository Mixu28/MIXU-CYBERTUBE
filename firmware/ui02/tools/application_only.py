"""Suppress pioarduino's factory merge; export the raw application image only."""
Import('env')
from pathlib import Path
import shutil

node=env.File(env.subst('$BUILD_DIR/${PROGNAME}.bin'))
executor=node.get_executor()
removed=0
kept=[]
for action in executor.post_actions:
    if getattr(getattr(action,'execfunction',None),'__name__','')=='esp32_create_combined_bin':
        removed+=1
    else:
        kept.append(action)
executor.post_actions=kept
delayed=[]
for handler,nodes,action in env.get('_PIO_DELAYED_ACTIONS',[]):
    if getattr(getattr(action,'execfunction',None),'__name__','')=='esp32_create_combined_bin':
        removed+=1
    else:
        delayed.append((handler,nodes,action))
env.Replace(_PIO_DELAYED_ACTIONS=delayed)
if removed!=1:
    raise RuntimeError('Pinned platform factory action changed; review application-only build')

def export_application(source,target,env):
    root=Path(env.subst('$PROJECT_DIR'))
    app=Path(env.subst('$BUILD_DIR/${PROGNAME}.bin'))
    data=app.read_bytes()
    if data[0]!=0xe9 or int.from_bytes(data[12:14],'little')!=9:
        raise RuntimeError('Application is not an ESP32-S3 image')
    name=env.GetProjectOption('custom_app_name','MIXU_CYBERTUBE_V1.0_CARDPUTER_ADV_APP.bin')
    if Path(name).name!=name or not name.endswith('.bin'):
        raise RuntimeError('Application export must be a .bin filename')
    dest=root/'artifacts'/name
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(app,dest)
    print('MIXU application-only export: '+str(dest))

env.AddPostAction(node,export_application)
