#pragma once
#include <cstdint>
#include <cstdio>
#include <algorithm>

// 240x135 HUD. No sprites, heap buffers, images or additional display rotation.
namespace cyber {
constexpr uint16_t Black=0x0000, Panel=0x0841, Green=0x47e2,
    Magenta=0xf81f, Cyan=0x07ff, Muted=0x8c71, Edge=0x2248;
template<class D> void text(D& d,int x,int y,const char* s,uint16_t c=Green,uint16_t bg=Black) {
    d.setTextColor(c,bg); d.setCursor(x,y); d.print(s);
}
template<class D> void frame(D& d,const char* heading) {
    d.fillScreen(Black); d.setTextSize(1); d.setTextWrap(false);
    d.drawFastHLine(4,2,232,Edge);
    text(d,8,7,heading);
    d.drawFastHLine(4,19,197,Green); d.drawFastHLine(205,19,31,Magenta);
}
template<class D> void libraryHeader(D& d,unsigned count,bool sd,int volume) {
    frame(d,"MIXU CYBERTUBE");
    char line[48];
    std::snprintf(line,sizeof(line),"%03u VIDEOS  SD:%s  AUD:%03d",count,sd?"OK":"ERR",volume);
    text(d,6,23,line,Cyan);
}
template<class D> void row(D& d,int y,const char* name,bool selected) {
    d.fillRect(4,y,232,12,selected?Edge:Panel);
    if(selected) {
        d.drawRect(4,y,232,12,Green); d.fillRect(4,y,3,12,Magenta);
    }
    text(d,10,y+2,selected?">":" ",selected?Magenta:Muted,selected?Edge:Panel);
    text(d,22,y+2,name,selected?Green:Muted,selected?Edge:Panel);
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
    if(total) d.fillRect(5,128,int(std::min(sample,total)*230/total),3,Green);
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
template<class D> void splash(D& d) {
    frame(d,"MIXU // SYSTEM ONLINE");
    d.drawRect(10,34,220,59,Edge);
    d.drawFastHLine(10,34,70,Magenta);
    text(d,23,46,"MIXU",Cyan);
    d.setTextSize(2); text(d,23,62,"CYBERTUBE"); d.setTextSize(1);
    text(d,12,105,"V1.1 // UI01    MCV1 PLAYER",Muted);
    text(d,12,122,"INITIALIZING MEDIA...",Green);
}
} // namespace cyber
