"""
Step 4: LLM Triage for Divergent Pairs

For pairs with low answer similarity (<70%), asks an LLM to determine:
- Are these the same question with data errors?
- Or different questions sharing a stem?

Input:
  - deduplication_v2/data/answer_comparisons.json
  - data/raw/questions_deduplicated_collated_20260121_221852.xlsx
Output: deduplication_v2/data/llm_triage_results.json
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
PROMPTS_DIR = SCRIPT_DIR.parent / "prompts"
COMPARISONS_FILE = DATA_DIR / "answer_comparisons.json"
SOURCE_FILE = PROJECT_ROOT / "data/raw/questions_deduplicated_collated_20260121_221852.xlsx"
OUTPUT_FILE = DATA_DIR / "llm_triage_results.json"
PROMPT_FILE = PROMPTS_DIR / "answer_set_triage_prompt.txt"

# LLM Configuration
LLM_MODEL = "openai/gpt-5.2"  # GPT 5.2 for triage


def load_prompt_template():
    """Load the triage prompt template."""
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_prompt(template: str, stem: str, qgd_1: int, qgd_2: int,
                 correct_1: str, incorrect_1: list,
                 correct_2: str, incorrect_2: list) -> str:
    """Build the full prompt for a pair."""
    incorrect_str_1 = "\n".join(f"- {ans}" for ans in incorrect_1 if ans)
    incorrect_str_2 = "\n".join(f"- {ans}" for ans in incorrect_2 if ans)

    return template.format(
        stem=stem,
        qgd_1=qgd_1,
        qgd_2=qgd_2,
        correct_answer_1=correct_1,
        incorrect_answers_1=incorrect_str_1 or "None",
        correct_answer_2=correct_2,
        incorrect_answers_2=incorrect_str_2 or "None"
    )


def call_llm(prompt: str, api_key: str) -> dict:
    """Call the LLM and parse the response."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0
    }

    for attempt in range(3):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 429:
                time.sleep(2 ** attempt * 2)
                continue

            if response.status_code != 200:
                return {"error": f"API error: {response.status_code}"}

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON from response
            try:
                # Extract JSON from markdown code block if present
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0]
                else:
                    json_str = content

                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                return {
                    "verdict": "PARSE_ERROR",
                    "raw_response": content[:500]
                }

        except requests.exceptions.Timeout:
            if attempt < 2:
                time.sleep(2)
            else:
                return {"error": "Timeout after 3 retries"}

    return {"error": "Failed after 3 attempts"}


def get_question_data(row: pd.Series) -> tuple:
    """Extract correct and incorrect answers from a row."""
    correct = str(row.get("OPTIMIZEDCORRECTANSWER", "")) if pd.notna(row.get("OPTIMIZEDCORRECTANSWER")) else ""

    incorrect = []
    for i in range(1, 10):
        col = f"IANSWER{i}"
        if col in row and pd.notna(row[col]):
            incorrect.append(str(row[col]))

    return correct, incorrect


def main():
    print("=" * 60)
    print("DEDUPLICATION V2 - STEP 4: LLM TRIAGE DIVERGENT PAIRS")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found")
        sys.exit(1)

    # Load comparisons
    print(f"\n1. Loading comparisons from {COMPARISONS_FILE.name}...")
    if not COMPARISONS_FILE.exists():
        print("ERROR: Comparisons file not found. Run compare_answer_sets.py first")
        sys.exit(1)

    with open(COMPARISONS_FILE, "r", encoding="utf-8") as f:
        comparisons = json.load(f)

    divergent_pairs = comparisons["divergent_pairs"]
    print(f"   Found {len(divergent_pairs)} divergent pairs to triage")

    if not divergent_pairs:
        print("   No divergent pairs to triage!")
        return

    # Load source data
    print(f"\n2. Loading source data from {SOURCE_FILE.name}...")
    source_df = pd.read_excel(SOURCE_FILE)

    qgd_to_row = {
        int(row["QUESTIONGROUPDESIGNATION"]): row
        for _, row in source_df.iterrows()
        if pd.notna(row["QUESTIONGROUPDESIGNATION"])
    }
    print(f"   Mapped {len(qgd_to_row)} QGDs")

    # Load prompt template
    print(f"\n3. Loading prompt template...")
    prompt_template = load_prompt_template()

    # Process divergent pairs
    print(f"\n4. Processing {len(divergent_pairs)} divergent pairs...")
    results = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "llm_model": LLM_MODEL,
            "total_pairs_triaged": 0
        },
        "triage_results": [],
        "summary": {
            "SAME_QUESTION_DATA_ERROR": 0,
            "SAME_QUESTION_MINOR_VARIATION": 0,
            "DIFFERENT_QUESTIONS": 0,
            "PARSE_ERROR": 0,
            "API_ERROR": 0
        }
    }

    for i, pair in enumerate(divergent_pairs):
        qgd_1 = pair["qgd_1"]
        qgd_2 = pair["qgd_2"]

        print(f"   [{i+1}/{len(divergent_pairs)}] QGD {qgd_1} vs {qgd_2}...", end=" ")

        # Get question data
        if qgd_1 not in qgd_to_row or qgd_2 not in qgd_to_row:
            print("SKIP (QGD not found)")
            continue

        row_1 = qgd_to_row[qgd_1]
        row_2 = qgd_to_row[qgd_2]

        stem = row_1.get("OPTIMIZEDQUESTION", "")
        correct_1, incorrect_1 = get_question_data(row_1)
        correct_2, incorrect_2 = get_question_data(row_2)

        # Build and send prompt
        prompt = build_prompt(
            prompt_template, stem, qgd_1, qgd_2,
            correct_1, incorrect_1, correct_2, incorrect_2
        )

        llm_response = call_llm(prompt, api_key)

        verdict = llm_response.get("verdict", "API_ERROR")
        print(verdict)

        # Track results
        result = {
            "cluster_id": pair["cluster_id"],
            "qgd_1": qgd_1,
            "qgd_2": qgd_2,
            "answer_similarity": pair["answer_similarity"],
            "stem_preview": pair["stem_preview"],
            "llm_response": llm_response
        }
        results["triage_results"].append(result)
        results["metadata"]["total_pairs_triaged"] += 1

        # Update summary
        if verdict in results["summary"]:
            results["summary"][verdict] += 1
        elif "error" in llm_response:
            results["summary"]["API_ERROR"] += 1
        else:
            results["summary"]["PARSE_ERROR"] += 1

        # Rate limiting
        time.sleep(0.5)

    # Save results
    print(f"\n5. Saving to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Pairs triaged: {results['metadata']['total_pairs_triaged']}")
    for verdict, count in results["summary"].items():
        if count > 0:
            print(f"   {verdict}: {count}")

    print(f"\nDone! Proceed to Step 5: generate_recommendations.py")


if __name__ == "__main__":
    main()
