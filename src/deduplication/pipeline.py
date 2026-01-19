"""
Main deduplication pipeline orchestration.

Coordinates:
1. Data loading
2. Cleanup (encoding fixes)
3. Embedding generation
4. Clustering (similarity detection)
5. Canonicalization (variant selection)
6. Output generation
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .config.settings import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    OUTPUT_DATA_PATH,
    SIMILARITY_THRESHOLD_REVIEW
)
from .cleanup import clean_all_questions, generate_cleanup_report
from .embeddings import generate_all_embeddings
from .clustering import (
    compute_similarity_matrix,
    find_duplicate_pairs,
    build_clusters,
    categorize_clusters,
    get_cluster_statistics
)
from .canonicalization import (
    canonicalize_all_clusters,
    create_canonical_mapping,
    generate_canonicalization_report
)

logger = logging.getLogger(__name__)


class DeduplicationPipeline:
    """
    End-to-end deduplication pipeline.

    Usage:
        >>> pipeline = DeduplicationPipeline()
        >>> results = pipeline.run(questions)
        >>> print(f"Reduced {len(questions)} -> {results['num_canonical']} questions")
    """

    def __init__(
        self,
        similarity_threshold: float = SIMILARITY_THRESHOLD_REVIEW,
        clean_encoding: bool = True,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize pipeline.

        Args:
            similarity_threshold: Minimum similarity for duplicate detection (default 0.88)
            clean_encoding: Whether to fix encoding artifacts (default True)
            output_dir: Where to save results (default: data/dedup_output/)
        """
        self.similarity_threshold = similarity_threshold
        self.clean_encoding = clean_encoding
        self.output_dir = Path(output_dir) if output_dir else Path(OUTPUT_DATA_PATH)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results = {}  # Store results from each step

    def run(
        self,
        questions: List[Dict],
        save_intermediate: bool = True,
        save_reports: bool = True
    ) -> Dict:
        """
        Run complete deduplication pipeline.

        Args:
            questions: List of question dicts (must have "id" field)
            save_intermediate: Save intermediate results to disk
            save_reports: Generate and save detailed reports

        Returns:
            Dict with canonical questions, mappings, and statistics

        Example:
            >>> questions = [{"id": "Q1", "stem": "..."}, ...]
            >>> pipeline = DeduplicationPipeline()
            >>> results = pipeline.run(questions)
            >>> results.keys()
            dict_keys(['canonical_questions', 'duplicate_mapping', 'stats', ...])
        """
        logger.info(f"Starting deduplication pipeline with {len(questions)} questions")
        start_time = datetime.now()

        # Step 1: Cleanup encoding artifacts
        if self.clean_encoding:
            logger.info("Step 1/5: Cleaning encoding artifacts")
            cleaned_questions, cleanup_stats = clean_all_questions(questions)
            self.results["cleanup_stats"] = cleanup_stats

            if save_reports:
                cleanup_report = generate_cleanup_report(questions)
                self._save_json("cleanup_report.json", cleanup_report)
        else:
            cleaned_questions = questions
            logger.info("Step 1/5: Skipping cleanup (clean_encoding=False)")

        # Step 2: Generate embeddings
        logger.info("Step 2/5: Generating embeddings")
        embeddings = generate_all_embeddings(cleaned_questions, show_progress=True)
        question_ids = [q.get("id", f"q_{i}") for i, q in enumerate(cleaned_questions)]

        if save_intermediate:
            self._save_embeddings(embeddings, question_ids)

        # Step 3: Compute similarity and find duplicates
        logger.info("Step 3/5: Computing similarity matrix")
        similarity_matrix = compute_similarity_matrix(embeddings)

        logger.info(f"Finding duplicate pairs (threshold={self.similarity_threshold})")
        duplicate_pairs = find_duplicate_pairs(
            similarity_matrix,
            question_ids,
            threshold=self.similarity_threshold
        )
        self.results["duplicate_pairs"] = duplicate_pairs

        if save_intermediate:
            self._save_json("duplicate_pairs.json", duplicate_pairs)

        # Step 4: Build and categorize clusters
        logger.info("Step 4/5: Building duplicate clusters")
        clusters = build_clusters(duplicate_pairs, question_ids)
        self.results["clusters"] = clusters

        logger.info("Categorizing clusters by confidence")
        categorized = categorize_clusters(clusters, similarity_matrix, question_ids)
        self.results["categorized_clusters"] = categorized

        cluster_stats = get_cluster_statistics(clusters, similarity_matrix, question_ids)
        self.results["cluster_stats"] = cluster_stats

        if save_intermediate:
            self._save_json("clusters.json", {
                "all_clusters": [list(c) for c in clusters],
                "categorized": {
                    k: [list(c) for c in v]
                    for k, v in categorized.items()
                },
                "stats": cluster_stats
            })

        # Step 5: Canonicalization
        logger.info("Step 5/5: Selecting canonical questions")
        canonical_mapping = create_canonical_mapping(clusters, cleaned_questions)
        self.results["canonical_mapping"] = canonical_mapping

        # Extract canonical questions
        canonical_ids = set(canonical_mapping.values())
        canonical_questions = [
            q for q in cleaned_questions
            if q.get("id") in canonical_ids
        ]

        # Add duplicate info to canonical questions
        for canonical_q in canonical_questions:
            canonical_id = canonical_q["id"]
            duplicates = [
                qid for qid, cid in canonical_mapping.items()
                if cid == canonical_id and qid != canonical_id
            ]
            canonical_q["duplicates"] = duplicates
            canonical_q["is_canonical"] = True

        # Mark non-canonical questions
        non_canonical_questions = [
            q for q in cleaned_questions
            if q.get("id") not in canonical_ids
        ]
        for q in non_canonical_questions:
            q["is_canonical"] = False
            q["canonical_id"] = canonical_mapping.get(q["id"])

        if save_intermediate:
            self._save_json("canonical_questions.json", canonical_questions)
            self._save_json("canonical_mapping.json", canonical_mapping)

        # Generate reports
        if save_reports:
            logger.info("Generating canonicalization report")
            canon_report = generate_canonicalization_report(clusters, cleaned_questions)
            self._save_json("canonicalization_report.json", canon_report)

        # Compute final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        final_stats = {
            "total_questions": len(questions),
            "canonical_questions": len(canonical_questions),
            "duplicate_questions": len(questions) - len(canonical_questions),
            "reduction_percentage": f"{((len(questions) - len(canonical_questions)) / len(questions) * 100):.1f}%",
            "num_clusters": len(clusters),
            "auto_merge_clusters": len(categorized["auto_merge"]),
            "review_needed_clusters": len(categorized["needs_review"]),
            "low_confidence_clusters": len(categorized["low_confidence"]),
            "avg_cluster_size": cluster_stats.get("avg_cluster_size", 0),
            "max_cluster_size": cluster_stats.get("max_cluster_size", 0),
            "processing_time_seconds": duration,
            "encoding_issues_fixed": self.results.get("cleanup_stats", {}).get("total_fixes", 0),
            "similarity_threshold": self.similarity_threshold
        }

        logger.info(
            f"Pipeline complete: {len(questions)} -> {len(canonical_questions)} questions "
            f"({final_stats['reduction_percentage']} reduction) in {duration:.1f}s"
        )

        # Save final summary
        if save_reports:
            self._save_json("pipeline_summary.json", final_stats)

        return {
            "canonical_questions": canonical_questions,
            "all_questions": cleaned_questions,  # Includes is_canonical and canonical_id flags
            "duplicate_mapping": canonical_mapping,
            "categorized_clusters": categorized,
            "stats": final_stats,
            "duplicate_pairs": duplicate_pairs[:100]  # First 100 for review
        }

    def run_from_file(
        self,
        input_file: Path,
        save_intermediate: bool = True,
        save_reports: bool = True
    ) -> Dict:
        """
        Run pipeline on questions loaded from JSON file.

        Args:
            input_file: Path to JSON file with questions
            save_intermediate: Save intermediate results
            save_reports: Generate reports

        Returns:
            Pipeline results dict

        Example:
            >>> pipeline = DeduplicationPipeline()
            >>> results = pipeline.run_from_file("data/raw/questions.json")
        """
        logger.info(f"Loading questions from {input_file}")
        with open(input_file, "r", encoding="utf-8") as f:
            questions = json.load(f)

        if not isinstance(questions, list):
            raise ValueError(f"Expected list of questions, got {type(questions)}")

        return self.run(questions, save_intermediate, save_reports)

    def run_incremental(
        self,
        new_question: Dict,
        existing_canonical_questions: List[Dict],
        existing_embeddings: Optional[List[List[float]]] = None
    ) -> Dict:
        """
        Check if a new question is a duplicate of existing canonical questions.

        Used for ongoing deduplication when new questions are added.

        Args:
            new_question: New question dict to check
            existing_canonical_questions: List of canonical question dicts
            existing_embeddings: Pre-computed embeddings (optional, will compute if None)

        Returns:
            Dict with match info or None if unique

        Example:
            >>> new_q = {"id": "Q_new", "stem": "What is the best treatment?"}
            >>> canonical_qs = [...]
            >>> result = pipeline.run_incremental(new_q, canonical_qs)
            >>> if result["is_duplicate"]:
            ...     print(f"Duplicate of {result['canonical_id']}")
        """
        from .embeddings import embed_single_question
        from .clustering import find_duplicates_for_new_question
        import numpy as np

        logger.info(f"Running incremental deduplication for question {new_question.get('id')}")

        # Clean new question
        if self.clean_encoding:
            from .cleanup import clean_question
            new_question, _ = clean_question(new_question)

        # Generate embedding for new question
        new_embedding = embed_single_question(new_question)

        # Generate embeddings for existing questions if not provided
        if existing_embeddings is None:
            existing_embeddings = generate_all_embeddings(existing_canonical_questions)
        else:
            existing_embeddings = np.array(existing_embeddings)

        # Find matches
        existing_ids = [q.get("id") for q in existing_canonical_questions]
        matches = find_duplicates_for_new_question(
            new_embedding,
            existing_embeddings,
            existing_ids,
            threshold=self.similarity_threshold
        )

        if matches:
            best_match = matches[0]
            return {
                "is_duplicate": True,
                "canonical_id": best_match["existing_id"],
                "similarity": best_match["similarity"],
                "all_matches": matches
            }
        else:
            return {
                "is_duplicate": False,
                "canonical_id": new_question.get("id"),  # This becomes a new canonical
                "similarity": None,
                "all_matches": []
            }

    def _save_json(self, filename: str, data: Dict):
        """Save data to JSON file in output directory."""
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved {filename}")

    def _save_embeddings(self, embeddings, question_ids):
        """Save embeddings in .npy format for reuse."""
        import numpy as np

        embeddings_path = self.output_dir / "embeddings.npy"
        ids_path = self.output_dir / "embedding_ids.json"

        np.save(embeddings_path, embeddings)
        with open(ids_path, "w") as f:
            json.dump(question_ids, f, indent=2)

        logger.debug(f"Saved embeddings to {embeddings_path}")


def run_deduplication(
    input_file: Path,
    output_dir: Optional[Path] = None,
    similarity_threshold: float = SIMILARITY_THRESHOLD_REVIEW,
    clean_encoding: bool = True
) -> Dict:
    """
    Convenience function to run full deduplication pipeline.

    Args:
        input_file: Path to JSON file with questions
        output_dir: Where to save results
        similarity_threshold: Duplicate detection threshold
        clean_encoding: Fix encoding artifacts

    Returns:
        Pipeline results dict

    Example:
        >>> results = run_deduplication("data/raw/questions.json")
        >>> print(f"Reduced to {results['stats']['canonical_questions']} questions")
    """
    pipeline = DeduplicationPipeline(
        similarity_threshold=similarity_threshold,
        clean_encoding=clean_encoding,
        output_dir=output_dir
    )

    return pipeline.run_from_file(input_file)


def generate_review_queue(
    categorized_clusters: Dict,
    questions: List[Dict],
    output_file: Optional[Path] = None
) -> List[Dict]:
    """
    Generate human review queue for borderline clusters.

    Args:
        categorized_clusters: Output from categorize_clusters()
        questions: List of all question dicts
        output_file: Optional path to save review queue

    Returns:
        List of clusters needing review with question details

    Example:
        >>> review_queue = generate_review_queue(categorized, questions)
        >>> for item in review_queue:
        ...     print(f"Cluster {item['cluster_id']}: {item['num_questions']} questions")
    """
    needs_review = categorized_clusters.get("needs_review", [])

    review_queue = []
    for i, cluster in enumerate(needs_review):
        cluster_questions = [q for q in questions if q.get("id") in cluster]

        review_item = {
            "cluster_id": f"review_{i}",
            "num_questions": len(cluster_questions),
            "question_ids": list(cluster),
            "questions": [
                {
                    "id": q.get("id"),
                    "stem": q.get("stem", "")[:200],  # First 200 chars
                    "source": q.get("source", "unknown"),
                    "activity": q.get("activity_name", "unknown")
                }
                for q in cluster_questions
            ]
        }
        review_queue.append(review_item)

    logger.info(f"Generated review queue with {len(review_queue)} clusters")

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(review_queue, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved review queue to {output_file}")

    return review_queue
