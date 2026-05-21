#!/usr/bin/env python3
"""Wrapper around the real PaperBanana package (llmsresearch/paperbanana).

Uses the PaperBanana multi-agent pipeline with OpenAI as the provider:
  Phase 1 (Linear Planning): Retriever → Planner → Stylist
  Phase 2 (Iterative Refinement): Visualizer ↔ Critic

Requires:
  pip install "paperbanana[openai]"   (or install from git for latest)
  OPENAI_API_KEY in .env

Usage:
  python paperbanana_generate.py "description" "output.png" --context "methodology text"
  python paperbanana_generate.py "description" "output.png" --direct
"""

import argparse
import asyncio
import logging
import os
import shutil
import sys

from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Walk up from this script to find .env at the workspace root
# Script lives at .github/skills/image-generator/scripts/paperbanana_generate.py
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SCRIPT_DIR.parents[3]  # scripts → image-generator → skills → .github → repo root
_ENV_FILE = _WORKSPACE_ROOT / ".env"

if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
    logger.info("Loaded .env from %s", _ENV_FILE)
else:
    # Fallback: let find_dotenv search from CWD upward
    load_dotenv()
    logger.warning("No .env at %s — falling back to find_dotenv()", _ENV_FILE)


def _build_settings(iterations: int = 3) -> "Settings":
    """Build PaperBanana Settings configured for OpenAI provider.

    Package defaults: gpt-5.2 (VLM), gpt-image-1.5 (image gen).
    Override via TEXT_MODEL / IMAGE_MODEL env vars if needed.
    """
    from paperbanana.core.config import Settings

    vlm_model = os.environ.get("TEXT_MODEL", "gpt-5.2")
    image_model = os.environ.get("IMAGE_MODEL", "gpt-image-1.5")

    kwargs: dict = {
        "vlm_provider": "openai",
        "image_provider": "openai_imagen",
        "vlm_model": vlm_model,
        "image_model": image_model,
        "openai_vlm_model": vlm_model,
        "openai_image_model": image_model,
        "refinement_iterations": iterations,
        "auto_refine": False,
        "optimize_inputs": False,
        "output_format": "png",
        "save_iterations": True,
    }

    return Settings(**kwargs)


async def run_pipeline(
    description: str,
    output_path: str,
    context: str = "",
    max_critic_rounds: int = 2,
) -> str:
    """Run the full PaperBanana pipeline via the real package.

    Returns the output image path.
    """
    from paperbanana import PaperBananaPipeline, GenerationInput, DiagramType

    settings = _build_settings(iterations=max_critic_rounds)
    pipeline = PaperBananaPipeline(settings=settings)

    gen_input = GenerationInput(
        source_context=context or description,
        communicative_intent=description,
        diagram_type=DiagramType.METHODOLOGY,
    )

    logger.info("Starting pipeline (provider=openai, iterations=%d)…", max_critic_rounds)
    result = await pipeline.generate(gen_input)

    # Copy the final image to the requested output path
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    shutil.copy2(result.image_path, output_path)

    logger.info("Pipeline complete: %d iteration(s), saved to %s", len(result.iterations), output_path)
    return output_path


def run_direct(description: str, output_path: str, size: str = "") -> str:
    """Direct OpenAI generation — single API call, simpler output."""
    import base64
    import openai

    client = openai.OpenAI()
    model = os.environ.get("IMAGE_MODEL", "gpt-image-1.5")
    size = size or os.environ.get("IMAGE_SIZE", "1536x1024")

    prompt = (
        "Create a professional, publication-quality technical diagram in clean vector infographic style. "
        "Use soft pastel color fills for blocks, thin gray borders, rounded rectangles, clean sans-serif labels, "
        "directional arrows with arrowheads, and generous whitespace on a pure white background. "
        "No monospaced fonts, no ASCII art, no terminal-style rendering. "
        "The diagram should look like a polished Figma/Lucidchart export.\n\n"
        f"{description}"
    )
    logger.info("Generating image via OpenAI direct mode (model=%s, size=%s)…", model, size)

    response = client.images.generate(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
        quality="high",
        background="opaque",
        output_format="png",
    )
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    image_data = base64.b64decode(response.data[0].b64_json)
    with open(output_path, "wb") as f:
        f.write(image_data)

    logger.info("Saved to %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PaperBanana academic illustration generator (llmsresearch/paperbanana)"
    )
    parser.add_argument("description", help="Illustration description / communicative intent")
    parser.add_argument("output", help="Output PNG path")
    parser.add_argument(
        "--context", default="",
        help="Methodology context text for the Planner agent"
    )
    parser.add_argument(
        "--critic-rounds", type=int, default=None,
        help="Visualizer-Critic refinement iterations (default: MAX_CRITIC_ROUNDS env or 2)"
    )
    parser.add_argument(
        "--direct", action="store_true",
        help="Skip PaperBanana pipeline, use direct OpenAI image generation"
    )
    parser.add_argument(
        "--size", default="",
        help="Image size (e.g., 1536x1024, 1024x1024). Default from IMAGE_SIZE env or 1536x1024"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not os.environ.get("OPENAI_API_KEY"):
        logger.error(
            "OPENAI_API_KEY not found in environment. "
            "Ensure .env exists at workspace root (%s) with OPENAI_API_KEY=sk-...",
            _WORKSPACE_ROOT,
        )
        sys.exit(1)

    max_rounds = args.critic_rounds or int(os.environ.get("MAX_CRITIC_ROUNDS", "2"))

    if args.direct:
        run_direct(args.description, args.output, size=args.size)
    else:
        asyncio.run(run_pipeline(
            description=args.description,
            output_path=args.output,
            context=args.context,
            max_critic_rounds=max_rounds,
        ))


if __name__ == "__main__":
    main()
