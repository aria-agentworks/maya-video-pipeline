# Maya Video Pipeline

Multi-persona AI influencer video pipeline using Replicate's Stable Video Diffusion.

## Personas

### MAYA — Cyber-Elegance / Baddie Core
Sultry tech-luxe aesthetic. Fair olive/honey-tan complexion, jet black S-curve waves, curvy hourglass build. Futuristic glamour, latex/PVC bodysuits. High motion video generation.
- Reference: `img/image_1778100540929_f5152823-4a6f-4c1e-8bfb-d2d03c20c8e2`
- Default motion_bucket_id: 165

### KAI — Corporate Chic / Quiet Luxury Professional
Professional corporate aesthetic. Medium warm tan skin, charcoal grey suits. Low motion, polished office scenes.
- Reference: `img/image_1778100542355_fe23b7c0-0e5a-4b5e-b1ca-a1ae97f4bd78`
- Default motion_bucket_id: 75

### ZARA — Clean Girl / Soft Minimalist
Authentic bestie aesthetic. Medium-tan olive skin, natural look. Medium motion, cozy casual content.
- Reference: `img/image_1778100543740_2d31f91a-644a-4e44-9732-ac28a9fbf9f8`
- Default motion_bucket_id: 115

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your `REPLICATE_API_TOKEN`
4. Place reference images in the `img/` folder

## Usage

```bash
python pipeline.py --persona maya --script scripts/maya_script1.txt --image img/maya_ref.jpg
python pipeline.py --persona kai --script scripts/kai_script1.txt --image img/kai_ref.jpg
python pipeline.py --persona zara --script scripts/zara_script1.txt --image img/zara_ref.jpg
```

Output videos will be saved to `output/`.

## Configuration

Each persona in `personas/` has a `persona.json` with:
- `name` & `description`
- `aesthetic_keywords` — for prompt generation
- `content_themes` — types of content
- `clothing_style` & `lighting_style`
- `prompt_templates` — optimized for Stable Video Diffusion
- `default_motion_bucket_id` — motion intensity for video generation

## Project Structure

```
.
├── pipeline.py              # Main orchestration script
├── prompts.py               # Persona-specific prompt generators
├── requirements.txt         # Dependencies
├── .env.example             # Environment variables template
├── README.md
├── personas/
│   ├── maya/persona.json
│   ├── kai/persona.json
│   └── zara/persona.json
├── scripts/
│   ├── maya_script1.txt
│   ├── kai_script1.txt
│   └── zara_script1.txt
├── img/                     # Reference images directory
└── output/                  # Generated videos
```