# Overlay UI Design Spec -- V2 Apple Frosted Glass

## Overview

Screen-bottom floating status bar for voice input visual feedback. tkinter + PIL.
Design language: macOS Sonoma notification style -- light frosted glass, soft shadow,
warm neutral tones, clean humanist typography, subtle red recording indicator.

## Dimensions (logical px @96dpi, runtime x DPI scale)

| Property | Value |
|----------|-------|
| Width | 290px |
| Height | 44px |
| Aspect | ~6.6:1 |
| Corner radius | 14px |
| Bottom margin | 80px |
| Shadow padding | 16px (canvas extends beyond body for drop shadow) |

## Color Palette

| Purpose | Color | Notes |
|---------|-------|-------|
| Background top | `rgb(255, 255, 255)` | Pure white |
| Background bottom | `rgb(243, 243, 248)` | Ultra-light warm gray (slight purple, macOS feel) |
| Frost noise alpha | 4-22 | Very subtle |
| Shadow | `rgba(0, 0, 0, 0.16)` | Soft, offset 2px down, blur 8px |
| Border | `rgba(0, 0, 0, 0.07)` | Nearly invisible hairline |
| Rec dot | `#E8433A` | SF Symbols red |
| Rec dot dim | `#F5A8A4` | Pale pink (breath low) |
| Rec label | `#C4372F` | Slightly darker red |
| Volume bar idle | `#D1D1D6` | System gray |
| Volume bar mid | `#F09E8C` | Warm peach-pink |
| Volume bar active | `#E8433A` | Matches rec dot |
| Recognizing text | `#48484A` | Dark gray (systemGray2) |
| Recognizing dots dim | `#D1D1D6` | Light gray |
| Recognizing dots hi | `#8E8E93` | Medium gray |
| Result text | `#1C1C1E` | Near-black (label color) |

## Typography

| Purpose | Font | Size | Weight |
|---------|------|------|--------|
| REC label | Segoe UI Variable | 8pt x DPI | Bold |
| Body/result | Segoe UI Variable | 9.5pt x DPI | Regular |

Fallback: Segoe UI (Win10). Chinese text renders well with both fonts.

## Background Rendering (PIL 3x supersampling)

1. Soft drop shadow (rounded rect, Gaussian blur, offset 2px down)
2. Vertical gradient fill (white top to warm gray bottom)
3. Subtle noise texture (18% density, mixed light/dark grains, alpha 4-22)
4. Top highlight band (white, quadratic alpha falloff, very subtle)
5. Rounded-rect mask (14px radius)
6. Hairline border (nearly invisible, black at 7% opacity)
7. Composite: shadow layer + body on transparent-key background
8. LANCZOS downsample to 1x

## States

### Recording
- Left: Red dot with gentle breathing pulse (sine wave, 2.5 Hz)
  - Faint halo using `stipple="gray25"` for transparency simulation
  - Solid inner dot: pale pink to red
- Label: "REC" in bold dark red
- Right: Volume timeline (deque scrolling, left=old, right=new)
  - Bars: idle gray -> peach-pink -> red (two-stage gradient)
  - Rounded caps via oval+rect composite

### Recognizing
- Centered text in dark gray + three pulsing dots
- Dots: light gray to medium gray, sequential sine pulse (2.8 Hz, 0.9 phase offset)
- Subtle size scaling (1.0x to 1.3x)

### Result
- Centered dark text on light glass, auto-hide after 2 seconds

## Interaction
- Mouse drag (WS_EX_NOACTIVATE -- no focus steal)
- Window alpha 0.96

## Design Philosophy (vs V1)

| Aspect | V1 (Tech Blue) | V2 (Apple) |
|--------|----------------|------------|
| Background | Dark navy gradient | Light frosted white |
| Border | Neon cyan glow | Soft drop shadow + hairline |
| Rec indicator | Cyan pulsing ring | Subtle red dot |
| Volume bars | Blue-to-cyan | Gray-to-peach-to-red |
| Text color | Cold white/blue | Dark gray/near-black |
| Font | Candara | Segoe UI Variable |
| Feel | Sci-fi / techy | Warm / minimal / Apple |

## Backup File
`sensetype/overlay_v2_apple.py`
