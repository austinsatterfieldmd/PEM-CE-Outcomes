#!/usr/bin/env python3
"""
Eye Care Stage 1 Classification — Classify questions by eye care condition.

Queries Supabase for unclassified questions, sends each through 2-model voting
(GPT-5.2 + Gemini 2.5 Pro) using the eye care classifier prompt, and updates
disease_state in the tags table.

Usage:
    python scripts/run_eye_care_stage1.py --dry-run --limit 5
    python scripts/run_eye_care_stage1.py --limit 50
    python scripts/run_eye_care_stage1.py
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.core.taggers.openrouter_client import OpenRouterClient, RetryConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROMPT_PATH = PROJECT_ROOT / "prompts" / "v1.0" / "eye_care_classifier_prompt.txt"
CHECKPOINT_DIR = PROJECT_ROOT / "data" / "checkpoints"

VOTING_MODELS = ["gpt", "gemini"]


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def get_supabase_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)
    return create_client(url, key)


def fetch_unclassified_questions(client, limit=None):
    """Fetch questions where disease_state is NULL and is_oncology=TRUE."""
    # Get questions without tags or with NULL disease_state
    query = (
        client.table("questions")
        .select("id, source_id, question_stem, correct_answer")
        .eq("is_oncology", True)
        .order("id")
    )
    if limit:
        query = query.limit(limit)
    result = query.execute()
    questions = result.data or []

    # Filter to those without disease_state in tags
    unclassified = []
    for q in questions:
        tag_result = (
            client.table("tags")
            .select("disease_state")
            .eq("question_id", q["id"])
            .execute()
        )
        if not tag_result.data or tag_result.data[0].get("disease_state") is None:
            unclassified.append(q)
        if limit and len(unclassified) >= limit:
            break

    return unclassified


def fetch_question_activities(client, question_id):
    """Get activity names for a question."""
    result = (
        client.table("question_activities")
        .select("activity_name")
        .eq("question_id", question_id)
        .execute()
    )
    return [r["activity_name"] for r in (result.data or [])]


# ---------------------------------------------------------------------------
# JSON parsing (adapted from disease_classifier.py)
# ---------------------------------------------------------------------------

def parse_eye_care_response(content: str) -> dict:
    """Parse JSON response from LLM for eye care classification."""
    default = {"is_eye_care": None, "condition": None, "condition_secondary": None}
    if not content:
        return default
    content = content.strip()

    # Strategy 1: Extract from ```json ... ``` code block
    json_block = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if json_block:
        try:
            parsed = json.loads(json_block.group(1).strip())
            return _normalize_parsed(parsed)
        except json.JSONDecodeError:
            pass

    # Strategy 2: Find raw JSON with is_eye_care key
    json_obj = re.search(r'\{[^{}]*"is_eye_care"[^{}]*\}', content)
    if json_obj:
        try:
            parsed = json.loads(json_obj.group(0))
            return _normalize_parsed(parsed)
        except json.JSONDecodeError:
            pass

    # Strategy 3: Try parsing entire content
    for prefix in ("```json", "```"):
        if content.startswith(prefix):
            content = content[len(prefix):]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        parsed = json.loads(content)
        return _normalize_parsed(parsed)
    except json.JSONDecodeError:
        pass

    # Strategy 4: Handle truncated JSON — extract fields with regex
    result = dict(default)
    eye_care_match = re.search(r'"is_eye_care"\s*:\s*(true|false)', content, re.IGNORECASE)
    if eye_care_match:
        result["is_eye_care"] = eye_care_match.group(1).lower() == "true"

    condition_match = re.search(r'"condition"\s*:\s*"([^"]+)"', content)
    if condition_match:
        result["condition"] = condition_match.group(1).strip()

    secondary_match = re.search(r'"condition_secondary"\s*:\s*"([^"]+)"', content)
    if secondary_match:
        result["condition_secondary"] = secondary_match.group(1).strip()

    if result["is_eye_care"] is not None or result["condition"] is not None:
        return result

    logger.warning(f"Failed to parse JSON: Content: {content[:200]}")
    return default


def _normalize_parsed(parsed: dict) -> dict:
    """Normalize parsed JSON to consistent format."""
    result = {
        "is_eye_care": parsed.get("is_eye_care"),
        "condition": parsed.get("condition"),
        "condition_secondary": parsed.get("condition_secondary"),
    }
    if result["is_eye_care"] is not None:
        result["is_eye_care"] = bool(result["is_eye_care"])
    return result


# ---------------------------------------------------------------------------
# Voting logic (adapted from disease_classifier.py)
# ---------------------------------------------------------------------------

def aggregate_votes(model_results: dict) -> dict:
    """
    Aggregate 2-model votes for eye care classification.

    Returns:
        {
            "is_eye_care": bool or None,
            "condition": str or None,
            "condition_secondary": str or None,
            "agreement": "unanimous" | "majority" | "conflict" | "partial_response",
            "needs_review": bool,
            "review_reason": str or None,
            "voting_details": { model_name: {is_eye_care, condition}, ... }
        }
    """
    valid_votes = {}
    for model, resp in model_results.items():
        if resp and resp.get("is_eye_care") is not None:
            valid_votes[model] = resp

    voting_details = {m: model_results.get(m, {}) for m in VOTING_MODELS}
    n_valid = len(valid_votes)

    # No valid votes
    if n_valid == 0:
        return {
            "is_eye_care": None,
            "condition": None,
            "condition_secondary": None,
            "agreement": "no_votes",
            "needs_review": True,
            "review_reason": "no_valid_votes",
            "voting_details": voting_details,
        }

    # Only 1 valid vote
    if n_valid == 1:
        vote = list(valid_votes.values())[0]
        return {
            "is_eye_care": vote.get("is_eye_care"),
            "condition": vote.get("condition"),
            "condition_secondary": vote.get("condition_secondary"),
            "agreement": "partial_response",
            "needs_review": True,
            "review_reason": "single_model_response",
            "voting_details": voting_details,
        }

    # 2 valid votes — compare
    votes = list(valid_votes.values())
    eye_care_votes = [v.get("is_eye_care") for v in votes]
    condition_votes = [v.get("condition") for v in votes]

    # Normalize condition names for comparison (case-insensitive)
    condition_normalized = [
        c.strip() if c else None for c in condition_votes
    ]

    # is_eye_care agreement
    if eye_care_votes[0] == eye_care_votes[1]:
        eye_care_agreement = "unanimous"
    else:
        eye_care_agreement = "conflict"

    # condition agreement (case-insensitive)
    c0 = (condition_normalized[0] or "").lower()
    c1 = (condition_normalized[1] or "").lower()
    if c0 == c1:
        condition_agreement = "unanimous"
    else:
        condition_agreement = "conflict"

    # Determine final values
    if eye_care_agreement == "unanimous" and condition_agreement == "unanimous":
        # Both agree on everything
        return {
            "is_eye_care": eye_care_votes[0],
            "condition": condition_votes[0],
            "condition_secondary": votes[0].get("condition_secondary"),
            "agreement": "unanimous",
            "needs_review": False,
            "review_reason": None,
            "voting_details": voting_details,
        }

    # Disagreement — use GPT's answer, flag for review
    gpt_vote = valid_votes.get("gpt", votes[0])
    reasons = []
    if eye_care_agreement == "conflict":
        reasons.append("eye_care_conflict")
    if condition_agreement == "conflict":
        reasons.append("condition_conflict")

    return {
        "is_eye_care": gpt_vote.get("is_eye_care"),
        "condition": gpt_vote.get("condition"),
        "condition_secondary": gpt_vote.get("condition_secondary"),
        "agreement": "conflict",
        "needs_review": True,
        "review_reason": "|".join(reasons),
        "voting_details": voting_details,
    }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

async def classify_question(
    llm_client: OpenRouterClient,
    system_prompt: str,
    question: dict,
    activity_names: list,
) -> dict:
    """Classify a single question using 2-model voting."""
    # Build user message
    parts = [
        f"**Question:** {question['question_stem']}",
        f"**Correct Answer:** {question.get('correct_answer', 'N/A')}",
    ]
    if activity_names:
        parts.append(f"**Activity Title:** {'; '.join(activity_names)}")

    user_message = "\n".join(parts)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Call models in parallel
    responses = await llm_client.generate_parallel(
        messages=messages,
        models=VOTING_MODELS,
        temperature=0.0,
        max_tokens=1000,
    )

    # Parse each model's response
    model_results = {}
    for model in VOTING_MODELS:
        resp = responses.get(model)
        if resp and isinstance(resp, dict) and "content" in resp:
            parsed = parse_eye_care_response(resp["content"])
            model_results[model] = parsed
        else:
            model_results[model] = None
            if resp and isinstance(resp, dict) and "error" in resp:
                logger.warning(f"  {model} error: {resp['error']}")

    # Aggregate votes
    result = aggregate_votes(model_results)
    result["question_id"] = question["id"]
    result["source_id"] = question.get("source_id")
    return result


async def classify_batch(
    llm_client: OpenRouterClient,
    supabase_client,
    system_prompt: str,
    questions: list,
    dry_run: bool = False,
) -> list:
    """Classify a batch of questions concurrently."""
    tasks = []
    for q in questions:
        activities = fetch_question_activities(supabase_client, q["id"])
        # Wrap each classification in a 90-second timeout to prevent hung requests
        coro = classify_question(llm_client, system_prompt, q, activities)
        tasks.append(asyncio.wait_for(coro, timeout=90.0))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"  Error classifying question {questions[i]['id']}: {result}")
            processed.append({
                "question_id": questions[i]["id"],
                "source_id": questions[i].get("source_id"),
                "is_eye_care": None,
                "condition": None,
                "agreement": "error",
                "needs_review": True,
                "review_reason": str(result),
            })
        else:
            processed.append(result)

    return processed


def update_supabase(client, result: dict):
    """Update tags table with classification result."""
    question_id = result["question_id"]
    condition = result.get("condition")
    condition_secondary = result.get("condition_secondary")
    is_eye_care = result.get("is_eye_care", True)

    tag_data = {
        "question_id": question_id,
        "disease_state": condition,
        "disease_state_1": condition if condition_secondary else None,
        "disease_state_2": condition_secondary,
        "needs_review": result.get("needs_review", False),
        "review_reason": result.get("review_reason"),
        "tag_status": result.get("agreement"),
        "agreement_level": result.get("agreement"),
    }

    # Upsert tag row
    client.table("tags").upsert(
        tag_data, on_conflict="question_id"
    ).execute()

    # If not eye care, mark is_oncology = FALSE on questions table
    if is_eye_care is False:
        client.table("questions").update(
            {"is_oncology": False}
        ).eq("id", question_id).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args):
    # Load prompt
    if not PROMPT_PATH.exists():
        logger.error(f"Prompt not found: {PROMPT_PATH}")
        sys.exit(1)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    logger.info(f"Loaded prompt: {PROMPT_PATH.name} ({len(system_prompt)} chars)")

    # Init clients
    supabase_client = get_supabase_client()
    llm_client = OpenRouterClient(retry_config=RetryConfig(max_retries=1))
    logger.info("Initialized Supabase + OpenRouter clients")

    # Fetch unclassified questions
    logger.info("Fetching unclassified questions from Supabase...")
    questions = fetch_unclassified_questions(supabase_client, limit=args.limit)
    logger.info(f"Found {len(questions)} unclassified questions")

    if not questions:
        logger.info("Nothing to classify. Exiting.")
        return

    # Process in batches
    all_results = []
    batch_size = args.batch_size
    total_batches = (len(questions) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(questions))
        batch = questions[start:end]

        logger.info(f"Batch {batch_idx + 1}/{total_batches}: questions {start + 1}-{end}")
        results = await classify_batch(
            llm_client, supabase_client, system_prompt, batch, args.dry_run
        )

        for r in results:
            condition = r.get("condition", "N/A")
            agreement = r.get("agreement", "?")
            logger.info(f"  QID={r['question_id']} → {condition} ({agreement})")

        if not args.dry_run:
            for r in results:
                if r.get("agreement") != "error":
                    update_supabase(supabase_client, r)

        all_results.extend(results)

    # Summary
    print("\n" + "=" * 60)
    print("CLASSIFICATION SUMMARY")
    print("=" * 60)

    conditions = [r.get("condition") or "UNCLASSIFIED" for r in all_results]
    condition_counts = Counter(conditions)
    for condition, count in condition_counts.most_common():
        print(f"  {condition}: {count}")

    agreements = Counter(r.get("agreement") for r in all_results)
    print(f"\nAgreement:")
    for level, count in agreements.most_common():
        print(f"  {level}: {count}")

    needs_review = sum(1 for r in all_results if r.get("needs_review"))
    print(f"\nNeeds review: {needs_review}/{len(all_results)}")

    # Cost summary
    usage = llm_client.get_usage_summary()
    print(f"\nAPI Cost: ${usage.get('total_cost', 0):.4f}")
    for model, stats in usage.get("by_model", {}).items():
        print(f"  {model}: {stats.get('calls', 0)} calls, ${stats.get('cost', 0):.4f}")

    # Save results
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = CHECKPOINT_DIR / f"eye_care_stage1_{timestamp}.json"

    # Serialize results (strip non-serializable items)
    serializable = []
    for r in all_results:
        sr = {k: v for k, v in r.items()}
        # Ensure voting_details is serializable
        if "voting_details" in sr:
            sr["voting_details"] = {
                m: v if isinstance(v, dict) else str(v)
                for m, v in sr["voting_details"].items()
            }
        serializable.append(sr)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)
    print(f"\nResults saved: {output_path}")

    if args.dry_run:
        print("\n*** DRY RUN — no changes written to Supabase ***")


def main():
    parser = argparse.ArgumentParser(
        description="Eye Care Stage 1 Classification — classify questions by condition"
    )
    parser.add_argument("--dry-run", action="store_true", help="Classify without updating Supabase")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions")
    parser.add_argument("--batch-size", type=int, default=5, help="Concurrent batch size (default: 5)")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
