---
name: fastled-color-specialist
description: FastLED color expert for palette generation, color math, performance optimization, and LED effect debugging across any FastLED project.
---

# FastLED Color Specialist Skill

Expert guidance on FastLED color theory, color space mathematics, palette design, and performance optimization.

## When to Use This Skill

This skill should be triggered when:
- Designing color palettes and harmonious color schemes for LED animations
- Converting between color spaces (RGB/HSV/HEX) or blending colors
- Optimizing color performance for constrained hardware
- Debugging color issues in LED effects (unexpected colors, banding, flicker)
- Understanding gamma correction, color perception, and visual effects
- Creating gradient chains and multi-effect color transitions

## Quick Reference

### Color Space Conversions

**RGB to HSV:**
```cpp
// FastLED provides CHSV type for HSV colors
CHSV color_hsv = rgb2hsv_approximate(CRGB(255, 128, 0)); // Orange
// H: 0-255 (0° = red, 85° = green, 170° = blue)
// S: 0-255 (0 = white, 255 = saturated)
// V: 0-255 (0 = black, 255 = bright)
```

**HSV to RGB:**
```cpp
CRGB color_rgb = CHSV(42, 255, 255); // Bright yellow
```

**HEX to RGB:**
```cpp
// Common FastLED web colors
CRGB red = CRGB::Red;        // 0xFF0000
CRGB blue = CRGB::Blue;      // 0x0000FF
CRGB custom = CRGB(0xAA, 0xBB, 0xCC); // Define custom
```

### Palette Generation Patterns

**Complementary (2 colors, high contrast):**
```cpp
// Pick primary color in HSV, add 128 to hue for opposite
CHSV primary(30, 255, 255);      // Orange
CHSV complement(158, 255, 255);  // Blue-green (30 + 128 = 158)
```

**Triadic (3 colors, balanced energy):**
```cpp
// Equally spaced 85° apart (255/3 = 85)
CHSV color1(0, 255, 255);    // Red
CHSV color2(85, 255, 255);   // Green
CHSV color3(170, 255, 255);  // Blue
```

**Analogous (3 colors, harmonious):**
```cpp
// Colors 30° apart (adjacent on color wheel)
CHSV primary(60, 255, 255);   // Yellow
CHSV left(30, 255, 255);      // Yellow-orange
CHSV right(90, 255, 255);     // Yellow-green
```

**Tetradic (4 colors, complex):**
```cpp
// Two complementary pairs (85° spacing, doubled)
CHSV c1(0, 255, 255);     // Red
CHSV c2(85, 255, 255);    // Green
CHSV c3(128, 255, 255);   // Cyan (complement of Red)
CHSV c4(213, 255, 255);   // Magenta (complement of Green)
```

### Color Blending

**Linear interpolation (blend two colors):**
```cpp
CRGB blend(CRGB color1, CRGB color2, uint8_t position) {
  // position: 0 = color1, 128 = middle, 255 = color2
  return blend8(color1, color2, position);
}
```

**Gradient (smooth transition across array):**
```cpp
fill_gradient_RGB(leds, NUM_LEDS, CRGB::Red, CRGB::Blue);
// Smooth transition from red to blue across all LEDs
```

**Color cycling (fade in/out):**
```cpp
// HSV allows easy brightness variation
CHSV color(Hue, Saturation, brightness); // Adjust value/brightness
fadeToBlackBy(leds, NUM_LEDS, fade_amount); // Dim all
```

### Gamma Correction

**Why it matters:** Human eyes perceive brightness non-linearly. Gamma correction makes colors look natural.

```cpp
// FastLED applies gamma correction with proper scaling
// Use these gamma tables for consistency:
const uint8_t gamma8[] = { /* lookup table */ };

// Apply to single LED
leds[0] = CRGB(gamma8[r], gamma8[g], gamma8[b]);
```

### Performance Optimization

**Memory efficient patterns:**
- Use `CHSV` instead of `CRGB` when storing palettes (3 bytes vs 3 bytes, but more efficient for color manipulation)
- Use color arrays instead of generating colors in loops
- Pre-calculate palettes during setup, not in the render loop

**Speed optimization:**
- `rgb2hsv_approximate()` is faster than `rgb2hsv()`
- Use `fill_solid()` and `fill_gradient_RGB()` for bulk operations
- Pre-allocate arrays instead of using vectors in hot loops

**Color order (critical for some LED types):**
```cpp
// Define color order for your LED type (often RGB or GRB)
FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
```

## Reference Files

Reference documentation in `references/`:

- **color_theory.md** - Color theory fundamentals and perception
- **color_spaces.md** - RGB, HSV, HEX explained with conversion formulas
- **palette_patterns.md** - Design patterns for harmonious palettes
- **blending_gradients.md** - Color blending, gradients, and transitions
- **performance_tips.md** - Memory and speed optimization
- **debugging_colors.md** - Troubleshooting common color issues
- **web_colors_reference.md** - FastLED web color table
- **gamma_correction.md** - Gamma tables and brightness perception

## Working with This Skill

### Quick Color Problem?
Check the Quick Reference section above for immediate patterns.

### Need Deep Dive?
Use reference files for:
- Detailed color theory and human perception
- Mathematical formulas for color conversions
- Systematic debugging approaches for color issues
- Performance optimization for constrained systems

### Code Examples?
All reference files contain practical code examples you can copy and adapt.

## RGB565 for Embedded Displays

When working with M5GFX, LovyanGFX, TFT_eSPI, or other embedded display libraries, colors use RGB565 (16-bit) instead of RGB888 (24-bit).

### RGB565 Structure

```
Red: 5 bits (0-31) | Green: 6 bits (0-63) | Blue: 5 bits (0-31)
```

Green gets 6 bits because human eyes are most sensitive to green.

### Conversion Functions

```cpp
// CRGB (FastLED) → RGB565
inline uint16_t crgbToRgb565(const CRGB& color) {
    return ((color.r & 0xF8) << 8) | ((color.g & 0xFC) << 3) | (color.b >> 3);
}

// RGB565 → RGB888
inline void rgb565ToRgb888(uint16_t color, uint8_t& r, uint8_t& g, uint8_t& b) {
    r = (color >> 8) & 0xF8; r |= r >> 5;
    g = (color >> 3) & 0xFC; g |= g >> 6;
    b = (color << 3) & 0xF8; b |= b >> 5;
}
```

### RGB565 Brightness Manipulation

```cpp
inline uint16_t dimColor(uint16_t color, float factor) {
    uint8_t r = (color >> 11) & 0x1F;
    uint8_t g = (color >> 5) & 0x3F;
    uint8_t b = color & 0x1F;
    r = (r * factor > 31) ? 31 : (uint8_t)(r * factor);
    g = (g * factor > 63) ? 63 : (uint8_t)(g * factor);
    b = (b * factor > 31) ? 31 : (uint8_t)(b * factor);
    return (r << 11) | (g << 5) | b;
}
```

### Neon Glow Pattern (3-Layer)

```cpp
void drawGlowBorder(int16_t x, int16_t y, int16_t w, int16_t h,
                    uint16_t color, bool highlight) {
    float glow = highlight ? 1.0f : 0.6f;
    display.drawRect(x, y, w, h, dimColor(color, 0.3f * glow));       // Outer
    display.drawRect(x+1, y+1, w-2, h-2, dimColor(color, 0.5f * glow)); // Middle
    display.drawRect(x+2, y+2, w-4, h-4, dimColor(color, glow));       // Inner
}
```

### When to Use Which Format

| Context | Format | Reason |
|---------|--------|--------|
| LED strips (WS2812) | CRGB | Hardware expects 24-bit |
| TFT/LCD displays | RGB565 | Native format, half memory |
| Color calculations | CRGB/CHSV | Better precision |
| Storage/transmission | RGB565 | ~45% smaller |

## Resources

### references/
Comprehensive documentation covering:
- Color theory and perception
- Color space mathematics and conversions
- Palette design patterns with psychological impact
- Blending and gradient techniques
- Performance optimization strategies
- Debugging methodologies
- Reference tables (web colors, gamma values)

### assets/
- Color palette templates
- Gamma correction lookup tables
- Example animation effects with colors
- Performance benchmarking templates

### scripts/
Helper utilities for:
- Converting colors between formats
- Generating palette variations
- Testing color perception

## Common Use Cases

**"I want vibrant, energetic colors"** → Triadic or tetradic palettes with high saturation
**"I want calming, natural colors"** → Analogous palettes with mid saturation
**"I need high contrast"** → Complementary pairs
**"Colors look wrong/washed out"** → Check gamma correction and color order
**"Animation is slow"** → Optimize palette generation, use pre-calculated colors
**"Banding/posterization visible"** → Use HSV color space for smoother gradients

## Integration with FastLED Skill

This skill is specialized for color work. For general FastLED questions (library setup, LED control, timing), refer to the general FastLED skill.

## Notes

- All code examples assume FastLED library is properly included and initialized
- Color math works identically on all FastLED-supported platforms
- Performance tips assume typical microcontroller constraints (ESP32, Arduino)
- Perception examples assume typical human color vision

## Quick Debugging Checklist

- [ ] Check color order (RGB vs GRB) matches your LED type
- [ ] Verify brightness/value isn't 0 (invisible color)
- [ ] Check saturation - low saturation = grayish/washed out
- [ ] Apply gamma correction for natural-looking colors
- [ ] Test with single LED before full animation
- [ ] Monitor memory/CPU if animation sluggish
