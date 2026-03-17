#!/usr/bin/env python3
"""
Tag remaining untagged/incomplete questions — insert missing tag rows,
run Stage 1 classification, then run Stage 2 tagging.

Handles three categories:
  - Questions with NO tag row at all (insert stubs)
  - Questions with tag row but NULL disease_state (Stage 1 incomplete)
  - Questions with disease_state but NULL topic (Stage 2 incomplete)

Usage:
    python scripts/tag_remaining_questions.py --dry-run
    python scripts/tag_remaining_questions.py --batch-size 3
    python scripts/tag_remaining_questions.py --skip-stage1
"""

import argparse
import asyncio
import io
import json
import logging
import os
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
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

load_dotenv(PROJECT_ROOT / ".env")

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.taggers.openrouter_client import OpenRouterClient, RetryConfig

from run_eye_care_stage1 import (
    get_supabase_client,
    fetch_unclassified_questions,
    classify_batch,
    update_supabase as update_supabase_stage1,
    PROMPT_PATH as STAGE1_PROMPT_PATH,
)
from run_eye_care_stage2 import (
    fetch_untagged_questions,
    tag_batch,
    update_supabase as update_supabase_stage2,
    save_checkpoint,
    PROMPT_PATH as STAGE2_PROMPT_PATH,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = PROJECT_ROOT / "data" / "checkpoints"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_all_ids(client, table: str, id_col: str, page_size: int = 1000) -> set:
    """Paginate through a table and collect all values of id_col."""
    ids = set()
    offset = 0
    while True:
        batch = (
            client.table(table)
            .select(id_col)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = batch.data or []
        ids.update(row[id_col] for row in rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return ids


# ---------------------------------------------------------------------------
# Step 1: Insert missing tag stubs
# ---------------------------------------------------------------------------

def step1_insert_stubs(client, dry_run: bool) -> int:
    """Find questions without tag rows and insert stub rows."""
    print("\n" + "=" * 60)
    print("STEP 1: Insert missing tag stubs")
    print("=" * 60)

    question_ids = fetch_all_ids(client, "questions", "id")
    tag_question_ids = fetch_all_ids(client, "tags", "question_id")
    missing = question_ids - tag_question_ids

    print(f"  Total questions: {len(question_ids)}")
    print(f"  Existing tag rows: {len(tag_question_ids)}")
    print(f"  Missing tag rows: {len(missing)}")

    if not missing:
        print("  Nothing to insert.")
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would insert {len(missing)} stub tag rows")
        return len(missing)

    inserted = 0
    for qid in sorted(missing):
        try:
            client.table("tags").insert({"question_id": qid}).execute()
            inserted += 1
        except Exception as e:
            logger.error(f"  Failed to insert stub for question_id={qid}: {e}")

    print(f"  Inserted {inserted} stub tag rows")
    return inserted


# ---------------------------------------------------------------------------
# Step 2: Stage 1 classification
# ---------------------------------------------------------------------------

async def step2_stage1(client, llm_client, batch_size: int, dry_run: bool) -> list:
    """Run Stage 1 classification on questions with NULL disease_state."""
    print("\n" + "=" * 60)
    print("STEP 2: Stage 1 — Classify by eye care condition")
    print("=" * 60)

    system_prompt = STAGE1_PROMPT_PATH.read_text(encoding="utf-8")
    logger.info(f"Loaded Stage 1 prompt ({len(system_prompt)} chars)")

    questions = fetch_unclassified_questions(client)
    print(f"  Questions needing Stage 1: {len(questions)}")

    if not questions:
        print("  Nothing to classify.")
        return []

    all_results = []
    total_batches = (len(questions) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(questions))
        batch = questions[start:end]

        logger.info(f"  Batch {batch_idx + 1}/{total_batches}: questions {start + 1}-{end}")
        results = await classify_batch(llm_client, client, system_prompt, batch, dry_run)

        for r in results:
            condition = r.get("condition", "N/A")
            agreement = r.get("agreement", "?")
            logger.info(f"    QID={r['question_id']} → {condition} ({agreement})")

        if not dry_run:
            for r in results:
                if r.get("agreement") != "error":
                    update_supabase_stage1(client, r)

        all_results.extend(results)

    # Summary
    conditions = Counter(r.get("condition") or "UNCLASSIFIED" for r in all_results)
    print(f"\n  Stage 1 classified {len(all_results)} questions — conditions:")
    for cond, count in conditions.most_common():
        print(f"    {cond}: {count}")

    # Save checkpoint
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cp_path = CHECKPOINT_DIR / f"remaining_stage1_{timestamp}.json"
    serializable = []
    for r in all_results:
        sr = {k: v for k, v in r.items()}
        if "voting_details" in sr:
            sr["voting_details"] = {
                m: v if isinstance(v, dict) else str(v)
                for m, v in sr["voting_details"].items()
            }
        serializable.append(sr)
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)
    print(f"  Checkpoint saved: {cp_path}")

    return all_results


# ---------------------------------------------------------------------------
# Step 3: Stage 2 tagging
# ---------------------------------------------------------------------------

async def step3_stage2(client, llm_client, batch_size: int, dry_run: bool) -> list:
    """Run Stage 2 tagging on questions with disease_state but NULL topic."""
    print("\n" + "=" * 60)
    print("STEP 3: Stage 2 — Assign all 66 tag fields")
    print("=" * 60)

    system_prompt = STAGE2_PROMPT_PATH.read_text(encoding="utf-8")
    logger.info(f"Loaded Stage 2 prompt ({len(system_prompt)} chars)")

    questions = fetch_untagged_questions(client)
    print(f"  Questions needing Stage 2: {len(questions)}")

    if not questions:
        print("  Nothing to tag.")
        return []

    all_results = []
    total_batches = (len(questions) + batch_size - 1) // batch_size

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cp_path = CHECKPOINT_DIR / f"remaining_stage2_{timestamp}.json"

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(questions))
        batch = questions[start:end]

        logger.info(f"  Batch {batch_idx + 1}/{total_batches}: questions {start + 1}-{end}")
        results = await tag_batch(llm_client, client, system_prompt, batch)

        for r in results:
            topic = r.get("tags", {}).get("topic", "N/A")
            agreement = r.get("agreement", "?")
            n_conflicts = len(r.get("conflict_fields", []))
            logger.info(f"    QID={r['question_id']} → topic={topic} ({agreement}, {n_conflicts} conflicts)")

        if not dry_run:
            for r in results:
                if r.get("agreement") != "error":
                    update_supabase_stage2(client, r)

        all_results.extend(results)
        save_checkpoint(all_results, cp_path)

    # Summary
    topics = Counter(r.get("tags", {}).get("topic") or "NO TOPIC" for r in all_results)
    print(f"\n  Stage 2 tagged {len(all_results)} questions — topics:")
    for topic, count in topics.most_common():
        print(f"    {topic}: {count}")
    print(f"  Checkpoint saved: {cp_path}")

    return all_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args):
    client = get_supabase_client()
    llm_client = OpenRouterClient(retry_config=RetryConfig(max_retries=1))
    logger.info("Initialized Supabase + OpenRouter clients")

    if not args.skip_stage1:
        # Step 1: Insert stubs
        step1_insert_stubs(client, args.dry_run)

        # Step 2: Stage 1 classification
        stage1_results = await step2_stage1(client, llm_client, args.batch_size, args.dry_run)
    else:
        print("\n  --skip-stage1: Skipping Steps 1 and 2")
        stage1_results = []

    # Step 3: Stage 2 tagging
    stage2_results = await step3_stage2(client, llm_client, args.batch_size, args.dry_run)

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"  Stage 1 classified: {len(stage1_results)} questions")
    print(f"  Stage 2 tagged: {len(stage2_results)} questions")

    usage = llm_client.get_usage_summary()
    total_cost = usage.get("total_cost", 0)
    print(f"  Total API cost: ${total_cost:.4f}")
    for model, stats in usage.get("by_model", {}).items():
        print(f"    {model}: {stats.get('calls', 0)} calls, ${stats.get('cost', 0):.4f}")

    if args.dry_run:
        print("\n*** DRY RUN — no changes written to Supabase ***")


def main():
    parser = argparse.ArgumentParser(
        description="Tag remaining untagged/incomplete questions (stubs + Stage 1 + Stage 2)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--batch-size", type=int, default=3, help="Concurrent LLM batch size (default: 3)")
    parser.add_argument("--skip-stage1", action="store_true", help="Skip steps 1-2, only run Stage 2")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
