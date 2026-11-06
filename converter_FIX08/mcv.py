"""MCV1: bounded, sequential JPEG/PCM container. Original MIXU implementation."""
import io
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

HEADER = struct.Struct('<4sHHHHIIIHHIQI16sI')
BLOCK = struct.Struct('<4sIQIIII')
MAX_JPEG = 32768
MAX_PCM = 4096

class FormatError(ValueError):
    pass

def crc(data):
    return zlib.crc32(data) & 0xffffffff

@dataclass(frozen=True)
class Header:
    fps: int
    rate: int
    frames: int
    samples: int
    max_jpeg: int

    def pack(self):
        b = HEADER.pack(b'MCV1', 1, 64, 240, 135, self.fps, 1, self.rate,
                        1, 16, self.frames, self.samples, self.max_jpeg, bytes(16), 0)
        return b[:60] + struct.pack('<I', crc(b[:60]))

    @classmethod
    def read(cls, f):
        b = f.read(64)
        if len(b) != 64:
            raise FormatError('Incomplete MCV header')
        magic, ver, size, w, h, num, den, rate, ch, bits, frames, samples, maximum, reserved, checksum = HEADER.unpack(b)
        if crc(b[:60]) != checksum:
            raise FormatError('Header CRC mismatch')
        if (magic, ver, size, w, h, den, ch, bits, reserved) != (b'MCV1', 1, 64, 240, 135, 1, 1, 16, bytes(16)):
            raise FormatError('Unsupported MCV profile')
        if num not in (12, 15) or rate not in (16000, 22050):
            raise FormatError('Unsupported frame/sample rate')
        if not 0 < frames <= num * 86400 or samples != frames * rate // num:
            raise FormatError('Invalid duration/sample count')
        if not 4 <= maximum <= MAX_JPEG:
            raise FormatError('Invalid JPEG limit')
        return cls(num, rate, frames, samples, maximum)

def check_jpeg(jpeg):
    """Check baseline SOF geometry before handing bytes to either decoder."""
    if jpeg[:2] != b'\xff\xd8' or jpeg[-2:] != b'\xff\xd9':
        raise FormatError('JPEG boundary missing')
    p, found = 2, False
    while p < len(jpeg) - 2:
        if jpeg[p] != 255:
            raise FormatError('Invalid JPEG marker')
        while p < len(jpeg) and jpeg[p] == 255:
            p += 1
        if p >= len(jpeg):
            raise FormatError('Truncated JPEG marker')
        marker = jpeg[p]
        p += 1
        if p + 2 > len(jpeg):
            raise FormatError('Truncated JPEG segment')
        n = int.from_bytes(jpeg[p:p+2], 'big')
        if n < 2 or p + n > len(jpeg):
            raise FormatError('Invalid JPEG segment length')
        if 0xc0 <= marker <= 0xcf and marker not in (0xc4, 0xc8, 0xcc):
            if marker != 0xc0 or n != 17 or jpeg[p+2] != 8 or jpeg[p+3:p+7] != b'\x00\x87\x00\xf0' or jpeg[p+7] != 3:
                raise FormatError('JPEG must be baseline 240x135 RGB/YCbCr')
            if jpeg[p+9] != 0x22 or jpeg[p+12] != 0x11 or jpeg[p+15] != 0x11:
                raise FormatError('E_JPEG_UNSUPPORTED: FIX07 requires sampling 22/11/11 (4:2:0)')
            found = True
        if marker == 0xda:
            if not found:
                raise FormatError('JPEG has no baseline SOF')
            return
        p += n
    raise FormatError('JPEG has no scan')

def blocks(f, header):
    for i in range(header.frames):
        b = f.read(32)
        if len(b) != 32:
            raise FormatError(f'Truncated block header {i}')
        magic, index, pts, count, n, checksum, hcrc = BLOCK.unpack(b)
        start = i * header.rate // header.fps
        end = (i + 1) * header.rate // header.fps
        if crc(b[:28]) != hcrc or (magic, index, pts, count) != (b'FRM1', i, start, end-start):
            raise FormatError(f'Invalid block header/timestamp {i}')
        if not 4 <= n <= header.max_jpeg or count * 2 > MAX_PCM:
            raise FormatError(f'Invalid block length {i}')
        pcm, jpeg = f.read(count * 2), f.read(n)
        if len(pcm) != count*2 or len(jpeg) != n or crc(pcm+jpeg) != checksum:
            raise FormatError(f'Truncated/corrupted payload {i}')
        check_jpeg(jpeg)
        yield pts, pcm, jpeg
    if f.read(1):
        raise FormatError('Trailing bytes after final block')

def validate(path, decode=False):
    with open(path, 'rb') as f:
        h = Header.read(f)
        for pts, pcm, jpeg in blocks(f, h):
            if decode:
                from PIL import Image
                with Image.open(io.BytesIO(jpeg)) as image:
                    image.load()
                    if image.size != (240, 135):
                        raise FormatError('Decoded JPEG dimensions mismatch')
        return h
