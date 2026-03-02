# Overlay UI Design Spec -- V3 Apple Refined

## Overview

Screen-bottom floating status bar for voice input visual feedback. tkinter + PIL.
Design language: macOS Sonoma notification style -- light frosted glass, soft shadow,
warm neutral tones, clean humanist typography, dramatic breathing red dot, organic waveform.

V3 addresses three user-reported issues from V2:
1. Red dot breathing was not visually perceptible
2. Volume bars hit maximum too easily and looked plain
3. Waveform bars jumped independently, creating a mechanical appearance

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
| Rec dot bright | `#E8433A` | SF Symbols red (breath peak) |
| Rec dot dim | `#F2CCC9` | **V3: Noticeably lighter pink** (breath trough, was #F5A8A4) |
| Rec label | `#C4372F` | Slightly darker red |
| Bar idle | `#D1D1D6` | System gray (silence) |
| Bar low | `#E0C8C0` | **V3: New** warm taupe-pink |
| Bar mid | `#F09E8C` | Warm peach-pink |
| Bar high | `#E8685E` | **V3: New** coral |
| Bar peak | `#E8433A` | Full red |
| Bar tip glow | `#FFB8A8` | **V3: New** bright peach for bar top highlight |
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

Unchanged from V2:
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

#### Red Dot -- Dramatic Breathing (V3 fix)

**Problem in V2:** The breath animation used a 0.6-1.0 color range with subtle color difference, making the pulse imperceptible.

**V3 solution -- dual-axis breathing:**
- **Color pulse:** Interpolation range widened from 0.6-1.0 to **0.2-1.0**
  - At trough (0.2): `#F2CCC9` -- noticeably pale pink, clearly "dim"
  - At peak (1.0): `#E8433A` -- full vivid red
  - The dim color was also changed from `#F5A8A4` to `#F2CCC9` for greater visual contrast
- **Size pulse:** Dot radius oscillates between **70% and 100%** of max (4.5px x DPI)
  - Creates a visible "heartbeat" effect
  - Halo also scales (75%-100% of 8px x DPI)
- **Timing:** `sin(now * 2.5)` -- approximately 0.4 Hz, matching a calm heartbeat feel

#### Volume Bars -- Adaptive Gain (V3 fix)

**Problem in V2:** Raw `current_volume` (0.0-1.0 from recorder, already sqrt-mapped) would routinely hit 1.0 during normal speech, causing bars to constantly max out.

**V3 solution -- rolling-window adaptive scaling:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Window | 6 seconds (~120 samples @ 50ms tick) | Recent volume history |
| Percentile | 80th | Reference "typical peak" within window |
| Min reference | 0.05 | Floor to prevent silence amplification |
| Rise speed | 0.3 | Fast response to sudden loudness |
| Decay rate | 0.92 | Slow fade when getting quieter |

Algorithm:
1. Append raw volume to rolling deque
2. Compute 80th percentile of window as `target_ref`
3. Smooth-track reference: fast rise (lerp 0.3), slow decay (exponential 0.92)
4. Scale: `normalized = raw / (reference * 1.25)`
5. Clamp to [0.0, 1.0]

Result: Normal speech peaks use ~80% of bar height. Quiet passages still show visible activity. Brief loud bursts may clip temporarily, then the reference adjusts upward.

#### Volume Bars -- Organic Visual Style (V3 fix)

**Problem in V2:** Plain rectangular bars with minimal rounded caps looked mechanical.

**V3 solution:**

1. **Four-stage color gradient** (was two-stage):
   - 0-20%: idle gray -> warm taupe-pink
   - 20-45%: taupe-pink -> peach
   - 45-75%: peach -> coral
   - 75-100%: coral -> full red
   - Creates a smooth, continuous warm gradient that avoids harsh transitions

2. **Tapered bars:** Each bar is wider at the center and narrower at the tips (65% taper ratio), creating an organic lens/petal shape rather than a rigid rectangle.

3. **Tip glow:** The top cap of each bar uses a brighter highlight color (35% blend toward `#FFB8A8`), simulating light catching the peak of each bar.

4. **Subtle reflection:** Below each bar, a faint mirrored oval at 12% stipple opacity creates a subtle "standing on glass" effect. Height is 20% of the bar, using a 70% blend toward the background color.

5. **Slightly wider bars** (3.5px base, was 3px) with tighter spacing (2.2px gap, was 2.5px) for a denser, more waveform-like appearance.

#### Waveform Smoothing (V3 fix)

**Problem in V2:** Each bar jumped independently based on its raw volume sample, creating a jagged, random appearance.

**V3 solution -- neighbor smoothing:**
- Each bar's display value is a weighted blend: 70% own value + 30% average of left and right neighbors
- Weight parameter: `_SMOOTH_WEIGHT = 0.3`
- Edge bars use their own value as the missing neighbor
- Creates a gentle, flowing envelope over the raw data
- Think: Apple Voice Memos waveform -- organic undulation, not random noise

### Recognizing

Unchanged from V2:
- Centered text in dark gray + three pulsing dots
- Dots: light gray to medium gray, sequential sine pulse (2.8 Hz, 0.9 phase offset)
- Subtle size scaling (1.0x to 1.3x)

### Result

Unchanged from V2:
- Centered dark text on light glass, auto-hide after 2 seconds

## Interaction

Unchanged from V2:
- Mouse drag (WS_EX_NOACTIVATE -- no focus steal)
- Window alpha 0.96

## Design Evolution

| Aspect | V2 (Apple) | V3 (Apple Refined) |
|--------|------------|-------------------|
| Red dot breath range | 0.6-1.0 (subtle) | 0.2-1.0 (dramatic) |
| Red dot dim color | #F5A8A4 (close to red) | #F2CCC9 (clearly pink) |
| Red dot size pulse | None | 70%-100% radius |
| Volume scaling | Raw (frequently maxed) | Adaptive gain (80th percentile) |
| Bar color stages | 2-stage (gray-peach-red) | 4-stage (gray-taupe-peach-coral-red) |
| Bar shape | Rectangular + round caps | Tapered (center-wide, tip-narrow) |
| Bar tips | Flat color | Glow highlight |
| Bar reflection | None | Subtle stippled mirror |
| Bar width | 3px | 3.5px (slightly wider) |
| Waveform smoothing | None (jagged) | Neighbor-weighted (organic) |

## Backup Files

- V1: `sensetype/overlay_v1_tech_blue.py`
- V2: `sensetype/overlay_v2_apple.py`
- V3: `sensetype/overlay_v3_apple_refined.py`
