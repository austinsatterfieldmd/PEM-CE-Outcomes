"""
Identify duplicate question clusters using cosine similarity.

Uses efficient numpy operations for pairwise similarity computation.
"""

import logging
from typing import List, Dict, Set
import numpy as np
from collections import defaultdict

from .config.settings import (
    SIMILARITY_THRESHOLD_AUTO_MERGE,
    SIMILARITY_THRESHOLD_REVIEW,
    SIMILARITY_THRESHOLD_RELATED,
)

logger = logging.getLogger(__name__)


def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Compute pairwise cosine similarity matrix.

    Args:
        embeddings: NumPy array of shape (n_questions, embedding_dim)

    Returns:
        Similarity matrix of shape (n_questions, n_questions)

    Example:
        >>> embeddings = np.random.rand(100, 1536)
        >>> sim_matrix = compute_similarity_matrix(embeddings)
        >>> sim_matrix.shape
        (100, 100)
        >>> np.allclose(np.diag(sim_matrix), 1.0)  # Diagonal is all 1s
        True
    """
    # Normalize embeddings to unit length
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms

    # Compute cosine similarity via dot product of normalized vectors
    similarity_matrix = np.dot(normalized, normalized.T)

    logger.debug(f"Computed similarity matrix with shape: {similarity_matrix.shape}")

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
        List of dicts with q1_id, q2_id, similarity score, sorted by similarity descending

    Example:
        >>> sim_matrix = np.array([[1.0, 0.95, 0.7], [0.95, 1.0, 0.8], [0.7, 0.8, 1.0]])
        >>> ids = ["Q1", "Q2", "Q3"]
        >>> pairs = find_duplicate_pairs(sim_matrix, ids, threshold=0.9)
        >>> len(pairs)
        1
        >>> pairs[0]["similarity"]
        0.95
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

    logger.info(f"Found {len(pairs)} duplicate pairs above threshold {threshold}")

    return pairs


def build_clusters(
    pairs: List[Dict],
    question_ids: List[str]
) -> List[Set[str]]:
    """
    Group duplicate pairs into clusters using union-find algorithm.

    If Q1 ~ Q2 and Q2 ~ Q3, then {Q1, Q2, Q3} form one cluster.

    Args:
        pairs: List of duplicate pair dicts
        question_ids: All question IDs

    Returns:
        List of sets, each containing IDs of duplicate questions

    Example:
        >>> pairs = [
        ...     {"q1_id": "Q1", "q2_id": "Q2", "similarity": 0.95},
        ...     {"q1_id": "Q2", "q2_id": "Q3", "similarity": 0.93}
        ... ]
        >>> ids = ["Q1", "Q2", "Q3", "Q4"]
        >>> clusters = build_clusters(pairs, ids)
        >>> {"Q1", "Q2", "Q3"} in clusters
        True
        >>> len(clusters)  # Q4 is unique, not in any cluster
        1
    """
    # Union-find data structure
    parent = {qid: qid for qid in question_ids}

    def find(x):
        """Find root of x with path compression."""
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        """Union two sets."""
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

    logger.info(f"Built {len(clusters)} duplicate clusters from {len(pairs)} pairs")

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

    Example:
        >>> clusters = [{"Q1", "Q2"}, {"Q3", "Q4", "Q5"}]
        >>> sim_matrix = np.array([...])  # Similarities
        >>> ids = ["Q1", "Q2", "Q3", "Q4", "Q5"]
        >>> categorized = categorize_clusters(clusters, sim_matrix, ids)
        >>> "auto_merge" in categorized
        True
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

        # Categorize based on minimum similarity
        if min_sim >= SIMILARITY_THRESHOLD_AUTO_MERGE:
            categorized["auto_merge"].append(cluster)
        elif min_sim >= SIMILARITY_THRESHOLD_REVIEW:
            categorized["needs_review"].append(cluster)
        else:
            categorized["low_confidence"].append(cluster)

    logger.info(
        f"Categorized clusters: {len(categorized['auto_merge'])} auto-merge, "
        f"{len(categorized['needs_review'])} needs review, "
        f"{len(categorized['low_confidence'])} low confidence"
    )

    return categorized


def find_duplicates_for_new_question(
    new_embedding: np.ndarray,
    existing_embeddings: np.ndarray,
    existing_ids: List[str],
    threshold: float = SIMILARITY_THRESHOLD_REVIEW
) -> List[Dict]:
    """
    Find potential duplicates for a newly added question.

    Used for ongoing deduplication when new questions are added.

    Args:
        new_embedding: Embedding vector for new question
        existing_embeddings: Matrix of existing question embeddings
        existing_ids: IDs corresponding to existing embeddings
        threshold: Similarity threshold

    Returns:
        List of potential matches with IDs and similarity scores, sorted descending

    Example:
        >>> new_emb = np.random.rand(1536)
        >>> existing_embs = np.random.rand(100, 1536)
        >>> ids = [f"Q{i}" for i in range(100)]
        >>> matches = find_duplicates_for_new_question(new_emb, existing_embs, ids)
        >>> all(m["similarity"] >= 0.88 for m in matches)
        True
    """
    # Normalize embeddings
    new_norm = new_embedding / np.linalg.norm(new_embedding)
    existing_norms = existing_embeddings / np.linalg.norm(
        existing_embeddings, axis=1, keepdims=True
    )

    # Compute cosine similarities
    similarities = np.dot(existing_norms, new_norm)

    # Find matches above threshold
    matches = []
    for i, sim in enumerate(similarities):
        if sim >= threshold:
            matches.append({
                "existing_id": existing_ids[i],
                "similarity": float(sim),
                "index": i
            })

    # Sort by similarity descending
    matches.sort(key=lambda x: -x["similarity"])

    logger.debug(f"Found {len(matches)} potential matches for new question")

    return matches


def get_cluster_statistics(
    clusters: List[Set[str]],
    similarity_matrix: np.ndarray,
    question_ids: List[str]
) -> Dict:
    """
    Compute statistics about duplicate clusters.

    Args:
        clusters: List of question ID sets
        similarity_matrix: Pairwise similarity scores
        question_ids: List mapping indices to IDs

    Returns:
        Dict with statistics (avg_cluster_size, max_cluster_size, etc.)
    """
    if not clusters:
        return {
            "num_clusters": 0,
            "avg_cluster_size": 0,
            "max_cluster_size": 0,
            "min_cluster_size": 0,
            "total_duplicate_questions": 0
        }

    id_to_idx = {qid: i for i, qid in enumerate(question_ids)}
    cluster_sizes = [len(c) for c in clusters]
    total_duplicates = sum(cluster_sizes)

    # Compute average intra-cluster similarity
    avg_similarities = []
    for cluster in clusters:
        indices = [id_to_idx[qid] for qid in cluster]
        sims = []
        for i, idx1 in enumerate(indices):
            for idx2 in indices[i + 1:]:
                sims.append(similarity_matrix[idx1][idx2])
        if sims:
            avg_similarities.append(np.mean(sims))

    return {
        "num_clusters": len(clusters),
        "avg_cluster_size": np.mean(cluster_sizes),
        "max_cluster_size": max(cluster_sizes),
        "min_cluster_size": min(cluster_sizes),
        "total_duplicate_questions": total_duplicates,
        "avg_intra_cluster_similarity": np.mean(avg_similarities) if avg_similarities else 0
    }
