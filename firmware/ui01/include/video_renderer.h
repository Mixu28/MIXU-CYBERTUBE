#pragma once
#include <lgfx/utility/lgfx_tjpgd.h>
#include <lgfx/v1/misc/colortype.hpp>
#include <algorithm>
#include <cstddef>
#include <cstdint>
namespace mcv {
// TJpgDec compacts partial MCU output to the width in JRECT. Preserve that
// source stride if a defensive display-boundary clip narrows the rectangle.
template<class Display> uint32_t renderVideoBlock(Display& display,void* bitmap,const JRECT& rect) {
    if (!bitmap || rect.left>rect.right || rect.top>rect.bottom ||
        rect.right-rect.left>=16 || rect.bottom-rect.top>=16) return 0;
    constexpr uint32_t Width=240, Height=135;
    if (rect.left>=Width || rect.top>=Height) return 1;
    uint32_t sourceWidth=rect.right-rect.left+1;
    uint32_t width=std::min(rect.right,Width-1)-rect.left+1;
    uint32_t height=std::min(rect.bottom,Height-1)-rect.top+1;
    auto pixels=static_cast<const lgfx::bgr888_t*>(bitmap); // Memory order R,G,B.
    if (width==sourceWidth) {
        display.pushImage(rect.left,rect.top,width,height,pixels);
    } else {
        for (uint32_t row=0;row<height;++row) {
            display.pushImage(rect.left,rect.top+row,width,1,pixels+row*sourceWidth);
            display.waitDMA();
        }
    }
    // Finish all transfers before TJpgDec reuses the MCU buffer.
    display.waitDMA();
    return 1;
}
} // namespace mcv
