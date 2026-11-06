#include <M5Cardputer.h>
#include <SD.h>
#include <SPI.h>
#include <esp_timer.h>
#include <atomic>
#include <algorithm>
#include <vector>
#include "mcv_reader.h"
#include "jpeg_decode.h"
#include "video_renderer.h"
#include "library_navigation.h"
#include "cyber_ui.h"

// Original MIXU application; no CardTube source or media incorporated.
namespace {
constexpr uint16_t Neon=cyber::Cyan, Navy=cyber::Black;
unsigned menuRow=0;
constexpr const char* VideoDir="/MIXU-CYBERTUBE/VIDEOS";
SPIClass sdSpi(FSPI);
File video;
mcv::Reader<File> reader(video);
struct Slot {
    mcv::Frame frame;
    std::atomic<bool> busy{false};
    bool loaded=false, shown=false, queued=false;
};
Slot slots[3]; // fixed 108 KiB payload pool, no PSRAM assumed
std::vector<String> library;
int volume=96;
mcv::LibrarySelection selection;
bool libraryVisible=false;
size_t nameOffset=0;
uint32_t nameScrollAt=0;
bool playing=false, paused=false, pauseRequested=false, sdReady=false;
uint32_t readIndex=0, audioIndex=0, displayIndex=0, overlayUntil=0;
uint64_t baseSample=0, pauseSample=0;
int64_t epoch=0;
uint64_t maxReadUs=0, maxDecodeUs=0;
String status;

void released(void*, const void* data, uint8_t) {
    for (auto& s:slots) if (data==s.frame.pcm) s.busy.store(false,std::memory_order_release);
}
void title(const char* text) {
    libraryVisible=false;
    cyber::frame(M5.Display,text);
}
void selectedName() {
    M5.Display.fillRect(0,84,240,16,Navy);
    M5.Display.setTextColor(Neon,Navy);
    String name=library.empty()?"(none)":library[selection.index];
    M5.Display.setCursor(4,84);
    M5.Display.print(name.substring(nameOffset,nameOffset+38));
    M5.Display.setCursor(4,92);
    M5.Display.print(name.substring(nameOffset+38,nameOffset+76));
}
void browser() {
    selection.normalise(library.size());
    cyber::libraryHeader(M5.Display,library.size(),sdReady,volume);
    for (size_t row=0;row<mcv::LibraryRows && selection.first+row<library.size();++row) {
        size_t index=selection.first+row;
        cyber::row(M5.Display,33+row*12,library[index].substring(0,34).c_str(),index==selection.index);
    }
    if (library.empty()) cyber::text(M5.Display,10,53,"NO VIDEOS // R TO RESCAN",cyber::Magenta);
    nameOffset=0; nameScrollAt=millis()+1000;
    selectedName();
    cyber::text(M5.Display,4,103,status.substring(0,38).c_str(),cyber::Muted);
    cyber::footer(M5.Display);
    libraryVisible=true;
}
void scrollSelectedName() {
    if (!libraryVisible || library.empty() || library[selection.index].length()<=76) return;
    uint32_t now=millis();
    if (int32_t(now-nameScrollAt)<0) return;
    size_t maximum=library[selection.index].length()-76;
    nameOffset=nameOffset>=maximum?0:nameOffset+1;
    nameScrollAt=now+((nameOffset==0 || nameOffset==maximum)?1000:250);
    selectedName();
}
void stop() {
    // end() joins the audio worker before any slot can be reused.
    M5.Speaker.end();
    playing=false; paused=false; pauseRequested=false;
    video.close();
    for (auto& s:slots) { s.busy=false; s.loaded=false; s.shown=false; s.queued=false; }
}
void fail(const String& message) {
    stop(); status=message;
    title("MIXU // ERROR");
    M5.Display.setCursor(4,28);
    M5.Display.setTextWrap(true);
    M5.Display.println(message);
    M5.Display.println("\nQ: Library / R: Rescan");
}
void scan() {
    String retained=library.empty()?"":library[selection.index];
    library.clear();
    if (!sdReady) {
        sdSpi.begin(40,39,14,12);
        sdReady=SD.begin(12,sdSpi,20000000);
    }
    if (!sdReady) { status="SD initialization failed"; browser(); return; }
    File directory=SD.open(VideoDir);
    if (!directory || !directory.isDirectory()) { status="VIDEOS directory missing"; browser(); return; }
    while (File f=directory.openNextFile()) {
        String name=f.name();
        int slash=name.lastIndexOf('/'); if (slash>=0) name=name.substring(slash+1);
        if (mcv::isVideoFilename(name.c_str(),f.isDirectory())) {
            mcv::Reader<File> candidate(f);
            if (candidate.open()) library.push_back(name);
        }
        f.close();
    }
    directory.close();
    std::sort(library.begin(),library.end());
    auto found=std::find(library.begin(),library.end(),retained);
    selection.index=found==library.end()?0:size_t(found-library.begin());
    selection.normalise(library.size());
    status=library.empty()?"No .mcv videos found":"";
    browser();
}
bool fill(Slot& s) {
    int64_t begin=esp_timer_get_time();
    if (!reader.next(s.frame)) { fail(reader.error); return false; }
    maxReadUs=std::max(maxReadUs,uint64_t(esp_timer_get_time()-begin));
    s.loaded=true; s.shown=false; s.queued=false;
    ++readIndex;
    return true;
}
uint32_t videoPixels(void*,void* bitmap,JRECT* rect);
void start() {
    if (library.empty()) return;
    stop();
    video=SD.open(String(VideoDir)+"/"+library[selection.index],FILE_READ);
    if (!video || !reader.open()) { fail(video?reader.error:"E_SD_OPEN"); return; }
    readIndex=audioIndex=displayIndex=0;
    maxReadUs=maxDecodeUs=0;
    for (auto& s:slots) if (readIndex<reader.h.frames && !fill(s)) return;
    // FIX04_STARTUP_BEGIN: finish the first image before starting the audio clock.
    M5.Display.waitDMA();
    M5.Display.fillScreen(TFT_BLACK);
    M5.Display.waitDMA();
    M5.Display.startWrite();
    auto firstImage=mcv::decodeJpeg(slots[0].frame.jpeg,slots[0].frame.jpegSize,nullptr,videoPixels);
    M5.Display.waitDMA();
    M5.Display.endWrite();
    if (!firstImage) {
        fail(String(firstImage.error)+" JDR="+String(firstImage.code)+" "+firstImage.phase+" frame=0");
        return;
    }
    // FIX04_STARTUP_END: playback indices remain at zero; service() is unchanged.
    auto cfg=M5.Speaker.config();
    cfg.sample_rate=reader.h.rate;
    cfg.stereo=false;
    cfg.dma_buf_len=128; cfg.dma_buf_count=4;
    M5.Speaker.config(cfg);
    M5.Speaker.setBufferReleaseCallback(nullptr,released);
    M5.Speaker.setVolume(volume);
    if (!M5.Speaker.begin()) { fail("ES8311 audio startup failed"); return; }
    playing=true; baseSample=0; epoch=esp_timer_get_time();
    libraryVisible=false;
    overlayUntil=0; // FIX06: fullscreen start; manual pause/volume OSD remains available.
}
Slot* at(uint32_t i) {
    for (auto& s:slots) if (s.loaded && s.frame.index==i) return &s;
    return nullptr;
}
void overlay(uint64_t sample) {
    if (paused) { cyber::menu(M5.Display,menuRow,volume); return; }
    cyber::osd(M5.Display,library[selection.index].substring(0,38).c_str(),
               sample,reader.h.samples,reader.h.rate,volume,false);
}
uint32_t videoPixels(void*,void* bitmap,JRECT* rect) {
    return mcv::renderVideoBlock(M5.Display,bitmap,*rect);
}
void service() {
    if (!playing) return;
    int64_t now=esp_timer_get_time();
    uint64_t clock=paused?pauseSample:baseSample+uint64_t(std::max<int64_t>(0,now-epoch))*reader.h.rate/1000000;
    // Queue at most two requests. Callback makes buffer ownership explicit.
    if (!paused && !pauseRequested && audioIndex<reader.h.frames && M5.Speaker.isPlaying(0)<2) {
        Slot* s=at(audioIndex);
        if (s && !s->queued) {
            if (clock>s->frame.pts+reader.h.rate/4) { fail("Audio deadline missed (>250ms)"); return; }
            s->busy.store(true,std::memory_order_release);
            if (!M5.Speaker.playRaw(s->frame.pcm,s->frame.count,reader.h.rate,false,1,0,false)) {
                s->busy=false; fail("Audio queue failed"); return;
            }
            s->queued=true; ++audioIndex;
        }
    }
    // Display only audio-queued frames and discard overdue visual frames.
    if (!paused && displayIndex<audioIndex) {
        Slot* s=at(displayIndex);
        if (s && clock>=s->frame.pts) {
            int64_t begin=esp_timer_get_time();
            if (clock<s->frame.pts+s->frame.count || displayIndex+1==audioIndex) {
                M5.Display.startWrite();
                auto decoded=mcv::decodeJpeg(s->frame.jpeg,s->frame.jpegSize,nullptr,videoPixels);
                M5.Display.endWrite();
                if (!decoded) {
                    fail(String(decoded.error)+" JDR="+String(decoded.code)+" "+decoded.phase+
                         " frame="+String(s->frame.index)); return;
                }
            }
            maxDecodeUs=std::max(maxDecodeUs,uint64_t(esp_timer_get_time()-begin));
            s->shown=true; ++displayIndex;
            if (millis()<overlayUntil || pauseRequested) overlay(clock);
        }
    }
    // Pause at the end of all audio already queued; preserve unread media.
    if (pauseRequested && !paused && displayIndex==audioIndex && !M5.Speaker.isPlaying(0) &&
        clock>=reader.h.sampleAt(audioIndex)+reader.h.rate/50) {
        pauseSample=reader.h.sampleAt(audioIndex); paused=true; pauseRequested=false;
        overlay(pauseSample);
    }
    for (auto& s:slots) {
        if (s.loaded && s.shown && s.queued && !s.busy.load(std::memory_order_acquire)) {
            s.loaded=false;
            if (readIndex<reader.h.frames && !fill(s)) return;
        }
    }
    if (!paused && !pauseRequested && displayIndex==reader.h.frames && !M5.Speaker.isPlaying(0) &&
        clock>=reader.h.samples+reader.h.rate/50) {
        String perf="Done. SD/JPG max "+String((unsigned long)(maxReadUs/1000))+"/"+String((unsigned long)(maxDecodeUs/1000))+"ms";
        stop(); status=perf; browser();
    }
}
void pauseToggle() {
    if (!playing) return;
    if (paused) { paused=false; baseSample=pauseSample; epoch=esp_timer_get_time(); }
    else { pauseRequested=!pauseRequested; menuRow=0; }
    overlayUntil=millis()+2500;
}
void input() {
    static mcv::KeyEdges keys;
    auto& k=M5Cardputer.Keyboard;
    uint16_t edge=keys.pressed(mcv::keyboardActions(k));
    if (edge&4) { stop(); status=""; browser(); return; }
    if ((edge&512) && !playing) { SD.end(); sdReady=false; scan(); return; }
    // UI-only dispatch after the unchanged audio-drain pause boundary.
    if (playing && paused) {
        if (edge&(mcv::Up|mcv::Down)) {
            menuRow=(menuRow+((edge&mcv::Down)?1:4))%5;
            overlay(pauseSample);
        }
        if (edge&mcv::Enter) {
            if (menuRow==0) pauseToggle();
            else if (menuRow==1 || menuRow==2) {
                selection.step(menuRow==1?1:-1,library.size()); start();
            } else if (menuRow==4) { stop(); status=""; browser(); }
            // VOLUME uses the existing +/- handler below.
            edge&=~uint16_t(mcv::Enter);
        }
    }
    if ((edge&mcv::Rescan) && playing) {
        overlayUntil=millis()+2500;
        if (paused) overlay(pauseSample);
    }
    if (edge&1) { if (playing) pauseToggle(); else start(); }
    if (edge&2) pauseToggle();
    int direction=mcv::navigationDelta(edge,playing);
    if (direction && !library.empty()) {
        bool resume=playing;
        selection.step(direction,library.size());
        if (resume) start(); else browser();
    }
    if (edge&(128|256)) {
        volume=std::max(0,std::min(255,volume+((edge&128)?8:-8)));
        M5.Speaker.setVolume(volume); overlayUntil=millis()+2500;
        if (paused) overlay(pauseSample);
        else if (!playing) browser();
    }
}
bool validBoard=false;
}
void setup() {
    auto cfg=M5.config();
    cfg.internal_mic=false; cfg.internal_imu=false; cfg.internal_spk=true;
    cfg.serial_baudrate=0;
    M5Cardputer.begin(cfg,true);
    M5.Display.setRotation(0); // FIX01: 90 degrees CCW from 1; ADV offset=1 gives 240x135.
    validBoard=M5.getBoard()==m5::board_t::board_M5CardputerADV;
    if (!validBoard) { title("MIXU // ADV REQUIRED"); return; }
    cyber::splash(M5.Display);
    delay(cyber::SplashDurationMs); // UI02: five-second splash before library scan.
    scan();
}
void loop() {
    if (!validBoard) { delay(100); return; }
    M5Cardputer.update(); input(); service(); scrollSelectedName(); delay(1);
}
