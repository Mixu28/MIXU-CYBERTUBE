"""Read-only ESP image integrity check; never imports serial or touches a port."""
import hashlib
import json
from pathlib import Path
import struct
import sys

def inspect(path):
    data=Path(path).read_bytes()
    if len(data)<24 or data[0]!=0xe9 or not 1<=data[1]<=16:
        raise ValueError('Invalid ESP image header')
    chip=struct.unpack_from('<H',data,12)[0]
    if chip!=9:
        raise ValueError('Not ESP32-S3')
    cursor=24
    checksum=0xef
    segments=[]
    for _ in range(data[1]):
        if cursor+8>len(data): raise ValueError('Truncated segment header')
        address,length=struct.unpack_from('<II',data,cursor)
        cursor+=8
        if length>len(data)-cursor: raise ValueError('Truncated segment payload')
        segments.append({'address':hex(address),'bytes':length})
        for b in data[cursor:cursor+length]: checksum^=b
        cursor+=length
    padded=(cursor+16)//16*16
    if data[padded-1]!=checksum: raise ValueError('ESP image XOR checksum mismatch')
    if data[23]!=1: raise ValueError('Expected appended SHA-256')
    if hashlib.sha256(data[:padded]).digest()!=data[padded:padded+32]:
        raise ValueError('ESP image appended SHA-256 mismatch')
    if len(data)!=padded+32: raise ValueError('Unexpected trailing image data')
    if data[0x8000:0x8003]==b'\xaa\x50\x01':
        raise ValueError('Looks like merged partition table')
    return {'bytes':len(data),'chip_id':chip,'segments':segments,
            'image_checksum':'passed','appended_sha256':'passed',
            'sha256':hashlib.sha256(data).hexdigest(),'raw_application':True,
            'slot_size_64k_aligned':((len(data)+65535)//65536)*65536}

if __name__=='__main__':
    print(json.dumps(inspect(sys.argv[1]),indent=2))
