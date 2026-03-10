#!/usr/bin/env python3
"""
Eye Care Stage 2 Tagging — Assign all 66 tag fields to classified questions.

Queries Supabase for questions that have disease_state but no topic (classified
in Stage 1 but not yet tagged). Uses 2-model voting (GPT-5.2 + Gemini 2.5 Pro)
via OpenRouter to assign all 66 tag fields, then updates the tags table.

Usage:
    python scripts/run_eye_care_stage2.py --dry-run --limit 5
    python scripts/run_eye_care_stage2.py --limit 50 --batch-size 3
    python scripts/run_eye_care_stage2.py
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

PROMPT_PATH = PROJECT_ROOT / "prompts" / "v1.0" / "eye_care_system_prompt.txt"
CHECKPOINT_DIR = PROJECT_ROOT / "data" / "checkpoints"

VOTING_MODELS = ["gpt", "gemini"]

# All 66 tag fields that the LLM should return
TAG_FIELDS = [
    "topic", "disease_stage", "disease_type", "treatment_line",
    "treatment_1", "treatment_2", "treatment_3", "treatment_4", "treatment_5",
    "biomarker_1", "biomarker_2", "biomarker_3", "biomarker_4", "biomarker_5",
    "trial_1", "trial_2", "trial_3", "trial_4", "trial_5",
    "drug_class_1", "drug_class_2", "drug_class_3",
    "drug_target_1", "drug_target_2", "drug_target_3",
    "prior_therapy_1", "prior_therapy_2", "prior_therapy_3",
    "resistance_mechanism",
    "metastatic_site_1", "metastatic_site_2", "metastatic_site_3",
    "symptom_1", "symptom_2", "symptom_3",
    "special_population_1", "special_population_2",
    "performance_status",
    "toxicity_type_1", "toxicity_type_2", "toxicity_type_3",
    "toxicity_type_4", "toxicity_type_5",
    "toxicity_organ", "toxicity_grade",
    "efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3",
    "outcome_context", "clinical_benefit",
    "guideline_source_1", "guideline_source_2",
    "evidence_type",
    "cme_outcome_level", "data_response_type",
    "stem_type", "lead_in_type", "answer_format",
    "answer_length_pattern", "distractor_homogeneity",
    "flaw_absolute_terms", "flaw_grammatical_cue",
    "flaw_implausible_distractor", "flaw_clang_association",
    "flaw_convergence_vulnerability", "flaw_double_negative",
]

# Boolean fields need special handling
BOOLEAN_FIELDS = {
    "flaw_absolute_terms", "flaw_grammatical_cue",
    "flaw_implausible_distractor", "flaw_clang_association",
    "flaw_convergence_vulnerability", "flaw_double_negative",
}


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


def fetch_untagged_questions(client, limit=None):
    """
    Fetch questions that have disease_state (Stage 1 done) but no topic (Stage 2 not done).
    """
    # Get all questions with tags that have disease_state but no topic
    query = (
        client.table("tags")
        .select("question_id, disease_state")
        .not_.is_("disease_state", "null")
        .is_("topic", "null")
        .order("question_id")
    )
    if limit:
        query = query.limit(limit)
    tag_result = query.execute()
    tag_rows = tag_result.data or []

    if not tag_rows:
        return []

    # Get the question details for these
    question_ids = [t["question_id"] for t in tag_rows]
    disease_map = {t["question_id"]: t["disease_state"] for t in tag_rows}

    # Fetch in chunks of 100 (Supabase IN filter limit)
    questions = []
    for i in range(0, len(question_ids), 100):
        chunk = question_ids[i:i+100]
        q_result = (
            client.table("questions")
            .select("id, source_id, question_stem, correct_answer")
            .in_("id", chunk)
            .execute()
        )
        for q in (q_result.data or []):
            q["disease_state"] = disease_map.get(q["id"])
            questions.append(q)

    # Sort by id
    questions.sort(key=lambda q: q["id"])
    return questions


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
# JSON parsing
# ---------------------------------------------------------------------------

def parse_tag_response(content: str) -> dict:
    """Parse 66-field JSON response from LLM."""
    if not content:
        return {}
    content = content.strip()

    # Strategy 1: Extract from ```json ... ``` code block
    json_block = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if json_block:
        try:
            return _normalize_tags(json.loads(json_block.group(1).strip()))
        except json.JSONDecodeError:
            pass

    # Strategy 2: Find the largest JSON object
    # Look for opening brace through closing brace
    brace_start = content.find('{')
    if brace_start >= 0:
        # Find matching closing brace
        depth = 0
        for i in range(brace_start, len(content)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return _normalize_tags(json.loads(content[brace_start:i+1]))
                    except json.JSONDecodeError:
                        break

    # Strategy 3: Try entire content
    for prefix in ("```json", "```"):
        if content.startswith(prefix):
            content = content[len(prefix):]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return _normalize_tags(json.loads(content))
    except json.JSONDecodeError:
        pass

    # Strategy 4: Regex extraction for key fields
    result = {}
    # Extract topic (most critical field)
    topic_match = re.search(r'"topic"\s*:\s*"([^"]+)"', content)
    if topic_match:
        result["topic"] = topic_match.group(1).strip()

    # Extract other string fields
    for field in TAG_FIELDS:
        if field in BOOLEAN_FIELDS:
            bool_match = re.search(rf'"{field}"\s*:\s*(true|false)', content, re.IGNORECASE)
            if bool_match:
                result[field] = bool_match.group(1).lower() == "true"
        elif field not in result:
            str_match = re.search(rf'"{field}"\s*:\s*"([^"]*)"', content)
            if str_match:
                val = str_match.group(1).strip()
                result[field] = val if val else None

    if result:
        return _normalize_tags(result)

    logger.warning(f"Failed to parse tag JSON: {content[:200]}")
    return {}


def _normalize_tags(parsed: dict) -> dict:
    """Normalize parsed tag values."""
    result = {}
    for field in TAG_FIELDS:
        val = parsed.get(field)
        if field in BOOLEAN_FIELDS:
            if isinstance(val, bool):
                result[field] = val
            elif isinstance(val, str):
                result[field] = val.lower() in ("true", "1", "yes")
            else:
                result[field] = False  # Default to false for boolean flaws
        else:
            if val is None or (isinstance(val, str) and val.strip().lower() in ("null", "n/a", "")):
                result[field] = None
            else:
                result[field] = str(val).strip() if val else None
    return result


# ---------------------------------------------------------------------------
# Voting logic
# ---------------------------------------------------------------------------

def aggregate_tag_votes(model_results: dict) -> dict:
    """
    Aggregate 2-model votes for 66 tag fields.

    For each field:
    - If both models agree, use that value (unanimous)
    - If they disagree, use GPT's value and flag for review
    """
    valid_models = {m: r for m, r in model_results.items() if r and isinstance(r, dict) and r.get("topic")}
    n_valid = len(valid_models)

    if n_valid == 0:
        return {
            "tags": {f: None for f in TAG_FIELDS},
            "agreement": "no_votes",
            "needs_review": True,
            "review_reason": "no_valid_votes",
            "conflict_fields": [],
            "voting_details": model_results,
        }

    if n_valid == 1:
        tags = list(valid_models.values())[0]
        return {
            "tags": tags,
            "agreement": "partial_response",
            "needs_review": True,
            "review_reason": "single_model_response",
            "conflict_fields": [],
            "voting_details": model_results,
        }

    # 2 valid votes — compare field by field
    models = list(valid_models.keys())
    votes_a = valid_models[models[0]]
    votes_b = valid_models[models[1]]

    final_tags = {}
    conflict_fields = []

    for field in TAG_FIELDS:
        val_a = votes_a.get(field)
        val_b = votes_b.get(field)

        # Normalize for comparison
        if field in BOOLEAN_FIELDS:
            a_norm = bool(val_a) if val_a is not None else False
            b_norm = bool(val_b) if val_b is not None else False
        else:
            a_norm = (str(val_a).strip().lower() if val_a else None)
            b_norm = (str(val_b).strip().lower() if val_b else None)

        if a_norm == b_norm:
            final_tags[field] = val_a if val_a is not None else val_b
        else:
            # Disagreement — prefer GPT's value
            gpt_val = valid_models.get("gpt", votes_a).get(field)
            final_tags[field] = gpt_val
            conflict_fields.append(field)

    # Determine overall agreement
    if not conflict_fields:
        agreement = "unanimous"
        needs_review = False
        review_reason = None
    else:
        agreement = "majority"  # GPT breaks ties
        needs_review = True
        review_reason = f"conflict_in_fields:{','.join(conflict_fields[:10])}"
        if len(conflict_fields) > 10:
            review_reason += f"...+{len(conflict_fields)-10}"

    return {
        "tags": final_tags,
        "agreement": agreement,
        "needs_review": needs_review,
        "review_reason": review_reason,
        "conflict_fields": conflict_fields,
        "voting_details": {m: model_results.get(m, {}) for m in VOTING_MODELS},
    }


# ---------------------------------------------------------------------------
# Tagging
# ---------------------------------------------------------------------------

async def tag_question(
    llm_client: OpenRouterClient,
    system_prompt: str,
    question: dict,
    activity_names: list,
) -> dict:
    """Tag a single question using 2-model voting."""
    # Build user message
    parts = [
        f"**Disease State:** {question.get('disease_state', 'Unknown')}",
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
        max_tokens=2000,  # 66 fields need more tokens
    )

    # Parse each model's response
    model_results = {}
    for model in VOTING_MODELS:
        resp = responses.get(model)
        if resp and isinstance(resp, dict) and "content" in resp:
            parsed = parse_tag_response(resp["content"])
            model_results[model] = parsed
        else:
            model_results[model] = None
            if resp and isinstance(resp, dict) and "error" in resp:
                logger.warning(f"  {model} error: {resp['error']}")

    # Aggregate votes
    result = aggregate_tag_votes(model_results)
    result["question_id"] = question["id"]
    result["source_id"] = question.get("source_id")
    result["disease_state"] = question.get("disease_state")
    return result


async def tag_batch(
    llm_client: OpenRouterClient,
    supabase_client,
    system_prompt: str,
    questions: list,
) -> list:
    """Tag a batch of questions concurrently."""
    tasks = []
    for q in questions:
        activities = fetch_question_activities(supabase_client, q["id"])
        coro = tag_question(llm_client, system_prompt, q, activities)
        tasks.append(asyncio.wait_for(coro, timeout=120.0))  # 2 min timeout per question

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"  Error tagging question {questions[i]['id']}: {result}")
            processed.append({
                "question_id": questions[i]["id"],
                "source_id": questions[i].get("source_id"),
                "disease_state": questions[i].get("disease_state"),
                "tags": {},
                "agreement": "error",
                "needs_review": True,
                "review_reason": str(result),
                "conflict_fields": [],
            })
        else:
            processed.append(result)

    return processed


def update_supabase(client, result: dict):
    """Update tags table with Stage 2 tag fields."""
    question_id = result["question_id"]
    tags = result.get("tags", {})

    if not tags or not tags.get("topic"):
        logger.warning(f"  Skipping QID={question_id}: no valid tags")
        return

    # Build update data — only include fields that exist in the DB
    update_data = {}
    for field in TAG_FIELDS:
        val = tags.get(field)
        if field in BOOLEAN_FIELDS:
            update_data[field] = bool(val) if val is not None else False
        else:
            update_data[field] = val

    # Add metadata
    update_data["tag_status"] = result.get("agreement", "unknown")
    update_data["agreement_level"] = result.get("agreement", "unknown")
    update_data["needs_review"] = result.get("needs_review", False)
    update_data["review_reason"] = result.get("review_reason")

    # Use metastatic_site columns for comorbidities (eye care mapping)
    # The prompt already uses metastatic_site_1-3 field names, so no remapping needed

    # Update the existing tag row
    client.table("tags").update(update_data).eq("question_id", question_id).execute()


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def save_checkpoint(results: list, checkpoint_path: Path):
    """Save results to checkpoint file."""
    serializable = []
    for r in results:
        sr = {}
        for k, v in r.items():
            if k == "voting_details":
                sr[k] = {
                    m: v2 if isinstance(v2, (dict, type(None))) else str(v2)
                    for m, v2 in (v or {}).items()
                }
            else:
                sr[k] = v
        serializable.append(sr)

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)


def load_checkpoint(checkpoint_path: Path) -> list:
    """Load results from checkpoint file."""
    if checkpoint_path.exists():
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


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

    # Checkpoint setup
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_path = CHECKPOINT_DIR / f"eye_care_stage2_{timestamp}.json"

    # Resume from checkpoint if specified
    all_results = []
    already_tagged_ids = set()
    if args.checkpoint:
        resume_path = Path(args.checkpoint)
        all_results = load_checkpoint(resume_path)
        already_tagged_ids = {r["question_id"] for r in all_results if r.get("agreement") != "error"}
        logger.info(f"Resumed from checkpoint: {len(all_results)} results ({len(already_tagged_ids)} successful)")
        checkpoint_path = resume_path  # Continue writing to the same file

    # Fetch untagged questions
    logger.info("Fetching untagged questions from Supabase (disease_state set, topic NULL)...")
    questions = fetch_untagged_questions(supabase_client, limit=args.limit)
    logger.info(f"Found {len(questions)} untagged questions")

    # Exclude already-processed questions from checkpoint
    if already_tagged_ids:
        questions = [q for q in questions if q["id"] not in already_tagged_ids]
        logger.info(f"After excluding checkpoint: {len(questions)} remaining")

    if not questions:
        logger.info("Nothing to tag. Exiting.")
        if all_results:
            _print_summary(all_results, llm_client)
        return

    # Process in batches
    batch_size = args.batch_size
    total_batches = (len(questions) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(questions))
        batch = questions[start:end]

        logger.info(f"Batch {batch_idx + 1}/{total_batches}: questions {start + 1}-{end}")
        results = await tag_batch(llm_client, supabase_client, system_prompt, batch)

        for r in results:
            topic = r.get("tags", {}).get("topic", "N/A")
            agreement = r.get("agreement", "?")
            n_conflicts = len(r.get("conflict_fields", []))
            logger.info(f"  QID={r['question_id']} → topic={topic} ({agreement}, {n_conflicts} conflicts)")

        if not args.dry_run:
            for r in results:
                if r.get("agreement") != "error":
                    update_supabase(supabase_client, r)

        all_results.extend(results)

        # Save checkpoint after each batch
        save_checkpoint(all_results, checkpoint_path)
        logger.info(f"  Checkpoint saved ({len(all_results)} total results)")

    # Summary
    _print_summary(all_results, llm_client)
    print(f"\nCheckpoint saved: {checkpoint_path}")

    if args.dry_run:
        print("\n*** DRY RUN - no changes written to Supabase ***")


def _print_summary(all_results: list, llm_client: OpenRouterClient):
    """Print tagging summary."""
    print("\n" + "=" * 60)
    print("STAGE 2 TAGGING SUMMARY")
    print("=" * 60)

    # Topic distribution
    topics = [r.get("tags", {}).get("topic") or "NO TOPIC" for r in all_results]
    topic_counts = Counter(topics)
    print("\nTopics:")
    for topic, count in topic_counts.most_common():
        print(f"  {topic}: {count}")

    # Disease state distribution
    diseases = [r.get("disease_state") or "UNKNOWN" for r in all_results]
    disease_counts = Counter(diseases)
    print(f"\nDisease states ({len(disease_counts)} unique):")
    for ds, count in disease_counts.most_common(10):
        print(f"  {ds}: {count}")
    if len(disease_counts) > 10:
        print(f"  ... and {len(disease_counts) - 10} more")

    # Agreement stats
    agreements = Counter(r.get("agreement") for r in all_results)
    print(f"\nAgreement:")
    for level, count in agreements.most_common():
        print(f"  {level}: {count}")

    # Conflict field frequency
    all_conflicts = []
    for r in all_results:
        all_conflicts.extend(r.get("conflict_fields", []))
    if all_conflicts:
        conflict_counts = Counter(all_conflicts)
        print(f"\nMost-conflicted fields:")
        for field, count in conflict_counts.most_common(10):
            print(f"  {field}: {count}")

    needs_review = sum(1 for r in all_results if r.get("needs_review"))
    print(f"\nNeeds review: {needs_review}/{len(all_results)}")

    # Cost summary
    usage = llm_client.get_usage_summary()
    print(f"\nAPI Cost: ${usage.get('total_cost', 0):.4f}")
    for model, stats in usage.get("by_model", {}).items():
        print(f"  {model}: {stats.get('calls', 0)} calls, ${stats.get('cost', 0):.4f}")


def main():
    parser = argparse.ArgumentParser(
        description="Eye Care Stage 2 Tagging - assign all 66 tag fields"
    )
    parser.add_argument("--dry-run", action="store_true", help="Tag without updating Supabase")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions")
    parser.add_argument("--batch-size", type=int, default=3, help="Concurrent batch size (default: 3)")
    parser.add_argument("--checkpoint", type=str, default=None, help="Resume from checkpoint file")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
