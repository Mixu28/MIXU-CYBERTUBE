#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>

namespace mcv {
constexpr size_t MaxJpeg = 32768, MaxPcm = 4096;
inline uint16_t u16(const uint8_t* p) { return p[0] | (uint16_t(p[1]) << 8); }
inline uint32_t u32(const uint8_t* p) { return u16(p) | (uint32_t(u16(p+2)) << 16); }
inline uint64_t u64(const uint8_t* p) { return u32(p) | (uint64_t(u32(p+4)) << 32); }
inline uint32_t crcUpdate(uint32_t c, const uint8_t* p, size_t n) {
    while (n--) {
        c ^= *p++;
        for (int b=0;b<8;++b) c = (c >> 1) ^ (0xedb88320u & (0u-(c & 1u)));
    }
    return c;
}
inline uint32_t crc(const uint8_t* p, size_t n) { return ~crcUpdate(0xffffffffu,p,n); }
inline const char* jpegProfileError(const uint8_t* j, size_t n) {
    if (n<4 || j[0]!=255 || j[1]!=216 || j[n-2]!=255 || j[n-1]!=217) return "E_JPEG_FILE: boundary";
    size_t p=2; bool found=false;
    while (p<n-2) {
        if (j[p]!=255) return "E_JPEG_FILE: marker";
        while (p<n && j[p]==255) ++p;
        if (p>=n) return "E_JPEG_FILE: truncated marker";
        uint8_t marker=j[p++];
        if (p+2>n) return "E_JPEG_FILE: truncated segment";
        size_t len=(size_t(j[p])<<8)|j[p+1];
        if (len<2 || len>n-p) return "E_JPEG_FILE: segment length";
        if (marker>=0xc0 && marker<=0xcf && marker!=0xc4 && marker!=0xc8 && marker!=0xcc) {
            if (marker!=0xc0) return "E_JPEG_UNSUPPORTED: baseline required";
            if (len!=17) return "E_JPEG_UNSUPPORTED: three components required";
            if (j[p+2]!=8 || j[p+3]!=0 || j[p+4]!=135 ||
                j[p+5]!=0 || j[p+6]!=240 || j[p+7]!=3)
                return "E_JPEG_UNSUPPORTED: 240x135 8-bit required";
            if ((j[p+9]!=0x11 && j[p+9]!=0x21 && j[p+9]!=0x22) ||
                j[p+12]!=0x11 || j[p+15]!=0x11)
                return "E_JPEG_UNSUPPORTED: sampling";
            found=true;
        }
        if (marker==0xda) return found?nullptr:"E_JPEG_FILE: no SOF";
        p+=len;
    }
    return "E_JPEG_FILE: no scan";
}
struct Header {
    uint32_t fps=0, rate=0, frames=0, maxJpeg=0;
    uint64_t samples=0;
    uint64_t sampleAt(uint32_t i) const { return uint64_t(i)*rate/fps; }
    uint64_t timeUs(uint64_t sample) const { return sample*1000000ULL/rate; }
};
struct Frame {
    uint32_t index=0, count=0, jpegSize=0;
    uint64_t pts=0;
    alignas(4) int16_t pcm[MaxPcm/2];
    uint8_t jpeg[MaxJpeg];
};
// Stream needs read(uint8_t*, size_t), position() and size(). No allocation.
template<class Stream> class Reader {
    Stream& s;
    uint32_t nextIndex=0;
    bool fail(const char* text) { error=text; return false; }
public:
    Header h;
    const char* error="";
    explicit Reader(Stream& stream):s(stream) {}
    bool open() {
        nextIndex=0; error="";
        uint8_t b[64];
        if (s.read(b,64)!=64) return fail("E_SD_READ: header incomplete");
        if (crc(b,60)!=u32(b+60)) return fail("Header CRC");
        if (memcmp(b,"MCV1",4) || u16(b+4)!=1 || u16(b+6)!=64 || u16(b+8)!=240 ||
            u16(b+10)!=135 || u32(b+16)!=1 || u16(b+24)!=1 || u16(b+26)!=16)
            return fail("Unsupported MCV profile");
        for (int i=44;i<60;++i) if (b[i]) return fail("Reserved header bytes");
        h.fps=u32(b+12); h.rate=u32(b+20); h.frames=u32(b+28);
        h.samples=u64(b+32); h.maxJpeg=u32(b+40);
        if ((h.fps!=12 && h.fps!=15) || (h.rate!=16000 && h.rate!=22050) ||
            !h.frames || h.frames>h.fps*86400u || h.samples!=h.sampleAt(h.frames) ||
            h.maxJpeg<4 || h.maxJpeg>MaxJpeg) return fail("Invalid MCV limits");
        return true;
    }
    bool next(Frame& f) {
        if (nextIndex>=h.frames) return fail("No further frames");
        uint8_t b[32];
        if (s.read(b,32)!=32) return fail("E_SD_READ: block header incomplete");
        f.index=u32(b+4); f.pts=u64(b+8); f.count=u32(b+16); f.jpegSize=u32(b+20);
        if (crc(b,28)!=u32(b+28) || memcmp(b,"FRM1",4) || f.index!=nextIndex ||
            f.pts!=h.sampleAt(nextIndex) || f.count!=h.sampleAt(nextIndex+1)-f.pts)
            return fail("Block CRC/timestamp");
        if (f.count>MaxPcm/2 || f.jpegSize<4 || f.jpegSize>h.maxJpeg)
            return fail("E_FRAME_LENGTH");
        const uint64_t payload=uint64_t(f.count)*2+f.jpegSize;
        if (uint64_t(s.position())>uint64_t(s.size()) || payload>uint64_t(s.size())-s.position())
            return fail("E_FRAME_TRUNCATED");
        auto audio=reinterpret_cast<uint8_t*>(f.pcm);
        if (s.read(audio,f.count*2)!=f.count*2 || s.read(f.jpeg,f.jpegSize)!=f.jpegSize)
            return fail("E_SD_READ: payload");
        uint32_t c=crcUpdate(0xffffffffu,audio,f.count*2);
        if (~crcUpdate(c,f.jpeg,f.jpegSize)!=u32(b+24)) return fail("E_PAYLOAD_CRC");
        if (const char* profile=jpegProfileError(f.jpeg,f.jpegSize)) return fail(profile);
        ++nextIndex;
        if (nextIndex==h.frames && s.position()!=s.size()) return fail("Trailing file data");
        return true;
    }
};
} // namespace mcv
