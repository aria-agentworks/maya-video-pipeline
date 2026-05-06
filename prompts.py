#!/usr/bin/env python3
"""
Prompt Generator Module

Generates optimized Stable Video Diffusion prompts from:
  - Persona presets (JSON config)
  - Raw arguments (name + style keywords)
  - Script text

The prompt builder intelligently selects content themes based on the script
and combines them with persona aesthetic keywords for consistent output.
"""

import json
import random
import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Persona-specific prompt templates
# ---------------------------------------------------------------------------

# These templates are used when loading from persona.json presets.
# They map content themes (from personas/*/persona.json) to Stable Video Diffusion prompts.

PERSONA_TEMPLATES = {
    "maya": {
        "glamour_shot": (
            "A glamorous woman with fair olive honey-tan skin and jet black S-curve waves, "
            "wearing a latex PVC bodysuit with strappy heels, posing in a luxury penthouse "
            "overlooking a glittering city skyline. Warm amber uplighting with neon pink accents, "
            "dramatic shadows. Cinematic, high fashion, 4K, sultry expression, perfect lighting, "
            "smooth skin, hourglass silhouette."
        ),
        "walking_shot": (
            "A confident woman with jet black S-curve waves wearing a black latex bodysuit and "
            "strappy stiletto heels, walking down a luxury penthouse hallway. Hips swaying, "
            "model walk, city lights visible through floor-to-ceiling windows. Warm amber "
            "uplighting with neon pink accents. Slow motion, cinematic, high fashion, sultry."
        ),
        "mirror_selfie": (
            "A glamorous woman in a latex PVC bodysuit taking a mirror selfie in a luxury "
            "penthouse. Phone in hand, sultry gaze, reflection in mirror. Jet black S-curve "
            "waves cascading over one shoulder. Warm amber uplighting, neon pink accents, "
            "dramatic shadows. Cinematic lighting, glamorous, 4K."
        ),
        "club_scene": (
            "A glamorous woman in a latex PVC bodysuit dancing in a VIP section of a luxury "
            "nightclub. Neon pink and blue lights reflecting off her jet black S-curve waves. "
            "Confident movement, baddie energy, strobe effects. Cinematic, high fashion, sultry, "
            "4K quality."
        ),
    },
    "kai": {
        "office_scene": (
            "A professional man with medium warm tan skin and jet black side-parted hair, "
            "wearing a charcoal grey tailored suit with white button-down, working at a "
            "minimalist desk in a modern glass-walled office. Soft natural window light with "
            "warm office uplighting. Confident, focused, corporate atmosphere, 4K, clean composition."
        ),
        "walking_shot": (
            "A polished professional with jet black side-parted hair wearing a charcoal grey "
            "tailored suit, walking through a modern financial district. Purposeful stride, "
            "leather briefcase in hand, city skyline backdrop. Golden hour city light, sharp "
            "attire, professional confidence. Cinematic, 4K."
        ),
        "coffee_shop": (
            "A professional man in a charcoal grey suit sitting in an upscale coffee shop. "
            "Laptop open, flat white with latte art. Jet black side-parted hair styled perfectly. "
            "Soft natural window light. Thoughtful gaze, quiet luxury aesthetic, clean composition."
        ),
        "desk_setup": (
            "A polished professional in a charcoal grey suit at a minimalist desk with dual "
            "monitors. Medium warm tan skin, focused expression. Clean workspace, productivity "
            "aesthetic, structured blazer. Soft warm office lighting, 4K."
        ),
    },
    "zara": {
        "morning_routine": (
            "A natural woman with medium-tan olive skin and dark espresso wavy curly messy hair, "
            "wearing an oversized grey cotton t-shirt, waking up in a sunlit bedroom with linen "
            "sheets. Soft morning window light, warm cozy tones. Yawn, stretch, authentic morning "
            "glow, messy bed hair, candid, relatable. Soft focus, natural beauty."
        ),
        "skincare": (
            "A natural woman with medium-tan olive skin performing her morning skincare routine. "
            "Patting serum on her glowy skin, bare face, natural skin texture. Dark espresso "
            "wavy messy hair tied loosely. Soft morning window light, warm bedside lamp glow. "
            "Glass skin glow, authentic, minimalist."
        ),
        "cozy_home": (
            "A woman with medium-tan olive skin and dark espresso wavy messy hair, wearing an "
            "oversized grey t-shirt, lounging comfortably at home. Mug of herbal tea in hand, "
            "relaxed smile. Soft morning light filtering through curtains. Warm cozy atmosphere, "
            "candid, authentic beauty, soft natural look."
        ),
        "candid_laugh": (
            "A natural woman with medium-tan olive skin laughing authentically in a cozy bedroom. "
            "Dark espresso wavy messy hair, oversized grey t-shirt. Genuine smile, crinkled eyes, "
            "relaxed posture. Soft morning window light. Joyful moment, soft natural beauty, "
            "candid, warm atmosphere."
        ),
    },
}

# ---------------------------------------------------------------------------
# Generic template (for raw/custom personas)
# ---------------------------------------------------------------------------

GENERIC_TEMPLATE = (
    "A {style_keywords} scene featuring {name}. "
    "Cinematic video, 4K quality, smooth motion, natural lighting. "
    "The subject moves naturally and authentically through the environment."
)


# ---------------------------------------------------------------------------
# PromptGenerator
# ---------------------------------------------------------------------------


class PromptGenerator:
    """
    Generates Stable Video Diffusion prompts from scripts and persona data.

    Supports:
      - Preset personas (maya, kai, zara) with pre-defined templates
      - Raw/custom personas from command-line arguments
    """

    def __init__(self):
        self.templates = PERSONA_TEMPLATES

    def _detect_content_theme(self, script: str) -> str:
        """
        Detect the content theme from the script text by looking for keywords.
        Falls back to a generic theme if nothing matches.
        """
        script_lower = script.lower()

        theme_keywords = {
            "glamour_shot": ["glamour", "posing", "sultry", "seductive", "latex", "bodysuit", "penthouse"],
            "walking_shot": ["walk", "stride", "sway", "hallway", "sidewalk"],
            "mirror_selfie": ["mirror", "selfie", "reflection", "phone in hand"],
            "club_scene": ["club", "nightclub", "dance", "neon", "VIP"],
            "office_scene": ["office", "desk", "corporate", "monitor", "keyboard"],
            "coffee_shop": ["coffee", "latte", "cafe", "flat white", "espresso"],
            "desk_setup": ["dual monitor", "workspace", "productivity", "laptop"],
            "morning_routine": ["morning", "wake", "bed", "yawn", "stretch", "alarm"],
            "skincare": ["skincare", "serum", "moisturize", "glow", "glass skin"],
            "cozy_home": ["cozy", "lounge", "couch", "tea", "mug", "herbal"],
            "candid_laugh": ["laugh", "smile", "candid", "joy", "genuine"],
        }

        scores = {}
        for theme, keywords in theme_keywords.items():
            scores[theme] = sum(1 for kw in keywords if kw in script_lower)

        best_theme = max(scores, key=scores.get)
        if scores[best_theme] == 0:
            return "generic"
        return best_theme

    def from_persona_preset(self, persona_name: str, script: str) -> str:
        """
        Generate a prompt using a preset persona's templates.
        Args:
            persona_name: One of 'maya', 'kai', 'zara'
            script: The script text to detect content theme from
        Returns:
            A prompt string optimized for Stable Video Diffusion
        """
        persona_name = persona_name.lower()
        if persona_name not in self.templates:
            return self.from_custom(
                script=script,
                name=persona_name.title(),
                style_keywords="stylish",
            )

        theme = self._detect_content_theme(script)
        templates = self.templates[persona_name]

        if theme in templates:
            prompt = templates[theme]
        elif theme == "generic":
            # Pick the first template as default
            prompt = list(templates.values())[0]
        else:
            prompt = list(templates.values())[0]

        return prompt

    def from_custom(self, script: str, name: str, style_keywords: str) -> str:
        """
        Generate a prompt for a custom/raw persona.
        Args:
            script: The script text
            name: The persona name
            style_keywords: Comma-separated aesthetic keywords
        Returns:
            A prompt string optimized for Stable Video Diffusion
        """
        theme = self._detect_content_theme(script)

        if theme != "generic":
            theme_name = theme.replace("_", " ").title()
            prompt = (
                f"A {style_keywords} scene: {theme_name}. "
                f"Featuring {name} in a natural, authentic moment. "
                f"Cinematic video, 4K quality, smooth motion, "
                f"professional lighting, natural atmosphere."
            )
        else:
            prompt = GENERIC_TEMPLATE.format(
                style_keywords=style_keywords,
                name=name,
            )

        return prompt

    def from_persona_json(self, persona_config: dict, script: str) -> str:
        """
        Generate a prompt from a loaded persona.json config dict.
        This bridges preset and custom modes by using the JSON data.
        """
        name = persona_config.get("name", "Persona")
        keywords = ", ".join(persona_config.get("aesthetic_keywords", []))
        return self.from_custom(
            script=script,
            name=name,
            style_keywords=keywords,
        )

    def build(
        self,
        script: str,
        name: str,
        style_keywords: str = "",
        persona_name: Optional[str] = None,
        persona_config: Optional[dict] = None,
    ) -> str:
        """
        Unified prompt builder. Determines the best strategy:

        1. If persona_name is given (maya/kai/zara), use preset templates
        2. If persona_config dict is given, use it to build custom prompt
        3. Otherwise, use raw name + style_keywords

        Args:
            script: The script text
            name: The persona name
            style_keywords: Comma-separated aesthetic keywords
            persona_name: Optional preset persona name
            persona_config: Optional loaded persona config dict

        Returns:
            A prompt string optimized for Stable Video Diffusion
        """
        if persona_name:
            return self.from_persona_preset(persona_name, script)
        elif persona_config:
            return self.from_persona_json(persona_config, script)
        else:
            return self.from_custom(script, name, style_keywords)


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def generate_prompt(
    script: str,
    name: str = "Custom",
    style_keywords: str = "",
    persona: Optional[str] = None,
) -> str:
    """Simple function wrapper for quick prompt generation."""
    generator = PromptGenerator()
    return generator.build(
        script=script,
        name=name,
        style_keywords=style_keywords,
        persona_name=persona,
    )
