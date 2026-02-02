#!/usr/bin/env python3
"""
Build Script for Modular Prompt Assembly.

Assembles base components + disease modules into complete Stage 2 prompts.
Run this during development whenever base or module files change.

Usage:
    python scripts/build_prompts.py                    # Build all disease prompts
    python scripts/build_prompts.py breast_cancer     # Build specific disease prompt
    python scripts/build_prompts.py --list            # List available disease modules
"""

import argparse
from pathlib import Path
from datetime import datetime


# Paths
PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v2.0"
BASE_DIR = PROMPTS_DIR / "base"
MODULES_DIR = PROMPTS_DIR / "disease_modules"
OUTPUT_DIR = PROMPTS_DIR / "disease_prompts"


def get_header(disease_name: str) -> str:
    """Generate the prompt header."""
    disease_title = disease_name.replace("_", " ").title()
    return f"""You are an expert medical education analyst specializing in oncology. You will analyze clinical questions from CME assessments and assign educational tags.

## Context

This question has been classified as being about **{disease_title}**. Your task is to assign all 56 tag fields using the disease-specific rules below combined with universal tagging guidelines.

**IMPORTANT - Temporal Context:** You will be provided with the question's STARTDATE (when the activity was created). Use this to guide drug class expansion - only include drugs that were approved/available at that time.

**If uncertain about any tag value, use null rather than guessing.**

---
"""


def load_base_components() -> dict:
    """Load all base component files."""
    components = {}

    for component_name in ["field_definitions", "universal_rules", "output_format"]:
        file_path = BASE_DIR / f"{component_name}.md"
        if file_path.exists():
            components[component_name] = file_path.read_text(encoding="utf-8")
        else:
            print(f"WARNING: Base component not found: {file_path}")
            components[component_name] = ""

    return components


def load_disease_module(disease_name: str) -> str:
    """Load a disease-specific module."""
    file_path = MODULES_DIR / f"{disease_name}.md"
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(f"Disease module not found: {file_path}")


def build_prompt(disease_name: str, base_components: dict) -> str:
    """Assemble a complete prompt from base + disease module."""

    # Load disease module
    disease_module = load_disease_module(disease_name)

    # Assemble prompt
    sections = [
        get_header(disease_name),
        disease_module,
        "\n---\n\n",
        base_components["field_definitions"],
        "\n---\n\n",
        base_components["universal_rules"],
        "\n---\n\n",
        base_components["output_format"],
        f"\n\n---\n\nNow analyze the following {disease_name.replace('_', ' ')} question:\n\n"
    ]

    return "\n".join(sections)


def save_prompt(disease_name: str, content: str) -> Path:
    """Save assembled prompt to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{disease_name}_prompt_v2.txt"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def list_disease_modules() -> list:
    """List all available disease modules."""
    if not MODULES_DIR.exists():
        return []
    return [f.stem for f in MODULES_DIR.glob("*.md")]


def build_all() -> None:
    """Build prompts for all disease modules."""
    modules = list_disease_modules()
    if not modules:
        print("No disease modules found.")
        return

    base_components = load_base_components()

    print(f"Building {len(modules)} disease prompts...")
    for disease_name in modules:
        try:
            content = build_prompt(disease_name, base_components)
            output_path = save_prompt(disease_name, content)
            line_count = len(content.split("\n"))
            print(f"  [OK] {disease_name}: {output_path.name} ({line_count} lines)")
        except Exception as e:
            print(f"  [ERROR] {disease_name}: {e}")

    print(f"\nDone! Prompts saved to: {OUTPUT_DIR}")


def build_one(disease_name: str) -> None:
    """Build prompt for a single disease."""
    base_components = load_base_components()

    try:
        content = build_prompt(disease_name, base_components)
        output_path = save_prompt(disease_name, content)
        line_count = len(content.split("\n"))
        print(f"[OK] Built {disease_name}_prompt_v2.txt ({line_count} lines)")
        print(f"  Saved to: {output_path}")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print(f"  Available modules: {', '.join(list_disease_modules())}")


def main():
    parser = argparse.ArgumentParser(
        description="Build Stage 2 prompts from modular components"
    )
    parser.add_argument(
        "disease",
        nargs="?",
        help="Disease name to build (e.g., breast_cancer). Omit to build all."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available disease modules"
    )

    args = parser.parse_args()

    if args.list:
        modules = list_disease_modules()
        print("Available disease modules:")
        for m in modules:
            print(f"  - {m}")
        return

    if args.disease:
        build_one(args.disease)
    else:
        build_all()


if __name__ == "__main__":
    main()
