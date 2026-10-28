# Nika Steam Scarf

**English** · [العربية](README.ar.md)

<a href="README.ar.md"><kbd>🌐 التبديل إلى العربية</kbd></a>

A monochrome Gear 5 / Nika fan-art animation: Luffy floats gently inside a flowing white steam-scarf frame on a pure black background.

![Animated preview](assets/animation.gif)

## Downloads

- [Square video — 1024 × 1024](assets/animation.mp4)
- [Phone video — 1080 × 1920](assets/phone.mp4)
- [Animated GIF — 640 × 640](assets/animation.gif)
- [All 300 PNG frames](assets/frames.zip)
- [Still image](assets/preview.png)

## Animation details

| Property | Value |
| --- | --- |
| Duration | 10 seconds |
| Video frame rate | 30 fps |
| Playback frames | 300 |
| Loop | Matching first and final PNG frames |
| Palette | White artwork on black |
| Movement | Gentle Luffy float and tilt; scarf follow-through and curl motion |

This repository preserves the approved **Lively** version. The later, stronger ScarfMotion experiment is excluded.

## Artwork and process

Eight AI-generated key drawings establish the cloud-scarf poses. The renderer matches one connected scarf outline and eight internal spiral contours, then creates intermediate shapes using periodic curves. Region timing, curl rotation, and a small character float give the shot its movement. The 300 final frames are rendered inbetweens; they are not 300 independently AI-generated drawings.

The topology checks verify a single connected scarf and eight enclosed spiral marks throughout the sequence. The first and last PNG images match. The GIF uses repeating 30/30/40 ms frame delays because its timing precision differs from video.

![Animation phases](assets/storyboard.png)

## Rebuild locally

Install Python 3.10 or newer and FFmpeg (including ffprobe), then run from the repository root:

```bash
python -m venv .venv
# Activate your virtual environment before continuing.
python -m pip install -r requirements.txt
python scripts/render.py
```

Outputs are created in `build/`, including PNG frames, square and portrait MP4 files, GIF, a storyboard, and validation data. Rendering uses CPU and keeps frames in memory; use a desktop environment for rebuilding.

## Repository contents

- `assets/`: final media, frames archive, original key drawings, prompts and validation data.
- `scripts/render.py`: complete renderer, with repository-relative paths.
- `requirements.txt`: Python dependencies.
- `README.ar.md`: Arabic documentation.

## Credits and context

Unofficial One Piece fan art. Monkey D. Luffy, Gear 5 and One Piece belong to their respective rights holders, including Eiichiro Oda / Shueisha / Toei Animation. This project is not affiliated with them.

Smoke-animation research included [Johannes Fast’s smoke-effects class](https://www.skillshare.com/en/classes/traditional-animation-how-to-create-smoke-effects/2084494770) and the [Ribbon Smoke lesson](https://draw.love-ink-llc.com/animatefx/BCAFXContent/BCAFX_Level-01/0103_03_Smoke.html). These are learning references, not endorsements or bundled third-party media.
