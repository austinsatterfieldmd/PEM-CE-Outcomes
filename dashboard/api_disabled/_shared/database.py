"""
Shared database access for Vercel serverless functions.

This module provides read-only access to the bundled SQLite database.
For Vercel deployment, the database is included as a static asset.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

# In Vercel, the working directory is the api folder's parent
# The database is at dashboard/data/questions.db
def get_db_path() -> Path:
    """Get the path to the SQLite database."""
    # Check for Vercel environment
    if os.environ.get("VERCEL"):
        # In Vercel, files are relative to project root
        return Path("/var/task/data/questions.db")
    else:
        # Local development - relative to this file
        return Path(__file__).parent.parent.parent / "data" / "questions.db"


class DatabaseService:
    """Read-only SQLite database service for serverless functions."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database service."""
        self.db_path = db_path or get_db_path()

    @contextmanager
    def get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def search_questions(
        self,
        query: Optional[str] = None,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        disease_stages: Optional[List[str]] = None,
        disease_types: Optional[List[str]] = None,
        treatment_lines: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
        trials: Optional[List[str]] = None,
        activities: Optional[List[str]] = None,
        min_confidence: Optional[float] = None,
        has_performance_data: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "id",
        sort_desc: bool = False
    ) -> Tuple[List[Dict], int]:
        """Search questions with filters. Returns (questions, total_count)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            select_fields = """
                q.id, q.question_stem, t.topic, t.topic_confidence,
                t.disease_state, t.treatment,
                p.pre_score, p.post_score,
                (SELECT COUNT(*) FROM question_activities qa WHERE qa.question_id = q.id) as activity_count
            """

            from_clause = """
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                LEFT JOIN performance p ON q.id = p.question_id AND p.segment = 'overall'
            """

            where_clauses = []
            params = []

            if query:
                where_clauses.append("q.id IN (SELECT rowid FROM questions_fts WHERE questions_fts MATCH ?)")
                params.append(query)

            if topics:
                placeholders = ",".join("?" * len(topics))
                where_clauses.append(f"t.topic IN ({placeholders})")
                params.extend(topics)

            if disease_states:
                placeholders = ",".join("?" * len(disease_states))
                where_clauses.append(f"t.disease_state IN ({placeholders})")
                params.extend(disease_states)

            if disease_stages:
                placeholders = ",".join("?" * len(disease_stages))
                where_clauses.append(f"t.disease_stage IN ({placeholders})")
                params.extend(disease_stages)

            if disease_types:
                placeholders = ",".join("?" * len(disease_types))
                where_clauses.append(f"t.disease_type IN ({placeholders})")
                params.extend(disease_types)

            if treatment_lines:
                placeholders = ",".join("?" * len(treatment_lines))
                where_clauses.append(f"t.treatment_line IN ({placeholders})")
                params.extend(treatment_lines)

            if treatments:
                placeholders = ",".join("?" * len(treatments))
                where_clauses.append(f"t.treatment IN ({placeholders})")
                params.extend(treatments)

            if biomarkers:
                placeholders = ",".join("?" * len(biomarkers))
                where_clauses.append(f"t.biomarker IN ({placeholders})")
                params.extend(biomarkers)

            if trials:
                placeholders = ",".join("?" * len(trials))
                where_clauses.append(f"t.trial IN ({placeholders})")
                params.extend(trials)

            if activities:
                placeholders = ",".join("?" * len(activities))
                where_clauses.append(f"""
                    q.id IN (SELECT question_id FROM question_activities WHERE activity_name IN ({placeholders}))
                """)
                params.extend(activities)

            if min_confidence is not None:
                where_clauses.append("t.topic_confidence >= ?")
                params.append(min_confidence)

            if has_performance_data is True:
                where_clauses.append("p.pre_score IS NOT NULL")
            elif has_performance_data is False:
                where_clauses.append("p.pre_score IS NULL")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Get total count
            count_sql = f"SELECT COUNT(DISTINCT q.id) {from_clause} WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]

            # Sorting
            sort_column = {
                "id": "q.id",
                "topic": "t.topic",
                "disease_state": "t.disease_state",
                "pre_score": "p.pre_score",
                "post_score": "p.post_score",
                "knowledge_gain": "(p.post_score - p.pre_score)",
                "confidence": "t.topic_confidence"
            }.get(sort_by, "q.id")

            sort_direction = "DESC" if sort_desc else "ASC"

            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT DISTINCT {select_fields}
                {from_clause}
                WHERE {where_sql}
                ORDER BY {sort_column} {sort_direction}
                LIMIT ? OFFSET ?
            """
            params.extend([page_size, offset])

            cursor.execute(query_sql, params)
            rows = cursor.fetchall()

            questions = []
            for row in rows:
                pre_score = row["pre_score"]
                post_score = row["post_score"]
                knowledge_gain = None
                if pre_score is not None and post_score is not None:
                    knowledge_gain = post_score - pre_score

                questions.append({
                    "id": row["id"],
                    "question_stem": row["question_stem"],
                    "topic": row["topic"],
                    "topic_confidence": row["topic_confidence"],
                    "disease_state": row["disease_state"],
                    "treatment": row["treatment"],
                    "pre_score": pre_score,
                    "post_score": post_score,
                    "knowledge_gain": knowledge_gain,
                    "activity_count": row["activity_count"]
                })

            return questions, total

    def get_question_detail(self, question_id: int) -> Optional[Dict]:
        """Get full question details by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT q.*, t.*
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                WHERE q.id = ?
            """, (question_id,))
            row = cursor.fetchone()

            if not row:
                return None

            cursor.execute("""
                SELECT segment, pre_score, post_score, pre_n, post_n
                FROM performance
                WHERE question_id = ?
            """, (question_id,))
            performance = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT activity_name
                FROM question_activities
                WHERE question_id = ?
            """, (question_id,))
            activities = [r["activity_name"] for r in cursor.fetchall()]

            incorrect_answers = None
            if row["incorrect_answers"]:
                try:
                    incorrect_answers = json.loads(row["incorrect_answers"])
                except json.JSONDecodeError:
                    incorrect_answers = []

            return {
                "id": row["id"],
                "question_stem": row["question_stem"],
                "correct_answer": row["correct_answer"],
                "incorrect_answers": incorrect_answers,
                "source_file": row["source_file"],
                "tags": {
                    "topic": row["topic"],
                    "topic_confidence": row["topic_confidence"],
                    "topic_method": row["topic_method"],
                    "disease_state": row["disease_state"],
                    "disease_state_confidence": row["disease_state_confidence"],
                    "disease_stage": row["disease_stage"],
                    "disease_type": row["disease_type"],
                    "treatment_line": row["treatment_line"] if "treatment_line" in row.keys() else None,
                    "treatment": row["treatment"],
                    "treatment_confidence": row["treatment_confidence"],
                    "biomarker": row["biomarker"],
                    "trial": row["trial"],
                },
                "performance": performance,
                "activities": activities
            }

    def get_filter_options(self) -> Dict[str, List[Dict]]:
        """Get all available filter options with counts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            options = {}

            tag_fields = [
                ("topics", "topic"),
                ("disease_states", "disease_state"),
                ("disease_stages", "disease_stage"),
                ("disease_types", "disease_type"),
                ("treatment_lines", "treatment_line"),
                ("treatments", "treatment"),
                ("biomarkers", "biomarker"),
                ("trials", "trial")
            ]

            for option_name, field_name in tag_fields:
                cursor.execute(f"""
                    SELECT {field_name} as value, COUNT(*) as count
                    FROM tags
                    WHERE {field_name} IS NOT NULL AND {field_name} != ''
                    GROUP BY {field_name}
                    ORDER BY count DESC
                """)
                options[option_name] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            cursor.execute("""
                SELECT activity_name as value, COUNT(*) as count
                FROM question_activities
                WHERE activity_name IS NOT NULL AND activity_name != ''
                GROUP BY activity_name
                ORDER BY count DESC
            """)
            options["activities"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            return options

    def get_dynamic_filter_options(
        self,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        disease_stages: Optional[List[str]] = None,
        disease_types: Optional[List[str]] = None,
        treatment_lines: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
        trials: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict]]:
        """Get filter options dynamically based on current selections."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            filter_fields = {
                'topics': ('topic', topics),
                'disease_states': ('disease_state', disease_states),
                'disease_stages': ('disease_stage', disease_stages),
                'disease_types': ('disease_type', disease_types),
                'treatment_lines': ('treatment_line', treatment_lines),
                'treatments': ('treatment', treatments),
                'biomarkers': ('biomarker', biomarkers),
                'trials': ('trial', trials),
            }

            options = {}

            for option_name, (field_name, _) in filter_fields.items():
                where_clauses = []
                params = []

                for other_name, (other_field, other_values) in filter_fields.items():
                    if other_name != option_name and other_values:
                        placeholders = ",".join("?" * len(other_values))
                        where_clauses.append(f"{other_field} IN ({placeholders})")
                        params.extend(other_values)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                query = f"""
                    SELECT {field_name} as value, COUNT(*) as count
                    FROM tags
                    WHERE {field_name} IS NOT NULL AND {field_name} != ''
                    AND {where_sql}
                    GROUP BY {field_name}
                    ORDER BY count DESC
                """
                cursor.execute(query, params)
                options[option_name] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Get activities with filters applied
            where_clauses = []
            params = []
            for _, (field_name, values) in filter_fields.items():
                if values:
                    placeholders = ",".join("?" * len(values))
                    where_clauses.append(f"t.{field_name} IN ({placeholders})")
                    params.extend(values)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            cursor.execute(f"""
                SELECT qa.activity_name as value, COUNT(DISTINCT qa.question_id) as count
                FROM question_activities qa
                JOIN tags t ON qa.question_id = t.question_id
                WHERE qa.activity_name IS NOT NULL AND qa.activity_name != ''
                AND {where_sql}
                GROUP BY qa.activity_name
                ORDER BY count DESC
            """, params)
            options["activities"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            return options

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM questions")
            total_questions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tags WHERE topic IS NOT NULL")
            tagged_questions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM performance WHERE pre_score IS NOT NULL")
            questions_with_performance = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT activity_name) FROM question_activities")
            total_activities = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM activities WHERE activity_date IS NOT NULL")
            activities_with_dates = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM demographic_performance")
            demographic_records = cursor.fetchone()[0]

            return {
                "total_questions": total_questions,
                "tagged_questions": tagged_questions,
                "questions_with_performance": questions_with_performance,
                "total_activities": total_activities,
                "activities_with_dates": activities_with_dates,
                "demographic_records": demographic_records
            }

    # ============== Report Aggregation Methods ==============

    def aggregate_performance_by_tag(
        self,
        group_by: str,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
        trials: Optional[List[str]] = None,
        activities: Optional[List[str]] = None,
        quarters: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Aggregate performance metrics grouped by a tag field."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            valid_group_fields = ['topic', 'disease_state', 'disease_stage', 'disease_type', 'treatment', 'biomarker', 'trial']
            if group_by not in valid_group_fields:
                raise ValueError(f"Invalid group_by field: {group_by}")

            where_clauses = [f"t.{group_by} IS NOT NULL", f"t.{group_by} != ''"]
            params = []

            if topics:
                placeholders = ",".join("?" * len(topics))
                where_clauses.append(f"t.topic IN ({placeholders})")
                params.extend(topics)

            if disease_states:
                placeholders = ",".join("?" * len(disease_states))
                where_clauses.append(f"t.disease_state IN ({placeholders})")
                params.extend(disease_states)

            if treatments:
                placeholders = ",".join("?" * len(treatments))
                where_clauses.append(f"t.treatment IN ({placeholders})")
                params.extend(treatments)

            if biomarkers:
                placeholders = ",".join("?" * len(biomarkers))
                where_clauses.append(f"t.biomarker IN ({placeholders})")
                params.extend(biomarkers)

            if trials:
                placeholders = ",".join("?" * len(trials))
                where_clauses.append(f"t.trial IN ({placeholders})")
                params.extend(trials)

            activity_join = ""
            if activities or quarters:
                activity_join = """
                    JOIN question_activities qa ON q.id = qa.question_id
                    JOIN activities a ON qa.activity_id = a.id
                """
                if activities:
                    placeholders = ",".join("?" * len(activities))
                    where_clauses.append(f"qa.activity_name IN ({placeholders})")
                    params.extend(activities)
                if quarters:
                    placeholders = ",".join("?" * len(quarters))
                    where_clauses.append(f"a.quarter IN ({placeholders})")
                    params.extend(quarters)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT
                    t.{group_by} as group_value,
                    AVG(p.pre_score) as avg_pre_score,
                    AVG(p.post_score) as avg_post_score,
                    SUM(COALESCE(p.pre_n, 0)) as total_pre_n,
                    SUM(COALESCE(p.post_n, 0)) as total_post_n,
                    COUNT(DISTINCT q.id) as question_count
                FROM questions q
                JOIN tags t ON q.id = t.question_id
                LEFT JOIN performance p ON q.id = p.question_id AND p.segment = 'overall'
                {activity_join}
                WHERE {where_sql}
                GROUP BY t.{group_by}
                ORDER BY question_count DESC
            """

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "group_value": row["group_value"],
                    "avg_pre_score": round(row["avg_pre_score"], 1) if row["avg_pre_score"] else None,
                    "avg_post_score": round(row["avg_post_score"], 1) if row["avg_post_score"] else None,
                    "total_pre_n": row["total_pre_n"] or 0,
                    "total_post_n": row["total_post_n"] or 0,
                    "question_count": row["question_count"]
                })

            return results

    def aggregate_performance_by_demographic(
        self,
        segment_by: str,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
        activities: Optional[List[str]] = None,
        quarters: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Aggregate performance metrics grouped by a demographic field."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            valid_segment_fields = ['specialty', 'practice_setting', 'region', 'practice_state']
            if segment_by not in valid_segment_fields:
                raise ValueError(f"Invalid segment_by field: {segment_by}")

            where_clauses = [f"dp.{segment_by} IS NOT NULL", f"dp.{segment_by} != ''"]
            params = []

            tag_join = ""
            if any([topics, disease_states, treatments, biomarkers]):
                tag_join = "JOIN tags t ON q.id = t.question_id"

                if topics:
                    placeholders = ",".join("?" * len(topics))
                    where_clauses.append(f"t.topic IN ({placeholders})")
                    params.extend(topics)

                if disease_states:
                    placeholders = ",".join("?" * len(disease_states))
                    where_clauses.append(f"t.disease_state IN ({placeholders})")
                    params.extend(disease_states)

                if treatments:
                    placeholders = ",".join("?" * len(treatments))
                    where_clauses.append(f"t.treatment IN ({placeholders})")
                    params.extend(treatments)

                if biomarkers:
                    placeholders = ",".join("?" * len(biomarkers))
                    where_clauses.append(f"t.biomarker IN ({placeholders})")
                    params.extend(biomarkers)

            if activities:
                placeholders = ",".join("?" * len(activities))
                where_clauses.append(f"a.activity_name IN ({placeholders})")
                params.extend(activities)

            if quarters:
                placeholders = ",".join("?" * len(quarters))
                where_clauses.append(f"a.quarter IN ({placeholders})")
                params.extend(quarters)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT
                    dp.{segment_by} as segment_value,
                    AVG(dp.pre_score) as avg_pre_score,
                    AVG(dp.post_score) as avg_post_score,
                    SUM(COALESCE(dp.n_respondents, 0)) as total_n,
                    COUNT(DISTINCT dp.question_id) as question_count
                FROM demographic_performance dp
                JOIN questions q ON dp.question_id = q.id
                LEFT JOIN activities a ON dp.activity_id = a.id
                {tag_join}
                WHERE {where_sql}
                GROUP BY dp.{segment_by}
                ORDER BY total_n DESC
            """

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "segment_value": row["segment_value"],
                    "avg_pre_score": round(row["avg_pre_score"], 1) if row["avg_pre_score"] else None,
                    "avg_post_score": round(row["avg_post_score"], 1) if row["avg_post_score"] else None,
                    "total_n": row["total_n"] or 0,
                    "question_count": row["question_count"]
                })

            return results

    def get_performance_trends(
        self,
        segment_by: Optional[str] = None,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Get performance trends over time (by quarter)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["a.quarter IS NOT NULL"]
            params = []

            tag_join = ""
            if any([topics, disease_states, treatments, biomarkers]):
                tag_join = "JOIN tags t ON q.id = t.question_id"

                if topics:
                    placeholders = ",".join("?" * len(topics))
                    where_clauses.append(f"t.topic IN ({placeholders})")
                    params.extend(topics)

                if disease_states:
                    placeholders = ",".join("?" * len(disease_states))
                    where_clauses.append(f"t.disease_state IN ({placeholders})")
                    params.extend(disease_states)

                if treatments:
                    placeholders = ",".join("?" * len(treatments))
                    where_clauses.append(f"t.treatment IN ({placeholders})")
                    params.extend(treatments)

                if biomarkers:
                    placeholders = ",".join("?" * len(biomarkers))
                    where_clauses.append(f"t.biomarker IN ({placeholders})")
                    params.extend(biomarkers)

            where_sql = " AND ".join(where_clauses)

            if segment_by and segment_by in ['specialty', 'practice_setting', 'region']:
                query = f"""
                    SELECT
                        a.quarter,
                        dp.{segment_by} as segment_value,
                        AVG(dp.pre_score) as avg_pre_score,
                        AVG(dp.post_score) as avg_post_score,
                        SUM(COALESCE(dp.n_respondents, 0)) as total_n
                    FROM demographic_performance dp
                    JOIN questions q ON dp.question_id = q.id
                    JOIN activities a ON dp.activity_id = a.id
                    {tag_join}
                    WHERE {where_sql} AND dp.{segment_by} IS NOT NULL
                    GROUP BY a.quarter, dp.{segment_by}
                    ORDER BY a.quarter, dp.{segment_by}
                """
            else:
                query = f"""
                    SELECT
                        a.quarter,
                        'Overall' as segment_value,
                        AVG(p.pre_score) as avg_pre_score,
                        AVG(p.post_score) as avg_post_score,
                        SUM(COALESCE(p.pre_n, 0)) as total_n
                    FROM questions q
                    JOIN question_activities qa ON q.id = qa.question_id
                    JOIN activities a ON qa.activity_id = a.id
                    LEFT JOIN performance p ON q.id = p.question_id AND p.segment = 'overall'
                    {tag_join}
                    WHERE {where_sql}
                    GROUP BY a.quarter
                    ORDER BY a.quarter
                """

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "quarter": row["quarter"],
                    "segment_value": row["segment_value"],
                    "avg_pre_score": round(row["avg_pre_score"], 1) if row["avg_pre_score"] else None,
                    "avg_post_score": round(row["avg_post_score"], 1) if row["avg_post_score"] else None,
                    "total_n": row["total_n"] or 0
                })

            return results

    def get_demographic_options(self) -> Dict[str, List[str]]:
        """Get available demographic filter options."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            options = {}

            cursor.execute("""
                SELECT DISTINCT specialty FROM demographic_performance
                WHERE specialty IS NOT NULL AND specialty != ''
                ORDER BY specialty
            """)
            options["specialties"] = [row["specialty"] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT practice_setting FROM demographic_performance
                WHERE practice_setting IS NOT NULL AND practice_setting != ''
                ORDER BY practice_setting
            """)
            options["practice_settings"] = [row["practice_setting"] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT region FROM demographic_performance
                WHERE region IS NOT NULL AND region != ''
                ORDER BY region
            """)
            options["regions"] = [row["region"] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT practice_state FROM demographic_performance
                WHERE practice_state IS NOT NULL AND practice_state != ''
                ORDER BY practice_state
            """)
            options["practice_states"] = [row["practice_state"] for row in cursor.fetchall()]

            return options

    def list_activities(
        self,
        quarter: Optional[str] = None,
        has_date: Optional[bool] = None
    ) -> List[Dict]:
        """List all activities with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if quarter:
                where_clauses.append("a.quarter = ?")
                params.append(quarter)

            if has_date is True:
                where_clauses.append("a.activity_date IS NOT NULL")
            elif has_date is False:
                where_clauses.append("a.activity_date IS NULL")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            cursor.execute(f"""
                SELECT a.*,
                    (SELECT COUNT(DISTINCT question_id) FROM question_activities WHERE activity_id = a.id) as question_count
                FROM activities a
                WHERE {where_sql}
                ORDER BY a.activity_date DESC NULLS LAST, a.activity_name
            """, params)

            return [dict(row) for row in cursor.fetchall()]


# Singleton instance for reuse across function invocations
_db_instance: Optional[DatabaseService] = None


def get_database() -> DatabaseService:
    """Get or create database service singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
    return _db_instance
