"""
Reclassify Distractor Homogeneity
==================================
Re-evaluates distractor_homogeneity for all questions in a checkpoint file
using the updated definition, via a single LLM call per question.

New definition:
  Homogeneous: All options are the SAME TYPE and similar SPECIFICITY
    (interchangeable format, just swapping one entity for another).
  Heterogeneous: Options differ in TYPE, SPECIFICITY, or are substantively
    different statements requiring independent clinical evaluation.

Usage:
  # Preview changes (dry run):
  python scripts/reclassify_distractors.py --dry-run

  # Apply changes:
  python scripts/reclassify_distractors.py --apply

  # Use a different model:
  python scripts/reclassify_distractors.py --model google/gemini-2.5-pro --apply
"""

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-sonnet-4"

CLASSIFICATION_PROMPT = """You are classifying answer options for medical education questions.

TASK: Determine if the answer options are "Homogeneous" or "Heterogeneous".

DEFINITIONS:

"Homogeneous" — All options are the SAME TYPE and similar SPECIFICITY (interchangeable format, just swapping one entity for another):
- All specific drug names: "Osimertinib" / "Erlotinib" / "Afatinib" / "Gefitinib"
- All regimen names: "Dara-VRd" / "VRd" / "KRd" / "Isa-VRd"
- All biomarkers: "EGFR" / "ALK" / "ROS1" / "KRAS"
- All short clinical phrases of similar scope and length
- All numbers or numeric values: "2" / "3" / "4" / "5"

"Heterogeneous" — Options differ in TYPE, SPECIFICITY, or are substantively different statements:
- Mixed categories (drug name vs. dosing schedule vs. monitoring plan)
- Different scope/specificity (brief phrase vs. complex multi-clause statement)
- Substantively different clinical assertions even if sharing a broad theme
- Example: "This patient's age does not exclude transplant" / "Deeper remission will not be possible" / "If deferred, transplant no longer an option" / "Transplant unlikely to prolong TTP" → Heterogeneous (different clinical rationales requiring independent evaluation)

DECISION RULE: If options are interchangeable in format (just swapping one entity for another), use "Homogeneous". If each option must be evaluated on its own clinical merits, use "Heterogeneous".

---

ANSWER OPTIONS:
{options_text}

Respond with ONLY one word: "Homogeneous" or "Heterogeneous"
"""


def classify_options(options: list[str], api_key: str, model: str) -> str | None:
    """Send answer options to LLM for classification."""
    options_text = "\n".join(f"- {opt}" for opt in options)
    prompt = CLASSIFICATION_PROMPT.format(options_text=options_text)

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        # Parse response
        if "Homogeneous" in content:
            return "Homogeneous"
        elif "Heterogeneous" in content:
            return "Heterogeneous"
        else:
            logger.warning(f"Unexpected response: {content}")
            return None

    except Exception as e:
        logger.error(f"API call failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Re-evaluate distractor_homogeneity using updated definition."
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=str(PROJECT_ROOT / "data" / "checkpoints" / "stage2_tagged_multiple_myeloma.json"),
        help="Path to checkpoint JSON file"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to checkpoint (default: dry run)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing (default behavior)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"OpenRouter model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API calls in seconds (default: 0.5)"
    )

    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        logger.error(f"Checkpoint file not found: {checkpoint_path}")
        sys.exit(1)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)

    # Load checkpoint
    logger.info(f"Loading checkpoint: {checkpoint_path}")
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} questions")
    logger.info(f"Using model: {args.model}")

    # Process each question
    changes = []
    errors = 0
    same = 0

    for i, q in enumerate(data):
        qid = q.get("question_id", "?")
        correct = q.get("correct_answer", "")
        incorrect = q.get("incorrect_answers", [])

        if not correct or not incorrect:
            logger.warning(f"Q{qid}: Missing answer options, skipping")
            continue

        all_options = [correct] + incorrect
        current = (q.get("final_tags") or {}).get("distractor_homogeneity", None)

        # Classify
        new_class = classify_options(all_options, api_key, args.model)

        if new_class is None:
            errors += 1
            logger.warning(f"Q{qid}: Classification failed")
            continue

        if new_class != current:
            changes.append({
                "question_id": qid,
                "old": current,
                "new": new_class,
                "options": all_options,
            })
            logger.info(f"Q{qid}: {current} -> {new_class}")
        else:
            same += 1

        # Rate limiting
        if args.delay > 0 and i < len(data) - 1:
            time.sleep(args.delay)

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info(f"RESULTS")
    logger.info(f"  Total questions: {len(data)}")
    logger.info(f"  Unchanged: {same}")
    logger.info(f"  Changed: {len(changes)}")
    logger.info(f"  Errors: {errors}")
    logger.info("=" * 50)

    if changes:
        logger.info("\nChanges:")
        for c in changes:
            logger.info(f"  Q{c['question_id']}: {c['old']} -> {c['new']}")
            # Show first 2 options for context
            for opt in c['options'][:2]:
                logger.info(f"    - {opt[:80]}{'...' if len(opt) > 80 else ''}")
            if len(c['options']) > 2:
                logger.info(f"    ... ({len(c['options'])} options total)")

    # Apply changes
    if args.apply and changes:
        # Create backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = checkpoint_path.with_suffix(f'.pre_distractor_update_{timestamp}.json')
        shutil.copy2(checkpoint_path, backup_path)
        logger.info(f"\nBackup created: {backup_path}")

        # Build lookup
        q_lookup = {q["question_id"]: q for q in data}

        for c in changes:
            q = q_lookup.get(c["question_id"])
            if q and q.get("final_tags"):
                # Check if human-edited
                edited_fields = q.get("human_edited_fields", []) or []
                if "distractor_homogeneity" in edited_fields:
                    logger.info(f"  Q{c['question_id']}: Skipping (human-edited)")
                    continue

                q["final_tags"]["distractor_homogeneity"] = c["new"]

                # Append to review_reason
                review_reason = q.get("review_reason", "") or ""
                if "distractor_reclassified" not in review_reason:
                    sep = "|" if review_reason else ""
                    q["review_reason"] = review_reason + sep + "distractor_reclassified"

        # Save
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved updated checkpoint: {checkpoint_path}")

    elif not args.apply and changes:
        logger.info(f"\n[DRY RUN] {len(changes)} changes would be applied. Use --apply to save.")


if __name__ == "__main__":
    main()
