#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace mcv {
constexpr size_t LibraryRows=4;
enum Action : uint16_t { Enter=1, Pause=2, Back=4, Down=8, Up=16, Next=32, Prev=64,
                         Louder=128, Quieter=256, Rescan=512 };
// Physical base keys keep navigation stable across Fn/Shift/Caps transitions.
template<class Keyboard> uint16_t keyboardActions(Keyboard& keyboard) {
    const auto& state=keyboard.keysState();
    uint16_t actions=(state.enter?Enter:0)|(state.space?Pause:0)|(state.esc?Back:0)|
        (state.down?Down:0)|(state.up?Up:0)|(state.right?Next:0)|(state.left?Prev:0);
    for (const auto& point:keyboard.keyList()) {
        if (point.x<0 || point.x>=14 || point.y<0 || point.y>=4) continue;
        switch (uint8_t(keyboard.getKeyValue(point).value_first)) {
        case 0x28: actions|=Enter; break; // Vendored KEY_ENTER.
        case ' ': actions|=Pause; break;
        case 'q': actions|=Back; break;
        case ';': case 'w': actions|=Up; break;
        case '.': case 's': actions|=Down; break;
        case ',': case 'p': actions|=Prev; break;
        case '/': case 'n': actions|=Next; break;
        case '=': actions|=Louder; break;
        case '-': actions|=Quieter; break;
        case 'r': actions|=Rescan; break;
        }
    }
    return actions;
}
struct KeyEdges {
    uint16_t previous=0;
    uint16_t pressed(uint16_t current) {
        uint16_t edge=current&~previous; previous=current; return edge;
    }
};
struct LibrarySelection {
    size_t index=0, first=0;
    void normalise(size_t count) {
        if (!count) { index=first=0; return; }
        index=std::min(index,count-1);
        first=std::min(first,count>LibraryRows?count-LibraryRows:0);
        if (index<first) first=index;
        if (index-first>=LibraryRows) first=index-LibraryRows+1;
    }
    bool step(int direction,size_t count) {
        normalise(count);
        if (!count || !direction) return false;
        size_t before=index;
        index=direction>0?(index==count-1?0:index+1):(index?index-1:count-1);
        normalise(count); return index!=before;
    }
};
inline int navigationDelta(uint16_t edges,bool playing) {
    bool forward=(edges&Next) || (!playing && (edges&Down));
    bool backward=(edges&Prev) || (!playing && (edges&Up));
    return int(forward)-int(backward);
}
inline bool isVideoFilename(const char* name,bool directory) {
    size_t n=std::strlen(name);
    if (directory || n<4 || name[n-4]!='.') return false;
    return (name[n-3]=='m'||name[n-3]=='M') &&
           (name[n-2]=='c'||name[n-2]=='C') && (name[n-1]=='v'||name[n-1]=='V');
}
} // namespace mcv
