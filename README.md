# Maya Video Pipeline

Multi-persona AI influencer video pipeline using Replicate's Stable Video Diffusion.

Generate AI videos from any reference image with style descriptions. Comes with 3 preset personas (Maya, Kai, Zara) or use your own reference images with custom styles.

## Features

- **Preset mode**: Use the built-in Maya, Kai, or Zara personas with predefined aesthetics
- **Raw mode**: Use ANY reference image with custom style keywords
- **Script-driven**: Write scene descriptions, the pipeline generates optimized prompts
- **Configurable**: Motion intensity, frame rate, video length — all adjustable

## Persona Presets

| Persona | Aesthetic | Default Motion | Reference |
|---------|-----------|---------------|-----------|
| **MAYA** | Cyber-Elegance / Baddie Core | 165 (high) | `img/maya_ref.jpg` |
| **KAI** | Corporate Chic / Quiet Luxury | 75 (low) | `img/kai_ref.jpg` |
| **ZARA** | Clean Girl / Soft Minimalist | 115 (medium) | `img/zara_ref.jpg` |

Each persona has detailed prompt templates in `personas/<name>/persona.json` covering multiple content themes (glamour shots, office scenes, morning routines, etc.).

## Setup

1. Clone the repo
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your Replicate API token:
   ```bash
   cp .env.example .env
   # Edit .env with your token: REPLICATE_API_TOKEN=your_token_here
   ```
4. Place reference images in the `img/` folder (or use any path)

## Usage

### Preset Mode (using built-in personas)

```bash
# Maya - Glamour/luxury hotel room
python pipeline.py --persona maya --script scripts/maya_script1.txt

# Kai - Corporate office entrance
python pipeline.py --persona kai --script scripts/kai_script1.txt

# Zara - Morning skincare routine
python pipeline.py --persona zara --script scripts/zara_script1.txt
```

Override persona defaults:
```bash
python pipeline.py --persona zara --script scripts/zara_script1.txt --motion 90 --output ./my_videos
```

### Raw Mode (any image, any style)

```bash
python pipeline.py --image ./myref.jpg --name "Luna" --style "cottagecore,dreamy,soft,aesthetic" --motion 80 --script ./script.txt

# Minimal — just image + script (uses defaults)
python pipeline.py --image ./myref.jpg --script ./script.txt
```

### Command-line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--persona` | Preset persona: maya, kai, or zara | — |
| `--image` | Path to reference image (required in raw mode) | — |
| `--name` | Persona name (raw mode) | "Custom" |
| `--style` | Comma-separated aesthetic keywords (raw mode) | "" |
| `--motion` | Motion bucket ID 1-255 | 127 or persona default |
| `--script` | Path to script file | **required** |
| `--fps` | Frames per second 6-30 | 24 |
| `--video-length` | Frames: 14 or 25 | 25 |
| `--sizing-strategy` | maintain_aspect_ratio or crop_to_16:9 | maintain_aspect_ratio |
| `--output` | Output directory | ./output/ |

## How It Works

1. **You provide**: A reference image + a script describing the scene
2. **The pipeline**:
   - Reads the script and detects the content theme
   - Generates an optimized prompt using persona aesthetics (or your custom style)
   - Sends the image + prompt to Replicate's Stable Video Diffusion
   - Polls for completion and downloads the output video
3. **You get**: A video in `output/`

## Project Structure

```
.
├── pipeline.py              # Main orchestration script
├── prompts.py               # Persona-specific & generic prompt generators
├── requirements.txt         # Dependencies
├── .env.example             # Environment variables template
├── README.md
├── personas/
│   ├── maya/persona.json    # Maya: Cyber-elegance, baddie core
│   ├── kai/persona.json     # Kai: Corporate chic, quiet luxury
│   └── zara/persona.json    # Zara: Clean girl, soft minimalist
├── scripts/
│   ├── maya_script1.txt     # Glamour/luxury hotel room tease
│   ├── kai_script1.txt      # Corporate boss walk into office
│   └── zara_script1.txt     # Morning skincare routine in bed
├── img/                     # Reference images directory
└── output/                  # Generated videos
```

## Motion Bucket ID Reference

| Range | Effect | Use Case |
|-------|--------|----------|
| 1-60 | Very subtle, near-static | Professional headshots, desk scenes |
| 61-100 | Gentle, natural movement | Coffee shop, casual walking |
| 101-140 | Moderate motion | Morning routines, candid moments |
| 141-180 | Dynamic, dramatic motion | Glamour walks, club scenes |
| 181-255 | Extreme motion | High-energy content |

## Requirements

- Python 3.8+
- Replicate API token (get one at https://replicate.com/account/api-tokens)
- Reference image (JPG or PNG)
