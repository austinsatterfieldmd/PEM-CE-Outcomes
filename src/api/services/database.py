"""
Database service for SQLite operations.

V3 - Updated for new project structure with voting and review tables.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import date

logger = logging.getLogger(__name__)

# Default database path - relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "databases" / "questions.db"

# Region mapping for US states
STATE_TO_REGION = {
    # West Coast
    'WA': 'West Coast', 'OR': 'West Coast', 'CA': 'West Coast', 'NV': 'West Coast',
    'AK': 'West Coast', 'HI': 'West Coast',
    # Midwest
    'MT': 'Midwest', 'ID': 'Midwest', 'WY': 'Midwest', 'ND': 'Midwest', 'SD': 'Midwest',
    'NE': 'Midwest', 'KS': 'Midwest', 'MN': 'Midwest', 'IA': 'Midwest', 'MO': 'Midwest',
    'WI': 'Midwest', 'IL': 'Midwest', 'MI': 'Midwest', 'IN': 'Midwest', 'OH': 'Midwest',
    'CO': 'Midwest', 'UT': 'Midwest',
    # Northeast
    'ME': 'Northeast', 'NH': 'Northeast', 'VT': 'Northeast', 'MA': 'Northeast',
    'RI': 'Northeast', 'CT': 'Northeast', 'NY': 'Northeast', 'NJ': 'Northeast',
    'PA': 'Northeast', 'DE': 'Northeast', 'MD': 'Northeast', 'DC': 'Northeast',
    # Southeast
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


class DatabaseService:
    """SQLite database service for question data."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        """Initialize database service."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema if needed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if tables exist (basic check)
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='questions'
            """)
            if cursor.fetchone():
                logger.info(f"Database already initialized at {self.db_path}")
                return

            # If database is empty, log a warning
            logger.warning(f"Database at {self.db_path} appears to be empty. Run migrations to initialize.")

    # ============== Question Operations ==============

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
        max_confidence: Optional[float] = None,
        has_performance_data: Optional[bool] = None,
        min_sample_size: Optional[int] = None,
        needs_review: Optional[bool] = None,
        review_flag_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "id",
        sort_desc: bool = False
    ) -> Tuple[List[Dict], int]:
        """
        Search questions with filters.
        Returns (questions, total_count).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build query
            select_fields = """
                q.id, q.question_stem, t.topic, t.topic_confidence,
                t.disease_state, t.disease_state_confidence, t.treatment,
                p.pre_score, p.post_score, p.pre_n, p.post_n,
                (SELECT COUNT(*) FROM question_activities qa WHERE qa.question_id = q.id) as activity_count
            """

            from_clause = """
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                LEFT JOIN performance p ON q.id = p.question_id AND p.segment = 'overall'
            """

            where_clauses = []
            params = []

            # Always filter out non-oncology questions by default
            where_clauses.append("(q.is_oncology IS NULL OR q.is_oncology = 1)")

            # Full-text search
            if query:
                where_clauses.append("q.id IN (SELECT rowid FROM questions_fts WHERE questions_fts MATCH ?)")
                params.append(query)

            # Tag filters
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
                where_clauses.append("t.overall_confidence >= ?")
                params.append(min_confidence)

            if max_confidence is not None:
                where_clauses.append("t.overall_confidence <= ?")
                params.append(max_confidence)

            if has_performance_data is True:
                where_clauses.append("p.pre_n IS NOT NULL AND p.pre_n > 0 AND p.post_n IS NOT NULL AND p.post_n > 0")
            elif has_performance_data is False:
                where_clauses.append("(p.pre_n IS NULL OR p.pre_n = 0 OR p.post_n IS NULL OR p.post_n = 0)")

            if min_sample_size is not None:
                where_clauses.append("(COALESCE(p.pre_n, 0) + COALESCE(p.post_n, 0)) >= ?")
                params.append(min_sample_size)

            if needs_review is True:
                where_clauses.append("t.needs_review = 1")
            elif needs_review is False:
                where_clauses.append("(t.needs_review IS NULL OR t.needs_review = 0)")

            # Filter by review flag type
            if review_flag_filter:
                where_clauses.append("(t.review_flags LIKE ? OR t.review_flags LIKE ? OR t.review_flags LIKE ?)")
                params.extend([
                    f'["{review_flag_filter}"%',
                    f'%"{review_flag_filter}"%',
                    f'%"{review_flag_filter}"]'
                ])

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
                "confidence": "t.overall_confidence",
                "sample_size": "(COALESCE(p.pre_n, 0) + COALESCE(p.post_n, 0))",
                "flagged_at": "t.flagged_at"
            }.get(sort_by, "q.id")

            sort_direction = "DESC" if sort_desc else "ASC"

            # Get paginated results
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT DISTINCT {select_fields}
                {from_clause}
                WHERE {where_sql}
                ORDER BY {sort_column} {sort_direction}
                LIMIT ? OFFSET ?
            """
            query_params = params + [page_size, offset]

            cursor.execute(query_sql, query_params)
            rows = cursor.fetchall()

            questions = []
            for row in rows:
                pre_score = row["pre_score"]
                post_score = row["post_score"]
                pre_n = row["pre_n"]
                post_n = row["post_n"]
                knowledge_gain = None
                if pre_score is not None and post_score is not None:
                    knowledge_gain = post_score - pre_score
                sample_size = None
                if pre_n is not None or post_n is not None:
                    sample_size = (pre_n or 0) + (post_n or 0)

                questions.append({
                    "id": row["id"],
                    "question_stem": row["question_stem"],
                    "topic": row["topic"],
                    "topic_confidence": row["topic_confidence"],
                    "disease_state": row["disease_state"],
                    "disease_state_confidence": row["disease_state_confidence"],
                    "treatment": row["treatment"],
                    "pre_score": pre_score,
                    "post_score": post_score,
                    "knowledge_gain": knowledge_gain,
                    "sample_size": sample_size,
                    "activity_count": row["activity_count"]
                })

            return questions, total

    def get_question_detail(self, question_id: int) -> Optional[Dict]:
        """Get full question details by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get question
            cursor.execute("""
                SELECT q.*, t.*
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                WHERE q.id = ?
            """, (question_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # Get performance data
            cursor.execute("""
                SELECT segment, pre_score, post_score, pre_n, post_n
                FROM performance
                WHERE question_id = ?
            """, (question_id,))
            performance = [dict(r) for r in cursor.fetchall()]

            # Get activities
            cursor.execute("""
                SELECT activity_name
                FROM question_activities
                WHERE question_id = ?
            """, (question_id,))
            activities = [r["activity_name"] for r in cursor.fetchall()]

            # Parse incorrect answers
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
                    "disease_stage_confidence": row["disease_stage_confidence"] if "disease_stage_confidence" in row.keys() else None,
                    "disease_type": row["disease_type"],
                    "disease_type_confidence": row["disease_type_confidence"] if "disease_type_confidence" in row.keys() else None,
                    "treatment_line": row["treatment_line"] if "treatment_line" in row.keys() else None,
                    "treatment_line_confidence": row["treatment_line_confidence"] if "treatment_line_confidence" in row.keys() else None,
                    "treatment": row["treatment"],
                    "treatment_confidence": row["treatment_confidence"],
                    "biomarker": row["biomarker"],
                    "biomarker_confidence": row["biomarker_confidence"] if "biomarker_confidence" in row.keys() else None,
                    "trial": row["trial"],
                    "trial_confidence": row["trial_confidence"] if "trial_confidence" in row.keys() else None,
                    "overall_confidence": row["overall_confidence"] if "overall_confidence" in row.keys() else None,
                    "needs_review": row["needs_review"] if "needs_review" in row.keys() else False,
                    "review_flags": json.loads(row["review_flags"]) if ("review_flags" in row.keys() and row["review_flags"]) else None,
                    "flagged_at": row["flagged_at"] if "flagged_at" in row.keys() else None
                },
                "performance": performance,
                "activities": activities
            }

    def insert_tags(
        self,
        question_id: int,
        topic: Optional[str] = None,
        topic_confidence: Optional[float] = None,
        topic_method: Optional[str] = None,
        disease_state: Optional[str] = None,
        disease_state_confidence: Optional[float] = None,
        disease_stage: Optional[str] = None,
        disease_stage_confidence: Optional[float] = None,
        disease_type: Optional[str] = None,
        disease_type_confidence: Optional[float] = None,
        treatment_line: Optional[str] = None,
        treatment_line_confidence: Optional[float] = None,
        treatment: Optional[str] = None,
        treatment_confidence: Optional[float] = None,
        biomarker: Optional[str] = None,
        biomarker_confidence: Optional[float] = None,
        trial: Optional[str] = None,
        trial_confidence: Optional[float] = None,
        review_flags: Optional[List[str]] = None,
        needs_review: bool = False,
        overall_confidence: Optional[float] = None,
        llm_calls_made: int = 0
    ):
        """Insert or update tags for a question."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tags
                (question_id, topic, topic_confidence, topic_method,
                 disease_state, disease_state_confidence,
                 disease_stage, disease_stage_confidence,
                 disease_type, disease_type_confidence,
                 treatment_line, treatment_line_confidence,
                 treatment, treatment_confidence,
                 biomarker, biomarker_confidence,
                 trial, trial_confidence,
                 review_flags, needs_review, overall_confidence, llm_calls_made,
                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                question_id, topic, topic_confidence, topic_method,
                disease_state, disease_state_confidence,
                disease_stage, disease_stage_confidence,
                disease_type, disease_type_confidence,
                treatment_line, treatment_line_confidence,
                treatment, treatment_confidence,
                biomarker, biomarker_confidence,
                trial, trial_confidence,
                json.dumps(review_flags) if review_flags else None,
                needs_review, overall_confidence, llm_calls_made
            ))
            conn.commit()

    def update_question_stem(self, question_id: int, new_question_stem: str):
        """Update the question stem for a question (admin only)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE questions
                SET question_stem = ?
                WHERE id = ?
            """, (new_question_stem, question_id))
            conn.commit()

    def flag_question(self, question_id: int, flag_reasons: List[str]):
        """Flag a question for review with specific reasons."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT review_flags, flagged_at FROM tags WHERE question_id = ?", (question_id,))
            row = cursor.fetchone()

            existing_flags = []
            already_flagged = False
            if row:
                if row["review_flags"]:
                    try:
                        existing_flags = json.loads(row["review_flags"])
                    except:
                        existing_flags = []
                already_flagged = row["flagged_at"] is not None

            all_flags = list(set(existing_flags + flag_reasons))

            if row:
                if already_flagged:
                    cursor.execute("""
                        UPDATE tags
                        SET review_flags = ?,
                            needs_review = 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE question_id = ?
                    """, (json.dumps(all_flags), question_id))
                else:
                    cursor.execute("""
                        UPDATE tags
                        SET review_flags = ?,
                            needs_review = 1,
                            flagged_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE question_id = ?
                    """, (json.dumps(all_flags), question_id))
            else:
                cursor.execute("""
                    INSERT INTO tags (question_id, review_flags, needs_review, flagged_at, updated_at)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (question_id, json.dumps(all_flags)))

            conn.commit()

    def update_question_oncology_status(self, question_id: int, is_oncology: bool):
        """Mark a question as oncology or non-oncology."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(questions)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'is_oncology' not in columns:
                cursor.execute("""
                    ALTER TABLE questions
                    ADD COLUMN is_oncology INTEGER DEFAULT 1
                """)

            cursor.execute("""
                UPDATE questions
                SET is_oncology = ?
                WHERE id = ?
            """, (1 if is_oncology else 0, question_id))
            conn.commit()

    # ============== Filter Options ==============

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

    # ============== Statistics ==============

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM questions")
            total_questions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tags WHERE topic IS NOT NULL")
            tagged_questions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT activity_name) FROM question_activities")
            total_activities = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM tags t
                JOIN questions q ON t.question_id = q.id
                WHERE t.needs_review = 1
                AND (q.is_oncology IS NULL OR q.is_oncology = 1)
            """)
            questions_need_review = cursor.fetchone()[0]

            return {
                "total_questions": total_questions,
                "tagged_questions": tagged_questions,
                "total_activities": total_activities,
                "questions_need_review": questions_need_review
            }

    # ============== Export ==============

    def get_questions_for_export(
        self,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        disease_stages: Optional[List[str]] = None,
        disease_types: Optional[List[str]] = None,
        treatment_lines: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
        trials: Optional[List[str]] = None,
        activities: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Get questions matching filters with full details for Excel export."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["(q.is_oncology IS NULL OR q.is_oncology = 1)"]
            params = []

            if topics:
                ph = ",".join("?" * len(topics))
                where_clauses.append(f"t.topic IN ({ph})")
                params.extend(topics)

            if disease_states:
                ph = ",".join("?" * len(disease_states))
                where_clauses.append(f"t.disease_state IN ({ph})")
                params.extend(disease_states)

            if disease_stages:
                ph = ",".join("?" * len(disease_stages))
                where_clauses.append(f"t.disease_stage IN ({ph})")
                params.extend(disease_stages)

            if disease_types:
                ph = ",".join("?" * len(disease_types))
                where_clauses.append(f"t.disease_type IN ({ph})")
                params.extend(disease_types)

            if treatment_lines:
                ph = ",".join("?" * len(treatment_lines))
                where_clauses.append(f"t.treatment_line IN ({ph})")
                params.extend(treatment_lines)

            if treatments:
                ph = ",".join("?" * len(treatments))
                where_clauses.append(f"t.treatment IN ({ph})")
                params.extend(treatments)

            if biomarkers:
                ph = ",".join("?" * len(biomarkers))
                where_clauses.append(f"t.biomarker IN ({ph})")
                params.extend(biomarkers)

            if trials:
                ph = ",".join("?" * len(trials))
                where_clauses.append(f"t.trial IN ({ph})")
                params.extend(trials)

            activity_join = ""
            if activities:
                activity_join = "JOIN question_activities qa ON q.id = qa.question_id"
                ph = ",".join("?" * len(activities))
                where_clauses.append(f"qa.activity_name IN ({ph})")
                params.extend(activities)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT DISTINCT
                    q.id,
                    q.question_stem,
                    q.correct_answer,
                    q.incorrect_answers,
                    t.topic,
                    t.disease_state,
                    t.disease_type,
                    t.disease_stage,
                    t.treatment,
                    t.treatment_line,
                    t.biomarker,
                    t.trial,
                    p.pre_score,
                    p.post_score,
                    p.pre_n as sample_size,
                    (SELECT GROUP_CONCAT(qa2.activity_name, '; ')
                     FROM question_activities qa2
                     WHERE qa2.question_id = q.id) as activities
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                LEFT JOIN performance p ON q.id = p.question_id AND p.segment = 'overall'
                {activity_join}
                WHERE {where_sql}
                ORDER BY q.id
            """

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                knowledge_gain = None
                if row["pre_score"] is not None and row["post_score"] is not None:
                    knowledge_gain = round(row["post_score"] - row["pre_score"], 1)

                results.append({
                    "id": row["id"],
                    "question_stem": row["question_stem"],
                    "correct_answer": row["correct_answer"],
                    "incorrect_answers": row["incorrect_answers"],
                    "topic": row["topic"],
                    "disease_state": row["disease_state"],
                    "disease_type": row["disease_type"],
                    "disease_stage": row["disease_stage"],
                    "treatment": row["treatment"],
                    "treatment_line": row["treatment_line"],
                    "biomarker": row["biomarker"],
                    "trial": row["trial"],
                    "pre_score": row["pre_score"],
                    "post_score": row["post_score"],
                    "knowledge_gain": knowledge_gain,
                    "sample_size": row["sample_size"],
                    "activities": row["activities"]
                })

            return results

    # ============== Aggregation Operations for Reports ==============

    def aggregate_performance_by_tag(
        self,
        group_by: str,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        disease_stages: Optional[List[str]] = None,
        disease_types: Optional[List[str]] = None,
        treatment_lines: Optional[List[str]] = None,
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

    def aggregate_performance_by_segment(
        self,
        segments: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        disease_stages: Optional[List[str]] = None,
        disease_types: Optional[List[str]] = None,
        treatment_lines: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
        trials: Optional[List[str]] = None,
        activities: Optional[List[str]] = None,
        quarters: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Aggregate performance metrics grouped by audience segment."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            valid_segments = [
                'overall', 'medical_oncologist', 'app', 'academic',
                'community', 'surgical_oncologist', 'radiation_oncologist'
            ]

            target_segments = segments if segments else valid_segments
            target_segments = [s for s in target_segments if s in valid_segments]

            if not target_segments:
                return []

            where_clauses = []
            params = []

            placeholders = ",".join("?" * len(target_segments))
            where_clauses.append(f"p.segment IN ({placeholders})")
            params.extend(target_segments)

            tag_join = ""
            if any([topics, disease_states, disease_stages, disease_types, treatment_lines, treatments, biomarkers, trials]):
                tag_join = "JOIN tags t ON q.id = t.question_id"

                if topics:
                    ph = ",".join("?" * len(topics))
                    where_clauses.append(f"t.topic IN ({ph})")
                    params.extend(topics)

                if disease_states:
                    ph = ",".join("?" * len(disease_states))
                    where_clauses.append(f"t.disease_state IN ({ph})")
                    params.extend(disease_states)

                if disease_stages:
                    ph = ",".join("?" * len(disease_stages))
                    where_clauses.append(f"t.disease_stage IN ({ph})")
                    params.extend(disease_stages)

                if disease_types:
                    ph = ",".join("?" * len(disease_types))
                    where_clauses.append(f"t.disease_type IN ({ph})")
                    params.extend(disease_types)

                if treatment_lines:
                    ph = ",".join("?" * len(treatment_lines))
                    where_clauses.append(f"t.treatment_line IN ({ph})")
                    params.extend(treatment_lines)

                if treatments:
                    ph = ",".join("?" * len(treatments))
                    where_clauses.append(f"t.treatment IN ({ph})")
                    params.extend(treatments)

                if biomarkers:
                    ph = ",".join("?" * len(biomarkers))
                    where_clauses.append(f"t.biomarker IN ({ph})")
                    params.extend(biomarkers)

                if trials:
                    ph = ",".join("?" * len(trials))
                    where_clauses.append(f"t.trial IN ({ph})")
                    params.extend(trials)

            activity_join = ""
            if activities or quarters:
                activity_join = "JOIN question_activities qa ON q.id = qa.question_id"
                if activities:
                    ph = ",".join("?" * len(activities))
                    where_clauses.append(f"qa.activity_name IN ({ph})")
                    params.extend(activities)
                if quarters:
                    ph = ",".join("?" * len(quarters))
                    where_clauses.append(f"qa.quarter IN ({ph})")
                    params.extend(quarters)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT
                    p.segment as segment,
                    AVG(p.pre_score) as avg_pre_score,
                    AVG(p.post_score) as avg_post_score,
                    SUM(COALESCE(p.pre_n, 0)) as total_pre_n,
                    SUM(COALESCE(p.post_n, 0)) as total_post_n,
                    COUNT(DISTINCT q.id) as question_count
                FROM questions q
                JOIN performance p ON q.id = p.question_id
                {tag_join}
                {activity_join}
                WHERE {where_sql}
                GROUP BY p.segment
                ORDER BY
                    CASE p.segment
                        WHEN 'overall' THEN 1
                        WHEN 'medical_oncologist' THEN 2
                        WHEN 'app' THEN 3
                        WHEN 'academic' THEN 4
                        WHEN 'community' THEN 5
                        WHEN 'surgical_oncologist' THEN 6
                        WHEN 'radiation_oncologist' THEN 7
                        ELSE 8
                    END
            """

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "segment": row["segment"],
                    "avg_pre_score": round(row["avg_pre_score"], 1) if row["avg_pre_score"] else None,
                    "avg_post_score": round(row["avg_post_score"], 1) if row["avg_post_score"] else None,
                    "total_pre_n": row["total_pre_n"] or 0,
                    "total_post_n": row["total_post_n"] or 0,
                    "question_count": row["question_count"]
                })

            return results

    def get_available_segments(self) -> List[Dict[str, Any]]:
        """Get list of audience segments that have data, with counts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT segment, COUNT(DISTINCT question_id) as question_count
                FROM performance
                WHERE pre_score IS NOT NULL OR post_score IS NOT NULL
                GROUP BY segment
                ORDER BY question_count DESC
            """)
            return [{"segment": row["segment"], "count": row["question_count"]} for row in cursor.fetchall()]

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

    def get_available_quarters(self) -> List[str]:
        """Get list of quarters that have activities."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT quarter FROM activities
                WHERE quarter IS NOT NULL
                ORDER BY quarter DESC
            """)
            return [row["quarter"] for row in cursor.fetchall()]

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

    def get_activity(self, activity_id: int) -> Optional[Dict]:
        """Get activity by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*,
                    (SELECT COUNT(DISTINCT question_id) FROM question_activities WHERE activity_id = a.id) as question_count
                FROM activities a
                WHERE a.id = ?
            """, (activity_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_activity_metadata(
        self,
        activity_name: str,
        activity_date: Optional[date] = None,
        target_audience: Optional[str] = None,
        description: Optional[str] = None
    ) -> int:
        """Insert or update activity metadata. Returns activity ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            quarter = get_quarter_from_date(activity_date) if activity_date else None

            cursor.execute("""
                INSERT INTO activities (activity_name, activity_date, quarter, target_audience, description)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(activity_name) DO UPDATE SET
                    activity_date = COALESCE(excluded.activity_date, activities.activity_date),
                    quarter = COALESCE(excluded.quarter, activities.quarter),
                    target_audience = COALESCE(excluded.target_audience, activities.target_audience),
                    description = COALESCE(excluded.description, activities.description)
            """, (activity_name, activity_date, quarter, target_audience, description))

            cursor.execute("SELECT id FROM activities WHERE activity_name = ?", (activity_name,))
            activity_id = cursor.fetchone()["id"]

            cursor.execute("""
                UPDATE question_activities SET activity_id = ? WHERE activity_name = ?
            """, (activity_id, activity_name))

            conn.commit()
            return activity_id

    # ============== Novel Entity Operations ==============

    def list_novel_entities(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        min_occurrences: Optional[int] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "occurrence_count",
        sort_desc: bool = True
    ) -> Tuple[List[Dict], int]:
        """List novel entities with filters and pagination."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if status:
                where_clauses.append("status = ?")
                params.append(status)

            if entity_type:
                where_clauses.append("entity_type = ?")
                params.append(entity_type)

            if min_confidence is not None:
                where_clauses.append("confidence >= ?")
                params.append(min_confidence)

            if min_occurrences is not None:
                where_clauses.append("occurrence_count >= ?")
                params.append(min_occurrences)

            if search_query:
                where_clauses.append("(entity_name LIKE ? OR normalized_name LIKE ?)")
                search_pattern = f"%{search_query}%"
                params.extend([search_pattern, search_pattern])

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            cursor.execute(f"SELECT COUNT(*) FROM novel_entities WHERE {where_sql}", params)
            total = cursor.fetchone()[0]

            sort_column = {
                "occurrence_count": "occurrence_count",
                "confidence": "confidence",
                "first_seen": "first_seen",
                "last_seen": "last_seen",
                "entity_name": "entity_name",
                "entity_type": "entity_type"
            }.get(sort_by, "occurrence_count")

            sort_direction = "DESC" if sort_desc else "ASC"
            offset = (page - 1) * page_size

            cursor.execute(f"""
                SELECT * FROM novel_entities
                WHERE {where_sql}
                ORDER BY {sort_column} {sort_direction}
                LIMIT ? OFFSET ?
            """, params + [page_size, offset])

            entities = []
            for row in cursor.fetchall():
                entity = dict(row)
                if entity.get("synonyms"):
                    try:
                        entity["synonyms"] = json.loads(entity["synonyms"])
                    except json.JSONDecodeError:
                        entity["synonyms"] = []
                else:
                    entity["synonyms"] = []
                entities.append(entity)

            return entities, total

    def get_novel_entity_detail(self, entity_id: int) -> Optional[Dict]:
        """Get full novel entity details including all occurrences."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM novel_entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if not row:
                return None

            entity = dict(row)

            if entity.get("synonyms"):
                try:
                    entity["synonyms"] = json.loads(entity["synonyms"])
                except json.JSONDecodeError:
                    entity["synonyms"] = []
            else:
                entity["synonyms"] = []

            cursor.execute("""
                SELECT neo.*, q.question_stem, q.correct_answer
                FROM novel_entity_occurrences neo
                LEFT JOIN questions q ON neo.question_id = q.id
                WHERE neo.novel_entity_id = ?
                ORDER BY neo.created_at DESC
            """, (entity_id,))

            occurrences = []
            for occ_row in cursor.fetchall():
                occurrences.append({
                    "id": occ_row["id"],
                    "question_id": occ_row["question_id"],
                    "source_text": occ_row["source_text"],
                    "extraction_confidence": occ_row["extraction_confidence"],
                    "created_at": occ_row["created_at"],
                    "question_stem": occ_row["question_stem"][:200] + "..." if occ_row["question_stem"] and len(occ_row["question_stem"]) > 200 else occ_row["question_stem"],
                    "correct_answer": occ_row["correct_answer"]
                })

            entity["occurrences"] = occurrences
            return entity

    def get_novel_entity_stats(self) -> Dict[str, Any]:
        """Get statistics about novel entities."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM novel_entities
                GROUP BY status
            """)
            status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM novel_entities
                WHERE status = 'pending'
                GROUP BY entity_type
            """)
            pending_by_type = {row["entity_type"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT COUNT(*) FROM novel_entities
                WHERE status = 'pending'
                AND confidence >= 0.90
                AND occurrence_count >= 3
            """)
            ready_for_auto_approve = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM novel_entities
                WHERE first_seen >= datetime('now', '-7 days')
            """)
            new_last_7_days = cursor.fetchone()[0]

            return {
                "total": sum(status_counts.values()),
                "pending": status_counts.get("pending", 0),
                "approved": status_counts.get("approved", 0),
                "auto_approved": status_counts.get("auto_approved", 0),
                "rejected": status_counts.get("rejected", 0),
                "pending_by_type": pending_by_type,
                "ready_for_auto_approve": ready_for_auto_approve,
                "new_last_7_days": new_last_7_days
            }

    def approve_novel_entity(
        self,
        entity_id: int,
        reviewed_by: str,
        drug_class: Optional[str] = None,
        synonyms: Optional[List[str]] = None,
        auto_approved: bool = False
    ) -> bool:
        """Approve a novel entity for addition to KB."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            status = "auto_approved" if auto_approved else "approved"
            synonyms_json = json.dumps(synonyms) if synonyms else None

            cursor.execute("""
                UPDATE novel_entities
                SET status = ?,
                    reviewed_by = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    drug_class = COALESCE(?, drug_class),
                    synonyms = COALESCE(?, synonyms)
                WHERE id = ?
            """, (status, reviewed_by, drug_class, synonyms_json, entity_id))

            conn.commit()
            return cursor.rowcount > 0

    def reject_novel_entity(
        self,
        entity_id: int,
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """Reject a novel entity."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE novel_entities
                SET status = 'rejected',
                    reviewed_by = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    notes = COALESCE(?, notes)
                WHERE id = ?
            """, (reviewed_by, notes, entity_id))

            conn.commit()
            return cursor.rowcount > 0

    def bulk_approve_novel_entities(
        self,
        min_confidence: float = 0.90,
        min_occurrences: int = 3,
        reviewed_by: str = "auto"
    ) -> int:
        """Auto-approve entities meeting confidence and occurrence thresholds."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE novel_entities
                SET status = 'auto_approved',
                    reviewed_by = ?,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE status = 'pending'
                AND confidence >= ?
                AND occurrence_count >= ?
            """, (reviewed_by, min_confidence, min_occurrences))

            approved_count = cursor.rowcount
            conn.commit()
            return approved_count

    def get_approved_entities_for_kb(
        self,
        entity_type: Optional[str] = None
    ) -> List[Dict]:
        """Get all approved entities ready to be added to KB."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["status IN ('approved', 'auto_approved')"]
            params = []

            if entity_type:
                where_clauses.append("entity_type = ?")
                params.append(entity_type)

            where_sql = " AND ".join(where_clauses)

            cursor.execute(f"""
                SELECT entity_name, normalized_name, entity_type, drug_class, synonyms
                FROM novel_entities
                WHERE {where_sql}
                ORDER BY entity_type, entity_name
            """, params)

            entities = []
            for row in cursor.fetchall():
                entity = dict(row)
                if entity.get("synonyms"):
                    try:
                        entity["synonyms"] = json.loads(entity["synonyms"])
                    except json.JSONDecodeError:
                        entity["synonyms"] = []
                else:
                    entity["synonyms"] = []
                entities.append(entity)

            return entities


    # ============== V3 Voting Results Operations ==============

    def save_voting_result(
        self,
        question_id: int,
        iteration: int,
        prompt_version: str,
        gpt_tags: Dict,
        claude_tags: Dict,
        gemini_tags: Dict,
        aggregated_tags: Dict,
        agreement_level: str,
        needs_review: bool,
        web_searches: Optional[List[Dict]] = None
    ) -> int:
        """Save a voting result from 3-model tagging."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO voting_results
                (question_id, iteration, prompt_version, gpt_tags, claude_tags, gemini_tags,
                 aggregated_tags, agreement_level, needs_review, web_searches, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                question_id, iteration, prompt_version,
                json.dumps(gpt_tags), json.dumps(claude_tags), json.dumps(gemini_tags),
                json.dumps(aggregated_tags), agreement_level, needs_review,
                json.dumps(web_searches) if web_searches else None
            ))
            conn.commit()
            return cursor.lastrowid

    def get_voting_results(
        self,
        agreement_level: Optional[str] = None,
        needs_review: Optional[bool] = None,
        iteration: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """Get voting results with filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if agreement_level:
                where_clauses.append("agreement_level = ?")
                params.append(agreement_level)

            if needs_review is not None:
                where_clauses.append("needs_review = ?")
                params.append(1 if needs_review else 0)

            if iteration is not None:
                where_clauses.append("iteration = ?")
                params.append(iteration)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM voting_results WHERE {where_sql}", params)
            total = cursor.fetchone()[0]

            # Get paginated results
            cursor.execute(f"""
                SELECT * FROM voting_results
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                for field in ['gpt_tags', 'claude_tags', 'gemini_tags', 'aggregated_tags', 'web_searches']:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except json.JSONDecodeError:
                            result[field] = {}
                results.append(result)

            return results, total

    def get_voting_result_by_id(self, result_id: int) -> Optional[Dict]:
        """Get a single voting result by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM voting_results WHERE id = ?", (result_id,))
            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)
            for field in ['gpt_tags', 'claude_tags', 'gemini_tags', 'aggregated_tags', 'web_searches']:
                if result.get(field):
                    try:
                        result[field] = json.loads(result[field])
                    except json.JSONDecodeError:
                        result[field] = {}
            return result

    def get_voting_results_for_question(self, question_id: int) -> List[Dict]:
        """Get all voting results for a question across iterations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM voting_results
                WHERE question_id = ?
                ORDER BY iteration DESC, created_at DESC
            """, (question_id,))

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                for field in ['gpt_tags', 'claude_tags', 'gemini_tags', 'aggregated_tags', 'web_searches']:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except json.JSONDecodeError:
                            result[field] = {}
                results.append(result)
            return results

    def count_voting_results(
        self,
        agreement_level: Optional[str] = None,
        needs_review: Optional[bool] = None
    ) -> int:
        """Count voting results with filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if agreement_level:
                where_clauses.append("agreement_level = ?")
                params.append(agreement_level)

            if needs_review is not None:
                where_clauses.append("needs_review = ?")
                params.append(1 if needs_review else 0)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            cursor.execute(f"SELECT COUNT(*) FROM voting_results WHERE {where_sql}", params)
            return cursor.fetchone()[0]

    def mark_voting_result_reviewed(self, result_id: int) -> bool:
        """Mark a voting result as reviewed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE voting_results
                SET needs_review = 0
                WHERE id = ?
            """, (result_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_tagging_statistics(self) -> Dict[str, Any]:
        """Get tagging statistics across all iterations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total tagged
            cursor.execute("SELECT COUNT(*) FROM voting_results")
            total_tagged = cursor.fetchone()[0]

            # By agreement level
            cursor.execute("""
                SELECT agreement_level, COUNT(*) as count
                FROM voting_results
                GROUP BY agreement_level
            """)
            by_agreement = {row["agreement_level"]: row["count"] for row in cursor.fetchall()}

            # By iteration
            cursor.execute("""
                SELECT iteration, COUNT(*) as count
                FROM voting_results
                GROUP BY iteration
            """)
            by_iteration = {row["iteration"]: row["count"] for row in cursor.fetchall()}

            # Review pending
            cursor.execute("SELECT COUNT(*) FROM voting_results WHERE needs_review = 1")
            review_pending = cursor.fetchone()[0]

            return {
                "total_tagged": total_tagged,
                "by_agreement": by_agreement,
                "by_iteration": by_iteration,
                "review_pending": review_pending,
                "total_api_cost": total_tagged * 0.12,  # Rough estimate
                "avg_cost_per_question": 0.12
            }

    def get_model_agreement_statistics(self) -> Dict[str, Any]:
        """Get model agreement statistics."""
        # This would require more detailed per-field analysis
        # For now return placeholder
        return {
            "pairwise_agreement": {
                "gpt_claude": 0.0,
                "gpt_gemini": 0.0,
                "claude_gemini": 0.0
            },
            "model_accuracy": {
                "gpt": {"correct": 0, "total": 0, "rate": 0.0},
                "claude": {"correct": 0, "total": 0, "rate": 0.0},
                "gemini": {"correct": 0, "total": 0, "rate": 0.0}
            },
            "common_disagreements": []
        }

    def get_random_unanimous_questions(self, count: int) -> List[Dict]:
        """Get random sample of unanimous questions for spot-checking."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT vr.*, q.question_stem, q.correct_answer
                FROM voting_results vr
                JOIN questions q ON vr.question_id = q.id
                WHERE vr.agreement_level = 'unanimous'
                ORDER BY RANDOM()
                LIMIT ?
            """, (count,))

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                for field in ['gpt_tags', 'claude_tags', 'gemini_tags', 'aggregated_tags']:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except json.JSONDecodeError:
                            result[field] = {}
                results.append(result)
            return results

    # ============== V3 Review Corrections Operations ==============

    def save_review_correction(
        self,
        question_id: int,
        iteration: int,
        original_tags: Dict,
        corrected_tags: Dict,
        disagreement_category: Optional[str] = None,
        reviewer_notes: Optional[str] = None
    ) -> int:
        """Save a human correction for a question."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO review_corrections
                (question_id, iteration, original_tags, corrected_tags,
                 disagreement_category, reviewer_notes, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                question_id, iteration,
                json.dumps(original_tags), json.dumps(corrected_tags),
                disagreement_category, reviewer_notes
            ))
            conn.commit()
            return cursor.lastrowid

    def get_review_corrections(
        self,
        iteration: Optional[int] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """Get review corrections with filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if iteration is not None:
                where_clauses.append("iteration = ?")
                params.append(iteration)

            if category:
                where_clauses.append("disagreement_category = ?")
                params.append(category)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM review_corrections WHERE {where_sql}", params)
            total = cursor.fetchone()[0]

            # Get paginated results
            cursor.execute(f"""
                SELECT * FROM review_corrections
                WHERE {where_sql}
                ORDER BY reviewed_at DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                for field in ['original_tags', 'corrected_tags']:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except json.JSONDecodeError:
                            result[field] = {}
                results.append(result)

            return results, total

    def get_corrections_for_question(self, question_id: int) -> List[Dict]:
        """Get all corrections for a question."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM review_corrections
                WHERE question_id = ?
                ORDER BY reviewed_at DESC
            """, (question_id,))

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                for field in ['original_tags', 'corrected_tags']:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except json.JSONDecodeError:
                            result[field] = {}
                results.append(result)
            return results

    def update_question_tags(self, question_id: int, tags: Dict):
        """Update a question's tags from corrected values."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tags SET
                    topic = ?,
                    disease_state = ?,
                    disease_stage = ?,
                    disease_type = ?,
                    treatment_line = ?,
                    treatment = ?,
                    biomarker = ?,
                    trial = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE question_id = ?
            """, (
                tags.get("topic"),
                tags.get("disease_state"),
                tags.get("disease_stage"),
                tags.get("disease_type"),
                tags.get("treatment_line"),
                tags.get("treatment"),
                tags.get("biomarker"),
                tags.get("trial"),
                question_id
            ))
            conn.commit()

    def log_spot_check(self, question_id: int, is_correct: bool):
        """Log a spot check result."""
        # For now, just log - could track in separate table
        logger.info(f"Spot check for question {question_id}: {'correct' if is_correct else 'incorrect'}")

    # ============== V3 Disagreement Patterns Operations ==============

    def get_disagreement_patterns(
        self,
        iteration: Optional[int] = None,
        implemented: Optional[bool] = None
    ) -> Tuple[List[Dict], int]:
        """Get disagreement patterns with filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if iteration is not None:
                where_clauses.append("iteration = ?")
                params.append(iteration)

            if implemented is not None:
                where_clauses.append("implemented = ?")
                params.append(1 if implemented else 0)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            cursor.execute(f"SELECT COUNT(*) FROM disagreement_patterns WHERE {where_sql}", params)
            total = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT * FROM disagreement_patterns
                WHERE {where_sql}
                ORDER BY frequency DESC
            """, params)

            patterns = []
            for row in cursor.fetchall():
                pattern = dict(row)
                if pattern.get("example_questions"):
                    try:
                        pattern["example_questions"] = json.loads(pattern["example_questions"])
                    except json.JSONDecodeError:
                        pattern["example_questions"] = []
                patterns.append(pattern)

            return patterns, total

    def save_disagreement_pattern(
        self,
        iteration: int,
        category: str,
        frequency: int,
        example_questions: List[int],
        recommended_action: str
    ) -> int:
        """Save a disagreement pattern."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO disagreement_patterns
                (iteration, category, frequency, example_questions, recommended_action, implemented, created_at)
                VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            """, (
                iteration, category, frequency,
                json.dumps(example_questions), recommended_action
            ))
            conn.commit()
            return cursor.lastrowid

    def mark_pattern_implemented(self, pattern_id: int) -> bool:
        """Mark a pattern as implemented."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE disagreement_patterns
                SET implemented = 1
                WHERE id = ?
            """, (pattern_id,))
            conn.commit()
            return cursor.rowcount > 0


# Singleton instance
_db_instance: Optional[DatabaseService] = None


def get_database(db_path: Path = DEFAULT_DB_PATH) -> DatabaseService:
    """Get or create database service singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService(db_path)
    return _db_instance
