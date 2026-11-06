"""Bounded baseline JPEG framing; segment payloads may themselves contain FFD9."""
from mcv import MAX_JPEG,FormatError,check_jpeg

class JpegFrames:
    def __init__(self,stream):self.stream=stream;self.buffer=b'';self.pos=0
    def take(self,n,allow_eof=False):
        while len(self.buffer)-self.pos<n:
            rest=self.buffer[self.pos:];chunk=self.stream.read(65536)
            self.buffer=rest+chunk;self.pos=0
            if not chunk:
                if allow_eof and not rest:return None
                raise FormatError('JPEG-Pipe vorzeitig beendet')
        result=self.buffer[self.pos:self.pos+n];self.pos+=n;return result
    def __iter__(self):
        while True:
            start=self.take(2,True)
            if start is None:return
            if start!=b'\xff\xd8':raise FormatError('JPEG-Pipe: SOI fehlt')
            data=bytearray(start)
            def append(part):
                if len(data)+len(part)>MAX_JPEG:raise FormatError('JPEG > 32768 Byte; Qualitaetszahl erhoehen')
                data.extend(part)
            while True:
                marker=self.take(2)
                if marker[0]!=255:raise FormatError('JPEG-Pipe: Marker fehlt')
                while marker[1]==255:append(b'\xff');marker=b'\xff'+self.take(1)
                append(marker)
                length=self.take(2);n=int.from_bytes(length,'big')
                if n<2 or n>MAX_JPEG:raise FormatError('JPEG-Segmentlaenge ungueltig')
                append(length);append(self.take(n-2))
                if marker[1]==0xda:break
            while True:
                if self.pos==len(self.buffer):
                    self.buffer=self.stream.read(65536);self.pos=0
                    if not self.buffer:raise FormatError('JPEG-Scan unvollstaendig')
                found=self.buffer.find(b'\xff',self.pos)
                if found<0:append(self.buffer[self.pos:]);self.pos=len(self.buffer);continue
                append(self.buffer[self.pos:found]);self.pos=found
                append(self.take(1));code=self.take(1)[0];append(bytes([code]))
                while code==255:code=self.take(1)[0];append(bytes([code]))
                if code==0xd9:break
                if code!=0 and not 0xd0<=code<=0xd7:raise FormatError('JPEG-Scanmarker nicht unterstuetzt')
            check_jpeg(data)
            yield bytes(data)
