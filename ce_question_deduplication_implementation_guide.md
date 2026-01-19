# CE Question Database Deduplication System

## Implementation Guide for Claude Code in Cursor

---

## Project Overview

### Problem Statement

You have a database of CE (Continuing Education) assessment questions with duplicates caused by:

1. **Multiple activity formats**: Same questions appear in live meetings, enduring online recordings, and journal articles
2. **Text variations**: Abbreviations vs. spelled-out terms, grammar inconsistencies
3. **Question reuse**: Questions reused across different activities with minor edits
4. **Encoding artifacts**: Symbol corruption from database imports/exports

### Solution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  RAW QUESTION DATABASE                                          │
│  (duplicates, inconsistent formatting, encoding issues)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: EMBEDDING GENERATION                                   │
│  Model: text-embedding-3-small or Voyage-3-lite                 │
│  Cost: ~$0.04-0.12 for 10k questions                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: SIMILARITY CLUSTERING                                  │
│  Cosine similarity to identify duplicate clusters               │
│  Threshold tuning for your data                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: CANONICALIZATION                                       │
│  Rule-based selection of best variant                           │
│  Minimal encoding artifact cleanup                              │
│  Cost: $0 (no LLM needed)                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLEAN CANONICAL DATABASE                                       │
│  - One record per unique question                               │
│  - Links to all source occurrences                              │
│  - Ready for ongoing deduplication                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Setup

### Directory Structure

```
ce-question-deduplication/
├── src/
│   ├── embeddings.py         # Embedding generation
│   ├── clustering.py         # Similarity detection
│   ├── canonicalization.py   # Best variant selection
│   ├── cleanup.py            # Encoding artifact fixes
│   ├── pipeline.py           # Main orchestration
│   └── utils.py              # Shared utilities
├── config/
│   └── settings.py           # Configuration constants
├── data/
│   ├── raw/                  # Input question exports
│   ├── processed/            # Intermediate files
│   └── output/               # Final canonical database
├── tests/
│   └── test_*.py             # Unit tests
├── requirements.txt
├── .env                      # API keys (gitignored)
└── README.md
```

### Dependencies

Create `requirements.txt`:

```
openai>=1.0.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
python-dotenv>=1.0.0
tqdm>=4.65.0
```

### Environment Variables

Create `.env` file:

```
OPENAI_API_KEY=your_key_here
# OR for Voyage AI:
VOYAGE_API_KEY=your_key_here
```

---

## Implementation Files

### 1. Configuration (`config/settings.py`)

```python
"""
Configuration settings for the deduplication pipeline.
Adjust thresholds based on your data after initial testing.
"""

# Embedding model selection
EMBEDDING_MODEL = "text-embedding-3-small"  # Options: text-embedding-3-small, text-embedding-3-large
EMBEDDING_DIMENSIONS = 1536  # 1536 for small, 3072 for large

# Alternative: Voyage AI (uncomment to use)
# EMBEDDING_PROVIDER = "voyage"
# EMBEDDING_MODEL = "voyage-3-lite"
# EMBEDDING_DIMENSIONS = 512

# Similarity thresholds (tune after reviewing sample clusters)
SIMILARITY_THRESHOLD_AUTO_MERGE = 0.95    # Auto-dedupe without review
SIMILARITY_THRESHOLD_REVIEW = 0.88        # Flag for human review
SIMILARITY_THRESHOLD_RELATED = 0.80       # Possibly related, likely distinct

# Batch processing
EMBEDDING_BATCH_SIZE = 2000  # OpenAI allows up to 2048 per request
PROCESSING_BATCH_SIZE = 1000  # For memory management

# Source quality rankings (higher = better, used in canonicalization)
SOURCE_QUALITY_SCORES = {
    "journal": 15,
    "enduring": 10,
    "online": 5,
    "webinar": 5,
    "live": 0,
    "slide": -5,
}

# File paths
RAW_DATA_PATH = "data/raw/"
PROCESSED_DATA_PATH = "data/processed/"
OUTPUT_DATA_PATH = "data/output/"
```

---

### 2. Embedding Generation (`src/embeddings.py`)

```python
"""
Generate embeddings for question text using OpenAI or Voyage AI.
"""

import os
from typing import List, Dict
import numpy as np
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
)


def get_openai_client():
    """Initialize OpenAI client."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def prepare_question_text(question: Dict) -> str:
    """
    Combine question stem and options into a single text for embedding.
    
    Args:
        question: Dict with 'stem' and 'options' keys
        
    Returns:
        Combined text string
    """
    stem = question.get("stem", "")
    options = question.get("options", [])
    
    # Combine stem with options
    options_text = " | ".join(options) if isinstance(options, list) else str(options)
    
    return f"{stem} Options: {options_text}"


def get_embeddings_batch(
    texts: List[str],
    client: OpenAI = None,
    model: str = EMBEDDING_MODEL
) -> List[List[float]]:
    """
    Get embeddings for a batch of texts.
    
    Args:
        texts: List of text strings to embed
        client: OpenAI client instance
        model: Embedding model name
        
    Returns:
        List of embedding vectors
    """
    if client is None:
        client = get_openai_client()
    
    response = client.embeddings.create(
        input=texts,
        model=model
    )
    
    return [item.embedding for item in response.data]


def generate_all_embeddings(
    questions: List[Dict],
    show_progress: bool = True
) -> np.ndarray:
    """
    Generate embeddings for all questions with batching.
    
    Args:
        questions: List of question dictionaries
        show_progress: Whether to show progress bar
        
    Returns:
        NumPy array of embeddings (n_questions x embedding_dim)
    """
    client = get_openai_client()
    
    # Prepare texts
    texts = [prepare_question_text(q) for q in questions]
    
    # Process in batches
    all_embeddings = []
    
    iterator = range(0, len(texts), EMBEDDING_BATCH_SIZE)
    if show_progress:
        iterator = tqdm(iterator, desc="Generating embeddings")
    
    for i in iterator:
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        batch_embeddings = get_embeddings_batch(batch, client)
        all_embeddings.extend(batch_embeddings)
    
    return np.array(all_embeddings)


def embed_single_question(question: Dict, client: OpenAI = None) -> np.ndarray:
    """
    Generate embedding for a single question (for new question processing).
    
    Args:
        question: Question dictionary
        client: Optional pre-initialized client
        
    Returns:
        Embedding vector as NumPy array
    """
    if client is None:
        client = get_openai_client()
    
    text = prepare_question_text(question)
    embeddings = get_embeddings_batch([text], client)
    
    return np.array(embeddings[0])
```

---

### 3. Similarity Clustering (`src/clustering.py`)

```python
"""
Identify duplicate question clusters using cosine similarity.
"""

from typing import List, Dict, Tuple, Set
import numpy as np
from collections import defaultdict

from config.settings import (
    SIMILARITY_THRESHOLD_AUTO_MERGE,
    SIMILARITY_THRESHOLD_REVIEW,
    SIMILARITY_THRESHOLD_RELATED,
)


def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Compute pairwise cosine similarity matrix.
    
    Args:
        embeddings: NumPy array of shape (n_questions, embedding_dim)
        
    Returns:
        Similarity matrix of shape (n_questions, n_questions)
    """
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms
    
    # Compute cosine similarity via dot product of normalized vectors
    similarity_matrix = np.dot(normalized, normalized.T)
    
    return similarity_matrix


def find_duplicate_pairs(
    similarity_matrix: np.ndarray,
    question_ids: List[str],
    threshold: float = SIMILARITY_THRESHOLD_REVIEW
) -> List[Dict]:
    """
    Find all pairs of questions above the similarity threshold.
    
    Args:
        similarity_matrix: Pairwise similarity scores
        question_ids: List of question IDs corresponding to matrix indices
        threshold: Minimum similarity to consider as potential duplicate
        
    Returns:
        List of dicts with q1_id, q2_id, similarity score
    """
    pairs = []
    n = len(question_ids)
    
    for i in range(n):
        for j in range(i + 1, n):
            sim = similarity_matrix[i][j]
            if sim >= threshold:
                pairs.append({
                    "q1_id": question_ids[i],
                    "q2_id": question_ids[j],
                    "q1_index": i,
                    "q2_index": j,
                    "similarity": float(sim)
                })
    
    # Sort by similarity descending
    pairs.sort(key=lambda x: -x["similarity"])
    
    return pairs


def build_clusters(
    pairs: List[Dict],
    question_ids: List[str]
) -> List[Set[str]]:
    """
    Group duplicate pairs into clusters using union-find.
    
    Args:
        pairs: List of duplicate pair dicts
        question_ids: All question IDs
        
    Returns:
        List of sets, each containing IDs of duplicate questions
    """
    # Union-find data structure
    parent = {qid: qid for qid in question_ids}
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Union all pairs
    for pair in pairs:
        union(pair["q1_id"], pair["q2_id"])
    
    # Group by root
    clusters_dict = defaultdict(set)
    for qid in question_ids:
        root = find(qid)
        clusters_dict[root].add(qid)
    
    # Return only clusters with more than one question
    clusters = [cluster for cluster in clusters_dict.values() if len(cluster) > 1]
    
    return clusters


def categorize_clusters(
    clusters: List[Set[str]],
    similarity_matrix: np.ndarray,
    question_ids: List[str]
) -> Dict[str, List[Set[str]]]:
    """
    Categorize clusters by confidence level based on minimum similarity within cluster.
    
    Args:
        clusters: List of question ID sets
        similarity_matrix: Pairwise similarity scores
        question_ids: List mapping indices to IDs
        
    Returns:
        Dict with 'auto_merge', 'needs_review', 'low_confidence' cluster lists
    """
    id_to_idx = {qid: i for i, qid in enumerate(question_ids)}
    
    categorized = {
        "auto_merge": [],
        "needs_review": [],
        "low_confidence": []
    }
    
    for cluster in clusters:
        # Find minimum similarity within cluster
        indices = [id_to_idx[qid] for qid in cluster]
        min_sim = 1.0
        
        for i, idx1 in enumerate(indices):
            for idx2 in indices[i + 1:]:
                sim = similarity_matrix[idx1][idx2]
                min_sim = min(min_sim, sim)
        
        # Categorize
        if min_sim >= SIMILARITY_THRESHOLD_AUTO_MERGE:
            categorized["auto_merge"].append(cluster)
        elif min_sim >= SIMILARITY_THRESHOLD_REVIEW:
            categorized["needs_review"].append(cluster)
        else:
            categorized["low_confidence"].append(cluster)
    
    return categorized


def find_duplicates_for_new_question(
    new_embedding: np.ndarray,
    existing_embeddings: np.ndarray,
    existing_ids: List[str],
    threshold: float = SIMILARITY_THRESHOLD_REVIEW
) -> List[Dict]:
    """
    Find potential duplicates for a newly added question.
    
    Args:
        new_embedding: Embedding vector for new question
        existing_embeddings: Matrix of existing question embeddings
        existing_ids: IDs corresponding to existing embeddings
        threshold: Similarity threshold
        
    Returns:
        List of potential matches with IDs and similarity scores
    """
    # Normalize
    new_norm = new_embedding / np.linalg.norm(new_embedding)
    existing_norms = existing_embeddings / np.linalg.norm(existing_embeddings, axis=1, keepdims=True)
    
    # Compute similarities
    similarities = np.dot(existing_norms, new_norm)
    
    # Find matches above threshold
    matches = []
    for i, sim in enumerate(similarities):
        if sim >= threshold:
            matches.append({
                "existing_id": existing_ids[i],
                "similarity": float(sim)
            })
    
    matches.sort(key=lambda x: -x["similarity"])
    
    return matches
```

---

### 4. Encoding Cleanup (`src/cleanup.py`)

```python
"""
Fix encoding artifacts and formatting issues.
Minimal changes only - preserve original content.
"""

import re
from typing import Dict, Optional


# Encoding artifact replacements
ENCODING_FIXES = {
    # Smart quotes gone wrong
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',
    "'": "'",
    "'": "'",
    """: '"',
    """: '"',
    
    # Mathematical/scientific symbols
    "â‰¤": "≤",
    "â‰¥": "≥",
    "Â±": "±",
    "Âµ": "µ",
    "â€"": "—",
    "â€"": "–",
    "â€¢": "•",
    
    # HTML entities
    "&nbsp;": " ",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&rsquo;": "'",
    "&lsquo;": "'",
    "&rdquo;": '"',
    "&ldquo;": '"',
    "&mdash;": "—",
    "&ndash;": "–",
    "&bull;": "•",
    "&deg;": "°",
    "&plusmn;": "±",
    "&le;": "≤",
    "&ge;": "≥",
    
    # Whitespace issues
    "\u00a0": " ",   # Non-breaking space
    "\u200b": "",    # Zero-width space
    "\ufeff": "",    # BOM
    "\t": " ",       # Tabs to spaces
}

# Patterns that indicate encoding problems (for detection)
ENCODING_ARTIFACT_PATTERNS = [
    r"â€™",
    r"â€œ",
    r"â€",
    r"Ã©",
    r"Ã¨",
    r"Ã ",
    r"â‰¤",
    r"â‰¥",
    r"Â±",
    r"Âµ",
    r"\x00",
    r"ï»¿",
]


def has_encoding_artifacts(text: str) -> bool:
    """
    Check if text contains encoding artifacts.
    
    Args:
        text: Text to check
        
    Returns:
        True if artifacts detected
    """
    if not text:
        return False
    
    for pattern in ENCODING_ARTIFACT_PATTERNS:
        if re.search(pattern, text):
            return True
    
    return False


def clean_encoding_artifacts(text: str) -> str:
    """
    Fix encoding artifacts in text.
    Does NOT change wording, grammar, or content.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return text
    
    cleaned = text
    
    # Apply all replacements
    for bad, good in ENCODING_FIXES.items():
        cleaned = cleaned.replace(bad, good)
    
    # Remove HTML tags that might have leaked in
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    
    # Normalize multiple spaces to single space
    cleaned = re.sub(r" {2,}", " ", cleaned)
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def clean_question(question: Dict) -> Dict:
    """
    Apply encoding cleanup to a question's stem and options.
    
    Args:
        question: Dict with 'stem' and 'options' keys
        
    Returns:
        Cleaned question dict with 'was_cleaned' flag
    """
    original_stem = question.get("stem", "")
    original_options = question.get("options", [])
    
    cleaned_stem = clean_encoding_artifacts(original_stem)
    cleaned_options = [clean_encoding_artifacts(opt) for opt in original_options]
    
    was_cleaned = (
        cleaned_stem != original_stem or
        cleaned_options != original_options
    )
    
    result = question.copy()
    result["stem"] = cleaned_stem
    result["options"] = cleaned_options
    result["was_cleaned"] = was_cleaned
    
    if was_cleaned:
        result["original_stem"] = original_stem
        result["original_options"] = original_options
    
    return result
```

---

### 5. Canonicalization (`src/canonicalization.py`)

```python
"""
Select the best variant from a cluster of duplicate questions.
Rule-based scoring - no LLM required.
"""

import re
from typing import List, Dict, Optional

from config.settings import SOURCE_QUALITY_SCORES
from src.cleanup import clean_question, has_encoding_artifacts


def score_question_quality(stem: str, options: List[str]) -> int:
    """
    Score a question variant based on quality heuristics.
    Higher score = better quality.
    
    Args:
        stem: Question text
        options: List of answer options
        
    Returns:
        Quality score (integer)
    """
    score = 0
    full_text = stem + " " + " ".join(options)
    
    # === ABBREVIATION HANDLING ===
    
    # Count standalone abbreviations (2-6 capital letters)
    abbreviations = re.findall(r"\b[A-Z]{2,6}\b", full_text)
    score -= len(abbreviations) * 3
    
    # Bonus for defined abbreviations: "non-small cell lung cancer (NSCLC)"
    defined_abbrevs = re.findall(r"\([A-Z]{2,6}\)", full_text)
    score += len(defined_abbrevs) * 5
    
    # === ENCODING/FORMATTING ISSUES ===
    
    if has_encoding_artifacts(full_text):
        score -= 25
    
    # === GRAMMAR & STRUCTURE ===
    
    # Proper question ending
    stem_stripped = stem.strip()
    if stem_stripped.endswith("?"):
        score += 5
    elif stem_stripped.endswith(":"):
        score += 3
    elif stem_stripped.endswith("."):
        score += 1
    
    # Starts with capital letter
    if stem and stem[0].isupper():
        score += 2
    
    # Penalize ALL CAPS
    if stem.isupper():
        score -= 15
    
    # === COMPLETENESS ===
    
    word_count = len(stem.split())
    if 15 <= word_count <= 100:
        score += 5
    elif word_count < 8:
        score -= 10  # Likely truncated
    elif word_count > 150:
        score -= 5   # Unusually long
    
    # === ANSWER OPTIONS ===
    
    for opt in options:
        opt_stripped = opt.strip() if opt else ""
        
        # Empty or very short options
        if len(opt_stripped) < 2:
            score -= 15
        
        # Consistent capitalization
        if opt_stripped and opt_stripped[0].isupper():
            score += 1
        
        # Whitespace issues
        if opt and opt != opt_stripped:
            score -= 2
        
        # Encoding issues in options
        if has_encoding_artifacts(opt_stripped):
            score -= 10
    
    return score


def get_source_score(source: str) -> int:
    """
    Get quality bonus based on source type.
    
    Args:
        source: Source identifier string
        
    Returns:
        Score bonus (integer)
    """
    source_lower = source.lower() if source else ""
    
    for keyword, bonus in SOURCE_QUALITY_SCORES.items():
        if keyword in source_lower:
            return bonus
    
    return 0


def select_best_variant(variants: List[Dict]) -> Dict:
    """
    Select the highest-quality variant from a list of duplicates.
    
    Args:
        variants: List of question dicts with 'id', 'stem', 'options', 'source'
        
    Returns:
        Dict with selected variant and metadata
    """
    if not variants:
        raise ValueError("No variants provided")
    
    if len(variants) == 1:
        return {
            "selected": variants[0],
            "score": score_question_quality(variants[0]["stem"], variants[0]["options"]),
            "margin": None,
            "runner_up": None,
            "all_scores": None
        }
    
    # Score all variants
    scored = []
    for v in variants:
        base_score = score_question_quality(v["stem"], v["options"])
        source_bonus = get_source_score(v.get("source", ""))
        total_score = base_score + source_bonus
        
        scored.append({
            "variant": v,
            "base_score": base_score,
            "source_bonus": source_bonus,
            "total_score": total_score
        })
    
    # Sort by total score descending
    scored.sort(key=lambda x: -x["total_score"])
    
    winner = scored[0]
    runner_up = scored[1] if len(scored) > 1 else None
    
    margin = None
    if runner_up:
        margin = winner["total_score"] - runner_up["total_score"]
    
    return {
        "selected": winner["variant"],
        "score": winner["total_score"],
        "base_score": winner["base_score"],
        "source_bonus": winner["source_bonus"],
        "margin": margin,
        "runner_up": runner_up["variant"] if runner_up else None,
        "runner_up_score": runner_up["total_score"] if runner_up else None,
        "all_scores": [(s["variant"]["id"], s["total_score"]) for s in scored]
    }


def canonicalize_cluster(
    variants: List[Dict],
    apply_cleanup: bool = True
) -> Dict:
    """
    Full canonicalization: select best variant and optionally clean encoding issues.
    
    Args:
        variants: List of duplicate question variants
        apply_cleanup: Whether to fix encoding artifacts
        
    Returns:
        Canonical question with full metadata
    """
    # Select best
    selection = select_best_variant(variants)
    
    # Apply cleanup if requested
    canonical = selection["selected"].copy()
    if apply_cleanup:
        canonical = clean_question(canonical)
    
    # Flag for review if margin is thin
    needs_review = (
        selection["margin"] is not None and
        selection["margin"] < 5
    )
    
    return {
        "canonical": canonical,
        "selection_score": selection["score"],
        "base_score": selection["base_score"],
        "source_bonus": selection["source_bonus"],
        "margin_over_runner_up": selection["margin"],
        "needs_review": needs_review,
        "source_variant_ids": [v["id"] for v in variants],
        "source_variant_count": len(variants),
        "all_scores": selection["all_scores"],
        "selection_method": "rule_based"
    }
```

---

### 6. Main Pipeline (`src/pipeline.py`)

```python
"""
Main orchestration pipeline for question deduplication.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from tqdm import tqdm

from config.settings import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    OUTPUT_DATA_PATH,
    SIMILARITY_THRESHOLD_AUTO_MERGE,
)
from src.embeddings import generate_all_embeddings, embed_single_question
from src.clustering import (
    compute_similarity_matrix,
    find_duplicate_pairs,
    build_clusters,
    categorize_clusters,
    find_duplicates_for_new_question,
)
from src.canonicalization import canonicalize_cluster


def load_questions(filepath: str) -> List[Dict]:
    """
    Load questions from JSON or CSV file.
    
    Expected format:
    - JSON: List of dicts with 'id', 'stem', 'options', 'correct_answer', 'source'
    - CSV: Columns for id, stem, option_a, option_b, option_c, option_d, correct, source
    """
    if filepath.endswith(".json"):
        with open(filepath, "r") as f:
            return json.load(f)
    
    elif filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
        questions = []
        for _, row in df.iterrows():
            questions.append({
                "id": str(row.get("id", row.name)),
                "stem": row.get("stem", row.get("question", "")),
                "options": [
                    row.get("option_a", row.get("a", "")),
                    row.get("option_b", row.get("b", "")),
                    row.get("option_c", row.get("c", "")),
                    row.get("option_d", row.get("d", "")),
                ],
                "correct_answer": row.get("correct", row.get("correct_answer", "")),
                "source": row.get("source", row.get("activity", "")),
                "metadata_tags": row.get("tags", ""),
            })
        return questions
    
    else:
        raise ValueError(f"Unsupported file format: {filepath}")


def save_results(data: Dict, filename: str, output_dir: str = OUTPUT_DATA_PATH):
    """Save results to JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved: {filepath}")


def run_full_pipeline(
    input_file: str,
    save_intermediates: bool = True
) -> Dict:
    """
    Run the complete deduplication pipeline.
    
    Args:
        input_file: Path to input question file (JSON or CSV)
        save_intermediates: Whether to save intermediate results
        
    Returns:
        Dict with canonical questions and statistics
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 60)
    print("CE Question Deduplication Pipeline")
    print("=" * 60)
    
    # Step 1: Load questions
    print("\n[1/5] Loading questions...")
    questions = load_questions(input_file)
    question_ids = [q["id"] for q in questions]
    print(f"      Loaded {len(questions)} questions")
    
    # Step 2: Generate embeddings
    print("\n[2/5] Generating embeddings...")
    embeddings = generate_all_embeddings(questions, show_progress=True)
    
    if save_intermediates:
        np.save(
            os.path.join(PROCESSED_DATA_PATH, f"embeddings_{timestamp}.npy"),
            embeddings
        )
    
    # Step 3: Compute similarity and find duplicates
    print("\n[3/5] Computing similarity matrix...")
    similarity_matrix = compute_similarity_matrix(embeddings)
    
    print("      Finding duplicate pairs...")
    pairs = find_duplicate_pairs(similarity_matrix, question_ids)
    print(f"      Found {len(pairs)} potential duplicate pairs")
    
    # Step 4: Build and categorize clusters
    print("\n[4/5] Building duplicate clusters...")
    clusters = build_clusters(pairs, question_ids)
    print(f"      Found {len(clusters)} duplicate clusters")
    
    categorized = categorize_clusters(clusters, similarity_matrix, question_ids)
    print(f"      - Auto-merge (high confidence): {len(categorized['auto_merge'])}")
    print(f"      - Needs review: {len(categorized['needs_review'])}")
    print(f"      - Low confidence: {len(categorized['low_confidence'])}")
    
    # Step 5: Canonicalize
    print("\n[5/5] Selecting canonical versions...")
    
    # Map question IDs to full question data
    id_to_question = {q["id"]: q for q in questions}
    
    canonical_questions = []
    review_queue = []
    
    # Process auto-merge clusters
    for cluster in tqdm(categorized["auto_merge"], desc="Auto-merge"):
        variants = [id_to_question[qid] for qid in cluster]
        result = canonicalize_cluster(variants)
        canonical_questions.append(result)
    
    # Process review-needed clusters
    for cluster in tqdm(categorized["needs_review"], desc="Review needed"):
        variants = [id_to_question[qid] for qid in cluster]
        result = canonicalize_cluster(variants)
        result["review_reason"] = "similarity_below_auto_threshold"
        review_queue.append(result)
    
    # Process low-confidence clusters
    for cluster in categorized["low_confidence"]:
        variants = [id_to_question[qid] for qid in cluster]
        result = canonicalize_cluster(variants)
        result["review_reason"] = "low_similarity_cluster"
        review_queue.append(result)
    
    # Find unique questions (not in any cluster)
    clustered_ids = set()
    for cluster in clusters:
        clustered_ids.update(cluster)
    
    unique_questions = []
    for q in questions:
        if q["id"] not in clustered_ids:
            unique_questions.append({
                "canonical": q,
                "source_variant_ids": [q["id"]],
                "source_variant_count": 1,
                "selection_method": "unique"
            })
    
    print(f"\n      Unique questions (no duplicates): {len(unique_questions)}")
    
    # Compile results
    results = {
        "run_timestamp": timestamp,
        "input_file": input_file,
        "statistics": {
            "total_input_questions": len(questions),
            "duplicate_clusters": len(clusters),
            "canonical_from_auto_merge": len(canonical_questions),
            "pending_review": len(review_queue),
            "unique_questions": len(unique_questions),
            "total_canonical": len(canonical_questions) + len(unique_questions),
            "reduction_percentage": round(
                (1 - (len(canonical_questions) + len(unique_questions)) / len(questions)) * 100, 1
            ) if questions else 0
        },
        "canonical_questions": canonical_questions + unique_questions,
        "review_queue": review_queue,
    }
    
    # Save results
    save_results(results, f"deduplication_results_{timestamp}.json")
    
    # Save review queue separately for easy access
    if review_queue:
        save_results(
            {"review_queue": review_queue},
            f"review_queue_{timestamp}.json"
        )
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Input questions:     {results['statistics']['total_input_questions']}")
    print(f"Duplicate clusters:  {results['statistics']['duplicate_clusters']}")
    print(f"Canonical questions: {results['statistics']['total_canonical']}")
    print(f"Pending review:      {results['statistics']['pending_review']}")
    print(f"Reduction:           {results['statistics']['reduction_percentage']}%")
    print("=" * 60)
    
    return results


def process_new_question(
    new_question: Dict,
    canonical_embeddings: np.ndarray,
    canonical_ids: List[str],
    canonical_questions: List[Dict]
) -> Dict:
    """
    Process a single new question against existing canonical database.
    For ongoing deduplication as new questions are added.
    
    Args:
        new_question: New question dict
        canonical_embeddings: Embeddings of canonical questions
        canonical_ids: IDs of canonical questions
        canonical_questions: Full canonical question data
        
    Returns:
        Dict with status and any matches found
    """
    # Generate embedding for new question
    new_embedding = embed_single_question(new_question)
    
    # Find potential duplicates
    matches = find_duplicates_for_new_question(
        new_embedding,
        canonical_embeddings,
        canonical_ids
    )
    
    if not matches:
        return {
            "status": "unique",
            "question": new_question,
            "matches": []
        }
    
    # Check confidence level of top match
    top_match = matches[0]
    
    if top_match["similarity"] >= SIMILARITY_THRESHOLD_AUTO_MERGE:
        return {
            "status": "duplicate",
            "question": new_question,
            "canonical_match_id": top_match["existing_id"],
            "similarity": top_match["similarity"],
            "all_matches": matches
        }
    else:
        return {
            "status": "review_needed",
            "question": new_question,
            "potential_matches": matches
        }


# Entry point for command-line usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline <input_file>")
        print("Example: python -m src.pipeline data/raw/questions.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    run_full_pipeline(input_file)
```

---

### 7. Utility Functions (`src/utils.py`)

```python
"""
Shared utility functions.
"""

import json
import os
from typing import List, Dict, Any


def ensure_directories():
    """Create required directories if they don't exist."""
    dirs = [
        "data/raw",
        "data/processed", 
        "data/output",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def export_review_report(review_queue: List[Dict], output_path: str):
    """
    Export review queue to a human-readable format for manual review.
    
    Args:
        review_queue: List of clusters needing review
        output_path: Path for output file
    """
    lines = ["# Question Deduplication Review Report\n"]
    lines.append("Review each cluster and confirm whether variants are duplicates.\n")
    lines.append("=" * 70 + "\n")
    
    for i, cluster in enumerate(review_queue, 1):
        lines.append(f"\n## Cluster {i}\n")
        lines.append(f"Reason for review: {cluster.get('review_reason', 'N/A')}\n")
        lines.append(f"Margin over runner-up: {cluster.get('margin_over_runner_up', 'N/A')}\n")
        
        lines.append("\n### Selected (Canonical) Version:\n")
        canonical = cluster.get("canonical", {})
        lines.append(f"ID: {canonical.get('id')}\n")
        lines.append(f"Source: {canonical.get('source')}\n")
        lines.append(f"Stem: {canonical.get('stem')}\n")
        lines.append("Options:\n")
        for j, opt in enumerate(canonical.get("options", []), 1):
            lines.append(f"  {j}. {opt}\n")
        
        lines.append("\n### All Variant IDs and Scores:\n")
        for qid, score in cluster.get("all_scores", []):
            marker = " <-- SELECTED" if qid == canonical.get("id") else ""
            lines.append(f"  - {qid}: {score}{marker}\n")
        
        lines.append("\n### Decision:\n")
        lines.append("[ ] Confirm as duplicates (use selected canonical)\n")
        lines.append("[ ] Not duplicates (keep separate)\n")
        lines.append("[ ] Different canonical preferred: ____________\n")
        lines.append("\n" + "-" * 70 + "\n")
    
    with open(output_path, "w") as f:
        f.writelines(lines)
    
    print(f"Review report saved to: {output_path}")


def load_canonical_database(filepath: str) -> tuple:
    """
    Load existing canonical database for ongoing deduplication.
    
    Returns:
        Tuple of (questions list, embeddings array, ids list)
    """
    import numpy as np
    
    with open(filepath, "r") as f:
        data = json.load(f)
    
    questions = data.get("canonical_questions", [])
    
    # Load corresponding embeddings if available
    embeddings_path = filepath.replace(".json", "_embeddings.npy")
    if os.path.exists(embeddings_path):
        embeddings = np.load(embeddings_path)
    else:
        embeddings = None
    
    ids = [q["canonical"]["id"] for q in questions]
    
    return questions, embeddings, ids
```

---

## Usage Instructions

### Initial Setup

```bash
# 1. Create project directory
mkdir ce-question-deduplication
cd ce-question-deduplication

# 2. Create directory structure
mkdir -p src config data/raw data/processed data/output tests

# 3. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file with your API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

### Prepare Your Data

Export your questions to JSON format:

```json
[
  {
    "id": "Q-0001",
    "stem": "What is the preferred first-line treatment for...",
    "options": [
      "Option A text",
      "Option B text", 
      "Option C text",
      "Option D text"
    ],
    "correct_answer": "B",
    "source": "Live Meeting 2023",
    "disease_state": "NSCLC",
    "topic": "Treatment Selection"
  }
]
```

Save to `data/raw/questions.json`

### Run the Pipeline

```bash
python -m src.pipeline data/raw/questions.json
```

### Review Output

Results are saved in `data/output/`:

- `deduplication_results_TIMESTAMP.json` - Full results
- `review_queue_TIMESTAMP.json` - Questions needing manual review

---

## Threshold Tuning Guide

After your first run, review sample clusters to calibrate thresholds:

| If you see... | Adjust... |
|---------------|-----------|
| True duplicates in "needs review" | Lower `SIMILARITY_THRESHOLD_AUTO_MERGE` |
| False duplicates being auto-merged | Raise `SIMILARITY_THRESHOLD_AUTO_MERGE` |
| Related but distinct questions clustered | Raise `SIMILARITY_THRESHOLD_REVIEW` |
| Missing obvious duplicates | Lower `SIMILARITY_THRESHOLD_REVIEW` |

### Recommended Starting Points

```python
# Conservative (fewer false positives, more manual review)
SIMILARITY_THRESHOLD_AUTO_MERGE = 0.96
SIMILARITY_THRESHOLD_REVIEW = 0.90

# Balanced (good for most cases)
SIMILARITY_THRESHOLD_AUTO_MERGE = 0.95
SIMILARITY_THRESHOLD_REVIEW = 0.88

# Aggressive (more automation, risk of false positives)
SIMILARITY_THRESHOLD_AUTO_MERGE = 0.93
SIMILARITY_THRESHOLD_REVIEW = 0.85
```

---

## Cost Summary

| Component | Cost for 10,000 Questions |
|-----------|---------------------------|
| Embeddings (text-embedding-3-small) | ~$0.04 |
| Embeddings (Voyage-3-lite) | ~$0.04 |
| Canonicalization | $0 (rule-based) |
| **Total** | **~$0.04** |

---

## Ongoing Deduplication

For new questions added to your database:

```python
from src.pipeline import process_new_question
from src.utils import load_canonical_database

# Load existing canonical database
questions, embeddings, ids = load_canonical_database(
    "data/output/deduplication_results_TIMESTAMP.json"
)

# Process new question
new_question = {
    "id": "Q-NEW-001",
    "stem": "What is the recommended treatment...",
    "options": ["A", "B", "C", "D"],
    "source": "New Activity 2025"
}

result = process_new_question(new_question, embeddings, ids, questions)

if result["status"] == "unique":
    # Add to canonical database
    pass
elif result["status"] == "duplicate":
    # Link to existing canonical question
    print(f"Duplicate of: {result['canonical_match_id']}")
else:
    # Add to review queue
    pass
```

---

## Next Steps

1. **Export your question data** to JSON format
2. **Run the pipeline** on a sample (100-500 questions) first
3. **Review the clusters** and adjust thresholds
4. **Run on full database** once thresholds are calibrated
5. **Set up ongoing process** for new questions

---

## Questions?

This implementation guide covers the core functionality. Additional features you might want to add:

- Database integration (PostgreSQL, MongoDB)
- Web interface for review queue
- Automated scheduling for batch processing
- Detailed logging and monitoring
- Export to your dashboard format
