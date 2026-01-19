"""
Select canonical (best) question variant from duplicate clusters.

Uses rule-based scoring across multiple quality dimensions:
- Source quality (journal > enduring > online > live)
- Encoding quality (fewer artifacts)
- Completeness (spelled-out terms preferred)
- Grammar/punctuation quality
"""

import logging
import re
from typing import Dict, List, Set
from collections import Counter

from .config.settings import SOURCE_QUALITY_SCORES
from .cleanup import get_encoding_quality_score

logger = logging.getLogger(__name__)


def score_source_quality(question: Dict) -> float:
    """
    Score based on source activity type.

    Args:
        question: Question dict with "source" or "activity_type" field

    Returns:
        Quality score (higher = better)

    Example:
        >>> q = {"source": "journal"}
        >>> score_source_quality(q)
        15.0
    """
    source = question.get("source", "").lower()
    activity_type = question.get("activity_type", "").lower()

    # Check source field first
    for source_type, score in SOURCE_QUALITY_SCORES.items():
        if source_type in source:
            return float(score)

    # Check activity_type field
    for source_type, score in SOURCE_QUALITY_SCORES.items():
        if source_type in activity_type:
            return float(score)

    # Default: neutral score
    return 0.0


def score_completeness(question: Dict) -> float:
    """
    Score based on completeness and detail level.

    Prefers:
    - Spelled-out terms over abbreviations
    - Longer, more detailed text
    - Presence of rationale/explanation

    Args:
        question: Question dict

    Returns:
        Completeness score (0.0-1.0)

    Example:
        >>> q1 = {"stem": "Non-small cell lung cancer treatment?"}
        >>> q2 = {"stem": "NSCLC treatment?"}
        >>> score_completeness(q1) > score_completeness(q2)
        True
    """
    score = 0.0

    # Check stem length (longer generally better for context)
    stem = question.get("stem", "")
    if len(stem) > 150:
        score += 0.3
    elif len(stem) > 100:
        score += 0.2
    elif len(stem) > 50:
        score += 0.1

    # Prefer spelled-out disease names
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

    text_lower = stem.lower()
    spelled_out_count = sum(1 for term in spelled_out_terms if term in text_lower)
    score += min(0.3, spelled_out_count * 0.1)

    # Bonus for having rationale/explanation
    if question.get("rationale") and len(question["rationale"]) > 50:
        score += 0.2

    # Bonus for having detailed options
    options = question.get("options", [])
    if isinstance(options, list):
        avg_option_length = sum(len(str(opt)) for opt in options) / max(len(options), 1)
        if avg_option_length > 50:
            score += 0.2
        elif avg_option_length > 30:
            score += 0.1

    return min(1.0, score)


def score_grammar(question: Dict) -> float:
    """
    Score based on grammar and punctuation quality.

    Args:
        question: Question dict

    Returns:
        Grammar score (0.0-1.0)

    Example:
        >>> q1 = {"stem": "What is the best treatment?"}
        >>> q2 = {"stem": "what is best treatment"}
        >>> score_grammar(q1) > score_grammar(q2)
        True
    """
    stem = question.get("stem", "")
    if not stem:
        return 0.5  # Neutral

    score = 1.0  # Start perfect, deduct for issues

    # Deduct for missing question mark (if it's a question)
    question_words = ["what", "which", "how", "when", "where", "who", "why", "is", "are", "does", "do"]
    first_word = stem.lower().split()[0] if stem.split() else ""

    if first_word in question_words and not stem.rstrip().endswith("?"):
        score -= 0.3

    # Deduct for all lowercase (likely copy-paste error)
    if stem.islower() and len(stem) > 10:
        score -= 0.2

    # Deduct for all uppercase (shouting)
    if stem.isupper() and len(stem) > 10:
        score -= 0.3

    # Deduct for missing capitalization at start
    if stem and not stem[0].isupper():
        score -= 0.1

    # Deduct for multiple spaces
    if "  " in stem:
        score -= 0.1

    # Deduct for multiple punctuation marks
    if re.search(r"[?.!]{2,}", stem):
        score -= 0.1

    return max(0.0, score)


def score_question(question: Dict) -> Dict[str, float]:
    """
    Compute all quality scores for a question.

    Args:
        question: Question dict

    Returns:
        Dict with individual scores and total

    Example:
        >>> q = {"source": "journal", "stem": "What is the best treatment?"}
        >>> scores = score_question(q)
        >>> scores["total"] > 0
        True
    """
    scores = {
        "source_quality": score_source_quality(question),
        "encoding_quality": get_encoding_quality_score(question) * 10,  # Scale to 0-10
        "completeness": score_completeness(question) * 10,  # Scale to 0-10
        "grammar": score_grammar(question) * 10  # Scale to 0-10
    }

    # Weighted total (source quality most important)
    scores["total"] = (
        scores["source_quality"] * 0.4 +
        scores["encoding_quality"] * 0.25 +
        scores["completeness"] * 0.20 +
        scores["grammar"] * 0.15
    )

    return scores


def select_canonical(cluster: Set[str], questions: List[Dict]) -> Dict:
    """
    Select the best question variant from a duplicate cluster.

    Args:
        cluster: Set of question IDs in the cluster
        questions: List of all question dicts

    Returns:
        Canonical question dict with scores

    Example:
        >>> cluster = {"Q1", "Q2"}
        >>> questions = [
        ...     {"id": "Q1", "source": "journal", "stem": "What is treatment?"},
        ...     {"id": "Q2", "source": "live", "stem": "what is treatment"}
        ... ]
        >>> canonical = select_canonical(cluster, questions)
        >>> canonical["id"]
        "Q1"
    """
    # Filter to cluster questions
    cluster_questions = [q for q in questions if q.get("id") in cluster]

    if not cluster_questions:
        logger.warning(f"Empty cluster: {cluster}")
        return None

    # Score each question
    scored = []
    for question in cluster_questions:
        scores = score_question(question)
        scored.append({
            "question": question,
            "scores": scores,
            "total_score": scores["total"]
        })

    # Sort by total score descending
    scored.sort(key=lambda x: -x["total_score"])

    # Return best question
    best = scored[0]

    logger.debug(
        f"Selected canonical from cluster of {len(cluster_questions)}: "
        f"ID={best['question'].get('id')}, "
        f"score={best['total_score']:.2f}"
    )

    return {
        "question": best["question"],
        "canonical_id": best["question"].get("id"),
        "scores": best["scores"],
        "cluster_size": len(cluster_questions),
        "alternatives": [s["question"].get("id") for s in scored[1:]]
    }


def canonicalize_all_clusters(
    clusters: List[Set[str]],
    questions: List[Dict]
) -> Dict:
    """
    Select canonical question for each cluster.

    Args:
        clusters: List of question ID sets
        questions: List of all question dicts

    Returns:
        Dict mapping cluster_id -> canonical question info

    Example:
        >>> clusters = [{"Q1", "Q2"}, {"Q3", "Q4", "Q5"}]
        >>> questions = [...]
        >>> canonicals = canonicalize_all_clusters(clusters, questions)
        >>> len(canonicals)
        2
    """
    canonicals = {}

    for i, cluster in enumerate(clusters):
        cluster_id = f"cluster_{i}"
        canonical = select_canonical(cluster, questions)

        if canonical:
            canonicals[cluster_id] = canonical

    logger.info(f"Canonicalized {len(canonicals)} clusters")

    return canonicals


def create_canonical_mapping(
    clusters: List[Set[str]],
    questions: List[Dict]
) -> Dict[str, str]:
    """
    Create mapping from duplicate ID -> canonical ID.

    Args:
        clusters: List of question ID sets
        questions: List of all question dicts

    Returns:
        Dict mapping question_id -> canonical_question_id

    Example:
        >>> clusters = [{"Q1", "Q2", "Q3"}]
        >>> questions = [
        ...     {"id": "Q1", "source": "journal", "stem": "Best treatment?"},
        ...     {"id": "Q2", "source": "live", "stem": "best treatment?"},
        ...     {"id": "Q3", "source": "online", "stem": "Best treatment?"}
        ... ]
        >>> mapping = create_canonical_mapping(clusters, questions)
        >>> mapping["Q2"]  # Points to best variant
        "Q1"
        >>> mapping["Q3"]
        "Q1"
    """
    mapping = {}

    for cluster in clusters:
        canonical = select_canonical(cluster, questions)

        if canonical:
            canonical_id = canonical["canonical_id"]

            # Map all cluster members to canonical (including canonical itself)
            for qid in cluster:
                mapping[qid] = canonical_id

    logger.info(
        f"Created canonical mapping: {len(mapping)} questions -> "
        f"{len(set(mapping.values()))} canonical questions"
    )

    return mapping


def get_canonicalization_stats(
    clusters: List[Set[str]],
    questions: List[Dict]
) -> Dict:
    """
    Compute statistics about canonicalization results.

    Args:
        clusters: List of question ID sets
        questions: List of all question dicts

    Returns:
        Stats dict

    Example:
        >>> clusters = [{"Q1", "Q2"}, {"Q3", "Q4", "Q5"}]
        >>> questions = [...]
        >>> stats = get_canonicalization_stats(clusters, questions)
        >>> stats["total_clusters"]
        2
    """
    canonicals = canonicalize_all_clusters(clusters, questions)

    # Cluster size distribution
    cluster_sizes = [len(cluster) for cluster in clusters]

    # Source distribution of canonical questions
    canonical_sources = []
    for canonical_info in canonicals.values():
        source = canonical_info["question"].get("source", "unknown")
        canonical_sources.append(source)

    source_counts = Counter(canonical_sources)

    # Score distribution
    canonical_scores = [c["scores"]["total"] for c in canonicals.values()]

    return {
        "total_clusters": len(clusters),
        "total_duplicates": sum(cluster_sizes),
        "total_canonical_questions": len(canonicals),
        "avg_cluster_size": sum(cluster_sizes) / len(clusters) if clusters else 0,
        "max_cluster_size": max(cluster_sizes) if cluster_sizes else 0,
        "min_cluster_size": min(cluster_sizes) if cluster_sizes else 0,
        "canonical_sources": dict(source_counts),
        "avg_canonical_score": sum(canonical_scores) / len(canonical_scores) if canonical_scores else 0,
        "min_canonical_score": min(canonical_scores) if canonical_scores else 0,
        "max_canonical_score": max(canonical_scores) if canonical_scores else 0
    }


def generate_canonicalization_report(
    clusters: List[Set[str]],
    questions: List[Dict]
) -> Dict:
    """
    Generate detailed report of canonicalization decisions.

    Args:
        clusters: List of question ID sets
        questions: List of all question dicts

    Returns:
        Report dict with examples and statistics

    Example:
        >>> clusters = [{"Q1", "Q2"}]
        >>> questions = [...]
        >>> report = generate_canonicalization_report(clusters, questions)
        >>> "stats" in report
        True
    """
    canonicals = canonicalize_all_clusters(clusters, questions)
    stats = get_canonicalization_stats(clusters, questions)

    # Sample canonical decisions (first 10)
    examples = []
    for cluster_id, canonical_info in list(canonicals.items())[:10]:
        canonical_q = canonical_info["question"]
        examples.append({
            "cluster_id": cluster_id,
            "canonical_id": canonical_info["canonical_id"],
            "canonical_stem": canonical_q.get("stem", "")[:100],
            "canonical_source": canonical_q.get("source", "unknown"),
            "score": canonical_info["scores"]["total"],
            "cluster_size": canonical_info["cluster_size"],
            "alternatives": canonical_info["alternatives"]
        })

    return {
        "stats": stats,
        "canonical_examples": examples,
        "total_reduction": f"{((stats['total_duplicates'] - stats['total_canonical_questions']) / stats['total_duplicates'] * 100):.1f}%"
            if stats['total_duplicates'] > 0 else "0%"
    }
