"""FIX08 command-line entry point; nothing downloads until main() is invoked."""
import argparse
import json
import sys
from engine import convert,from_youtube

def main():
    parser=argparse.ArgumentParser(description='FIX08: lokale Datei oder HTTPS-YouTube-Link, automatisch 1 oder 2 MCV-Dateien')
    parser.add_argument('source');parser.add_argument('output_root');parser.add_argument('--name')
    parser.add_argument('--quality',type=int,default=5);parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    worker=from_youtube if args.source.startswith('https://') else convert
    try:
        result=worker(args.source,args.output_root,name=args.name,quality=args.quality,
                      seconds=300 if args.preview else None,log=print)
        print(json.dumps(result,ensure_ascii=False));return 0
    except Exception as exc:print(str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
