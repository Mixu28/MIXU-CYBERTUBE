// Streaming verifier using the unchanged FIX06 MCV reader and JPEG decoder.
#include "mcv_reader.h"
#include "jpeg_decode.h"
#include <bitset>
#include <fstream>
#include <iostream>
#include <cstdint>
#include <string>
#include <filesystem>
struct File {
    std::ifstream stream;
    uint64_t offset=0,length=0;
    explicit File(const std::filesystem::path& path):stream(path,std::ios::binary) {
        if(!stream)return;
        stream.seekg(0,std::ios::end);auto end=stream.tellg();
        if(end>=0)length=uint64_t(end);
        stream.seekg(0);
    }
    size_t read(uint8_t* data,size_t count) {
        stream.read(reinterpret_cast<char*>(data),count);size_t got=stream.gcount();offset+=got;return got;
    }
    uint64_t size() const {return length;}
    uint64_t position() const {return offset;}
};
struct Coverage {std::bitset<240*135> pixels;unsigned bottom=0;};
static uint32_t output(void* target,void*,JRECT* rect) {
    auto& covered=*static_cast<Coverage*>(target);
    if(rect->left>rect->right || rect->top>rect->bottom || rect->right>=240 || rect->bottom>=135)return 0;
    for(unsigned y=rect->top;y<=rect->bottom;++y)for(unsigned x=rect->left;x<=rect->right;++x){
        size_t index=y*240+x;if(covered.pixels.test(index))return 0;covered.pixels.set(index);
    }
    if(rect->bottom==134)covered.bottom+=rect->right-rect->left+1;
    return 1;
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
#else
int main(int argc,char** argv) {
#endif
    if(argc!=2)return 2;
    File file(argv[1]);
    if(!file.stream || file.length>0x7fffffffULL){std::cerr<<"File missing or exceeds FIX06 signed-offset limit";return 1;}
    mcv::Reader<File> reader(file);if(!reader.open()){std::cerr<<reader.error;return 1;}
    mcv::Frame frame;Coverage covered;
    for(uint32_t i=0;i<reader.h.frames;++i){
        if(!reader.next(frame)){std::cerr<<reader.error<<" frame="<<i;return 1;}
        covered.pixels.reset();covered.bottom=0;
        auto result=mcv::decodeJpeg(frame.jpeg,frame.jpegSize,&covered,output);
        if(!result || covered.pixels.count()!=240*135 || covered.bottom!=240){
            std::cerr<<(result.error?result.error:"E_COVERAGE")<<" JDR="<<result.code<<" frame="<<i;return 1;
        }
    }
    std::cout<<"{\"frames\":"<<reader.h.frames<<",\"samples\":"<<reader.h.samples
             <<",\"bytes\":"<<file.length<<",\"last_offset\":"<<file.offset
             <<",\"all_frames_decoded\":true,\"all_135_rows_covered\":true,\"bounded_frame_bytes\":"<<sizeof(frame)<<"}";
    return 0;
}
