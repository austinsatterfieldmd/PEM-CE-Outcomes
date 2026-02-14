"""
Supabase Database Service — Drop-in replacement for DatabaseService when targeting Supabase.

Provides the same interface as DatabaseService but writes to Supabase PostgreSQL
via supabase-py (using the service role key which bypasses RLS).

Usage:
    from dashboard.backend.services.supabase_db import SupabaseDatabaseService
    db = SupabaseDatabaseService()  # Uses SUPABASE_URL + SUPABASE_SERVICE_KEY from env
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import date, datetime

logger = logging.getLogger(__name__)

# Region mapping for US states (shared with database.py)
STATE_TO_REGION = {
    'WA': 'West Coast', 'OR': 'West Coast', 'CA': 'West Coast', 'NV': 'West Coast',
    'AK': 'West Coast', 'HI': 'West Coast',
    'MT': 'Midwest', 'ID': 'Midwest', 'WY': 'Midwest', 'ND': 'Midwest', 'SD': 'Midwest',
    'NE': 'Midwest', 'KS': 'Midwest', 'MN': 'Midwest', 'IA': 'Midwest', 'MO': 'Midwest',
    'WI': 'Midwest', 'IL': 'Midwest', 'MI': 'Midwest', 'IN': 'Midwest', 'OH': 'Midwest',
    'CO': 'Midwest', 'UT': 'Midwest',
    'ME': 'Northeast', 'NH': 'Northeast', 'VT': 'Northeast', 'MA': 'Northeast',
    'RI': 'Northeast', 'CT': 'Northeast', 'NY': 'Northeast', 'NJ': 'Northeast',
    'PA': 'Northeast', 'DE': 'Northeast', 'MD': 'Northeast', 'DC': 'Northeast',
    'VA': 'Southeast', 'WV': 'Southeast', 'KY': 'Southeast', 'TN': 'Southeast',
    'NC': 'Southeast', 'SC': 'Southeast', 'GA': 'Southeast', 'FL': 'Southeast',
    'AL': 'Southeast', 'MS': 'Southeast', 'LA': 'Southeast', 'AR': 'Southeast',
    'OK': 'Southeast', 'TX': 'Southeast', 'NM': 'Southeast', 'AZ': 'Southeast',
}


def get_region_from_state(state_code: str) -> Optional[str]:
    """Get region name from US state code."""
    return STATE_TO_REGION.get(state_code.upper() if state_code else None)


def get_quarter_from_date(d: date) -> str:
    """Get quarter string from date (e.g., '2024 Q3')."""
    quarter = (d.month - 1) // 3 + 1
    return f"{d.year} Q{quarter}"


class SupabaseDatabaseService:
    """Database service targeting Supabase PostgreSQL via supabase-py."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize Supabase client with service role key.

        Args:
            url: Supabase project URL. Defaults to SUPABASE_URL env var.
            key: Service role key (bypasses RLS). Defaults to SUPABASE_SERVICE_KEY env var.
        """
        try:
            from supabase import create_client, Client
        except ImportError:
            raise ImportError(
                "supabase-py is required for Supabase target. Install with: pip install supabase"
            )

        self.url = url or os.environ.get('SUPABASE_URL') or os.environ.get('VITE_SUPABASE_URL')
        self.key = key or os.environ.get('SUPABASE_SERVICE_KEY')

        if not self.url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.key:
            raise ValueError("SUPABASE_SERVICE_KEY environment variable is required")

        self.client: Client = create_client(self.url, self.key)
        logger.info(f"Connected to Supabase: {self.url}")

    # ============== Question Operations ==============

    def get_question_by_source_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Look up a question by its source_id (QGD)."""
        result = (
            self.client.table('questions')
            .select('id, source_id, question_stem')
            .eq('source_id', source_id)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            # Query edited_by_user from tags table
            tags_result = (
                self.client.table('tags')
                .select('edited_by_user')
                .eq('question_id', row['id'])
                .limit(1)
                .execute()
            )
            row['edited_by_user'] = (
                tags_result.data[0]['edited_by_user']
                if tags_result.data and tags_result.data[0].get('edited_by_user')
                else False
            )
            return row
        return None

    def insert_question(
        self,
        question_stem: str,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[list] = None,
        source_file: Optional[str] = None,
        source_question_id: Optional[int] = None,
        source_id: Optional[str] = None,
    ) -> int:
        """Insert a new question and return its database ID."""
        data = {
            'question_stem': question_stem,
            'correct_answer': correct_answer,
            'source_file': source_file,
            'source_id': str(source_id) if source_id else None,
        }

        if incorrect_answers:
            if isinstance(incorrect_answers, list):
                import json as _json
                data['incorrect_answers'] = _json.dumps(incorrect_answers)
            else:
                data['incorrect_answers'] = str(incorrect_answers)

        result = self.client.table('questions').insert(data).execute()

        if not result.data:
            raise RuntimeError(f"Failed to insert question (source_id={source_id})")

        return result.data[0]['id']

    def update_question(
        self,
        question_id: int,
        question_stem: Optional[str] = None,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[list] = None,
        source_file: Optional[str] = None,
    ) -> None:
        """Update an existing question."""
        data = {}
        if question_stem is not None:
            data['question_stem'] = question_stem
        if correct_answer is not None:
            data['correct_answer'] = correct_answer
        if incorrect_answers is not None:
            if isinstance(incorrect_answers, list):
                import json as _json
                data['incorrect_answers'] = _json.dumps(incorrect_answers)
            else:
                data['incorrect_answers'] = str(incorrect_answers)
        if source_file is not None:
            data['source_file'] = source_file

        if data:
            self.client.table('questions').update(data).eq('id', question_id).execute()

    # ============== Tag Operations ==============

    def insert_tags(
        self,
        question_id: int,
        topic: Optional[str] = None,
        disease_state: Optional[str] = None,
        needs_review: bool = False,
        overall_confidence: Optional[float] = None,
    ) -> None:
        """Insert a minimal tag record for a question."""
        data = {
            'question_id': question_id,
            'topic': topic,
            'disease_state': disease_state,
            'needs_review': needs_review,
            'overall_confidence': overall_confidence,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        data['question_id'] = question_id  # Always include FK

        self.client.table('tags').insert(data).execute()

    def update_tags(self, question_id: int, tag_update: Dict[str, Any]) -> None:
        """Update tags for a question."""
        if not tag_update:
            return

        processed = {}
        for k, v in tag_update.items():
            if isinstance(v, bool):
                processed[k] = v
            elif v is None:
                continue  # Skip None values
            else:
                processed[k] = v

        if processed:
            self.client.table('tags').update(processed).eq('question_id', question_id).execute()

    # ============== Performance Operations ==============

    def insert_performance(
        self,
        question_id: int,
        segment: str,
        pre_score: Optional[float] = None,
        post_score: Optional[float] = None,
        pre_n: Optional[int] = None,
        post_n: Optional[int] = None
    ) -> None:
        """Insert or update performance metrics for a question segment.

        Uses upsert on the UNIQUE(question_id, segment) constraint.
        """
        data = {
            'question_id': question_id,
            'segment': segment,
            'pre_score': round(pre_score, 2) if pre_score is not None else None,
            'post_score': round(post_score, 2) if post_score is not None else None,
            'pre_n': pre_n,
            'post_n': post_n,
        }
        self.client.table('performance').upsert(
            data, on_conflict='question_id,segment'
        ).execute()

    def insert_performance_batch(self, rows: List[Dict[str, Any]]) -> int:
        """Batch upsert performance rows.

        Args:
            rows: List of dicts with question_id, segment, pre_score, post_score, pre_n, post_n

        Returns:
            Number of rows upserted.
        """
        BATCH_SIZE = 100
        total = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            # Round scores
            for row in batch:
                if row.get('pre_score') is not None:
                    row['pre_score'] = round(row['pre_score'], 2)
                if row.get('post_score') is not None:
                    row['post_score'] = round(row['post_score'], 2)
            self.client.table('performance').upsert(
                batch, on_conflict='question_id,segment'
            ).execute()
            total += len(batch)
        return total

    def insert_demographic_performance(
        self,
        question_id: int,
        activity_id: Optional[int] = None,
        specialty: Optional[str] = None,
        practice_setting: Optional[str] = None,
        practice_state: Optional[str] = None,
        pre_score: Optional[float] = None,
        post_score: Optional[float] = None,
        n_respondents: Optional[int] = None
    ) -> Optional[int]:
        """Insert demographic performance data. Returns record ID."""
        region = get_region_from_state(practice_state) if practice_state else None

        data = {
            'question_id': question_id,
            'activity_id': activity_id,
            'specialty': specialty,
            'practice_setting': practice_setting,
            'practice_state': practice_state,
            'region': region,
            'pre_score': round(pre_score, 2) if pre_score is not None else None,
            'post_score': round(post_score, 2) if post_score is not None else None,
            'n_respondents': n_respondents,
        }
        # Remove None values (except question_id which is always required)
        data = {k: v for k, v in data.items() if v is not None}
        data['question_id'] = question_id

        result = self.client.table('demographic_performance').insert(data).execute()
        if result.data:
            return result.data[0].get('id')
        return None

    def insert_demographic_performance_batch(self, rows: List[Dict[str, Any]]) -> int:
        """Batch insert demographic performance rows.

        Args:
            rows: List of dicts with question_id, activity_id, specialty, etc.

        Returns:
            Number of rows inserted.
        """
        BATCH_SIZE = 100
        total = 0
        # Add region derivation for each row
        for row in rows:
            if row.get('practice_state') and not row.get('region'):
                row['region'] = get_region_from_state(row['practice_state'])
            if row.get('pre_score') is not None:
                row['pre_score'] = round(row['pre_score'], 2)
            if row.get('post_score') is not None:
                row['post_score'] = round(row['post_score'], 2)

        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            self.client.table('demographic_performance').insert(batch).execute()
            total += len(batch)
        return total

    # ============== Activity Operations ==============

    def insert_activity(self, question_id: int, activity_name: str) -> None:
        """Insert an activity association for a question."""
        # Ensure activity exists
        existing = (
            self.client.table('activities')
            .select('id, activity_name')
            .eq('activity_name', activity_name)
            .limit(1)
            .execute()
        )
        if not existing.data:
            result = self.client.table('activities').insert(
                {'activity_name': activity_name}
            ).execute()
            activity_id = result.data[0]['id'] if result.data else None
        else:
            activity_id = existing.data[0]['id']

        # Insert question-activity association (ignore duplicates)
        try:
            self.client.table('question_activities').insert({
                'question_id': question_id,
                'activity_name': activity_name,
                'activity_id': activity_id,
            }).execute()
        except Exception as e:
            if 'duplicate' in str(e).lower() or '23505' in str(e):
                pass  # Already exists
            else:
                raise

    def insert_activity_with_date(
        self, question_id: int, activity_name: str, activity_date: Optional[date] = None
    ) -> None:
        """Insert an activity with a start date."""
        quarter = get_quarter_from_date(activity_date) if activity_date else None

        # Ensure activity exists
        existing = (
            self.client.table('activities')
            .select('id, activity_name')
            .eq('activity_name', activity_name)
            .limit(1)
            .execute()
        )
        if not existing.data:
            result = self.client.table('activities').insert({
                'activity_name': activity_name,
                'activity_date': activity_date.isoformat() if activity_date else None,
                'quarter': quarter,
            }).execute()
            activity_id = result.data[0]['id'] if result.data else None
        else:
            activity_id = existing.data[0]['id']
            # Update date if not set
            if activity_date:
                self.client.table('activities').update({
                    'activity_date': activity_date.isoformat(),
                    'quarter': quarter,
                }).eq('activity_name', activity_name).is_('activity_date', 'null').execute()

        # Insert question-activity association
        try:
            self.client.table('question_activities').insert({
                'question_id': question_id,
                'activity_name': activity_name,
                'activity_id': activity_id,
                'activity_date': activity_date.isoformat() if activity_date else None,
                'quarter': quarter,
            }).execute()
        except Exception as e:
            if 'duplicate' in str(e).lower() or '23505' in str(e):
                pass
            else:
                raise

    def upsert_activity_metadata(
        self,
        activity_name: str,
        activity_date: Optional[date] = None,
        target_audience: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[int]:
        """Insert or update activity metadata. Returns activity ID."""
        quarter = get_quarter_from_date(activity_date) if activity_date else None

        data = {
            'activity_name': activity_name,
        }
        if activity_date is not None:
            data['activity_date'] = activity_date.isoformat()
        if quarter is not None:
            data['quarter'] = quarter
        if target_audience is not None:
            data['target_audience'] = target_audience
        if description is not None:
            data['description'] = description

        result = self.client.table('activities').upsert(
            data, on_conflict='activity_name'
        ).execute()

        activity_id = result.data[0].get('id') if result.data else None

        # Update question_activities with the activity_id
        if activity_id:
            self.client.table('question_activities').update(
                {'activity_id': activity_id}
            ).eq('activity_name', activity_name).is_('activity_id', 'null').execute()

        return activity_id

    def insert_question_activity(
        self,
        question_id: int,
        activity_name: str,
        activity_id: Optional[int] = None,
        activity_date: Optional[date] = None,
        quarter: Optional[str] = None,
        pre_score: Optional[float] = None,
        post_score: Optional[float] = None,
        pre_n: Optional[int] = None,
        post_n: Optional[int] = None,
    ) -> None:
        """Insert a question-activity association with optional performance data."""
        data = {
            'question_id': question_id,
            'activity_name': activity_name,
        }
        if activity_id is not None:
            data['activity_id'] = activity_id
        if activity_date is not None:
            data['activity_date'] = activity_date.isoformat()
        if quarter is not None:
            data['quarter'] = quarter
        if pre_score is not None:
            data['pre_score'] = round(pre_score, 2)
        if post_score is not None:
            data['post_score'] = round(post_score, 2)
        if pre_n is not None:
            data['pre_n'] = pre_n
        if post_n is not None:
            data['post_n'] = post_n

        try:
            self.client.table('question_activities').upsert(
                data, on_conflict='question_id,activity_name'
            ).execute()
        except Exception as e:
            if 'duplicate' in str(e).lower() or '23505' in str(e):
                pass
            else:
                raise

    # ============== QCore Scoring ==============

    def calculate_qcore_for_question(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Calculate and store QCore score for a question.

        Reads quality-relevant tag fields from Supabase, scores using the
        Python QCore scorer, and writes the result back.
        """
        try:
            from src.core.preprocessing.qcore_scorer import calculate_qcore_score
        except ImportError:
            logger.warning(f"QCore scorer not available, skipping question {question_id}")
            return None

        # Read quality-relevant tag fields
        result = self.client.table('tags').select(
            'cme_outcome_level, data_response_type, stem_type, lead_in_type, '
            'answer_format, answer_length_pattern, distractor_homogeneity, '
            'flaw_absolute_terms, flaw_grammatical_cue, flaw_implausible_distractor, '
            'flaw_clang_association, flaw_convergence_vulnerability, flaw_double_negative, '
            'answer_option_count'
        ).eq('question_id', question_id).execute()

        if not result.data:
            logger.debug(f"No tags found for question {question_id}, skipping QCore")
            return None

        tags = result.data[0]

        # Determine CME level
        cme_level = 4
        cme_value = tags.get('cme_outcome_level') or ''
        if '3' in str(cme_value) or 'knowledge' in str(cme_value).lower():
            cme_level = 3

        score_result = calculate_qcore_score(tags, cme_level=cme_level)

        # Write back to Supabase
        self.client.table('tags').update({
            'qcore_score': score_result['total_score'],
            'qcore_grade': score_result['grade'],
            'qcore_breakdown': json.dumps(score_result['breakdown']),
        }).eq('question_id', question_id).execute()

        return score_result

    def calculate_qcore_for_all_questions(self) -> Dict[str, int]:
        """Calculate QCore scores for all questions with tags.

        Returns:
            Dict with scored, skipped, and error counts.
        """
        try:
            from src.core.preprocessing.qcore_scorer import calculate_qcore_score
        except ImportError:
            logger.error("QCore scorer not available")
            return {'scored': 0, 'skipped': 0, 'errors': 0}

        # Get all question_ids that have tags
        result = self.client.table('tags').select('question_id').execute()
        question_ids = [r['question_id'] for r in result.data] if result.data else []

        scored = 0
        skipped = 0
        errors = 0

        for qid in question_ids:
            try:
                score_result = self.calculate_qcore_for_question(qid)
                if score_result:
                    scored += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.warning(f"QCore error for question {qid}: {e}")
                errors += 1

        logger.info(f"QCore batch complete: {scored} scored, {skipped} skipped, {errors} errors")
        return {'scored': scored, 'skipped': skipped, 'errors': errors}

    # ============== Stats & Utility ==============

    def get_stats(self) -> Dict[str, Any]:
        """Get basic database statistics."""
        total = self.client.table('questions').select('id', count='exact').execute()
        tagged = (
            self.client.table('tags')
            .select('question_id', count='exact')
            .not_.is_('topic', 'null')
            .execute()
        )

        return {
            'total_questions': total.count or 0,
            'tagged_questions': tagged.count or 0,
        }

    def clear_database(self) -> None:
        """Clear all data from the database. DESTRUCTIVE operation."""
        # Delete in dependency order (children first)
        tables = [
            'tag_proposal_candidates', 'tag_proposals',
            'duplicate_decisions', 'cluster_members', 'duplicate_clusters',
            'novel_entity_occurrences', 'novel_entities',
            'data_error_questions', 'user_defined_values',
            'demographic_performance', 'question_activities',
            'performance', 'tags', 'activities', 'questions',
        ]
        for table in tables:
            try:
                # Delete all rows (Supabase requires a filter, use gt id 0)
                self.client.table(table).delete().gte('id', 0).execute()
            except Exception as e:
                logger.warning(f"Failed to clear table {table}: {e}")

        logger.info("All tables cleared")

    def clear_performance_data(self) -> None:
        """Clear only performance-related tables. Used before reimporting performance data."""
        tables = ['demographic_performance', 'question_activities', 'performance', 'activities']
        for table in tables:
            try:
                self.client.table(table).delete().gte('id', 0).execute()
                logger.info(f"Cleared table: {table}")
            except Exception as e:
                logger.warning(f"Failed to clear table {table}: {e}")
