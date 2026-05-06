#!/usr/bin/env python3
"""
Maya Video Pipeline

Multi-persona AI influencer video pipeline using Replicate's Stable Video Diffusion.

Usage (preset mode):
    python pipeline.py --persona maya --script scripts/maya_script1.txt
    python pipeline.py --persona kai --script scripts/kai_script1.txt
    python pipeline.py --persona zara --script scripts/zara_script1.txt

Usage (raw mode):
    python pipeline.py --image path/to/ref.jpg --name "PersonaName" --style "keywords" --motion 100 \
        --script path/to/script.txt

All modes:
    python pipeline.py --persona maya --script scripts/maya_script1.txt --output ./my_videos
"""

import argparse
import json
import os
import sys
import time
import logging
from pathlib import Path

import replicate
import requests
from dotenv import load_dotenv
from PIL import Image

from prompts import PromptGenerator

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PERSONAS_DIR = Path(__file__).parent / "personas"
OUTPUT_DIR = Path(__file__).parent / "output"

# Default Stable Video Diffusion model
MODEL_VERSION = "sunfjun/stable-video-diffusion:d68b6e09eedbac7a49e3d8644999d93579c386a083768235cabca88796d70d82"

# -----------------------------------------------------------------------
# Persona Loading
# -----------------------------------------------------------------------


def load_persona(persona_name: str) -> dict:
    """Load a persona configuration from the personas/ directory."""
    persona_path = PERSONAS_DIR / persona_name.lower() / "persona.json"
    if not persona_path.exists():
        available = [p.name for p in PERSONAS_DIR.iterdir() if p.is_dir()]
        log.error(
            "Persona '%s' not found. Available personas: %s",
            persona_name,
            ", ".join(available),
        )
        sys.exit(1)
    with open(persona_path, "r") as f:
        return json.load(f)


def build_config(args: argparse.Namespace) -> dict:
    """
    Build the pipeline configuration from either preset persona mode
    or raw arguments (image + name + style + motion).
    """
    if args.persona:
        # ---- Preset mode: load from persona.json ----
        persona = load_persona(args.persona)
        ref_image = (
            args.image
            if args.image
            else Path(__file__).parent / persona.get("reference_image", "")
        )
        motion_bucket_id = args.motion if args.motion is not None else persona.get("default_motion_bucket_id", 127)
        style_keywords = ", ".join(persona.get("aesthetic_keywords", []))
        name = persona["name"]
        log.info("Loaded persona: %s (motion=%s)", name, motion_bucket_id)
    else:
        # ---- Raw mode: use provided arguments ----
        if not args.image:
            log.error("Raw mode requires --image. Use --persona for presets, or provide --image.")
            sys.exit(1)
        ref_image = args.image
        name = args.name or "Custom"
        style_keywords = args.style or ""
        motion_bucket_id = args.motion if args.motion is not None else 127
        log.info("Raw mode: %s (motion=%s)", name, motion_bucket_id)

    return {
        "name": name,
        "reference_image": ref_image,
        "style_keywords": style_keywords,
        "motion_bucket_id": motion_bucket_id,
        "script_path": args.script,
        "output_dir": Path(args.output) if args.output else OUTPUT_DIR,
        "fps": args.fps,
        "video_length": args.video_length,
        "sizing_strategy": args.sizing_strategy,
    }


# -----------------------------------------------------------------------
# File Helpers
# -----------------------------------------------------------------------


def read_script(path: str) -> str:
    """Read a script text file."""
    p = Path(path)
    if not p.exists():
        log.error("Script file not found: %s", path)
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def validate_image(path: str) -> None:
    """Validate that the reference image exists and is a valid image."""
    p = Path(path)
    if not p.exists():
        log.error("Reference image not found: %s", path)
        sys.exit(1)
    try:
        with Image.open(p) as img:
            log.info("Reference image: %s (%sx%s)", p.name, img.width, img.height)
    except Exception as e:
        log.error("Invalid image file '%s': %s", path, e)
        sys.exit(1)


# -----------------------------------------------------------------------
# Replicate API
# -----------------------------------------------------------------------


def submit_prediction(image_path: str, prompt: str, config: dict) -> dict:
    """Submit an image-to-video prediction to Replicate."""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        log.error(
            "REPLICATE_API_TOKEN not found. Add it to your .env file "
            "or export it as an environment variable."
        )
        sys.exit(1)

    if image_path.startswith("http://") or image_path.startswith("https://"):
        img_uri = image_path
    else:
        from base64 import b64encode
        with open(image_path, "rb") as f:
            img_data = b64encode(f.read()).decode("utf-8")
            img_uri = f"data:image/{Path(image_path).suffix[1:]};base64,{img_data}"

    log.info("Submitting prediction to Replicate (model: %s)...", MODEL_VERSION)
    log.info("  Prompt: %s", prompt[:80] + "..." if len(prompt) > 80 else prompt)
    log.info("  Motion bucket: %s | FPS: %s | Frames: %s",
             config["motion_bucket_id"], config["fps"], config["video_length"])

    try:
        video_length_str = "14_frames_with_svd_xt" if config["video_length"] == 25 else "14_frames_with_svd"
        output = replicate.run(
            MODEL_VERSION,
            input={
                "input_image": img_uri,
                "video_length": video_length_str,
                "sizing_strategy": config["sizing_strategy"],
                "frames_per_second": config["fps"],
                "motion_bucket_id": config["motion_bucket_id"],
                "cond_aug": 0.02,
                "decoding_t": 14,
            },
        )
        return output
    except Exception as e:
        log.error("Replicate API call failed: %s", e)
        sys.exit(1)


def download_video(url: str, output_path: Path) -> Path:
    """Download the generated video from a URL."""
    log.info("Downloading video from %s", url)
    resp = requests.get(url, stream=True, timeout=300)
    resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    log.info("Video saved to: %s", output_path)
    return output_path


# -----------------------------------------------------------------------
# Main Pipeline
# -----------------------------------------------------------------------


def run_pipeline(config: dict) -> Path:
    """Execute the full video generation pipeline."""
    name = config["name"]
    if config["script_path"] is None:
        script_text = "A glamorous woman walking in neon city lights, cinematic lighting, hyper-realistic"
    else:
        script_text = read_script(config["script_path"])
    ref_image = str(config["reference_image"])
    validate_image(ref_image)

    # Generate prompt from script + persona/style
    generator = PromptGenerator()
    prompt = generator.build(
        script=script_text,
        name=name,
        style_keywords=config["style_keywords"],
    )
    log.info("Generated prompt (%d chars)", len(prompt))

    # Submit to Replicate
    output = submit_prediction(ref_image, prompt, config)

    # Replicate returns a list of URLs for video output
    if isinstance(output, list):
        video_url = output[0]
    elif isinstance(output, str):
        video_url = output
    else:
        log.error("Unexpected output format from Replicate: %s", type(output))
        sys.exit(1)

    # Download the result
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_filename = f"{name.lower()}_{timestamp}.mp4"
    output_path = Path(config["output_dir"]) / output_filename

    return download_video(video_url, output_path)


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Multi-persona AI influencer video pipeline using Replicate Stable Video Diffusion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preset mode: use a predefined persona
  python pipeline.py --persona maya --script scripts/maya_script1.txt

  # Preset mode with override
  python pipeline.py --persona zara --script scripts/zara_script1.txt --motion 90

  # Raw mode: use any reference image with custom style
  python pipeline.py --image ./myref.jpg --name "Luna" --style "cottagecore,dreamy,soft" --motion 80 --script ./script.txt

  # Minimal raw mode (just image + script, uses defaults)
  python pipeline.py --image ./ref.jpg --script ./script.txt
        """,
    )

    # Mode selection (mutually exclusive-ish: --persona is preset, --image is raw)
    parser.add_argument(
        "--persona",
        choices=["maya", "kai", "zara"],
        help="Load a preset persona configuration (maya, kai, or zara)",
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Path to reference image (required in raw mode)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Name for the persona (used in raw mode)",
    )
    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="Comma-separated aesthetic keywords describing the look (used in raw mode)",
    )
    parser.add_argument(
        "--motion",
        type=int,
        default=None,
        help="Motion bucket ID (1-255, higher = more motion. Default: 127, or persona default)",
    )

    # Video parameters (with defaults)
    parser.add_argument(
        "--fps",
        type=int,
        default=24,
        choices=range(6, 31),
        metavar="[6-30]",
        help="Frames per second (6-30, default: 24)",
    )
    parser.add_argument(
        "--video-length",
        type=int,
        default=25,
        choices=[14, 25],
        help="Number of frames: 14 or 25 (default: 25)",
    )
    parser.add_argument(
        "--sizing-strategy",
        type=str,
        default="maintain_aspect_ratio",
        choices=["maintain_aspect_ratio", "crop_to_16:9"],
        help="Sizing strategy for the output video",
    )

    # Required paths
    parser.add_argument(
        "--script",
        type=str,
        default=None,
        help="Path to the script text file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for generated videos (default: ./output/)",
    )

    return parser


# -----------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------


def main():
    parser = create_parser()
    args = parser.parse_args()

    # Require either --persona or --image
    if not args.persona and not args.image:
        parser.error("Either --persona (preset) or --image (raw mode) is required.")

    config = build_config(args)
    output_path = run_pipeline(config)

    print()
    print("=" * 60)
    log.info("Pipeline complete!")
    log.info("Output: %s", output_path)
    print("=" * 60)


if __name__ == "__main__":
    main()
