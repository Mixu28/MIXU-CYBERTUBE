#pragma once
// Same M5GFX decoder, 3900-byte pool and unscaled BGR888 output as drawJpg().
// Preserve its actual result instead of collapsing all errors to false.
#include <lgfx/utility/lgfx_tjpgd.h>
#include <algorithm>
#include <cstdlib>
#include <cstring>
namespace mcv {
struct JpegResult {
    const char* error;
    int code;
    const char* phase;
    explicit operator bool() const { return error==nullptr; }
};
using JpegOutput=uint32_t (*)(void*,void*,JRECT*);
struct JpegInput {
    const uint8_t* bytes;
    size_t size, position;
    void* target;
    JpegOutput output;
};
inline uint32_t jpegRead(void* device,uint8_t* dest,uint32_t count) {
    auto& input=*static_cast<JpegInput*>(device);
    count=std::min<size_t>(count,input.size-input.position);
    if (dest) std::memcpy(dest,input.bytes+input.position,count);
    input.position+=count;
    return count;
}
inline uint32_t jpegOutput(void* device,void* bitmap,JRECT* rect) {
    auto& input=*static_cast<JpegInput*>(device);
    return input.output(input.target,bitmap,rect);
}
inline const char* jpegError(JRESULT result) {
    switch (result) {
    case JDR_MEM1: return "E_JPEG_POOL";
    case JDR_MEM2: return "E_JPEG_INPUT_BUFFER";
    case JDR_FMT2: case JDR_FMT3: return "E_JPEG_UNSUPPORTED";
    case JDR_INP: return "E_JPEG_INPUT"; // Memory input, not an SD read.
    default: return "E_JPEG_DECODE";
    }
}
inline JpegResult decodeJpeg(const uint8_t* data,size_t size,void* target,JpegOutput output,
                            void* (*allocate)(size_t)=std::malloc,
                            void (*release)(void*)=std::free) {
    constexpr size_t PoolSize=3900;
    void* pool=allocate(PoolSize);
    if (!pool) return {"E_MEM_ALLOC",-1,"alloc"};
    JpegInput input{data,size,0,target,output};
    lgfxJdec decoder{};
    auto result=lgfx_jd_prepare(&decoder,jpegRead,pool,PoolSize,&input);
    const char* phase="prepare";
    if (result==JDR_OK && (decoder.width!=240 || decoder.height!=135)) {
        release(pool);
        return {"E_JPEG_UNSUPPORTED",-1,"size"};
    }
    if (result==JDR_OK) {
        phase="decode";
        result=lgfx_jd_decomp(&decoder,jpegOutput,0);
    }
    release(pool);
    return {result==JDR_OK?nullptr:jpegError(result),int(result),phase};
}
} // namespace mcv
