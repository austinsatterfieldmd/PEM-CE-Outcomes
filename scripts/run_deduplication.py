"""
Question Deduplication Script

Finds duplicate questions based on question text + all answer options.
Two questions with the same stem but different answer choices are considered unique.

Output preserves ALL original columns and adds deduplication metadata columns.

INTEGRATES with src/deduplication/ module for quality-based canonical selection:
- Encoding quality (fewer artifacts = better)
- Completeness (spelled-out terms, longer text = better)
- Grammar (proper punctuation, capitalization = better)

STORES embeddings (semantic hashes) in the Excel file for future duplicate lookups.
"""

import os
import sys
import re
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

# Import existing deduplication modules for quality scoring
from src.deduplication.cleanup import get_encoding_quality_score, ENCODING_FIXES

load_dotenv()


# =============================================================================
# EMBEDDING TEXT GENERATION
# =============================================================================

def embedding_to_json(embedding: list) -> str:
    """
    Convert embedding vector to JSON string for Excel storage.

    The embedding is a 1536-dimensional vector from text-embedding-3-small.
    Storing as JSON allows reconstruction for future duplicate detection.
    """
    return json.dumps(embedding)


def json_to_embedding(json_str: str) -> list:
    """
    Convert JSON string back to embedding vector.

    Used when loading embeddings from Excel for comparison.
    """
    return json.loads(json_str)


def build_embedding_text(row: pd.Series) -> str:
    """
    Build text for embedding from question + all answer options.

    Concatenates:
    - QUESTION (column D)
    - CANSWER1-5 (correct answers, columns G-K)
    - IANSWER1-9 (incorrect answers, columns L-T)

    Skips null/NaN values.
    """
    parts = []

    # Question text
    if pd.notna(row.get('QUESTION')):
        parts.append(f"Question: {row['QUESTION']}")

    # Correct answers
    for i in range(1, 6):
        col = f'CANSWER{i}'
        if col in row and pd.notna(row[col]):
            parts.append(f"Correct: {row[col]}")

    # Incorrect answers
    for i in range(1, 10):
        col = f'IANSWER{i}'
        if col in row and pd.notna(row[col]):
            parts.append(f"Incorrect: {row[col]}")

    return " | ".join(parts)


# =============================================================================
# QUALITY SCORING FUNCTIONS (adapted from src/deduplication/canonicalization.py)
# =============================================================================

# Source quality rankings (will be used when source/activity_type columns are available)
SOURCE_QUALITY_SCORES = {
    "journal": 15,
    "enduring": 10,
    "online": 5,
    "webinar": 5,
    "live": 0,
    "slide": -5,
}


def score_source_quality(row: pd.Series) -> float:
    """
    Score based on source activity type (when available).

    For current historical data without source columns, returns neutral score.
    Future automated process will include source/activity_type columns.
    """
    # Check for source column (future data will have this)
    source = str(row.get("source", row.get("SOURCE", ""))).lower()
    activity_type = str(row.get("activity_type", row.get("ACTIVITY_TYPE", ""))).lower()

    # Check source field
    for source_type, score in SOURCE_QUALITY_SCORES.items():
        if source_type in source:
            return float(score)

    # Check activity_type field
    for source_type, score in SOURCE_QUALITY_SCORES.items():
        if source_type in activity_type:
            return float(score)

    # Default: neutral score (current historical data)
    return 0.0


def score_encoding_quality(row: pd.Series) -> float:
    """
    Score based on encoding artifact presence (fewer = better).

    Uses the ENCODING_FIXES dictionary from src/deduplication/cleanup.py
    to detect artifacts like: smart quotes, em dashes, accented chars.
    """
    # Build combined text from question + all answers
    text_parts = []

    question = row.get('QUESTION', '')
    if pd.notna(question):
        text_parts.append(str(question))

    # Add all answers
    for i in range(1, 6):
        col = f'CANSWER{i}'
        if col in row and pd.notna(row[col]):
            text_parts.append(str(row[col]))

    for i in range(1, 10):
        col = f'IANSWER{i}'
        if col in row and pd.notna(row[col]):
            text_parts.append(str(row[col]))

    combined_text = " ".join(text_parts)
    total_chars = len(combined_text)

    if total_chars == 0:
        return 1.0

    # Count artifact characters
    artifact_chars = 0
    for artifact in ENCODING_FIXES.keys():
        artifact_chars += combined_text.count(artifact) * len(artifact)

    # Score: 1.0 - (artifact_proportion * 10)
    penalty = min(1.0, (artifact_chars / total_chars) * 10)
    return max(0.0, 1.0 - penalty)


def score_completeness(row: pd.Series) -> float:
    """
    Score based on completeness and detail level.

    Prefers:
    - Longer, more detailed question text
    - Spelled-out terms over abbreviations
    - More complete answer options
    """
    score = 0.0

    question = str(row.get('QUESTION', ''))

    # Check question length (longer generally better for context)
    if len(question) > 150:
        score += 0.3
    elif len(question) > 100:
        score += 0.2
    elif len(question) > 50:
        score += 0.1

    # Prefer spelled-out disease names over abbreviations
    spelled_out_terms = [
        "non-small cell lung cancer",
        "small cell lung cancer",
        "colorectal cancer",
        "breast cancer",
        "multiple myeloma",
        "renal cell carcinoma",
        "hepatocellular carcinoma",
        "metastatic",
        "advanced",
        "recurrent",
        "refractory"
    ]

    text_lower = question.lower()
    spelled_out_count = sum(1 for term in spelled_out_terms if term in text_lower)
    score += min(0.3, spelled_out_count * 0.1)

    # Bonus for having more complete answers
    answer_count = 0
    total_answer_length = 0

    for i in range(1, 6):
        col = f'CANSWER{i}'
        if col in row and pd.notna(row[col]):
            answer_count += 1
            total_answer_length += len(str(row[col]))

    for i in range(1, 10):
        col = f'IANSWER{i}'
        if col in row and pd.notna(row[col]):
            answer_count += 1
            total_answer_length += len(str(row[col]))

    if answer_count > 0:
        avg_answer_length = total_answer_length / answer_count
        if avg_answer_length > 50:
            score += 0.2
        elif avg_answer_length > 30:
            score += 0.1

    return min(1.0, score)


def score_grammar(row: pd.Series) -> float:
    """
    Score based on grammar and punctuation quality.
    """
    question = str(row.get('QUESTION', ''))
    if not question:
        return 0.5  # Neutral

    score = 1.0  # Start perfect, deduct for issues

    # Deduct for missing question mark (if it starts with question word)
    question_words = ["what", "which", "how", "when", "where", "who", "why", "is", "are", "does", "do"]
    first_word = question.lower().split()[0] if question.split() else ""

    if first_word in question_words and not question.rstrip().endswith("?"):
        score -= 0.3

    # Deduct for all lowercase (likely copy-paste error)
    if question.islower() and len(question) > 10:
        score -= 0.2

    # Deduct for all uppercase (shouting)
    if question.isupper() and len(question) > 10:
        score -= 0.3

    # Deduct for missing capitalization at start
    if question and not question[0].isupper():
        score -= 0.1

    # Deduct for multiple spaces
    if "  " in question:
        score -= 0.1

    # Deduct for multiple punctuation marks
    if re.search(r"[?.!]{2,}", question):
        score -= 0.1

    return max(0.0, score)


def calculate_quality_score(row: pd.Series) -> float:
    """
    Calculate overall quality score for a question row.

    Weighted combination:
    - Source quality: 40% (0 for historical data without source column)
    - Encoding quality: 25%
    - Completeness: 20%
    - Grammar: 15%
    """
    source_score = score_source_quality(row)
    encoding_score = score_encoding_quality(row) * 10  # Scale to 0-10
    completeness_score = score_completeness(row) * 10  # Scale to 0-10
    grammar_score = score_grammar(row) * 10  # Scale to 0-10

    total = (
        source_score * 0.4 +
        encoding_score * 0.25 +
        completeness_score * 0.20 +
        grammar_score * 0.15
    )

    return total


def get_embeddings_batch(texts: list, api_key: str, model: str = "openai/text-embedding-3-small", batch_size: int = 100, max_retries: int = 3) -> list:
    """
    Get embeddings for a list of texts in batches using OpenRouter API.

    OpenRouter provides access to OpenAI's embedding models via their unified API.
    Includes retry logic for rate limits and transient errors.
    """
    import time

    all_embeddings = []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MJH-AI-Accelerator/CE-Outcomes-Dashboard",
        "X-Title": "CE Question Deduplication"
    }

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch)} texts)...")

        # Retry logic for transient errors
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers=headers,
                    json={
                        "input": batch,
                        "model": model
                    },
                    timeout=60
                )

                if response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt * 5  # Exponential backoff: 5s, 10s, 20s
                    print(f"    Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if response.status_code != 200:
                    raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

                data = response.json()
                if "data" not in data:
                    raise Exception(f"Unexpected API response format: {data}")

                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)
                break  # Success, exit retry loop

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"    Timeout, retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                else:
                    raise Exception(f"Timeout after {max_retries} retries on batch {i//batch_size + 1}")

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    Error: {e}, retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                else:
                    raise

    return all_embeddings


def find_duplicates(embeddings: np.ndarray, df: pd.DataFrame, threshold: float = 0.95) -> dict:
    """
    Find duplicate clusters based on cosine similarity.
    Uses QUALITY-BASED canonical selection (best version, not first).

    Returns dict mapping each row index to its cluster ID and canonical status.
    """
    n = len(embeddings)

    print(f"  Computing similarity matrix for {n} questions...")
    similarity_matrix = cosine_similarity(embeddings)

    # Pre-compute quality scores for all questions
    print(f"  Computing quality scores for canonical selection...")
    quality_scores = df.apply(calculate_quality_score, axis=1).tolist()

    # Track which rows have been assigned to clusters
    assigned = set()
    clusters = {}  # row_idx -> (cluster_id, is_canonical, canonical_idx, similarity, quality_score)
    cluster_id = 0

    for i in range(n):
        if i in assigned:
            continue

        # Find all rows similar to this one
        similar_indices = np.where(similarity_matrix[i] >= threshold)[0]

        if len(similar_indices) == 1:
            # Unique question (only similar to itself)
            clusters[i] = (cluster_id, True, i, 1.0, quality_scores[i])
            assigned.add(i)
        else:
            # Found duplicates - select BEST quality as canonical
            cluster_members = [idx for idx in similar_indices if idx not in assigned]

            if cluster_members:
                # Find the member with highest quality score
                best_idx = max(cluster_members, key=lambda idx: quality_scores[idx])

                for idx in cluster_members:
                    is_canonical = (idx == best_idx)
                    sim_score = similarity_matrix[i][idx]
                    clusters[idx] = (cluster_id, is_canonical, best_idx, float(sim_score), quality_scores[idx])
                    assigned.add(idx)

        cluster_id += 1

        if (i + 1) % 1000 == 0:
            print(f"  Processed {i + 1}/{n} questions...")

    return clusters


def main():
    # Configuration
    INPUT_FILE = project_root / "data" / "raw" / "FulLQuestionsAnswers_NoPrevDesignations_011626_V2.xlsx"
    OUTPUT_FILE = project_root / "data" / "raw" / f"questions_deduplicated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    SIMILARITY_THRESHOLD = 0.95  # Questions with >= 95% similarity are duplicates
    EMBEDDING_MODEL = "openai/text-embedding-3-small"

    print("=" * 60)
    print("QUESTION DEDUPLICATION PIPELINE")
    print("=" * 60)

    # Check for API key (using OpenRouter for embeddings)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment variables")
        print("Please add it to your .env file")
        sys.exit(1)

    print(f"   Using OpenRouter API for embeddings ({EMBEDDING_MODEL})")
    print(f"   Embeddings will be stored in Excel output file")

    # Load data
    print(f"\n1. Loading data from {INPUT_FILE}...")
    df = pd.read_excel(INPUT_FILE)
    print(f"   Loaded {len(df)} rows with {len(df.columns)} columns")
    print(f"   Columns: {list(df.columns)}")

    # Add row_id for tracking
    df['row_id'] = range(len(df))

    # Build embedding texts
    print("\n2. Building embedding texts (question + all answers)...")
    embedding_texts = df.apply(build_embedding_text, axis=1).tolist()
    print(f"   Sample text: {embedding_texts[0][:200]}...")

    # Get embeddings
    print("\n3. Generating embeddings via OpenRouter API...")
    embeddings = get_embeddings_batch(embedding_texts, api_key)
    embeddings_array = np.array(embeddings)
    print(f"   Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}")

    # Find duplicates with quality-based canonical selection
    print(f"\n4. Finding duplicates (threshold: {SIMILARITY_THRESHOLD})...")
    print("   Using QUALITY-BASED canonical selection (best version, not first)")
    clusters = find_duplicates(embeddings_array, df, threshold=SIMILARITY_THRESHOLD)

    # Add deduplication columns
    print("\n5. Adding deduplication metadata columns...")
    df['cluster_id'] = df['row_id'].map(lambda x: clusters[x][0])
    df['is_canonical'] = df['row_id'].map(lambda x: clusters[x][1])
    df['canonical_row_id'] = df['row_id'].map(lambda x: clusters[x][2])
    df['similarity_score'] = df['row_id'].map(lambda x: clusters[x][3])
    df['quality_score'] = df['row_id'].map(lambda x: clusters[x][4])

    # Calculate statistics
    n_clusters = df['cluster_id'].nunique()
    n_canonical = df['is_canonical'].sum()
    n_duplicates = len(df) - n_canonical

    print(f"\n" + "=" * 60)
    print("DEDUPLICATION RESULTS")
    print("=" * 60)
    print(f"   Total questions:     {len(df)}")
    print(f"   Unique clusters:     {n_clusters}")
    print(f"   Canonical questions: {n_canonical}")
    print(f"   Duplicates found:    {n_duplicates}")
    print(f"   Reduction:           {n_duplicates / len(df) * 100:.1f}%")

    # Show some duplicate examples with quality scores
    duplicate_clusters = df[~df['is_canonical']]['cluster_id'].unique()[:3]
    if len(duplicate_clusters) > 0:
        print(f"\n   Sample duplicate clusters (showing quality-based canonical selection):")
        for cid in duplicate_clusters:
            cluster_df = df[df['cluster_id'] == cid].sort_values('quality_score', ascending=False)
            print(f"\n   Cluster {cid} ({len(cluster_df)} questions):")
            for _, row in cluster_df.head(3).iterrows():
                q_preview = str(row['QUESTION'])[:70] + "..." if len(str(row['QUESTION'])) > 70 else str(row['QUESTION'])
                canonical_marker = " [CANONICAL]" if row['is_canonical'] else ""
                print(f"     - Row {row['row_id']}{canonical_marker}: {q_preview}")
                print(f"       Quality: {row['quality_score']:.2f}, Similarity: {row['similarity_score']:.3f}")

    # Add embedding column (stored as JSON string)
    print(f"\n6. Adding embedding column to output...")
    df['embedding'] = [embedding_to_json(emb.tolist()) for emb in embeddings_array]
    print(f"   Embedding dimension: {len(embeddings[0])} (text-embedding-3-small)")

    # Save Excel output
    print(f"\n7. Saving Excel output to {OUTPUT_FILE}...")

    # Reorder columns: original columns first, then new metadata columns, then embedding
    original_cols = [c for c in df.columns if c not in ['row_id', 'cluster_id', 'is_canonical', 'canonical_row_id', 'similarity_score', 'quality_score', 'embedding']]
    new_cols = ['row_id', 'cluster_id', 'is_canonical', 'canonical_row_id', 'similarity_score', 'quality_score', 'embedding']
    df = df[original_cols + new_cols]

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"   Saved {len(df)} rows with {len(df.columns)} columns")

    # Calculate approximate file size
    print(f"\n" + "=" * 60)
    print("COLUMN SUMMARY")
    print("=" * 60)
    print("   ORIGINAL COLUMNS (preserved):")
    for i, col in enumerate(original_cols):
        print(f"     {chr(65+i)}. {col}")
    print("\n   NEW COLUMNS (added):")
    for i, col in enumerate(new_cols):
        print(f"     {chr(65+len(original_cols)+i)}. {col}")

    print(f"\n" + "=" * 60)
    print("OUTPUT FILE")
    print("=" * 60)
    print(f"   {OUTPUT_FILE}")
    print(f"\n   Each row includes its 1536-dimensional embedding vector (as JSON).")
    print(f"   Canonical embeddings: {n_canonical} (for future duplicate lookup)")
    print(f"\nDone! Embeddings stored in Excel file for future duplicate detection.")


if __name__ == "__main__":
    main()
