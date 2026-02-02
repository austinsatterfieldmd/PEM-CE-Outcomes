"""
Step 1: Generate Stem-Only Embeddings

Creates embeddings from question stems only (no answers).
This allows us to find questions with similar stems regardless of answer set issues.

Input: data/raw/questions_deduplicated_collated_20260121_221852.xlsx
Output: deduplication_v2/data/stem_embeddings.parquet
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Configuration
INPUT_FILE = PROJECT_ROOT / "data/raw/questions_deduplicated_collated_20260121_221852.xlsx"
OUTPUT_FILE = Path(__file__).parent.parent / "data/stem_embeddings.parquet"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
BATCH_SIZE = 100


def get_embeddings_batch(texts: list, api_key: str, batch_size: int = 100) -> list:
    """Get embeddings for a list of texts in batches using OpenRouter API."""
    import time

    all_embeddings = []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MJH-AI-Accelerator/CE-Outcomes-Dashboard",
        "X-Title": "CE Question Deduplication V2"
    }

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch)} texts)...")

        for attempt in range(3):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers=headers,
                    json={
                        "input": batch,
                        "model": EMBEDDING_MODEL
                    },
                    timeout=60
                )

                if response.status_code == 429:
                    wait_time = 2 ** attempt * 5
                    print(f"    Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if response.status_code != 200:
                    raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

                data = response.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)
                break

            except requests.exceptions.Timeout:
                if attempt < 2:
                    print(f"    Timeout, retrying ({attempt + 1}/3)...")
                    time.sleep(2)
                else:
                    raise

    return all_embeddings


def main():
    print("=" * 60)
    print("DEDUPLICATION V2 - STEP 1: GENERATE STEM EMBEDDINGS")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment")
        sys.exit(1)

    # Load data
    print(f"\n1. Loading data from {INPUT_FILE.name}...")
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    df = pd.read_excel(INPUT_FILE)
    print(f"   Loaded {len(df)} rows")

    # Get stem column
    stem_col = "OPTIMIZEDQUESTION"
    if stem_col not in df.columns:
        print(f"ERROR: Column '{stem_col}' not found")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    # Prepare stems for embedding
    print("\n2. Preparing question stems...")
    stems = df[stem_col].fillna("").astype(str).tolist()
    non_empty = sum(1 for s in stems if s.strip())
    print(f"   {non_empty} non-empty stems out of {len(stems)}")

    # Generate embeddings
    print(f"\n3. Generating embeddings via OpenRouter API ({EMBEDDING_MODEL})...")
    embeddings = get_embeddings_batch(stems, api_key, BATCH_SIZE)
    print(f"   Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}")

    # Build output dataframe
    print("\n4. Building output dataframe...")
    output_df = pd.DataFrame({
        "qgd": df["QUESTIONGROUPDESIGNATION"],
        "stem": df[stem_col],
        "embedding": [json.dumps(emb) for emb in embeddings]
    })

    # Save as parquet
    print(f"\n5. Saving to {OUTPUT_FILE.name}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_parquet(OUTPUT_FILE, index=False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Input rows: {len(df)}")
    print(f"   Embeddings generated: {len(embeddings)}")
    print(f"   Embedding dimension: {len(embeddings[0])}")
    print(f"   Output file: {OUTPUT_FILE}")
    print(f"\nDone! Proceed to Step 2: cluster_by_stem.py")


if __name__ == "__main__":
    main()
