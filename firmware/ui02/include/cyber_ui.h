#pragma once
#include <cstdint>
#include <cstdio>
#include <algorithm>

// 240x135 HUD. No sprites, heap buffers, images or additional display rotation.
namespace cyber {
constexpr uint16_t Black=0x0000, Panel=0x0841, Green=0x47e2,
    Magenta=0xf81f, Cyan=0x07ff, Muted=0x9d3a, Edge=0x118b,
    PinkGlow=0x580b, BlueGlow=0x018c, Selected=0x2008;
constexpr uint32_t SplashDurationMs=5000;
constexpr const char SplashCaption[]="MIXU CYBERPUNKTUBE";
template<class D> void text(D& d,int x,int y,const char* s,uint16_t c=Cyan,uint16_t bg=Black) {
    d.setTextColor(c,bg); d.setCursor(x,y); d.print(s);
}
template<class D> void frame(D& d,const char* heading) {
    d.fillScreen(Black); d.setTextSize(1); d.setTextWrap(false);
    d.drawFastHLine(4,2,232,Edge);
    text(d,8,7,heading);
    d.drawFastHLine(4,19,197,Cyan); d.drawFastHLine(205,19,31,Magenta);
}
template<class D> void libraryHeader(D& d,unsigned count,bool sd,int volume) {
    frame(d,"MIXU CYBERTUBE");
    char line[48];
    std::snprintf(line,sizeof(line),"%03u VIDEOS  SD:%s  AUD:%03d",count,sd?"OK":"ERR",volume);
    text(d,6,23,line,Cyan);
}
template<class D> void row(D& d,int y,const char* name,bool selected) {
    d.fillRect(4,y,232,12,selected?Selected:Panel);
    if(selected) {
        d.drawRect(4,y,232,12,Magenta); d.fillRect(4,y,3,12,Magenta);
    }
    text(d,10,y+2,selected?">":" ",selected?Magenta:Muted,selected?Selected:Panel);
    text(d,22,y+2,name,selected?Cyan:Muted,selected?Selected:Panel);
}
template<class D> void footer(D& d) {
    d.drawFastHLine(4,112,232,Edge);
    text(d,6,116,"W/S ;/. SELECT  ENTER PLAY",Cyan);
    text(d,6,126,"N/P VIDEO  R SCAN  +/- VOL",Muted);
}
template<class D> void osd(D& d,const char* name,uint64_t sample,uint64_t total,
                            uint32_t rate,int volume,bool paused) {
    d.fillRect(0,100,240,35,Black);
    d.drawFastHLine(4,100,232,Magenta);
    text(d,6,103,name,Cyan);
    unsigned long sec=rate?sample/rate:0, duration=rate?total/rate:0;
    char line[48];
    std::snprintf(line,sizeof(line),"%s %02lu:%02lu/%02lu:%02lu V:%03d",
        paused?"PAUSE":"PLAY",sec/60,sec%60,duration/60,duration%60,volume);
    text(d,6,114,line);
    d.drawRect(4,127,232,5,Edge);
    if(total) d.fillRect(5,128,int(std::min(sample,total)*230/total),3,Magenta);
}
template<class D> void menu(D& d,unsigned selected,int volume) {
    frame(d,"MIXU // PAUSED");
    const char* items[]={"RESUME","NEXT VIDEO","PREV VIDEO","VOLUME","EXIT TO LIBRARY"};
    char value[32];
    for(unsigned i=0;i<5;++i) {
        std::snprintf(value,sizeof(value),"VOLUME  %03d  +/-",volume);
        row(d,25+i*14,i==3?value:items[i],i==selected);
    }
    text(d,6,101,"W/S ;/. SELECT  ENTER OK",Cyan);
    text(d,6,114,"SPACE RESUME  +/- VOLUME",Muted);
    text(d,6,125,"Q LIB  N/P VIDEO  R OSD",Muted);
}
// Four 7x7 angular letter masks: 28 bytes, expanded directly to primitives.
// Bracket framing echoes the local project icon; no bitmap is embedded.
template<class D> void logo(D& d) {
    static constexpr uint8_t glyphs[4][7]={
        {0x63,0x77,0x7f,0x6b,0x63,0x63,0x63}, // M
        {0x7f,0x7f,0x1c,0x1c,0x1c,0x7f,0x7f}, // I
        {0x63,0x77,0x3e,0x1c,0x3e,0x77,0x63}, // X
        {0x63,0x63,0x63,0x63,0x63,0x7f,0x3e}  // U
    };
    // Draw halos first, then offset blue edges and the bright neon cores.
    for(int pass=0;pass<3;++pass) for(int letter=0;letter<4;++letter)
        for(int y=0;y<7;++y) for(int x=0;x<7;++x) {
            if(!(glyphs[letter][y]&(0x40>>x))) continue;
            int px=24+letter*50+x*6, py=36+y*6;
            if(pass==0) d.fillRect(px-2,py-2,10,10,letter%2?BlueGlow:PinkGlow);
            else if(pass==1) d.fillRect(px+1,py+1,7,7,Cyan);
            else d.fillRect(px,py,6,6,letter%2?Cyan:Magenta);
        }
}
template<class D> void splash(D& d) {
    d.fillScreen(Black); d.setTextSize(1); d.setTextWrap(false);
    text(d,12,8,"MIXU // NEON SYSTEM",Cyan);
    text(d,12,122,"V1.1 / UI02",Muted);
    text(d,162,122,"MCV1 READY",Cyan);
    // Open HUD corners keep the large wordmark visually uncluttered.
    d.drawFastHLine(8,25,48,Magenta); d.fillRect(8,25,2,25,Magenta);
    d.drawFastHLine(184,87,48,Cyan); d.fillRect(230,64,2,24,Cyan);
    d.drawFastHLine(8,87,18,BlueGlow); d.drawFastHLine(214,25,18,PinkGlow);
    logo(d);
    constexpr int captionX=(240-(sizeof(SplashCaption)-1)*12)/2;
    d.setTextSize(2);
    text(d,captionX+1,99,SplashCaption,PinkGlow);
    text(d,captionX,98,SplashCaption,Cyan);
    d.setTextSize(1);
}
} // namespace cyber
