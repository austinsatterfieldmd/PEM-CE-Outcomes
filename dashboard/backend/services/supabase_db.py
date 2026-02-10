"""
Supabase Database Service — Drop-in replacement for DatabaseService when targeting Supabase.

Provides the same interface as DatabaseService but writes to Supabase PostgreSQL
via supabase-py (using the service role key which bypasses RLS).

Usage:
    from dashboard.backend.services.supabase_db import SupabaseDatabaseService
    db = SupabaseDatabaseService()  # Uses SUPABASE_URL + SUPABASE_SERVICE_KEY from env
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import date

logger = logging.getLogger(__name__)


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

    def get_question_by_source_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Look up a question by its source_id (QGD)."""
        result = (
            self.client.table('questions')
            .select('id, source_id, question_stem, edited_by_user')
            .eq('source_id', source_id)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            # Normalize edited_by_user to bool
            row['edited_by_user'] = bool(row.get('edited_by_user'))
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
                data['incorrect_answers'] = '\n'.join(incorrect_answers)
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
                data['incorrect_answers'] = '\n'.join(incorrect_answers)
            else:
                data['incorrect_answers'] = str(incorrect_answers)
        if source_file is not None:
            data['source_file'] = source_file

        if data:
            self.client.table('questions').update(data).eq('id', question_id).execute()

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

        # Convert Python booleans to PostgreSQL-compatible values
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

    def insert_activity(self, question_id: int, activity_name: str) -> None:
        """Insert an activity association for a question."""
        # Ensure activity exists
        existing = (
            self.client.table('activities')
            .select('activity_name')
            .eq('activity_name', activity_name)
            .limit(1)
            .execute()
        )
        if not existing.data:
            self.client.table('activities').insert({'activity_name': activity_name}).execute()

        # Insert question-activity association (ignore duplicates)
        try:
            self.client.table('question_activities').insert({
                'question_id': question_id,
                'activity_name': activity_name,
            }).execute()
        except Exception as e:
            if 'duplicate' in str(e).lower() or '23505' in str(e):
                pass  # Already exists
            else:
                raise

    def insert_activity_with_date(self, question_id: int, activity_name: str, activity_date: date) -> None:
        """Insert an activity with a start date."""
        # Ensure activity exists with date
        existing = (
            self.client.table('activities')
            .select('activity_name')
            .eq('activity_name', activity_name)
            .limit(1)
            .execute()
        )
        if not existing.data:
            self.client.table('activities').insert({
                'activity_name': activity_name,
                'start_date': activity_date.isoformat(),
            }).execute()
        else:
            # Update date if not set
            self.client.table('activities').update({
                'start_date': activity_date.isoformat(),
            }).eq('activity_name', activity_name).is_('start_date', 'null').execute()

        # Insert question-activity association
        try:
            self.client.table('question_activities').insert({
                'question_id': question_id,
                'activity_name': activity_name,
            }).execute()
        except Exception as e:
            if 'duplicate' in str(e).lower() or '23505' in str(e):
                pass
            else:
                raise

    def calculate_qcore_for_question(self, question_id: int) -> None:
        """Calculate QCore score for a question.

        In Supabase mode, this is a no-op since QCore scoring will be
        handled separately (either as an RPC function or post-migration batch).
        """
        # QCore scoring requires complex logic that's in the SQLite DatabaseService.
        # For now, skip it during Supabase import — can be run as a batch later.
        logger.debug(f"QCore scoring skipped for question {question_id} (Supabase mode)")

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
