"""Build a deterministic Windows x64 validator using documented GCC/MinGW-w64.
Run: set MINGW_BIN to your UCRT64 bin directory, then py -3 build_validator.py.
Only local source/object/PE files are processed; no download, COM or upload API.
"""
from pathlib import Path
import os,shutil,subprocess,hashlib,json,re,argparse
BASE=Path(__file__).resolve().parent

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    native=BASE/'native'
    toolroot=os.environ.get('MINGW_BIN')
    def tool(name):
        found=str(Path(toolroot)/(name+'.exe')) if toolroot else shutil.which(name)
        if not found or not Path(found).is_file():raise RuntimeError('Missing UCRT64 tool: '+name+'; set MINGW_BIN')
        return Path(found).resolve()
    gcc,gxx,objdump=tool('gcc'),tool('g++'),tool('objdump')
    env=dict(os.environ,SOURCE_DATE_EPOCH='1609459200',PYTHONDONTWRITEBYTECODE='1',LC_ALL='C')
    env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    def run(args):
        result=subprocess.run([str(a) for a in args],env=env,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        return result.stdout
    common=['-O2','-fno-ident','-frandom-seed=mixu-fix08-github03',
            '-ffile-prefix-map='+str(BASE)+'=.', '-ffile-prefix-map='+str(output)+'=.',
            '-fdebug-prefix-map='+str(BASE)+'=.', '-fdebug-prefix-map='+str(output)+'=.']
    run([gcc,*common,'-std=c11','-I'+str(native/'lgfx/utility'),'-c',native/'lgfx/utility/lgfx_tjpgd.c','-o',output/'decoder.o'])
    run([gxx,*common,'-std=c++17','-municode','-I'+str(native),native/'validate_mcv.cpp',output/'decoder.o',
         '-static','-static-libgcc','-static-libstdc++','-Wl,--no-insert-timestamp',
         '-Wl,--build-id=none','-Wl,--strip-all','-Wl,-Map,'+str(output/'validator.map'),'-o',output/'validate_mcv.exe'])
    text=(output/'validator.map').read_text(encoding='utf-8',errors='replace')
    pulled=text.split('Discarded input sections',1)[0]
    archives=[]
    for name in sorted(set(re.findall(r'([^\s()]+\.a)\(',pulled))):
        path=Path(name).resolve()
        if not path.is_file():raise RuntimeError('Cannot identify link archive: '+name)
        archives.append({'name':path.name,'sha256':digest(path),'bytes':path.stat().st_size})
    imports=re.findall(r'DLL Name:\s*(\S+)',run([objdump,'-p',output/'validate_mcv.exe']))
    result={'gcc_version':run([gcc,'-dumpfullversion','-dumpversion']).strip(),
            'target':run([gcc,'-dumpmachine']).strip(),'gcc_sha256':digest(gcc),'gxx_sha256':digest(gxx),
            'source_sha256':{p.relative_to(BASE).as_posix():digest(p) for p in sorted(native.rglob('*')) if p.is_file()},
            'flags':common[:3]+['-std=c11/-std=c++17','-municode','-static','-static-libgcc','-static-libstdc++','--no-insert-timestamp','--build-id=none','--strip-all','path prefix maps to .'],
            'source_date_epoch':env['SOURCE_DATE_EPOCH'],'validator_sha256':digest(output/'validate_mcv.exe'),
            'validator_bytes':(output/'validate_mcv.exe').stat().st_size,'static_archives_with_pulled_members':archives,
            'system_dll_imports':imports,'dlls_distributed':False,
            'compilation_process':'Plain original C/C++ through unmodified installed GCC, no requested LTO or custom GCC plugins; native object code'}
    (output/'build_info.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=BASE/'.build-validator')
    args=parser.parse_args();print(json.dumps(build(args.output),indent=2))
