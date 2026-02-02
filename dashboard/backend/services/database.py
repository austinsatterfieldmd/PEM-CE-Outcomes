"""
Database service for SQLite operations.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import date

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "questions.db"

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

    @staticmethod
    def _str_to_bool(val):
        """Convert string boolean to actual boolean (database stores 'True'/'False' as strings)."""
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ('true', 'yes', '1', 't', 'y')
        return bool(val)

    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Questions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_question_id INTEGER,  -- Original question ID from source system
                    source_id INTEGER,           -- Source identifier (links to Snowflake)
                    question_stem TEXT NOT NULL,
                    correct_answer TEXT,
                    incorrect_answers TEXT,  -- JSON array
                    source_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tags table (one row per question)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    question_id INTEGER PRIMARY KEY,
                    topic TEXT,
                    topic_confidence REAL,
                    topic_method TEXT,
                    disease_state TEXT,
                    disease_state_confidence REAL,
                    disease_stage TEXT,
                    disease_stage_confidence REAL,
                    disease_type TEXT,
                    disease_type_confidence REAL,
                    treatment_line TEXT,
                    treatment_line_confidence REAL,
                    treatment TEXT,
                    treatment_confidence REAL,
                    biomarker TEXT,
                    biomarker_confidence REAL,
                    trial TEXT,
                    trial_confidence REAL,
                    review_flags TEXT,  -- JSON array: ['LLM_FALLBACK', 'LOW_CONFIDENCE', etc.]
                    needs_review BOOLEAN DEFAULT FALSE,
                    overall_confidence REAL,
                    llm_calls_made INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
                )
            """)

            # Migration: Add new columns if they don't exist (for existing DBs)
            # 70-field schema migration
            migration_columns = [
                # Existing columns
                ("disease_stage_confidence", "REAL"),
                ("disease_type_confidence", "REAL"),
                ("treatment_line", "TEXT"),
                ("treatment_line_confidence", "REAL"),
                ("biomarker_confidence", "REAL"),
                ("trial_confidence", "REAL"),
                ("review_flags", "TEXT"),
                ("needs_review", "BOOLEAN DEFAULT FALSE"),
                ("overall_confidence", "REAL"),
                ("llm_calls_made", "INTEGER DEFAULT 0"),
                ("flagged_at", "TIMESTAMP"),

                # === NEW 70-field schema columns ===
                # Core fields split/added
                ("disease_state_1", "TEXT"),  # Primary disease state (rare: supports 2 disease states)
                ("disease_state_2", "TEXT"),  # Secondary disease state (rare cases like MM + NHL)
                ("disease_type_1", "TEXT"),
                ("disease_type_2", "TEXT"),

                # Multi-value fields (treatment, biomarker, trial split into 5 slots each)
                ("treatment_1", "TEXT"),
                ("treatment_2", "TEXT"),
                ("treatment_3", "TEXT"),
                ("treatment_4", "TEXT"),
                ("treatment_5", "TEXT"),
                ("biomarker_1", "TEXT"),
                ("biomarker_2", "TEXT"),
                ("biomarker_3", "TEXT"),
                ("biomarker_4", "TEXT"),
                ("biomarker_5", "TEXT"),
                ("trial_1", "TEXT"),
                ("trial_2", "TEXT"),
                ("trial_3", "TEXT"),
                ("trial_4", "TEXT"),
                ("trial_5", "TEXT"),

                # Group B: Patient Characteristics (8 fields - added comorbidity_1/2/3)
                ("treatment_eligibility", "TEXT"),
                ("age_group", "TEXT"),
                ("organ_dysfunction", "TEXT"),
                ("fitness_status", "TEXT"),
                ("disease_specific_factor", "TEXT"),
                ("comorbidity_1", "TEXT"),
                ("comorbidity_2", "TEXT"),
                ("comorbidity_3", "TEXT"),

                # Group C: Treatment Metadata (10 fields)
                ("drug_class_1", "TEXT"),
                ("drug_class_2", "TEXT"),
                ("drug_class_3", "TEXT"),
                ("drug_target_1", "TEXT"),
                ("drug_target_2", "TEXT"),
                ("drug_target_3", "TEXT"),
                ("prior_therapy_1", "TEXT"),
                ("prior_therapy_2", "TEXT"),
                ("prior_therapy_3", "TEXT"),
                ("resistance_mechanism", "TEXT"),

                # Group D: Clinical Context (7 fields)
                ("metastatic_site_1", "TEXT"),
                ("metastatic_site_2", "TEXT"),
                ("metastatic_site_3", "TEXT"),
                ("symptom_1", "TEXT"),
                ("symptom_2", "TEXT"),
                ("symptom_3", "TEXT"),
                ("performance_status", "TEXT"),

                # Group E: Safety/Toxicity (7 fields)
                ("toxicity_type_1", "TEXT"),
                ("toxicity_type_2", "TEXT"),
                ("toxicity_type_3", "TEXT"),
                ("toxicity_type_4", "TEXT"),
                ("toxicity_type_5", "TEXT"),
                ("toxicity_organ", "TEXT"),
                ("toxicity_grade", "TEXT"),

                # Group F: Efficacy/Outcomes (5 fields)
                ("efficacy_endpoint_1", "TEXT"),
                ("efficacy_endpoint_2", "TEXT"),
                ("efficacy_endpoint_3", "TEXT"),
                ("outcome_context", "TEXT"),
                ("clinical_benefit", "TEXT"),

                # Group G: Evidence/Guidelines (3 fields)
                ("guideline_source_1", "TEXT"),
                ("guideline_source_2", "TEXT"),
                ("evidence_type", "TEXT"),

                # Group H: Question Format/Quality (13 fields)
                ("cme_outcome_level", "TEXT"),
                ("data_response_type", "TEXT"),
                ("stem_type", "TEXT"),
                ("lead_in_type", "TEXT"),
                ("answer_format", "TEXT"),
                ("answer_length_pattern", "TEXT"),
                ("distractor_homogeneity", "TEXT"),
                ("flaw_absolute_terms", "BOOLEAN"),
                ("flaw_grammatical_cue", "BOOLEAN"),
                ("flaw_implausible_distractor", "BOOLEAN"),
                ("flaw_clang_association", "BOOLEAN"),
                ("flaw_convergence_vulnerability", "BOOLEAN"),
                ("flaw_double_negative", "BOOLEAN"),

                # Computed Fields (2)
                ("answer_option_count", "INTEGER"),
                ("correct_answer_position", "TEXT"),

                # Additional review metadata
                ("review_reason", "TEXT"),
                ("agreement_level", "TEXT"),

                # Audit trail for human edits
                ("edited_by_user", "BOOLEAN DEFAULT FALSE"),
                ("edited_at", "TIMESTAMP"),
                ("edited_fields", "TEXT"),  # JSON array of edited field names

                # Tag agreement status (computed from 8 core tags' field_votes)
                # Values: 'verified', 'unanimous', 'majority', 'conflict'
                ("tag_status", "TEXT"),

                # Worst-case agreement across ALL field_votes (for Review page)
                # Values: 'verified', 'unanimous', 'majority', 'conflict'
                ("worst_case_agreement", "TEXT"),

                # QCore Score (computed from quality fields)
                ("qcore_score", "REAL"),           # 0-100 quality score
                ("qcore_grade", "TEXT"),           # A, B, C, D
                ("qcore_breakdown", "TEXT"),       # JSON: {flaws: {}, structure_deductions: {}, structure_bonuses: {}}
                ("qcore_scored_at", "TIMESTAMP"),  # When score was last calculated
            ]
            for col_name, col_type in migration_columns:
                try:
                    cursor.execute(f"ALTER TABLE tags ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            # Questions table migration: add source tracking columns
            questions_migration_columns = [
                ("source_question_id", "INTEGER"),  # Original question ID from checkpoint
                ("source_id", "INTEGER"),           # Source ID (QGD) for linking to Snowflake
                ("canonical_source_id", "TEXT"),    # For duplicates: points to canonical's source_id (defaults to own source_id)
            ]
            for col_name, col_type in questions_migration_columns:
                try:
                    cursor.execute(f"ALTER TABLE questions ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            # Performance metrics by segment
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    segment TEXT NOT NULL,
                    pre_score REAL,
                    post_score REAL,
                    pre_n INTEGER,
                    post_n INTEGER,
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                    UNIQUE(question_id, segment)
                )
            """)
            
            # Activities metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_name TEXT NOT NULL UNIQUE,
                    activity_date DATE,
                    quarter TEXT,
                    target_audience TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Question-Activity relationships
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS question_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    activity_name TEXT NOT NULL,
                    activity_id INTEGER,
                    activity_date DATE,
                    quarter TEXT,
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL,
                    UNIQUE(question_id, activity_name)
                )
            """)
            
            # Demographic performance table for granular segmentation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS demographic_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    activity_id INTEGER,
                    specialty TEXT,
                    practice_setting TEXT,
                    practice_state TEXT,
                    region TEXT,
                    pre_score REAL,
                    post_score REAL,
                    n_respondents INTEGER,
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL
                )
            """)
            
            # Novel entities table - for LLM-extracted entities not in KB
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS novel_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,  -- 'treatment', 'trial', 'disease', 'biomarker'
                    normalized_name TEXT,
                    confidence REAL DEFAULT 0.75,
                    occurrence_count INTEGER DEFAULT 1,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'auto_approved'
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    drug_class TEXT,
                    synonyms TEXT,  -- JSON array
                    notes TEXT,
                    UNIQUE(entity_name, entity_type)
                )
            """)

            # User-defined values for dropdown fields
            # When users enter custom values via "Other...", they get persisted here
            # so they appear in dropdowns for future questions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_defined_values (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    UNIQUE(field_name, value)
                )
            """)

            # ========== Deduplication Tables ==========

            # Duplicate clusters - groups of similar questions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_clusters (
                    cluster_id INTEGER PRIMARY KEY,
                    canonical_question_id INTEGER REFERENCES questions(id),
                    canonical_source_id TEXT,
                    status TEXT DEFAULT 'pending',  -- pending, confirmed, rejected
                    similarity_threshold REAL,      -- 0.90 or 0.95
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewed_by TEXT
                )
            """)

            # Cluster members - questions in each cluster
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cluster_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cluster_id INTEGER REFERENCES duplicate_clusters(cluster_id) ON DELETE CASCADE,
                    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
                    source_id TEXT,
                    similarity_to_canonical REAL,
                    is_canonical BOOLEAN DEFAULT FALSE,
                    UNIQUE(cluster_id, question_id)
                )
            """)

            # User decisions on duplicate pairs (for audit trail)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cluster_id INTEGER REFERENCES duplicate_clusters(cluster_id),
                    question_id_1 INTEGER,
                    question_id_2 INTEGER,
                    similarity_score REAL,
                    decision TEXT,  -- 'duplicate', 'not_duplicate', 'undecided'
                    decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    decided_by TEXT
                )
            """)

            # ========== Tag Proposal Tables ==========

            # Tag proposals - proposed tag values to apply retroactively
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tag_proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_name TEXT NOT NULL,
                    proposed_value TEXT NOT NULL,
                    search_query TEXT,
                    proposal_reason TEXT,
                    status TEXT DEFAULT 'pending',
                    match_count INTEGER DEFAULT 0,
                    approved_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    completed_at TIMESTAMP
                )
            """)

            # Tag proposal candidates - questions matching the search query
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tag_proposal_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id INTEGER REFERENCES tag_proposals(id) ON DELETE CASCADE,
                    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
                    match_score REAL,
                    current_value TEXT,
                    decision TEXT DEFAULT 'pending',
                    decided_at TIMESTAMP,
                    decided_by TEXT,
                    notes TEXT,
                    UNIQUE(proposal_id, question_id)
                )
            """)

            # Novel entity occurrences - track which questions surfaced each entity
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS novel_entity_occurrences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    novel_entity_id INTEGER NOT NULL,
                    question_id INTEGER,
                    source_text TEXT NOT NULL,
                    extraction_confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (novel_entity_id) REFERENCES novel_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL
                )
            """)

            # Migration: Add new columns to question_activities (for existing DBs)
            qa_migration_columns = [
                ("activity_id", "INTEGER"),
                ("activity_date", "DATE"),
                ("quarter", "TEXT"),
            ]
            for col_name, col_type in qa_migration_columns:
                try:
                    cursor.execute(f"ALTER TABLE question_activities ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_topic ON tags(topic)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_disease_state ON tags(disease_state)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_disease_stage ON tags(disease_stage)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_disease_type ON tags(disease_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_treatment_line ON tags(treatment_line)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_treatment ON tags(treatment)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_biomarker ON tags(biomarker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_trial ON tags(trial)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_segment ON performance(segment)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_name ON question_activities(activity_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_quarter ON question_activities(quarter)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_activity_date ON question_activities(activity_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_quarter ON activities(quarter)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(activity_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_demo_perf_specialty ON demographic_performance(specialty)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_demo_perf_setting ON demographic_performance(practice_setting)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_demo_perf_region ON demographic_performance(region)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_demo_perf_activity ON demographic_performance(activity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_novel_entities_status ON novel_entities(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_novel_entities_type ON novel_entities(entity_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_novel_occurrences_entity ON novel_entity_occurrences(novel_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_defined_values_field ON user_defined_values(field_name)")
            # Dedup indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dup_clusters_status ON duplicate_clusters(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster_members_cluster ON cluster_members(cluster_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster_members_question ON cluster_members(question_id)")
            # Tag proposal indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_proposals_status ON tag_proposals(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_proposals_field ON tag_proposals(field_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposal_candidates_proposal ON tag_proposal_candidates(proposal_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposal_candidates_question ON tag_proposal_candidates(question_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposal_candidates_decision ON tag_proposal_candidates(decision)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_canonical_source ON questions(canonical_source_id)")
            
            # Full-text search virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5(
                    question_stem,
                    correct_answer,
                    content='questions',
                    content_rowid='id'
                )
            """)
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def clear_database(self):
        """Clear all data from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM demographic_performance")
            cursor.execute("DELETE FROM question_activities")
            cursor.execute("DELETE FROM activities")
            cursor.execute("DELETE FROM performance")
            cursor.execute("DELETE FROM tags")
            cursor.execute("DELETE FROM questions")
            cursor.execute("DELETE FROM questions_fts")
            conn.commit()
            logger.info("Database cleared")
    
    # ============== Question Operations ==============

    def get_question_by_source_id(self, source_id: str) -> Optional[Dict]:
        """
        Look up a question by QUESTIONGROUPDESIGNATION (QGD).

        Returns dict with id, source_question_id, source_id, and edited_by_user
        or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT q.id, q.source_question_id, q.source_id, q.question_stem,
                       q.correct_answer, q.incorrect_answers, q.source_file,
                       COALESCE(t.edited_by_user, 0) as edited_by_user
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                WHERE q.source_id = ?
            """, (source_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def update_question(
        self,
        question_id: int,
        question_stem: str,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[List[str]] = None,
        source_file: Optional[str] = None,
    ):
        """
        Update an existing question's data (stem, answers, source_file).
        Does NOT touch tags — use update_tags() for that.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE questions
                SET question_stem = ?,
                    correct_answer = ?,
                    incorrect_answers = ?,
                    source_file = ?
                WHERE id = ?
            """, (
                question_stem,
                correct_answer,
                json.dumps(incorrect_answers) if incorrect_answers else None,
                source_file,
                question_id,
            ))

            # Update FTS index
            cursor.execute("DELETE FROM questions_fts WHERE rowid = ?", (question_id,))
            cursor.execute("""
                INSERT INTO questions_fts (rowid, question_stem, correct_answer)
                VALUES (?, ?, ?)
            """, (question_id, question_stem, correct_answer or ""))

            conn.commit()

    def insert_question(
        self,
        question_stem: str,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[List[str]] = None,
        source_file: Optional[str] = None,
        source_question_id: Optional[int] = None,
        source_id: Optional[int] = None
    ) -> int:
        """Insert a question and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO questions (question_stem, correct_answer, incorrect_answers, source_file, source_question_id, source_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                question_stem,
                correct_answer,
                json.dumps(incorrect_answers) if incorrect_answers else None,
                source_file,
                source_question_id,
                source_id
            ))
            question_id = cursor.lastrowid
            
            # Update FTS index
            cursor.execute("""
                INSERT INTO questions_fts (rowid, question_stem, correct_answer)
                VALUES (?, ?, ?)
            """, (question_id, question_stem, correct_answer or ""))
            
            conn.commit()
            return question_id
    
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
        """Insert or update tags for a question (legacy method for backwards compatibility)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tags
                (question_id, topic, topic_confidence, topic_method,
                 disease_state, disease_state_confidence,
                 disease_stage, disease_stage_confidence,
                 disease_type_1, disease_type_confidence,
                 treatment_line, treatment_line_confidence,
                 treatment_1, treatment_confidence,
                 biomarker_1, biomarker_confidence,
                 trial_1, trial_confidence,
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

    def update_tags(self, question_id: int, tags: Dict[str, Any], mark_as_reviewed: bool = False):
        """
        Update tags for a question using the 70-field schema.
        Only updates fields that are provided (non-None values).

        Args:
            question_id: The question ID to update
            tags: Dictionary of tag field names to values
            mark_as_reviewed: If True, sets needs_review=False and overall_confidence=1.0
        """
        # All valid tag column names in the database (70 fields + metadata)
        valid_columns = {
            # Core Classification
            'topic', 'topic_confidence', 'topic_method',
            'disease_state', 'disease_state_1', 'disease_state_2', 'disease_state_confidence',
            'disease_stage', 'disease_stage_confidence',
            'disease_type_1', 'disease_type_2', 'disease_type_confidence',
            'treatment_line', 'treatment_line_confidence',
            # Multi-value fields
            'treatment_1', 'treatment_2', 'treatment_3', 'treatment_4', 'treatment_5', 'treatment_confidence',
            'biomarker_1', 'biomarker_2', 'biomarker_3', 'biomarker_4', 'biomarker_5', 'biomarker_confidence',
            'trial_1', 'trial_2', 'trial_3', 'trial_4', 'trial_5', 'trial_confidence',
            # Patient Characteristics
            'treatment_eligibility', 'age_group', 'organ_dysfunction', 'fitness_status', 'disease_specific_factor',
            'comorbidity_1', 'comorbidity_2', 'comorbidity_3',
            # Treatment Metadata
            'drug_class_1', 'drug_class_2', 'drug_class_3',
            'drug_target_1', 'drug_target_2', 'drug_target_3',
            'prior_therapy_1', 'prior_therapy_2', 'prior_therapy_3', 'resistance_mechanism',
            # Clinical Context
            'metastatic_site_1', 'metastatic_site_2', 'metastatic_site_3',
            'symptom_1', 'symptom_2', 'symptom_3', 'performance_status',
            # Safety/Toxicity
            'toxicity_type_1', 'toxicity_type_2', 'toxicity_type_3', 'toxicity_type_4', 'toxicity_type_5',
            'toxicity_organ', 'toxicity_grade',
            # Efficacy/Outcomes
            'efficacy_endpoint_1', 'efficacy_endpoint_2', 'efficacy_endpoint_3',
            'outcome_context', 'clinical_benefit',
            # Evidence/Guidelines
            'guideline_source_1', 'guideline_source_2', 'evidence_type',
            # Question Format/Quality
            'cme_outcome_level', 'data_response_type', 'stem_type', 'lead_in_type',
            'answer_format', 'answer_length_pattern', 'distractor_homogeneity',
            'flaw_absolute_terms', 'flaw_grammatical_cue', 'flaw_implausible_distractor',
            'flaw_clang_association', 'flaw_convergence_vulnerability', 'flaw_double_negative',
            # Computed fields
            'answer_option_count', 'correct_answer_position',
            # Review metadata
            'needs_review', 'review_flags', 'review_reason', 'flagged_at', 'agreement_level',
            'overall_confidence', 'llm_calls_made',
            # Tag status for filtering
            'tag_status', 'worst_case_agreement'
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # First ensure a tags row exists for this question
            cursor.execute("SELECT question_id FROM tags WHERE question_id = ?", (question_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO tags (question_id) VALUES (?)", (question_id,))

            # Build UPDATE statement with only provided fields
            updates = []
            values = []

            for field, value in tags.items():
                if field in valid_columns and value is not None:
                    # Handle special cases
                    if field == 'review_flags' and isinstance(value, list):
                        value = json.dumps(value)
                    updates.append(f"{field} = ?")
                    values.append(value)

            # If marking as reviewed, clear review flags and mark as human-reviewed
            if mark_as_reviewed:
                updates.append("needs_review = ?")
                values.append(False)
                updates.append("overall_confidence = ?")
                values.append(1.0)
                # Mark as reviewed by user (protects from import overwrite)
                updates.append("edited_by_user = ?")
                values.append(True)
                updates.append("edited_at = CURRENT_TIMESTAMP")
                # Set tag_status and worst_case_agreement to 'verified' (human has approved)
                updates.append("tag_status = ?")
                values.append("verified")
                updates.append("worst_case_agreement = ?")
                values.append("verified")

            # Always update the timestamp
            updates.append("updated_at = CURRENT_TIMESTAMP")

            if updates:
                values.append(question_id)
                sql = f"UPDATE tags SET {', '.join(updates)} WHERE question_id = ?"
                cursor.execute(sql, values)
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
            # Get existing review flags and flagged_at
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
                # Check if already has a flagged_at timestamp
                already_flagged = row["flagged_at"] is not None

            # Merge with new flags (avoid duplicates)
            all_flags = list(set(existing_flags + flag_reasons))

            # Update tags to mark as needing review
            if row:
                # Record exists, update it
                if already_flagged:
                    # Don't overwrite flagged_at if already set
                    cursor.execute("""
                        UPDATE tags
                        SET review_flags = ?,
                            needs_review = 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE question_id = ?
                    """, (json.dumps(all_flags), question_id))
                else:
                    # Set flagged_at for first time
                    cursor.execute("""
                        UPDATE tags
                        SET review_flags = ?,
                            needs_review = 1,
                            flagged_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE question_id = ?
                    """, (json.dumps(all_flags), question_id))
            else:
                # No tags record exists, create one
                cursor.execute("""
                    INSERT INTO tags (question_id, review_flags, needs_review, flagged_at, updated_at)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (question_id, json.dumps(all_flags)))

            conn.commit()

    def update_question_oncology_status(self, question_id: int, is_oncology: bool):
        """Mark a question as oncology or non-oncology."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if is_oncology column exists, if not add it
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

    def insert_performance(
        self,
        question_id: int,
        segment: str,
        pre_score: Optional[float] = None,
        post_score: Optional[float] = None,
        pre_n: Optional[int] = None,
        post_n: Optional[int] = None
    ):
        """Insert performance metrics for a question segment."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO performance 
                (question_id, segment, pre_score, post_score, pre_n, post_n)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (question_id, segment, pre_score, post_score, pre_n, post_n))
            conn.commit()
    
    def insert_activity(self, question_id: int, activity_name: str):
        """Add an activity association for a question."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # First ensure activity exists in activities table
            cursor.execute("""
                INSERT OR IGNORE INTO activities (activity_name) VALUES (?)
            """, (activity_name,))

            # Get the activity ID
            cursor.execute("SELECT id FROM activities WHERE activity_name = ?", (activity_name,))
            activity_row = cursor.fetchone()
            activity_id = activity_row["id"] if activity_row else None

            # Insert the question-activity relationship
            cursor.execute("""
                INSERT OR IGNORE INTO question_activities (question_id, activity_name, activity_id)
                VALUES (?, ?, ?)
            """, (question_id, activity_name, activity_id))
            conn.commit()

    def insert_activity_with_date(
        self,
        question_id: int,
        activity_name: str,
        activity_date: Optional[date] = None
    ):
        """
        Add an activity association for a question with a specific date.

        Used for new format where each question-activity pair has its own date
        (e.g., same activity name used across different dates).

        Args:
            question_id: The question ID
            activity_name: Name of the activity
            activity_date: Date of this specific activity instance
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Calculate quarter from date if provided
            quarter = get_quarter_from_date(activity_date) if activity_date else None

            # Ensure activity exists in activities table
            cursor.execute("""
                INSERT OR IGNORE INTO activities (activity_name) VALUES (?)
            """, (activity_name,))

            # Get the activity ID
            cursor.execute("SELECT id FROM activities WHERE activity_name = ?", (activity_name,))
            activity_row = cursor.fetchone()
            activity_id = activity_row["id"] if activity_row else None

            # Insert the question-activity relationship with date and quarter
            cursor.execute("""
                INSERT OR IGNORE INTO question_activities
                (question_id, activity_name, activity_id, activity_date, quarter)
                VALUES (?, ?, ?, ?, ?)
            """, (question_id, activity_name, activity_id, activity_date, quarter))
            conn.commit()
    
    # ============== Activity Metadata Operations ==============
    
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
            
            # Calculate quarter from date if provided
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
            
            # Update question_activities with the activity_id
            cursor.execute("""
                UPDATE question_activities SET activity_id = ? WHERE activity_name = ?
            """, (activity_id, activity_name))
            
            conn.commit()
            return activity_id
    
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
    
    def get_activity_by_name(self, activity_name: str) -> Optional[Dict]:
        """Get activity by name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, 
                    (SELECT COUNT(DISTINCT question_id) FROM question_activities WHERE activity_name = a.activity_name) as question_count
                FROM activities a
                WHERE a.activity_name = ?
            """, (activity_name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
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
    
    # ============== Demographic Performance Operations ==============
    
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
    ) -> int:
        """Insert demographic performance data. Returns record ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Derive region from state
            region = get_region_from_state(practice_state) if practice_state else None
            
            cursor.execute("""
                INSERT INTO demographic_performance 
                (question_id, activity_id, specialty, practice_setting, practice_state, region, pre_score, post_score, n_respondents)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (question_id, activity_id, specialty, practice_setting, practice_state, region, pre_score, post_score, n_respondents))
            
            conn.commit()
            return cursor.lastrowid
    
    # ============== Query Operations ==============
    
    # Mapping of advanced filter category key -> list of DB columns in the tags table.
    # Single-column categories have one entry; multi-slot categories span multiple columns.
    ADVANCED_FILTER_COLUMNS = {
        # Patient Characteristics
        'treatment_eligibilities': ['treatment_eligibility'],
        'age_groups': ['age_group'],
        'fitness_statuses': ['fitness_status'],
        'organ_dysfunctions': ['organ_dysfunction'],
        'disease_specific_factors': ['disease_specific_factor'],
        'comorbidities': ['comorbidity_1', 'comorbidity_2', 'comorbidity_3'],
        # Treatment Details
        'drug_classes': ['drug_class_1', 'drug_class_2', 'drug_class_3'],
        'drug_targets': ['drug_target_1', 'drug_target_2', 'drug_target_3'],
        'prior_therapies': ['prior_therapy_1', 'prior_therapy_2', 'prior_therapy_3'],
        'resistance_mechanisms': ['resistance_mechanism'],
        # Clinical Context
        'metastatic_sites': ['metastatic_site_1', 'metastatic_site_2', 'metastatic_site_3'],
        'symptoms': ['symptom_1', 'symptom_2', 'symptom_3'],
        'performance_statuses': ['performance_status'],
        # Safety/Toxicity
        'toxicity_types': ['toxicity_type_1', 'toxicity_type_2', 'toxicity_type_3', 'toxicity_type_4', 'toxicity_type_5'],
        'toxicity_organs': ['toxicity_organ'],
        'toxicity_grades': ['toxicity_grade'],
        # Efficacy/Outcomes
        'efficacy_endpoints': ['efficacy_endpoint_1', 'efficacy_endpoint_2', 'efficacy_endpoint_3'],
        'outcome_contexts': ['outcome_context'],
        'clinical_benefits': ['clinical_benefit'],
        # Evidence/Guidelines
        'guideline_sources': ['guideline_source_1', 'guideline_source_2'],
        'evidence_types': ['evidence_type'],
        # Question Format
        'cme_outcome_levels': ['cme_outcome_level'],
        'stem_types': ['stem_type'],
        'lead_in_types': ['lead_in_type'],
        'answer_formats': ['answer_format'],
        'distractor_homogeneities': ['distractor_homogeneity'],
    }

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
        source_files: Optional[List[str]] = None,
        # Patient characteristics filters (70-field schema)
        treatment_eligibilities: Optional[List[str]] = None,
        age_groups: Optional[List[str]] = None,
        fitness_statuses: Optional[List[str]] = None,
        organ_dysfunctions: Optional[List[str]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        has_performance_data: Optional[bool] = None,
        min_sample_size: Optional[int] = None,
        needs_review: Optional[bool] = None,
        review_flag_filter: Optional[str] = None,
        worst_case_agreement: Optional[str] = None,
        tag_status_filter: Optional[str] = None,
        exclude_numeric: Optional[bool] = None,
        activity_start_after: Optional[str] = None,
        activity_start_before: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "id",
        sort_desc: bool = False,
        advanced_filters: Optional[Dict[str, List[str]]] = None,
    ) -> Tuple[List[Dict], int]:
        """
        Search questions with filters.
        Returns (questions, total_count).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build query
            # Calculate performance from demographic_performance (granular data) for consistency
            select_fields = """
                q.id, q.source_id, q.question_stem, t.topic, t.topic_confidence,
                t.disease_state, t.disease_state_confidence, t.treatment,
                dp_agg.pre_score, dp_agg.post_score, dp_agg.pre_n, dp_agg.post_n,
                (SELECT COUNT(*) FROM question_activities qa WHERE qa.question_id = q.id) as activity_count,
                t.tag_status,
                t.worst_case_agreement,
                t.qcore_score,
                t.qcore_grade
            """

            from_clause = """
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                LEFT JOIN (
                    SELECT
                        question_id,
                        SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_score * pre_n ELSE 0 END) /
                            NULLIF(SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_n ELSE 0 END), 0) as pre_score,
                        SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_score * post_n ELSE 0 END) /
                            NULLIF(SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_n ELSE 0 END), 0) as post_score,
                        SUM(CASE WHEN pre_score IS NOT NULL THEN pre_n ELSE 0 END) as pre_n,
                        SUM(CASE WHEN post_score IS NOT NULL THEN post_n ELSE 0 END) as post_n
                    FROM demographic_performance
                    GROUP BY question_id
                ) dp_agg ON q.id = dp_agg.question_id
            """
            
            where_clauses = []
            params = []

            # Always filter out non-oncology questions by default
            where_clauses.append("(q.is_oncology IS NULL OR q.is_oncology = 1)")

            # Exclude confirmed duplicates (questions with canonical_source_id pointing to another question)
            where_clauses.append("(q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))")

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
                # Search across disease_state_1, disease_state_2, and legacy disease_state field
                placeholders = ",".join("?" * len(disease_states))
                where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({placeholders}) OR t.disease_state_2 IN ({placeholders}))")
                params.extend(disease_states)
                params.extend(disease_states)

            if disease_stages:
                placeholders = ",".join("?" * len(disease_stages))
                where_clauses.append(f"t.disease_stage IN ({placeholders})")
                params.extend(disease_stages)

            if disease_types:
                # Search across both disease_type_1 and disease_type_2
                placeholders = ",".join("?" * len(disease_types))
                where_clauses.append(f"(t.disease_type_1 IN ({placeholders}) OR t.disease_type_2 IN ({placeholders}))")
                params.extend(disease_types)
                params.extend(disease_types)

            if treatment_lines:
                placeholders = ",".join("?" * len(treatment_lines))
                where_clauses.append(f"t.treatment_line IN ({placeholders})")
                params.extend(treatment_lines)

            if treatments:
                # Search across all treatment slots (treatment_1 through treatment_5)
                placeholders = ",".join("?" * len(treatments))
                treatment_conditions = " OR ".join([f"t.treatment_{i} IN ({placeholders})" for i in range(1, 6)])
                where_clauses.append(f"({treatment_conditions})")
                for _ in range(5):
                    params.extend(treatments)

            if biomarkers:
                # Search across all biomarker slots (biomarker_1 through biomarker_5)
                placeholders = ",".join("?" * len(biomarkers))
                biomarker_conditions = " OR ".join([f"t.biomarker_{i} IN ({placeholders})" for i in range(1, 6)])
                where_clauses.append(f"({biomarker_conditions})")
                for _ in range(5):
                    params.extend(biomarkers)

            if trials:
                # Search across all trial slots (trial_1 through trial_5)
                placeholders = ",".join("?" * len(trials))
                trial_conditions = " OR ".join([f"t.trial_{i} IN ({placeholders})" for i in range(1, 6)])
                where_clauses.append(f"({trial_conditions})")
                for _ in range(5):
                    params.extend(trials)

            # Patient characteristics filters (70-field schema)
            if treatment_eligibilities:
                placeholders = ",".join("?" * len(treatment_eligibilities))
                where_clauses.append(f"t.treatment_eligibility IN ({placeholders})")
                params.extend(treatment_eligibilities)

            if age_groups:
                placeholders = ",".join("?" * len(age_groups))
                where_clauses.append(f"t.age_group IN ({placeholders})")
                params.extend(age_groups)

            if fitness_statuses:
                placeholders = ",".join("?" * len(fitness_statuses))
                where_clauses.append(f"t.fitness_status IN ({placeholders})")
                params.extend(fitness_statuses)

            if organ_dysfunctions:
                placeholders = ",".join("?" * len(organ_dysfunctions))
                where_clauses.append(f"t.organ_dysfunction IN ({placeholders})")
                params.extend(organ_dysfunctions)

            # Advanced filters — data-driven WHERE clauses
            if advanced_filters:
                for cat_key, values in advanced_filters.items():
                    if not values or cat_key not in self.ADVANCED_FILTER_COLUMNS:
                        continue
                    columns = self.ADVANCED_FILTER_COLUMNS[cat_key]
                    if len(columns) == 1:
                        placeholders = ",".join("?" * len(values))
                        where_clauses.append(f"t.{columns[0]} IN ({placeholders})")
                        params.extend(values)
                    else:
                        # Multi-slot: match if ANY slot contains the value
                        or_parts = []
                        for col in columns:
                            placeholders = ",".join("?" * len(values))
                            or_parts.append(f"t.{col} IN ({placeholders})")
                            params.extend(values)
                        where_clauses.append(f"({' OR '.join(or_parts)})")

            if activities:
                placeholders = ",".join("?" * len(activities))
                where_clauses.append(f"""
                    q.id IN (SELECT question_id FROM question_activities WHERE activity_name IN ({placeholders}))
                """)
                params.extend(activities)

            if source_files:
                placeholders = ",".join("?" * len(source_files))
                where_clauses.append(f"q.source_file IN ({placeholders})")
                params.extend(source_files)

            if min_confidence is not None:
                where_clauses.append("t.overall_confidence >= ?")
                params.append(min_confidence)

            if max_confidence is not None:
                where_clauses.append("t.overall_confidence <= ?")
                params.append(max_confidence)

            if has_performance_data is True:
                where_clauses.append("dp_agg.pre_n IS NOT NULL AND dp_agg.pre_n > 0 AND dp_agg.post_n IS NOT NULL AND dp_agg.post_n > 0")
            elif has_performance_data is False:
                where_clauses.append("(dp_agg.pre_n IS NULL OR dp_agg.pre_n = 0 OR dp_agg.post_n IS NULL OR dp_agg.post_n = 0)")

            if min_sample_size is not None:
                where_clauses.append("(COALESCE(dp_agg.pre_n, 0) + COALESCE(dp_agg.post_n, 0)) >= ?")
                params.append(min_sample_size)

            if needs_review is True:
                where_clauses.append("t.needs_review = 1")
            elif needs_review is False:
                where_clauses.append("(t.needs_review IS NULL OR t.needs_review = 0)")

            # Filter by review flag type
            # Check both review_flags (JSON array, legacy) and review_reason (text, new voting system)
            if review_flag_filter:
                where_clauses.append("""(
                    t.review_flags LIKE ? OR t.review_flags LIKE ? OR t.review_flags LIKE ?
                    OR t.review_reason LIKE ?
                )""")
                # Match at start, middle, or end of JSON array (for review_flags)
                # Match anywhere in text (for review_reason)
                params.extend([
                    f'["{review_flag_filter}"%',
                    f'%"{review_flag_filter}"%',
                    f'%"{review_flag_filter}"]',
                    f'%{review_flag_filter}%'
                ])

            # Filter by worst_case_agreement status (ALL fields - for Review page)
            if worst_case_agreement:
                if worst_case_agreement == 'verified_only':
                    where_clauses.append("t.worst_case_agreement = 'verified'")
                elif worst_case_agreement == 'verified_or_unanimous':
                    where_clauses.append("t.worst_case_agreement IN ('verified', 'unanimous')")
                elif worst_case_agreement == 'verified_unanimous_majority':
                    where_clauses.append("t.worst_case_agreement IN ('verified', 'unanimous', 'majority')")

            # Filter by tag_status (8 core tags - for Question Explorer page)
            if tag_status_filter:
                if tag_status_filter == 'verified_only':
                    where_clauses.append("t.tag_status = 'verified'")
                elif tag_status_filter == 'verified_or_unanimous':
                    where_clauses.append("t.tag_status IN ('verified', 'unanimous')")
                elif tag_status_filter == 'verified_unanimous_majority':
                    where_clauses.append("t.tag_status IN ('verified', 'unanimous', 'majority')")

            # Exclude numeric questions (data_response_type = 'Numeric')
            if exclude_numeric:
                where_clauses.append("(t.data_response_type IS NULL OR t.data_response_type != 'Numeric')")

            # Activity date range filter
            # Filter questions where at least one activity falls within the date range
            # Uses demographic_performance table (which has dated activity links) instead of question_activities
            if activity_start_after or activity_start_before:
                date_conditions = []
                date_params = []
                if activity_start_after:
                    # Convert YYYY-MM to date for comparison (first day of month)
                    date_conditions.append("a.activity_date >= ?")
                    date_params.append(f"{activity_start_after}-01")
                if activity_start_before:
                    # Convert YYYY-MM to date for comparison (last day of month)
                    # Use last day of month (31 to be safe, SQLite will handle comparison correctly)
                    date_conditions.append("a.activity_date <= ?")
                    date_params.append(f"{activity_start_before}-31")

                date_where = " AND ".join(date_conditions)
                where_clauses.append(f"""
                    q.id IN (
                        SELECT DISTINCT dp.question_id
                        FROM demographic_performance dp
                        JOIN activities a ON dp.activity_id = a.id
                        WHERE a.activity_date IS NOT NULL AND {date_where}
                    )
                """)
                params.extend(date_params)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Get total count
            count_sql = f"SELECT COUNT(DISTINCT q.id) {from_clause} WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]

            # Sorting (uses dp_agg alias for performance data from demographic_performance subquery)
            sort_column = {
                "id": "q.id",
                "topic": "t.topic",
                "disease_state": "t.disease_state",
                "pre_score": "dp_agg.pre_score",
                "post_score": "dp_agg.post_score",
                "knowledge_gain": "(dp_agg.post_score - dp_agg.pre_score)",
                "confidence": "t.overall_confidence",
                "sample_size": "(COALESCE(dp_agg.pre_n, 0) + COALESCE(dp_agg.post_n, 0))",
                "flagged_at": "t.flagged_at",
                "qcore_score": "t.qcore_score"
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
            # Use a copy of params and add pagination parameters
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

                question_dict = {
                    "id": row["id"],
                    "source_id": row["source_id"],
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
                    "activity_count": row["activity_count"],
                    "tag_status": row["tag_status"],
                    "worst_case_agreement": row["worst_case_agreement"],
                    "qcore_score": row["qcore_score"],
                    "qcore_grade": row["qcore_grade"],
                }

                questions.append(question_dict)
            
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
            
            # Segment name mapping: database -> frontend
            SEGMENT_MAP = {
                'MedicalOncology': 'medical_oncologist',
                'SurgicalOncology': 'surgical_oncologist',
                'RadiationOncology': 'radiation_oncologist',
                'NP/PA': 'app',
                'CommunityOncology': 'community',
                'AcademicOncology': 'academic',
                'NursingOncology': 'nursing',
            }

            # Calculate overall performance from demographic_performance (granular data)
            # This ensures consistency with per-activity and per-segment data
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_score * pre_n ELSE 0 END) /
                        NULLIF(SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_n ELSE 0 END), 0) as pre_score,
                    SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_score * post_n ELSE 0 END) /
                        NULLIF(SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_n ELSE 0 END), 0) as post_score,
                    SUM(CASE WHEN pre_score IS NOT NULL THEN pre_n ELSE 0 END) as total_pre_n,
                    SUM(CASE WHEN post_score IS NOT NULL THEN post_n ELSE 0 END) as total_post_n
                FROM demographic_performance
                WHERE question_id = ?
            """, (question_id,))
            overall_row = cursor.fetchone()

            performance = []
            if overall_row and (overall_row["pre_score"] is not None or overall_row["post_score"] is not None):
                performance.append({
                    "segment": "overall",
                    "pre_score": overall_row["pre_score"],
                    "post_score": overall_row["post_score"],
                    "pre_n": overall_row["total_pre_n"] if overall_row["total_pre_n"] > 0 else None,
                    "post_n": overall_row["total_post_n"] if overall_row["total_post_n"] > 0 else None
                })

            # Get segment-level performance by aggregating from demographic_performance
            # Weighted average across all activities for each specialty
            # Uses separate pre_n and post_n for accurate weighting
            cursor.execute("""
                SELECT
                    specialty,
                    SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_score * pre_n ELSE 0 END) /
                        NULLIF(SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_n ELSE 0 END), 0) as pre_score,
                    SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_score * post_n ELSE 0 END) /
                        NULLIF(SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_n ELSE 0 END), 0) as post_score,
                    SUM(CASE WHEN pre_score IS NOT NULL THEN pre_n ELSE 0 END) as total_pre_n,
                    SUM(CASE WHEN post_score IS NOT NULL THEN post_n ELSE 0 END) as total_post_n
                FROM demographic_performance
                WHERE question_id = ?
                GROUP BY specialty
            """, (question_id,))
            segment_rows = cursor.fetchall()

            for seg_row in segment_rows:
                db_segment = seg_row["specialty"]
                frontend_segment = SEGMENT_MAP.get(db_segment, db_segment.lower() if db_segment else 'unknown')
                performance.append({
                    "segment": frontend_segment,
                    "pre_score": seg_row["pre_score"],
                    "post_score": seg_row["post_score"],
                    "pre_n": seg_row["total_pre_n"] if seg_row["total_pre_n"] > 0 else None,
                    "post_n": seg_row["total_post_n"] if seg_row["total_post_n"] > 0 else None
                })
            
            # Get activities directly from demographic_performance joined with activities table
            # (bypasses potentially corrupted question_activities data)
            cursor.execute("""
                SELECT DISTINCT dp.activity_id, a.activity_name, a.activity_date, a.quarter
                FROM demographic_performance dp
                JOIN activities a ON dp.activity_id = a.id
                WHERE dp.question_id = ?
                ORDER BY a.activity_date DESC NULLS LAST
            """, (question_id,))
            activity_rows = cursor.fetchall()

            # Legacy activities list for backwards compatibility
            activities = [r["activity_name"] for r in activity_rows]

            activity_details = []
            for act_row in activity_rows:
                activity_id = act_row["activity_id"]
                act_detail = {
                    "activity_name": act_row["activity_name"],
                    "activity_date": act_row["activity_date"],
                    "quarter": act_row["quarter"],
                    "performance": []
                }

                # Get per-activity performance from demographic_performance
                # Uses separate pre_n and post_n columns for accurate data
                cursor.execute("""
                    SELECT
                        specialty,
                        pre_score,
                        post_score,
                        pre_n,
                        post_n
                    FROM demographic_performance
                    WHERE question_id = ? AND activity_id = ?
                """, (question_id, activity_id))
                act_perf_rows = cursor.fetchall()
                if act_perf_rows:
                    # Map segment names and add 'overall' aggregate
                    act_perf_list = []
                    total_pre_weighted = 0
                    total_post_weighted = 0
                    total_pre_n = 0  # n with valid pre_score
                    total_post_n = 0  # n with valid post_score
                    for ap in act_perf_rows:
                        db_seg = ap["specialty"]
                        frontend_seg = SEGMENT_MAP.get(db_seg, db_seg.lower() if db_seg else 'unknown')
                        pre_score = ap["pre_score"]
                        post_score = ap["post_score"]
                        pre_n = ap["pre_n"] or 0
                        post_n = ap["post_n"] or 0
                        act_perf_list.append({
                            "segment": frontend_seg,
                            "pre_score": pre_score,
                            "post_score": post_score,
                            "pre_n": pre_n if pre_score is not None else None,
                            "post_n": post_n if post_score is not None else None
                        })
                        if pre_score is not None and pre_n > 0:
                            total_pre_weighted += pre_score * pre_n
                            total_pre_n += pre_n
                        if post_score is not None and post_n > 0:
                            total_post_weighted += post_score * post_n
                            total_post_n += post_n
                    # Add 'overall' for this activity (only include scores that have data)
                    act_perf_list.insert(0, {
                        "segment": "overall",
                        "pre_score": total_pre_weighted / total_pre_n if total_pre_n > 0 else None,
                        "post_score": total_post_weighted / total_post_n if total_post_n > 0 else None,
                        "pre_n": total_pre_n if total_pre_n > 0 else None,
                        "post_n": total_post_n if total_post_n > 0 else None
                    })
                    act_detail["performance"] = act_perf_list

                activity_details.append(act_detail)
            
            # Parse incorrect answers
            incorrect_answers = None
            if row["incorrect_answers"]:
                try:
                    incorrect_answers = json.loads(row["incorrect_answers"])
                except json.JSONDecodeError:
                    incorrect_answers = []
            
            # Helper to safely get row value
            def safe_get(key, default=None):
                return row[key] if key in row.keys() else default

            return {
                "id": row["id"],
                "source_question_id": safe_get("source_question_id"),  # Original ID from checkpoint
                "source_id": safe_get("source_id"),  # Links to Snowflake
                "question_stem": row["question_stem"],
                "correct_answer": row["correct_answer"],
                "incorrect_answers": incorrect_answers,
                "source_file": row["source_file"],
                "tags": {
                    # === Group A: Core Classification ===
                    "topic": safe_get("topic"),
                    "topic_confidence": safe_get("topic_confidence"),
                    "topic_method": safe_get("topic_method"),
                    "disease_state": safe_get("disease_state"),  # Legacy field for backwards compatibility
                    "disease_state_1": safe_get("disease_state_1") or safe_get("disease_state"),  # Fallback to old field
                    "disease_state_2": safe_get("disease_state_2"),  # Rare: secondary disease state
                    "disease_state_confidence": safe_get("disease_state_confidence"),
                    "disease_stage": safe_get("disease_stage"),
                    "disease_stage_confidence": safe_get("disease_stage_confidence"),
                    "disease_type_1": safe_get("disease_type_1") or safe_get("disease_type"),  # Fallback to old field
                    "disease_type_2": safe_get("disease_type_2"),
                    "disease_type_confidence": safe_get("disease_type_confidence"),
                    "treatment_line": safe_get("treatment_line"),
                    "treatment_line_confidence": safe_get("treatment_line_confidence"),

                    # === Multi-value Fields ===
                    "treatment_1": safe_get("treatment_1") or safe_get("treatment"),  # Fallback to old field
                    "treatment_2": safe_get("treatment_2"),
                    "treatment_3": safe_get("treatment_3"),
                    "treatment_4": safe_get("treatment_4"),
                    "treatment_5": safe_get("treatment_5"),
                    "treatment_confidence": safe_get("treatment_confidence"),
                    "biomarker_1": safe_get("biomarker_1") or safe_get("biomarker"),  # Fallback to old field
                    "biomarker_2": safe_get("biomarker_2"),
                    "biomarker_3": safe_get("biomarker_3"),
                    "biomarker_4": safe_get("biomarker_4"),
                    "biomarker_5": safe_get("biomarker_5"),
                    "biomarker_confidence": safe_get("biomarker_confidence"),
                    "trial_1": safe_get("trial_1") or safe_get("trial"),  # Fallback to old field
                    "trial_2": safe_get("trial_2"),
                    "trial_3": safe_get("trial_3"),
                    "trial_4": safe_get("trial_4"),
                    "trial_5": safe_get("trial_5"),
                    "trial_confidence": safe_get("trial_confidence"),

                    # === Group B: Patient Characteristics ===
                    "treatment_eligibility": safe_get("treatment_eligibility"),
                    "age_group": safe_get("age_group"),
                    "organ_dysfunction": safe_get("organ_dysfunction"),
                    "fitness_status": safe_get("fitness_status"),
                    "disease_specific_factor": safe_get("disease_specific_factor"),
                    "comorbidity_1": safe_get("comorbidity_1"),
                    "comorbidity_2": safe_get("comorbidity_2"),
                    "comorbidity_3": safe_get("comorbidity_3"),

                    # === Group C: Treatment Metadata ===
                    "drug_class_1": safe_get("drug_class_1"),
                    "drug_class_2": safe_get("drug_class_2"),
                    "drug_class_3": safe_get("drug_class_3"),
                    "drug_target_1": safe_get("drug_target_1"),
                    "drug_target_2": safe_get("drug_target_2"),
                    "drug_target_3": safe_get("drug_target_3"),
                    "prior_therapy_1": safe_get("prior_therapy_1"),
                    "prior_therapy_2": safe_get("prior_therapy_2"),
                    "prior_therapy_3": safe_get("prior_therapy_3"),
                    "resistance_mechanism": safe_get("resistance_mechanism"),

                    # === Group D: Clinical Context ===
                    "metastatic_site_1": safe_get("metastatic_site_1"),
                    "metastatic_site_2": safe_get("metastatic_site_2"),
                    "metastatic_site_3": safe_get("metastatic_site_3"),
                    "symptom_1": safe_get("symptom_1"),
                    "symptom_2": safe_get("symptom_2"),
                    "symptom_3": safe_get("symptom_3"),
                    "performance_status": safe_get("performance_status"),

                    # === Group E: Safety/Toxicity ===
                    "toxicity_type_1": safe_get("toxicity_type_1"),
                    "toxicity_type_2": safe_get("toxicity_type_2"),
                    "toxicity_type_3": safe_get("toxicity_type_3"),
                    "toxicity_type_4": safe_get("toxicity_type_4"),
                    "toxicity_type_5": safe_get("toxicity_type_5"),
                    "toxicity_organ": safe_get("toxicity_organ"),
                    "toxicity_grade": safe_get("toxicity_grade"),

                    # === Group F: Efficacy/Outcomes ===
                    "efficacy_endpoint_1": safe_get("efficacy_endpoint_1"),
                    "efficacy_endpoint_2": safe_get("efficacy_endpoint_2"),
                    "efficacy_endpoint_3": safe_get("efficacy_endpoint_3"),
                    "outcome_context": safe_get("outcome_context"),
                    "clinical_benefit": safe_get("clinical_benefit"),

                    # === Group G: Evidence/Guidelines ===
                    "guideline_source_1": safe_get("guideline_source_1"),
                    "guideline_source_2": safe_get("guideline_source_2"),
                    "evidence_type": safe_get("evidence_type"),

                    # === Group H: Question Format/Quality ===
                    "cme_outcome_level": safe_get("cme_outcome_level"),
                    "data_response_type": safe_get("data_response_type"),
                    "stem_type": safe_get("stem_type"),
                    "lead_in_type": safe_get("lead_in_type"),
                    "answer_format": safe_get("answer_format"),
                    "answer_length_pattern": safe_get("answer_length_pattern"),
                    "distractor_homogeneity": safe_get("distractor_homogeneity"),
                    "flaw_absolute_terms": safe_get("flaw_absolute_terms"),
                    "flaw_grammatical_cue": safe_get("flaw_grammatical_cue"),
                    "flaw_implausible_distractor": safe_get("flaw_implausible_distractor"),
                    "flaw_clang_association": safe_get("flaw_clang_association"),
                    "flaw_convergence_vulnerability": safe_get("flaw_convergence_vulnerability"),
                    "flaw_double_negative": safe_get("flaw_double_negative"),

                    # === Computed Fields ===
                    "answer_option_count": safe_get("answer_option_count"),
                    "correct_answer_position": safe_get("correct_answer_position"),

                    # === Review metadata ===
                    "needs_review": safe_get("needs_review", False),
                    "review_flags": json.loads(row["review_flags"]) if (safe_get("review_flags")) else None,
                    "review_reason": safe_get("review_reason"),
                    "flagged_at": safe_get("flagged_at"),
                    "agreement_level": safe_get("agreement_level"),
                    "tag_status": safe_get("tag_status"),  # Computed from 8 core tags
                    "worst_case_agreement": safe_get("worst_case_agreement"),  # Worst case across ALL fields
                },
                "performance": performance,
                "activities": activities,
                "activity_details": activity_details,
                # QCore quality score
                "qcore_score": safe_get("qcore_score"),
                "qcore_grade": safe_get("qcore_grade"),
                "qcore_breakdown": json.loads(row["qcore_breakdown"]) if safe_get("qcore_breakdown") else None
            }

    def get_filter_options(self) -> Dict[str, List[Dict]]:
        """Get all available filter options with counts (70-field schema, oncology only)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            options = {}

            # Base filter to exclude non-oncology and duplicate questions
            oncology_filter = "(q.is_oncology IS NULL OR q.is_oncology = 1) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))"

            # Get unique values with counts for each simple tag field
            simple_tag_fields = [
                ("topics", "topic"),
                # disease_states handled separately - aggregates disease_state_1, disease_state_2, and legacy disease_state
                ("disease_stages", "disease_stage"),
                ("treatment_lines", "treatment_line"),
                # Patient characteristics (70-field schema)
                ("treatment_eligibilities", "treatment_eligibility"),
                ("age_groups", "age_group"),
                ("fitness_statuses", "fitness_status"),
                ("organ_dysfunctions", "organ_dysfunction"),
            ]

            for option_name, field_name in simple_tag_fields:
                cursor.execute(f"""
                    SELECT t.{field_name} as value, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    WHERE t.{field_name} IS NOT NULL AND t.{field_name} != ''
                    AND {oncology_filter}
                    GROUP BY t.{field_name}
                    ORDER BY count DESC
                """)
                options[option_name] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Multi-value fields: aggregate across all slots (oncology only)
            # Disease states (disease_state_1, disease_state_2, and legacy disease_state for backwards compatibility)
            cursor.execute(f"""
                SELECT value, SUM(cnt) as count FROM (
                    SELECT t.disease_state_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state_1 IS NOT NULL AND t.disease_state_1 != '' AND {oncology_filter} GROUP BY t.disease_state_1
                    UNION ALL
                    SELECT t.disease_state_2 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state_2 IS NOT NULL AND t.disease_state_2 != '' AND {oncology_filter} GROUP BY t.disease_state_2
                    UNION ALL
                    SELECT t.disease_state as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state IS NOT NULL AND t.disease_state != '' AND t.disease_state_1 IS NULL AND {oncology_filter} GROUP BY t.disease_state
                )
                GROUP BY value ORDER BY count DESC
            """)
            options["disease_states"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Disease types (disease_type_1 and disease_type_2)
            cursor.execute(f"""
                SELECT value, SUM(cnt) as count FROM (
                    SELECT t.disease_type_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_type_1 IS NOT NULL AND t.disease_type_1 != '' AND {oncology_filter} GROUP BY t.disease_type_1
                    UNION ALL
                    SELECT t.disease_type_2 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_type_2 IS NOT NULL AND t.disease_type_2 != '' AND {oncology_filter} GROUP BY t.disease_type_2
                )
                GROUP BY value ORDER BY count DESC
            """)
            options["disease_types"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Treatments (treatment_1 through treatment_5)
            cursor.execute(f"""
                SELECT value, SUM(cnt) as count FROM (
                    SELECT t.treatment_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_1 IS NOT NULL AND t.treatment_1 != '' AND {oncology_filter} GROUP BY t.treatment_1
                    UNION ALL
                    SELECT t.treatment_2 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_2 IS NOT NULL AND t.treatment_2 != '' AND {oncology_filter} GROUP BY t.treatment_2
                    UNION ALL
                    SELECT t.treatment_3 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_3 IS NOT NULL AND t.treatment_3 != '' AND {oncology_filter} GROUP BY t.treatment_3
                    UNION ALL
                    SELECT t.treatment_4 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_4 IS NOT NULL AND t.treatment_4 != '' AND {oncology_filter} GROUP BY t.treatment_4
                    UNION ALL
                    SELECT t.treatment_5 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_5 IS NOT NULL AND t.treatment_5 != '' AND {oncology_filter} GROUP BY t.treatment_5
                )
                GROUP BY value ORDER BY count DESC
            """)
            options["treatments"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Biomarkers (biomarker_1 through biomarker_5)
            cursor.execute(f"""
                SELECT value, SUM(cnt) as count FROM (
                    SELECT t.biomarker_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_1 IS NOT NULL AND t.biomarker_1 != '' AND {oncology_filter} GROUP BY t.biomarker_1
                    UNION ALL
                    SELECT t.biomarker_2 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_2 IS NOT NULL AND t.biomarker_2 != '' AND {oncology_filter} GROUP BY t.biomarker_2
                    UNION ALL
                    SELECT t.biomarker_3 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_3 IS NOT NULL AND t.biomarker_3 != '' AND {oncology_filter} GROUP BY t.biomarker_3
                    UNION ALL
                    SELECT t.biomarker_4 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_4 IS NOT NULL AND t.biomarker_4 != '' AND {oncology_filter} GROUP BY t.biomarker_4
                    UNION ALL
                    SELECT t.biomarker_5 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_5 IS NOT NULL AND t.biomarker_5 != '' AND {oncology_filter} GROUP BY t.biomarker_5
                )
                GROUP BY value ORDER BY count DESC
            """)
            options["biomarkers"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Trials (trial_1 through trial_5)
            cursor.execute(f"""
                SELECT value, SUM(cnt) as count FROM (
                    SELECT t.trial_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_1 IS NOT NULL AND t.trial_1 != '' AND {oncology_filter} GROUP BY t.trial_1
                    UNION ALL
                    SELECT t.trial_2 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_2 IS NOT NULL AND t.trial_2 != '' AND {oncology_filter} GROUP BY t.trial_2
                    UNION ALL
                    SELECT t.trial_3 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_3 IS NOT NULL AND t.trial_3 != '' AND {oncology_filter} GROUP BY t.trial_3
                    UNION ALL
                    SELECT t.trial_4 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_4 IS NOT NULL AND t.trial_4 != '' AND {oncology_filter} GROUP BY t.trial_4
                    UNION ALL
                    SELECT t.trial_5 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_5 IS NOT NULL AND t.trial_5 != '' AND {oncology_filter} GROUP BY t.trial_5
                )
                GROUP BY value ORDER BY count DESC
            """)
            options["trials"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Get activities (oncology only)
            cursor.execute(f"""
                SELECT qa.activity_name as value, COUNT(*) as count
                FROM question_activities qa
                JOIN questions q ON qa.question_id = q.id
                WHERE qa.activity_name IS NOT NULL AND qa.activity_name != ''
                AND {oncology_filter}
                GROUP BY qa.activity_name
                ORDER BY count DESC
            """)
            options["activities"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Get source files (oncology only, for batch tracking)
            cursor.execute(f"""
                SELECT source_file as value, COUNT(*) as count
                FROM questions
                WHERE source_file IS NOT NULL AND source_file != ''
                AND (is_oncology IS NULL OR is_oncology = 1)
                GROUP BY source_file
                ORDER BY count DESC
            """)
            options["source_files"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Advanced filter categories — data-driven via ADVANCED_FILTER_COLUMNS (oncology only)
            for cat_key, columns in self.ADVANCED_FILTER_COLUMNS.items():
                if cat_key in options:
                    continue  # Already computed above (e.g. treatment_eligibilities)
                if len(columns) == 1:
                    col = columns[0]
                    cursor.execute(f"""
                        SELECT t.{col} as value, COUNT(*) as count
                        FROM tags t
                        JOIN questions q ON t.question_id = q.id
                        WHERE t.{col} IS NOT NULL AND t.{col} != ''
                        AND {oncology_filter}
                        GROUP BY t.{col}
                        ORDER BY count DESC
                    """)
                    options[cat_key] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]
                else:
                    # Multi-slot: UNION ALL across columns (oncology only)
                    unions = " UNION ALL ".join(
                        f"SELECT t.{col} as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.{col} IS NOT NULL AND t.{col} != '' AND {oncology_filter} GROUP BY t.{col}"
                        for col in columns
                    )
                    cursor.execute(f"""
                        SELECT value, SUM(cnt) as count FROM ({unions})
                        GROUP BY value ORDER BY count DESC
                    """)
                    options[cat_key] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

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
        # Patient characteristics (70-field schema)
        treatment_eligibilities: Optional[List[str]] = None,
        age_groups: Optional[List[str]] = None,
        fitness_statuses: Optional[List[str]] = None,
        organ_dysfunctions: Optional[List[str]] = None,
        # Advanced filters
        advanced_filters: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Get filter options dynamically based on current selections.
        For each filter field, returns options that exist when OTHER filters are applied.
        This allows cascading/dependent filter behavior.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Define core filter fields - use primary slot for multi-value fields
            # disease_states handled separately via UNION ALL across disease_state_1, disease_state_2, and legacy disease_state
            core_filter_fields = {
                'topics': ('topic', topics),
                # 'disease_states' handled separately below
                'disease_stages': ('disease_stage', disease_stages),
                'disease_types': ('disease_type_1', disease_types),
                'treatment_lines': ('treatment_line', treatment_lines),
                'treatments': ('treatment_1', treatments),
                'biomarkers': ('biomarker_1', biomarkers),
                'trials': ('trial_1', trials),
                'treatment_eligibilities': ('treatment_eligibility', treatment_eligibilities),
                'age_groups': ('age_group', age_groups),
                'fitness_statuses': ('fitness_status', fitness_statuses),
                'organ_dysfunctions': ('organ_dysfunction', organ_dysfunctions),
            }

            # Track disease_states for special handling
            disease_states_filter = disease_states

            # Helper: build WHERE clauses from all active filters EXCEPT the excluded one
            def build_other_filters_where(exclude_key: str):
                clauses = []
                p = []
                # Core filters
                for name, (field, vals) in core_filter_fields.items():
                    if name != exclude_key and vals:
                        placeholders = ",".join("?" * len(vals))
                        clauses.append(f"{field} IN ({placeholders})")
                        p.extend(vals)
                # Handle disease_states specially (spans disease_state_1, disease_state_2, and legacy disease_state)
                if exclude_key != 'disease_states' and disease_states_filter:
                    placeholders = ",".join("?" * len(disease_states_filter))
                    clauses.append(f"(COALESCE(disease_state_1, disease_state) IN ({placeholders}) OR disease_state_2 IN ({placeholders}))")
                    p.extend(disease_states_filter)
                    p.extend(disease_states_filter)
                # Advanced filters
                if advanced_filters:
                    for cat_key, vals in advanced_filters.items():
                        if cat_key == exclude_key or not vals or cat_key not in self.ADVANCED_FILTER_COLUMNS:
                            continue
                        # Skip if already handled as core filter
                        if cat_key in core_filter_fields:
                            continue
                        columns = self.ADVANCED_FILTER_COLUMNS[cat_key]
                        if len(columns) == 1:
                            placeholders = ",".join("?" * len(vals))
                            clauses.append(f"{columns[0]} IN ({placeholders})")
                            p.extend(vals)
                        else:
                            or_parts = []
                            for col in columns:
                                placeholders = ",".join("?" * len(vals))
                                or_parts.append(f"{col} IN ({placeholders})")
                                p.extend(vals)
                            clauses.append(f"({' OR '.join(or_parts)})")
                return " AND ".join(clauses) if clauses else "1=1", p

            options = {}

            # Base filter - exclude non-oncology and duplicate questions
            oncology_filter = "(q.is_oncology IS NULL OR q.is_oncology = 1) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))"

            # Core filter options — each gets options with all OTHER filters applied
            for option_name, (field_name, _) in core_filter_fields.items():
                where_sql, params = build_other_filters_where(option_name)
                query = f"""
                    SELECT t.{field_name} as value, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    WHERE t.{field_name} IS NOT NULL AND t.{field_name} != ''
                    AND {oncology_filter}
                    AND {where_sql}
                    GROUP BY t.{field_name}
                    ORDER BY count DESC
                """
                cursor.execute(query, params)
                options[option_name] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Disease states: special handling with UNION ALL across disease_state_1, disease_state_2, and legacy disease_state
            where_sql, params = build_other_filters_where('disease_states')
            ds_query = f"""
                SELECT value, SUM(cnt) as count FROM (
                    SELECT t.disease_state_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state_1 IS NOT NULL AND t.disease_state_1 != '' AND {oncology_filter} AND {where_sql} GROUP BY t.disease_state_1
                    UNION ALL
                    SELECT t.disease_state_2 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state_2 IS NOT NULL AND t.disease_state_2 != '' AND {oncology_filter} AND {where_sql} GROUP BY t.disease_state_2
                    UNION ALL
                    SELECT t.disease_state as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state IS NOT NULL AND t.disease_state != '' AND t.disease_state_1 IS NULL AND {oncology_filter} AND {where_sql} GROUP BY t.disease_state
                )
                GROUP BY value ORDER BY count DESC
            """
            # Params need to be repeated 3 times (once for each UNION branch)
            cursor.execute(ds_query, params + params + params)
            options["disease_states"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Advanced filter category options — data-driven
            for cat_key, columns in self.ADVANCED_FILTER_COLUMNS.items():
                if cat_key in options:
                    continue  # Already computed as core filter
                where_sql, params = build_other_filters_where(cat_key)
                if len(columns) == 1:
                    col = columns[0]
                    cursor.execute(f"""
                        SELECT t.{col} as value, COUNT(*) as count
                        FROM tags t
                        JOIN questions q ON t.question_id = q.id
                        WHERE t.{col} IS NOT NULL AND t.{col} != ''
                        AND {oncology_filter}
                        AND {where_sql}
                        GROUP BY t.{col}
                        ORDER BY count DESC
                    """, params)
                    options[cat_key] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]
                else:
                    # Multi-slot: UNION ALL across columns, each with the same WHERE
                    unions = []
                    all_params = []
                    for col in columns:
                        unions.append(f"""
                            SELECT t.{col} as value, COUNT(*) as cnt
                            FROM tags t
                            JOIN questions q ON t.question_id = q.id
                            WHERE t.{col} IS NOT NULL AND t.{col} != ''
                            AND {oncology_filter}
                            AND {where_sql}
                            GROUP BY t.{col}
                        """)
                        all_params.extend(params)
                    cursor.execute(f"""
                        SELECT value, SUM(cnt) as count FROM ({' UNION ALL '.join(unions)})
                        GROUP BY value ORDER BY count DESC
                    """, all_params)
                    options[cat_key] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            # Get activities with all filters applied
            where_sql, params = build_other_filters_where('__activities__')
            cursor.execute(f"""
                SELECT qa.activity_name as value, COUNT(DISTINCT qa.question_id) as count
                FROM question_activities qa
                JOIN tags t ON qa.question_id = t.question_id
                JOIN questions q ON qa.question_id = q.id
                WHERE qa.activity_name IS NOT NULL AND qa.activity_name != ''
                AND {oncology_filter}
                AND {where_sql}
                GROUP BY qa.activity_name
                ORDER BY count DESC
            """, params)
            options["activities"] = [{"value": r["value"], "count": r["count"]} for r in cursor.fetchall()]

            return options
    
    # ============== Aggregation Operations for Reports ==============
    
    def aggregate_performance_by_tag(
        self,
        group_by: str,  # 'topic', 'disease_state', 'treatment', 'biomarker', 'trial'
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
        """
        Aggregate performance metrics grouped by a tag field.
        Returns list of {group_value, avg_pre_score, avg_post_score, total_n, question_count}.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Validate group_by field
            valid_group_fields = ['topic', 'disease_state', 'disease_stage', 'disease_type', 'treatment', 'biomarker', 'trial']
            if group_by not in valid_group_fields:
                raise ValueError(f"Invalid group_by field: {group_by}")
            
            where_clauses = [f"t.{group_by} IS NOT NULL", f"t.{group_by} != ''"]
            params = []
            
            # Apply tag filters
            if topics:
                placeholders = ",".join("?" * len(topics))
                where_clauses.append(f"t.topic IN ({placeholders})")
                params.extend(topics)
            
            if disease_states:
                # Search across disease_state_1, disease_state_2, and legacy disease_state field
                placeholders = ",".join("?" * len(disease_states))
                where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({placeholders}) OR t.disease_state_2 IN ({placeholders}))")
                params.extend(disease_states)
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
            
            # Activity and quarter filters
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

    def aggregate_performance_by_tag_and_segment(
        self,
        group_by: str,  # 'topic', 'disease_state', 'treatment', 'biomarker', 'trial'
        segments: List[str],  # audience segments to include
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
        """
        Aggregate performance metrics grouped by BOTH a tag field AND audience segment.
        Returns list of {group_value, segment, avg_pre_score, avg_post_score, total_n, question_count}.

        This allows comparing different audience segments within each tag group.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Validate group_by field
            valid_group_fields = ['topic', 'disease_state', 'disease_stage', 'disease_type', 'treatment', 'biomarker', 'trial']
            if group_by not in valid_group_fields:
                raise ValueError(f"Invalid group_by field: {group_by}")

            # Validate segments
            valid_segments = [
                'overall', 'medical_oncologist', 'app', 'academic',
                'community', 'surgical_oncologist', 'radiation_oncologist'
            ]
            segments = [s for s in segments if s in valid_segments]
            if not segments:
                return []

            where_clauses = [f"t.{group_by} IS NOT NULL", f"t.{group_by} != ''"]
            params = []

            # Segment filter
            placeholders = ",".join("?" * len(segments))
            where_clauses.append(f"p.segment IN ({placeholders})")
            params.extend(segments)

            # Apply tag filters
            if topics:
                ph = ",".join("?" * len(topics))
                where_clauses.append(f"t.topic IN ({ph})")
                params.extend(topics)

            if disease_states:
                # Search across disease_state_1, disease_state_2, and legacy disease_state field
                ph = ",".join("?" * len(disease_states))
                where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({ph}) OR t.disease_state_2 IN ({ph}))")
                params.extend(disease_states)
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

            # Activity and quarter filters
            activity_join = ""
            if activities or quarters:
                activity_join = """
                    JOIN question_activities qa ON q.id = qa.question_id
                    JOIN activities a ON qa.activity_id = a.id
                """
                if activities:
                    ph = ",".join("?" * len(activities))
                    where_clauses.append(f"qa.activity_name IN ({ph})")
                    params.extend(activities)
                if quarters:
                    ph = ",".join("?" * len(quarters))
                    where_clauses.append(f"a.quarter IN ({ph})")
                    params.extend(quarters)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT
                    t.{group_by} as group_value,
                    p.segment as segment,
                    AVG(p.pre_score) as avg_pre_score,
                    AVG(p.post_score) as avg_post_score,
                    SUM(COALESCE(p.pre_n, 0)) as total_pre_n,
                    SUM(COALESCE(p.post_n, 0)) as total_post_n,
                    COUNT(DISTINCT q.id) as question_count
                FROM questions q
                JOIN tags t ON q.id = t.question_id
                JOIN performance p ON q.id = p.question_id
                {activity_join}
                WHERE {where_sql}
                GROUP BY t.{group_by}, p.segment
                ORDER BY question_count DESC, t.{group_by}, p.segment
            """

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "group_value": row["group_value"],
                    "segment": row["segment"],
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
        """
        Aggregate performance metrics grouped by audience segment.

        Uses the performance table which stores scores per segment:
        - overall, medical_oncologist, app, academic, community,
          surgical_oncologist, radiation_oncologist

        Returns list of {segment, avg_pre_score, avg_post_score, total_n, question_count}.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Valid audience segments
            valid_segments = [
                'overall', 'medical_oncologist', 'app', 'academic',
                'community', 'surgical_oncologist', 'radiation_oncologist'
            ]

            # Filter to requested segments or use all
            target_segments = segments if segments else valid_segments
            target_segments = [s for s in target_segments if s in valid_segments]

            if not target_segments:
                return []

            where_clauses = []
            params = []

            # Segment filter
            placeholders = ",".join("?" * len(target_segments))
            where_clauses.append(f"p.segment IN ({placeholders})")
            params.extend(target_segments)

            # Tag filters (join with tags table)
            tag_join = ""
            if any([topics, disease_states, disease_stages, disease_types, treatment_lines, treatments, biomarkers, trials]):
                tag_join = "JOIN tags t ON q.id = t.question_id"

                if topics:
                    ph = ",".join("?" * len(topics))
                    where_clauses.append(f"t.topic IN ({ph})")
                    params.extend(topics)

                if disease_states:
                    # Search across disease_state_1, disease_state_2, and legacy disease_state field
                    ph = ",".join("?" * len(disease_states))
                    where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({ph}) OR t.disease_state_2 IN ({ph}))")
                    params.extend(disease_states)
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

            # Activity and quarter filters
            activity_join = ""
            if activities or quarters:
                activity_join = """
                    JOIN question_activities qa ON q.id = qa.question_id
                """
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

    def aggregate_performance_by_demographic(
        self,
        segment_by: str,  # 'specialty', 'practice_setting', 'region'
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
        activities: Optional[List[str]] = None,
        quarters: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Aggregate performance metrics grouped by a demographic field.
        Uses demographic_performance table for granular segmentation.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Validate segment_by field
            valid_segment_fields = ['specialty', 'practice_setting', 'region', 'practice_state']
            if segment_by not in valid_segment_fields:
                raise ValueError(f"Invalid segment_by field: {segment_by}")
            
            where_clauses = [f"dp.{segment_by} IS NOT NULL", f"dp.{segment_by} != ''"]
            params = []
            
            # Apply tag filters (join with tags table)
            tag_join = ""
            if any([topics, disease_states, treatments, biomarkers]):
                tag_join = "JOIN tags t ON q.id = t.question_id"
                
                if topics:
                    placeholders = ",".join("?" * len(topics))
                    where_clauses.append(f"t.topic IN ({placeholders})")
                    params.extend(topics)
                
                if disease_states:
                    # Search across disease_state_1, disease_state_2, and legacy disease_state field
                    placeholders = ",".join("?" * len(disease_states))
                    where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({placeholders}) OR t.disease_state_2 IN ({placeholders}))")
                    params.extend(disease_states)
                    params.extend(disease_states)

                if treatments:
                    placeholders = ",".join("?" * len(treatments))
                    where_clauses.append(f"t.treatment IN ({placeholders})")
                    params.extend(treatments)

                if biomarkers:
                    placeholders = ",".join("?" * len(biomarkers))
                    where_clauses.append(f"t.biomarker IN ({placeholders})")
                    params.extend(biomarkers)

            # Activity and quarter filters
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
                    SUM(COALESCE(dp.pre_n, 0) + COALESCE(dp.post_n, 0)) as total_n,
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
        segment_by: Optional[str] = None,  # 'specialty', 'practice_setting', 'region' or None for overall
        topics: Optional[List[str]] = None,
        disease_states: Optional[List[str]] = None,
        treatments: Optional[List[str]] = None,
        biomarkers: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Get performance trends over time (by quarter).
        Returns list of {quarter, segment_value (if segmented), avg_pre_score, avg_post_score, total_n}.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            where_clauses = ["a.quarter IS NOT NULL"]
            params = []
            
            # Tag filters
            tag_join = ""
            if any([topics, disease_states, treatments, biomarkers]):
                tag_join = "JOIN tags t ON q.id = t.question_id"
                
                if topics:
                    placeholders = ",".join("?" * len(topics))
                    where_clauses.append(f"t.topic IN ({placeholders})")
                    params.extend(topics)
                
                if disease_states:
                    # Search across disease_state_1, disease_state_2, and legacy disease_state field
                    placeholders = ",".join("?" * len(disease_states))
                    where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({placeholders}) OR t.disease_state_2 IN ({placeholders}))")
                    params.extend(disease_states)
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
                # Use demographic_performance table for segmented trends
                query = f"""
                    SELECT
                        a.quarter,
                        dp.{segment_by} as segment_value,
                        AVG(dp.pre_score) as avg_pre_score,
                        AVG(dp.post_score) as avg_post_score,
                        SUM(COALESCE(dp.pre_n, 0) + COALESCE(dp.post_n, 0)) as total_n
                    FROM demographic_performance dp
                    JOIN questions q ON dp.question_id = q.id
                    JOIN activities a ON dp.activity_id = a.id
                    {tag_join}
                    WHERE {where_sql} AND dp.{segment_by} IS NOT NULL
                    GROUP BY a.quarter, dp.{segment_by}
                    ORDER BY a.quarter, dp.{segment_by}
                """
            else:
                # Overall trends using performance table
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
            
            # Specialties
            cursor.execute("""
                SELECT DISTINCT specialty FROM demographic_performance 
                WHERE specialty IS NOT NULL AND specialty != ''
                ORDER BY specialty
            """)
            options["specialties"] = [row["specialty"] for row in cursor.fetchall()]
            
            # Practice settings
            cursor.execute("""
                SELECT DISTINCT practice_setting FROM demographic_performance 
                WHERE practice_setting IS NOT NULL AND practice_setting != ''
                ORDER BY practice_setting
            """)
            options["practice_settings"] = [row["practice_setting"] for row in cursor.fetchall()]
            
            # Regions
            cursor.execute("""
                SELECT DISTINCT region FROM demographic_performance 
                WHERE region IS NOT NULL AND region != ''
                ORDER BY region
            """)
            options["regions"] = [row["region"] for row in cursor.fetchall()]
            
            # States
            cursor.execute("""
                SELECT DISTINCT practice_state FROM demographic_performance 
                WHERE practice_state IS NOT NULL AND practice_state != ''
                ORDER BY practice_state
            """)
            options["practice_states"] = [row["practice_state"] for row in cursor.fetchall()]
            
            return options
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics (unique oncology questions only, excludes duplicates)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Count unique oncology questions (exclude non-oncology and confirmed duplicates)
            cursor.execute("""
                SELECT COUNT(*) FROM questions
                WHERE (is_oncology IS NULL OR is_oncology = 1)
                AND (canonical_source_id IS NULL OR canonical_source_id = CAST(source_id AS TEXT))
            """)
            total_questions = cursor.fetchone()[0]

            # Count tagged unique oncology questions only
            cursor.execute("""
                SELECT COUNT(*) FROM tags t
                JOIN questions q ON t.question_id = q.id
                WHERE t.topic IS NOT NULL
                AND (q.is_oncology IS NULL OR q.is_oncology = 1)
                AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
            """)
            tagged_questions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT activity_name) FROM question_activities")
            total_activities = cursor.fetchone()[0]

            # Count questions needing review (flagged for review, excluding non-oncology and duplicates)
            cursor.execute("""
                SELECT COUNT(*) FROM tags t
                JOIN questions q ON t.question_id = q.id
                WHERE t.needs_review = 1
                AND (q.is_oncology IS NULL OR q.is_oncology = 1)
                AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
            """)
            questions_need_review = cursor.fetchone()[0]

            # Count confirmed duplicate questions (for reference)
            cursor.execute("""
                SELECT COUNT(*) FROM questions
                WHERE canonical_source_id IS NOT NULL
                AND canonical_source_id != CAST(source_id AS TEXT)
            """)
            duplicate_questions = cursor.fetchone()[0]

            return {
                "total_questions": total_questions,
                "tagged_questions": tagged_questions,
                "total_activities": total_activities,
                "questions_need_review": questions_need_review,
                "duplicate_questions": duplicate_questions
            }

    # ============== Novel Entity Operations ==============

    def insert_novel_entity(
        self,
        entity_name: str,
        entity_type: str,
        confidence: float = 0.75,
        question_id: Optional[int] = None,
        source_text: Optional[str] = None,
        drug_class: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Insert or update a novel entity with deduplication.

        If entity already exists, increments occurrence_count and updates last_seen.
        Returns the novel_entity id.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Normalize the entity name
            normalized_name = entity_name.lower().strip()

            # Check if entity already exists
            cursor.execute("""
                SELECT id, occurrence_count, confidence
                FROM novel_entities
                WHERE normalized_name = ? AND entity_type = ?
            """, (normalized_name, entity_type))
            existing = cursor.fetchone()

            if existing:
                # Update existing entity - rolling average for confidence
                entity_id = existing["id"]
                old_count = existing["occurrence_count"]
                old_confidence = existing["confidence"] or 0.75
                new_confidence = (old_confidence * old_count + confidence) / (old_count + 1)

                cursor.execute("""
                    UPDATE novel_entities
                    SET occurrence_count = occurrence_count + 1,
                        last_seen = CURRENT_TIMESTAMP,
                        confidence = ?
                    WHERE id = ?
                """, (new_confidence, entity_id))
            else:
                # Insert new entity
                cursor.execute("""
                    INSERT INTO novel_entities
                    (entity_name, entity_type, normalized_name, confidence, drug_class, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (entity_name, entity_type, normalized_name, confidence, drug_class, notes))
                entity_id = cursor.lastrowid

            # Record the occurrence if we have context
            if source_text or question_id:
                cursor.execute("""
                    INSERT INTO novel_entity_occurrences
                    (novel_entity_id, question_id, source_text, extraction_confidence)
                    VALUES (?, ?, ?, ?)
                """, (entity_id, question_id, source_text or "", confidence))

            conn.commit()
            return entity_id

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
        """
        List novel entities with filters and pagination.
        Returns (entities, total_count).
        """
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

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM novel_entities WHERE {where_sql}", params)
            total = cursor.fetchone()[0]

            # Valid sort columns
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
                # Parse synonyms JSON if present
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

            # Get entity
            cursor.execute("SELECT * FROM novel_entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if not row:
                return None

            entity = dict(row)

            # Parse synonyms
            if entity.get("synonyms"):
                try:
                    entity["synonyms"] = json.loads(entity["synonyms"])
                except json.JSONDecodeError:
                    entity["synonyms"] = []
            else:
                entity["synonyms"] = []

            # Get occurrences with question details
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

    def approve_novel_entity(
        self,
        entity_id: int,
        reviewed_by: str,
        drug_class: Optional[str] = None,
        synonyms: Optional[List[str]] = None,
        auto_approved: bool = False
    ) -> bool:
        """
        Approve a novel entity for addition to KB.
        Returns True if successful.
        """
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
        """
        Reject a novel entity.
        Returns True if successful.
        """
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
        """
        Auto-approve entities meeting confidence and occurrence thresholds.
        Returns count of entities approved.
        """
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

    def get_novel_entity_stats(self) -> Dict[str, Any]:
        """Get statistics about novel entities."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM novel_entities
                GROUP BY status
            """)
            status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            # Counts by entity type
            cursor.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM novel_entities
                WHERE status = 'pending'
                GROUP BY entity_type
            """)
            pending_by_type = {row["entity_type"]: row["count"] for row in cursor.fetchall()}

            # High-confidence pending (ready for auto-approve)
            cursor.execute("""
                SELECT COUNT(*) FROM novel_entities
                WHERE status = 'pending'
                AND confidence >= 0.90
                AND occurrence_count >= 3
            """)
            ready_for_auto_approve = cursor.fetchone()[0]

            # Recent activity
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

    def get_approved_entities_for_kb(
        self,
        entity_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all approved entities ready to be added to KB.
        Used by KBUpdater service.
        """
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
        """
        Get questions matching filters with full details for Excel export.
        Returns list of question dicts with all tags and performance data.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["(q.is_oncology IS NULL OR q.is_oncology = 1)"]
            params = []

            # Tag filters
            if topics:
                ph = ",".join("?" * len(topics))
                where_clauses.append(f"t.topic IN ({ph})")
                params.extend(topics)

            if disease_states:
                # Search across disease_state_1, disease_state_2, and legacy disease_state field
                ph = ",".join("?" * len(disease_states))
                where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({ph}) OR t.disease_state_2 IN ({ph}))")
                params.extend(disease_states)
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

            # Activity filter
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

    def get_questions_for_full_export(
        self,
        source_files: Optional[List[str]] = None,
        needs_review: Optional[bool] = None,
        disease_states: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Get questions with ALL 70 tag fields for comprehensive Excel export.
        Supports filtering by source_file for batch workflow.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["(q.is_oncology IS NULL OR q.is_oncology = 1)"]
            params = []

            if source_files:
                ph = ",".join("?" * len(source_files))
                where_clauses.append(f"q.source_file IN ({ph})")
                params.extend(source_files)

            if needs_review is True:
                where_clauses.append("t.needs_review = 1")
            elif needs_review is False:
                where_clauses.append("(t.needs_review IS NULL OR t.needs_review = 0)")

            if disease_states:
                # Search across disease_state_1, disease_state_2, and legacy disease_state field
                ph = ",".join("?" * len(disease_states))
                where_clauses.append(f"(COALESCE(t.disease_state_1, t.disease_state) IN ({ph}) OR t.disease_state_2 IN ({ph}))")
                params.extend(disease_states)
                params.extend(disease_states)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT DISTINCT
                    q.id,
                    q.question_stem,
                    q.correct_answer,
                    q.incorrect_answers,
                    q.source_file,
                    -- Core Classification
                    t.topic,
                    t.disease_state,
                    t.disease_type_1,
                    t.disease_type_2,
                    t.disease_stage,
                    t.treatment_line,
                    -- Multi-value Fields
                    t.treatment_1, t.treatment_2, t.treatment_3, t.treatment_4, t.treatment_5,
                    t.biomarker_1, t.biomarker_2, t.biomarker_3, t.biomarker_4, t.biomarker_5,
                    t.trial_1, t.trial_2, t.trial_3, t.trial_4, t.trial_5,
                    -- Patient Characteristics
                    t.treatment_eligibility,
                    t.age_group,
                    t.organ_dysfunction,
                    t.fitness_status,
                    t.disease_specific_factor,
                    t.comorbidity_1, t.comorbidity_2, t.comorbidity_3,
                    -- Treatment Metadata
                    t.drug_class_1, t.drug_class_2, t.drug_class_3,
                    t.drug_target_1, t.drug_target_2, t.drug_target_3,
                    t.prior_therapy_1, t.prior_therapy_2, t.prior_therapy_3,
                    t.resistance_mechanism,
                    -- Clinical Context
                    t.metastatic_site_1, t.metastatic_site_2, t.metastatic_site_3,
                    t.symptom_1, t.symptom_2, t.symptom_3,
                    t.performance_status,
                    -- Safety/Toxicity
                    t.toxicity_type_1, t.toxicity_type_2, t.toxicity_type_3, t.toxicity_type_4, t.toxicity_type_5,
                    t.toxicity_organ,
                    t.toxicity_grade,
                    -- Efficacy/Outcomes
                    t.efficacy_endpoint_1, t.efficacy_endpoint_2, t.efficacy_endpoint_3,
                    t.outcome_context,
                    t.clinical_benefit,
                    -- Evidence/Guidelines
                    t.guideline_source_1, t.guideline_source_2,
                    t.evidence_type,
                    -- Question Format/Quality
                    t.cme_outcome_level,
                    t.data_response_type,
                    t.stem_type,
                    t.lead_in_type,
                    t.answer_format,
                    t.answer_length_pattern,
                    t.distractor_homogeneity,
                    t.flaw_absolute_terms,
                    t.flaw_grammatical_cue,
                    t.flaw_implausible_distractor,
                    t.flaw_clang_association,
                    t.flaw_convergence_vulnerability,
                    t.flaw_double_negative,
                    -- Computed Fields
                    t.answer_option_count,
                    t.correct_answer_position,
                    -- Performance
                    p.pre_score,
                    p.post_score,
                    p.pre_n as sample_size,
                    (SELECT GROUP_CONCAT(qa2.activity_name, '; ')
                     FROM question_activities qa2
                     WHERE qa2.question_id = q.id) as activities
                FROM questions q
                LEFT JOIN tags t ON q.id = t.question_id
                LEFT JOIN performance p ON q.id = p.question_id AND p.segment = 'overall'
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
                    "source_file": row["source_file"],
                    # Core Classification
                    "topic": row["topic"],
                    "disease_state": row["disease_state"],
                    "disease_type_1": row["disease_type_1"],
                    "disease_type_2": row["disease_type_2"],
                    "disease_stage": row["disease_stage"],
                    "treatment_line": row["treatment_line"],
                    # Multi-value Fields
                    "treatment_1": row["treatment_1"],
                    "treatment_2": row["treatment_2"],
                    "treatment_3": row["treatment_3"],
                    "treatment_4": row["treatment_4"],
                    "treatment_5": row["treatment_5"],
                    "biomarker_1": row["biomarker_1"],
                    "biomarker_2": row["biomarker_2"],
                    "biomarker_3": row["biomarker_3"],
                    "biomarker_4": row["biomarker_4"],
                    "biomarker_5": row["biomarker_5"],
                    "trial_1": row["trial_1"],
                    "trial_2": row["trial_2"],
                    "trial_3": row["trial_3"],
                    "trial_4": row["trial_4"],
                    "trial_5": row["trial_5"],
                    # Patient Characteristics
                    "treatment_eligibility": row["treatment_eligibility"],
                    "age_group": row["age_group"],
                    "organ_dysfunction": row["organ_dysfunction"],
                    "fitness_status": row["fitness_status"],
                    "disease_specific_factor": row["disease_specific_factor"],
                    "comorbidity_1": row["comorbidity_1"],
                    "comorbidity_2": row["comorbidity_2"],
                    "comorbidity_3": row["comorbidity_3"],
                    # Treatment Metadata
                    "drug_class_1": row["drug_class_1"],
                    "drug_class_2": row["drug_class_2"],
                    "drug_class_3": row["drug_class_3"],
                    "drug_target_1": row["drug_target_1"],
                    "drug_target_2": row["drug_target_2"],
                    "drug_target_3": row["drug_target_3"],
                    "prior_therapy_1": row["prior_therapy_1"],
                    "prior_therapy_2": row["prior_therapy_2"],
                    "prior_therapy_3": row["prior_therapy_3"],
                    "resistance_mechanism": row["resistance_mechanism"],
                    # Clinical Context
                    "metastatic_site_1": row["metastatic_site_1"],
                    "metastatic_site_2": row["metastatic_site_2"],
                    "metastatic_site_3": row["metastatic_site_3"],
                    "symptom_1": row["symptom_1"],
                    "symptom_2": row["symptom_2"],
                    "symptom_3": row["symptom_3"],
                    "performance_status": row["performance_status"],
                    # Safety/Toxicity
                    "toxicity_type_1": row["toxicity_type_1"],
                    "toxicity_type_2": row["toxicity_type_2"],
                    "toxicity_type_3": row["toxicity_type_3"],
                    "toxicity_type_4": row["toxicity_type_4"],
                    "toxicity_type_5": row["toxicity_type_5"],
                    "toxicity_organ": row["toxicity_organ"],
                    "toxicity_grade": row["toxicity_grade"],
                    # Efficacy/Outcomes
                    "efficacy_endpoint_1": row["efficacy_endpoint_1"],
                    "efficacy_endpoint_2": row["efficacy_endpoint_2"],
                    "efficacy_endpoint_3": row["efficacy_endpoint_3"],
                    "outcome_context": row["outcome_context"],
                    "clinical_benefit": row["clinical_benefit"],
                    # Evidence/Guidelines
                    "guideline_source_1": row["guideline_source_1"],
                    "guideline_source_2": row["guideline_source_2"],
                    "evidence_type": row["evidence_type"],
                    # Question Format/Quality
                    "cme_outcome_level": row["cme_outcome_level"],
                    "data_response_type": row["data_response_type"],
                    "stem_type": row["stem_type"],
                    "lead_in_type": row["lead_in_type"],
                    "answer_format": row["answer_format"],
                    "answer_length_pattern": row["answer_length_pattern"],
                    "distractor_homogeneity": row["distractor_homogeneity"],
                    "flaw_absolute_terms": self._str_to_bool(row["flaw_absolute_terms"]),
                    "flaw_grammatical_cue": self._str_to_bool(row["flaw_grammatical_cue"]),
                    "flaw_implausible_distractor": self._str_to_bool(row["flaw_implausible_distractor"]),
                    "flaw_clang_association": self._str_to_bool(row["flaw_clang_association"]),
                    "flaw_convergence_vulnerability": self._str_to_bool(row["flaw_convergence_vulnerability"]),
                    "flaw_double_negative": self._str_to_bool(row["flaw_double_negative"]),
                    # Computed Fields
                    "answer_option_count": row["answer_option_count"],
                    "correct_answer_position": row["correct_answer_position"],
                    # Performance
                    "pre_score": row["pre_score"],
                    "post_score": row["post_score"],
                    "knowledge_gain": knowledge_gain,
                    "sample_size": row["sample_size"],
                    "activities": row["activities"]
                })

            return results

    # ============== User-Defined Values Operations ==============

    def get_user_defined_values(self, field_name: str) -> List[str]:
        """
        Get all user-defined values for a specific field.

        Args:
            field_name: The tag field name (e.g., 'treatment_1', 'drug_class_1')

        Returns:
            List of user-defined values for this field
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value FROM user_defined_values
                WHERE field_name = ?
                ORDER BY value
            """, (field_name,))
            return [row["value"] for row in cursor.fetchall()]

    def get_all_user_defined_values(self) -> Dict[str, List[str]]:
        """
        Get all user-defined values grouped by field name.

        Returns:
            Dict mapping field_name -> list of values
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT field_name, value FROM user_defined_values
                ORDER BY field_name, value
            """)

            result: Dict[str, List[str]] = {}
            for row in cursor.fetchall():
                field_name = row["field_name"]
                if field_name not in result:
                    result[field_name] = []
                result[field_name].append(row["value"])

            return result

    def add_user_defined_value(self, field_name: str, value: str, created_by: Optional[str] = None) -> bool:
        """
        Add a user-defined value for a field.

        Args:
            field_name: The tag field name
            value: The custom value to add
            created_by: Optional username who added this value

        Returns:
            True if the value was added, False if it already exists
        """
        if not value or not value.strip():
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO user_defined_values (field_name, value, created_by)
                    VALUES (?, ?, ?)
                """, (field_name, value.strip(), created_by))
                conn.commit()
                logger.info(f"Added user-defined value '{value}' for field '{field_name}'")
                return True
            except sqlite3.IntegrityError:
                # Value already exists for this field
                return False

    def add_user_defined_values_batch(self, values: List[Dict[str, str]], created_by: Optional[str] = None) -> int:
        """
        Add multiple user-defined values at once.

        Args:
            values: List of dicts with 'field_name' and 'value' keys
            created_by: Optional username who added these values

        Returns:
            Number of new values added
        """
        added_count = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in values:
                field_name = item.get("field_name")
                value = item.get("value")
                if field_name and value and value.strip():
                    try:
                        cursor.execute("""
                            INSERT INTO user_defined_values (field_name, value, created_by)
                            VALUES (?, ?, ?)
                        """, (field_name, value.strip(), created_by))
                        added_count += 1
                    except sqlite3.IntegrityError:
                        # Value already exists
                        pass
            conn.commit()

        if added_count > 0:
            logger.info(f"Added {added_count} user-defined values")
        return added_count

    def delete_user_defined_value(self, field_name: str, value: str) -> bool:
        """
        Delete a user-defined value.

        Returns:
            True if the value was deleted, False if it didn't exist
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_defined_values
                WHERE field_name = ? AND value = ?
            """, (field_name, value))
            conn.commit()
            return cursor.rowcount > 0

    # ============== Deduplication Operations ==============

    def create_duplicate_cluster(
        self,
        question_ids: List[int],
        similarity_threshold: float = 0.90,
        canonical_question_id: Optional[int] = None
    ) -> int:
        """
        Create a new duplicate cluster with the given questions.

        Args:
            question_ids: List of question IDs to include in cluster
            similarity_threshold: The similarity threshold used to detect duplicates
            canonical_question_id: Optional ID of the canonical question (if already determined)

        Returns:
            The cluster_id of the created cluster
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create the cluster
            cursor.execute("""
                INSERT INTO duplicate_clusters (similarity_threshold, status)
                VALUES (?, 'pending')
            """, (similarity_threshold,))
            cluster_id = cursor.lastrowid

            # Add members
            for qid in question_ids:
                # Get source_id for this question
                cursor.execute("SELECT source_id FROM questions WHERE id = ?", (qid,))
                row = cursor.fetchone()
                source_id = str(row["source_id"]) if row and row["source_id"] else None

                is_canonical = (qid == canonical_question_id) if canonical_question_id else False
                cursor.execute("""
                    INSERT INTO cluster_members (cluster_id, question_id, source_id, is_canonical)
                    VALUES (?, ?, ?, ?)
                """, (cluster_id, qid, source_id, is_canonical))

            conn.commit()
            return cluster_id

    def search_duplicate_candidates(
        self,
        query: str,
        exclude_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for potential duplicate candidates using FTS.

        Args:
            query: Keyword to search for in question_stem and correct_answer
            exclude_id: Question ID to exclude from results
            limit: Max results to return

        Returns:
            List of candidate question dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build FTS query - search question_stem and correct_answer
            fts_query = f'"{query}"'  # Exact phrase match

            # Build exclusion clause
            exclude_clause = ""
            params = [fts_query, limit]
            if exclude_id:
                exclude_clause = "AND q.id != ?"
                params = [fts_query, exclude_id, limit]

            cursor.execute(f"""
                SELECT DISTINCT
                    q.id,
                    q.source_id,
                    q.question_stem,
                    q.correct_answer,
                    t.disease_state,
                    t.topic
                FROM questions q
                JOIN questions_fts fts ON q.id = fts.rowid
                LEFT JOIN tags t ON q.id = t.question_id
                WHERE questions_fts MATCH ?
                  AND (q.canonical_source_id IS NULL OR q.canonical_source_id = q.source_id)
                  {exclude_clause}
                ORDER BY bm25(questions_fts) DESC
                LIMIT ?
            """, params)

            candidates = []
            for row in cursor.fetchall():
                candidates.append({
                    "id": row["id"],
                    "source_id": str(row["source_id"]) if row["source_id"] else None,
                    "question_stem": row["question_stem"],
                    "correct_answer": row["correct_answer"],
                    "disease_state": row["disease_state"],
                    "topic": row["topic"],
                })
            return candidates

    def get_duplicate_clusters(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get duplicate clusters with their members.

        Args:
            status: Filter by status ('pending', 'confirmed', 'rejected')
            limit: Max clusters to return
            offset: Pagination offset

        Returns:
            List of cluster dicts with members
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clause = "WHERE 1=1"
            params = []
            if status:
                where_clause += " AND dc.status = ?"
                params.append(status)

            # Get clusters
            cursor.execute(f"""
                SELECT dc.cluster_id, dc.canonical_question_id, dc.canonical_source_id,
                       dc.status, dc.similarity_threshold, dc.created_at, dc.reviewed_at,
                       dc.reviewed_by, COUNT(cm.id) as member_count
                FROM duplicate_clusters dc
                LEFT JOIN cluster_members cm ON dc.cluster_id = cm.cluster_id
                {where_clause}
                GROUP BY dc.cluster_id
                ORDER BY dc.created_at DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            clusters = []
            for row in cursor.fetchall():
                cluster = dict(row)

                # Get members for this cluster
                cursor.execute("""
                    SELECT cm.question_id, cm.source_id, cm.similarity_to_canonical, cm.is_canonical,
                           q.question_stem, q.correct_answer, q.incorrect_answers, q.source_file
                    FROM cluster_members cm
                    JOIN questions q ON cm.question_id = q.id
                    WHERE cm.cluster_id = ?
                """, (cluster["cluster_id"],))
                members = []
                for m in cursor.fetchall():
                    member = dict(m)
                    # Parse incorrect_answers JSON
                    if member.get("incorrect_answers"):
                        try:
                            member["incorrect_answers"] = json.loads(member["incorrect_answers"])
                        except:
                            member["incorrect_answers"] = []
                    members.append(member)
                cluster["members"] = members
                clusters.append(cluster)

            return clusters

    def get_duplicate_cluster(self, cluster_id: int) -> Optional[Dict]:
        """Get a single cluster with full question details."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT cluster_id, canonical_question_id, canonical_source_id,
                       status, similarity_threshold, created_at, reviewed_at, reviewed_by
                FROM duplicate_clusters
                WHERE cluster_id = ?
            """, (cluster_id,))
            row = cursor.fetchone()
            if not row:
                return None

            cluster = dict(row)

            # Get members with full question details
            cursor.execute("""
                SELECT cm.question_id, cm.source_id, cm.similarity_to_canonical, cm.is_canonical,
                       q.question_stem, q.correct_answer, q.incorrect_answers, q.source_file
                FROM cluster_members cm
                JOIN questions q ON cm.question_id = q.id
                WHERE cm.cluster_id = ?
            """, (cluster_id,))

            members = []
            for m in cursor.fetchall():
                member = dict(m)
                # Parse incorrect_answers JSON
                if member.get("incorrect_answers"):
                    try:
                        member["incorrect_answers"] = json.loads(member["incorrect_answers"])
                    except:
                        member["incorrect_answers"] = []
                members.append(member)

            cluster["members"] = members
            return cluster

    def confirm_duplicate_cluster(
        self,
        cluster_id: int,
        canonical_question_id: int,
        selected_question_ids: Optional[List[int]] = None,
        reviewed_by: Optional[str] = None
    ) -> bool:
        """
        Confirm a duplicate cluster and set the canonical question.

        This updates:
        1. The cluster's canonical_question_id and status
        2. All non-canonical questions' canonical_source_id to point to canonical's source_id

        If selected_question_ids is provided (partial confirmation):
        - Only confirm selected questions as duplicates
        - Remove unselected questions from the cluster

        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get the canonical question's source_id
            cursor.execute("SELECT source_id FROM questions WHERE id = ?", (canonical_question_id,))
            row = cursor.fetchone()
            if not row:
                return False
            canonical_source_id = str(row["source_id"]) if row["source_id"] else None

            # If partial confirmation, remove unselected questions from cluster
            if selected_question_ids:
                # Get all current members
                cursor.execute(
                    "SELECT question_id FROM cluster_members WHERE cluster_id = ?",
                    (cluster_id,)
                )
                all_member_ids = [r["question_id"] for r in cursor.fetchall()]

                # Find unselected questions
                unselected_ids = [qid for qid in all_member_ids if qid not in selected_question_ids]

                # Remove unselected from cluster
                if unselected_ids:
                    placeholders = ','.join(['?'] * len(unselected_ids))
                    cursor.execute(f"""
                        DELETE FROM cluster_members
                        WHERE cluster_id = ? AND question_id IN ({placeholders})
                    """, [cluster_id] + unselected_ids)
                    logger.info(f"Removed {len(unselected_ids)} unselected questions from cluster {cluster_id}")

            # Update cluster
            cursor.execute("""
                UPDATE duplicate_clusters
                SET canonical_question_id = ?, canonical_source_id = ?,
                    status = 'confirmed', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
                WHERE cluster_id = ?
            """, (canonical_question_id, canonical_source_id, reviewed_by, cluster_id))

            # Update cluster members - mark canonical
            cursor.execute("""
                UPDATE cluster_members
                SET is_canonical = (question_id = ?)
                WHERE cluster_id = ?
            """, (canonical_question_id, cluster_id))

            # Update non-canonical questions' canonical_source_id (only for remaining members)
            cursor.execute("""
                UPDATE questions
                SET canonical_source_id = ?
                WHERE id IN (
                    SELECT question_id FROM cluster_members
                    WHERE cluster_id = ? AND question_id != ?
                )
            """, (canonical_source_id, cluster_id, canonical_question_id))

            # Record decision
            cursor.execute("""
                INSERT INTO duplicate_decisions (cluster_id, decision, decided_by)
                VALUES (?, 'duplicate', ?)
            """, (cluster_id, reviewed_by))

            conn.commit()
            return True

    def reject_duplicate_cluster(
        self,
        cluster_id: int,
        reviewed_by: Optional[str] = None
    ) -> bool:
        """
        Reject a duplicate cluster (mark as not actually duplicates).

        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE duplicate_clusters
                SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
                WHERE cluster_id = ?
            """, (reviewed_by, cluster_id))

            # Record decision
            cursor.execute("""
                INSERT INTO duplicate_decisions (cluster_id, decision, decided_by)
                VALUES (?, 'not_duplicate', ?)
            """, (cluster_id, reviewed_by))

            conn.commit()
            return cursor.rowcount > 0

    def get_dedup_stats(self) -> Dict:
        """Get deduplication statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_clusters,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_clusters,
                    SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_clusters,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_clusters
                FROM duplicate_clusters
            """)
            row = cursor.fetchone()

            # Count questions with canonical_source_id != source_id (confirmed duplicates)
            cursor.execute("""
                SELECT COUNT(*) as duplicate_questions
                FROM questions
                WHERE canonical_source_id IS NOT NULL
                  AND canonical_source_id != CAST(source_id AS TEXT)
            """)
            dup_row = cursor.fetchone()

            return {
                "total_clusters": row["total_clusters"] or 0,
                "pending_clusters": row["pending_clusters"] or 0,
                "confirmed_clusters": row["confirmed_clusters"] or 0,
                "rejected_clusters": row["rejected_clusters"] or 0,
                "duplicate_questions": dup_row["duplicate_questions"] or 0
            }

    def import_dedup_report(self, report_path: str) -> int:
        """
        Import duplicates from a dedup report JSON file into clusters.

        Supports two formats:
        1. Legacy format with 'duplicates' array
        2. New format with 'clusters' dict (question_id -> cluster info)

        Args:
            report_path: Path to the dedup report JSON

        Returns:
            Number of clusters created
        """
        import json as json_module
        from collections import defaultdict

        with open(report_path, 'r') as f:
            report = json_module.load(f)

        clusters_created = 0

        # Handle new format with 'clusters' dict
        # Keys are checkpoint question_ids (stored as source_question_id in dashboard DB)
        if "clusters" in report and isinstance(report["clusters"], dict):
            # Group by cluster_id
            cluster_groups = defaultdict(list)
            threshold = report.get("threshold", 0.90)

            for question_id_str, info in report["clusters"].items():
                if info.get("is_duplicate"):
                    cluster_id = info.get("cluster_id")
                    cluster_groups[cluster_id].append({
                        "checkpoint_question_id": int(question_id_str),
                        "checkpoint_canonical_id": info.get("canonical_question_id"),
                        "similarity_score": info.get("similarity_score", threshold)
                    })

            # Create clusters for each group
            with self.get_connection() as conn:
                cursor = conn.cursor()

                for cluster_id, members in cluster_groups.items():
                    if not members:
                        continue

                    # Get the canonical checkpoint ID (should be the same for all members)
                    checkpoint_canonical_id = members[0]["checkpoint_canonical_id"]

                    # Collect all checkpoint question IDs: canonical + duplicates
                    checkpoint_ids = set()
                    checkpoint_ids.add(checkpoint_canonical_id)
                    for m in members:
                        checkpoint_ids.add(m["checkpoint_question_id"])

                    # Map checkpoint IDs to dashboard DB IDs via source_question_id
                    db_id_map = {}
                    for cid in checkpoint_ids:
                        cursor.execute(
                            "SELECT id FROM questions WHERE source_question_id = ?",
                            (cid,)
                        )
                        row = cursor.fetchone()
                        if row:
                            db_id_map[cid] = row["id"]

                    # Check we have enough questions and the canonical
                    if len(db_id_map) >= 2 and checkpoint_canonical_id in db_id_map:
                        db_canonical_id = db_id_map[checkpoint_canonical_id]
                        db_question_ids = list(db_id_map.values())

                        # Use lowest similarity score from members as threshold
                        min_similarity = min(m["similarity_score"] for m in members)
                        self.create_duplicate_cluster(
                            question_ids=db_question_ids,
                            similarity_threshold=min_similarity,
                            canonical_question_id=db_canonical_id
                        )
                        clusters_created += 1

            return clusters_created

        # Handle legacy format with 'duplicates' array
        duplicates = report.get("duplicates", [])

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for dup in duplicates:
                # Look up question IDs by source_id (QGD)
                canonical_qgd = dup.get("canonical_source_id") or dup.get("canonical_id")
                duplicate_qgd = dup.get("duplicate_source_id") or dup.get("duplicate_id")
                similarity = dup.get("similarity", 0.90)

                # Find question IDs
                cursor.execute("SELECT id FROM questions WHERE source_id = ?", (canonical_qgd,))
                canonical_row = cursor.fetchone()
                cursor.execute("SELECT id FROM questions WHERE source_id = ?", (duplicate_qgd,))
                duplicate_row = cursor.fetchone()

                if canonical_row and duplicate_row:
                    question_ids = [canonical_row["id"], duplicate_row["id"]]
                    self.create_duplicate_cluster(
                        question_ids=question_ids,
                        similarity_threshold=similarity,
                        canonical_question_id=canonical_row["id"]
                    )
                    clusters_created += 1

        return clusters_created

    # ========== Tag Proposal Methods ==========

    def create_tag_proposal(
        self,
        field_name: str,
        proposed_value: str,
        search_query: str,
        proposal_reason: str = "",
        created_by: str = None
    ) -> Dict:
        """
        Create a new tag proposal and find matching candidate questions.

        Args:
            field_name: The tag field to update (e.g., 'topic', 'treatment_1')
            proposed_value: The proposed tag value
            search_query: Keyword to search in question text
            proposal_reason: Optional context for why this tag is proposed
            created_by: User who created the proposal

        Returns:
            Dict with proposal details including matched candidates
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create the proposal
            cursor.execute("""
                INSERT INTO tag_proposals (field_name, proposed_value, search_query, proposal_reason, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (field_name, proposed_value, search_query, proposal_reason, created_by))
            proposal_id = cursor.lastrowid

            # Search for candidate questions using FTS
            # FTS5 searches both question_stem AND correct_answer columns
            # Exclude hidden duplicates (canonical_source_id != source_id)
            search_term = search_query.replace('"', '""')  # Escape quotes
            cursor.execute("""
                SELECT q.id, q.question_stem, q.correct_answer, q.source_id,
                       t.{field_name} as current_value,
                       bm25(questions_fts) as match_score
                FROM questions q
                JOIN questions_fts fts ON q.id = fts.rowid
                LEFT JOIN tags t ON q.id = t.question_id
                WHERE questions_fts MATCH ?
                  AND (q.canonical_source_id IS NULL OR q.canonical_source_id = q.source_id)
                ORDER BY bm25(questions_fts)
                LIMIT 100
            """.format(field_name=field_name), (f'"{search_term}"',))

            candidates = []
            for row in cursor.fetchall():
                cursor.execute("""
                    INSERT INTO tag_proposal_candidates (proposal_id, question_id, match_score, current_value)
                    VALUES (?, ?, ?, ?)
                """, (proposal_id, row["id"], abs(row["match_score"]), row["current_value"]))

                # Truncate question_stem for display
                stem = row["question_stem"]
                if len(stem) > 200:
                    stem = stem[:200] + "..."

                candidates.append({
                    "id": cursor.lastrowid,
                    "question_id": row["id"],
                    "question_stem": stem,
                    "correct_answer": row["correct_answer"],
                    "source_id": str(row["source_id"]) if row["source_id"] else None,
                    "current_value": row["current_value"],
                    "match_score": abs(row["match_score"]),
                    "decision": "pending"
                })

            # Update match count
            cursor.execute("""
                UPDATE tag_proposals SET match_count = ? WHERE id = ?
            """, (len(candidates), proposal_id))

            conn.commit()

            return {
                "id": proposal_id,
                "field_name": field_name,
                "proposed_value": proposed_value,
                "search_query": search_query,
                "proposal_reason": proposal_reason,
                "status": "pending",
                "match_count": len(candidates),
                "approved_count": 0,
                "created_by": created_by,
                "candidates": candidates
            }

    def get_tag_proposals(self, status: str = None) -> List[Dict]:
        """
        Get list of tag proposals with optional status filter.

        Args:
            status: Filter by status (pending, reviewing, ready_to_apply, applied, abandoned)

        Returns:
            List of proposal dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute("""
                    SELECT id, field_name, proposed_value, search_query, proposal_reason,
                           status, match_count, approved_count, created_at, created_by, completed_at
                    FROM tag_proposals
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT id, field_name, proposed_value, search_query, proposal_reason,
                           status, match_count, approved_count, created_at, created_by, completed_at
                    FROM tag_proposals
                    ORDER BY created_at DESC
                """)

            return [dict(row) for row in cursor.fetchall()]

    def get_proposal_with_candidates(self, proposal_id: int) -> Optional[Dict]:
        """
        Get a proposal with all its candidate questions.

        Args:
            proposal_id: The proposal ID

        Returns:
            Dict with proposal details and candidates, or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get proposal
            cursor.execute("""
                SELECT id, field_name, proposed_value, search_query, proposal_reason,
                       status, match_count, approved_count, created_at, created_by, completed_at
                FROM tag_proposals
                WHERE id = ?
            """, (proposal_id,))
            row = cursor.fetchone()
            if not row:
                return None

            proposal = dict(row)

            # Get candidates with question details
            cursor.execute("""
                SELECT c.id, c.question_id, c.match_score, c.current_value, c.decision,
                       c.decided_at, c.decided_by, c.notes,
                       q.question_stem, q.source_id, q.correct_answer
                FROM tag_proposal_candidates c
                JOIN questions q ON c.question_id = q.id
                WHERE c.proposal_id = ?
                ORDER BY c.decision ASC, c.match_score DESC
            """, (proposal_id,))

            candidates = []
            for row in cursor.fetchall():
                candidates.append({
                    "id": row["id"],
                    "question_id": row["question_id"],
                    "match_score": row["match_score"],
                    "current_value": row["current_value"],
                    "decision": row["decision"],
                    "decided_at": row["decided_at"],
                    "decided_by": row["decided_by"],
                    "notes": row["notes"],
                    "question_stem": row["question_stem"],
                    "source_id": str(row["source_id"]) if row["source_id"] else None,
                    "correct_answer": row["correct_answer"]
                })

            proposal["candidates"] = candidates
            return proposal

    def review_proposal_candidates(
        self,
        proposal_id: int,
        approved_ids: List[int],
        skipped_ids: List[int],
        reviewed_by: str
    ) -> Dict:
        """
        Mark candidates as approved or skipped.

        Args:
            proposal_id: The proposal ID
            approved_ids: List of candidate IDs to approve
            skipped_ids: List of candidate IDs to skip
            reviewed_by: User who made the decisions

        Returns:
            Dict with updated counts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            now = "CURRENT_TIMESTAMP"

            # Update approved candidates
            if approved_ids:
                placeholders = ",".join("?" * len(approved_ids))
                cursor.execute(f"""
                    UPDATE tag_proposal_candidates
                    SET decision = 'approved', decided_at = CURRENT_TIMESTAMP, decided_by = ?
                    WHERE id IN ({placeholders}) AND proposal_id = ?
                """, [reviewed_by] + approved_ids + [proposal_id])

            # Update skipped candidates
            if skipped_ids:
                placeholders = ",".join("?" * len(skipped_ids))
                cursor.execute(f"""
                    UPDATE tag_proposal_candidates
                    SET decision = 'skipped', decided_at = CURRENT_TIMESTAMP, decided_by = ?
                    WHERE id IN ({placeholders}) AND proposal_id = ?
                """, [reviewed_by] + skipped_ids + [proposal_id])

            # Count approved
            cursor.execute("""
                SELECT COUNT(*) FROM tag_proposal_candidates
                WHERE proposal_id = ? AND decision = 'approved'
            """, (proposal_id,))
            approved_count = cursor.fetchone()[0]

            # Count pending
            cursor.execute("""
                SELECT COUNT(*) FROM tag_proposal_candidates
                WHERE proposal_id = ? AND decision = 'pending'
            """, (proposal_id,))
            pending_count = cursor.fetchone()[0]

            # Update proposal
            new_status = "pending" if pending_count > 0 else ("ready_to_apply" if approved_count > 0 else "reviewing")
            cursor.execute("""
                UPDATE tag_proposals
                SET approved_count = ?, status = ?
                WHERE id = ?
            """, (approved_count, new_status, proposal_id))

            conn.commit()

            return {
                "proposal_id": proposal_id,
                "approved_count": approved_count,
                "pending_count": pending_count,
                "status": new_status
            }

    def apply_proposal(self, proposal_id: int, reviewed_by: str) -> Dict:
        """
        Apply approved tags to the database.

        Args:
            proposal_id: The proposal ID
            reviewed_by: User who applied the changes

        Returns:
            Dict with count of updated questions
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get proposal details
            cursor.execute("""
                SELECT field_name, proposed_value FROM tag_proposals WHERE id = ?
            """, (proposal_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Proposal {proposal_id} not found")

            field_name = row["field_name"]
            proposed_value = row["proposed_value"]

            # Get approved candidate question IDs
            cursor.execute("""
                SELECT question_id FROM tag_proposal_candidates
                WHERE proposal_id = ? AND decision = 'approved'
            """, (proposal_id,))
            question_ids = [r["question_id"] for r in cursor.fetchall()]

            if not question_ids:
                return {"proposal_id": proposal_id, "updated_count": 0}

            # Update tags for approved questions
            placeholders = ",".join("?" * len(question_ids))
            cursor.execute(f"""
                UPDATE tags
                SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE question_id IN ({placeholders})
            """, [proposed_value] + question_ids)

            updated_count = cursor.rowcount

            # Mark proposal as applied
            cursor.execute("""
                UPDATE tag_proposals
                SET status = 'applied', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (proposal_id,))

            conn.commit()

            logger.info(f"Applied proposal {proposal_id}: set {field_name}='{proposed_value}' for {updated_count} questions")

            return {
                "proposal_id": proposal_id,
                "field_name": field_name,
                "proposed_value": proposed_value,
                "updated_count": updated_count
            }

    def abandon_proposal(self, proposal_id: int) -> bool:
        """
        Mark a proposal as abandoned.

        Args:
            proposal_id: The proposal ID

        Returns:
            True if successful, False if proposal not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tag_proposals
                SET status = 'abandoned', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (proposal_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_proposal_stats(self) -> Dict:
        """
        Get aggregate statistics for tag proposals.

        Returns:
            Dict with total, pending, ready_to_apply, applied counts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'reviewing' THEN 1 ELSE 0 END) as reviewing,
                    SUM(CASE WHEN status = 'ready_to_apply' THEN 1 ELSE 0 END) as ready_to_apply,
                    SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied,
                    SUM(CASE WHEN status = 'abandoned' THEN 1 ELSE 0 END) as abandoned
                FROM tag_proposals
            """)
            row = cursor.fetchone()

            return {
                "total": row["total"] or 0,
                "pending": row["pending"] or 0,
                "reviewing": row["reviewing"] or 0,
                "ready_to_apply": row["ready_to_apply"] or 0,
                "applied": row["applied"] or 0,
                "abandoned": row["abandoned"] or 0
            }

    # ========== QCore Scoring Methods ==========

    def calculate_qcore_for_question(self, question_id: int) -> Optional[Dict]:
        """
        Calculate and store QCore score for a single question.

        Args:
            question_id: The question ID to score

        Returns:
            Dict with score details, or None if question not found/has no tags
        """
        from src.core.preprocessing.qcore_scorer import calculate_qcore_score

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get quality fields from tags table
            cursor.execute("""
                SELECT
                    cme_outcome_level, data_response_type, stem_type, lead_in_type,
                    answer_format, answer_length_pattern, distractor_homogeneity,
                    flaw_absolute_terms, flaw_grammatical_cue, flaw_implausible_distractor,
                    flaw_clang_association, flaw_convergence_vulnerability, flaw_double_negative,
                    answer_option_count
                FROM tags
                WHERE question_id = ?
            """, (question_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # Build tags dict for scorer
            tags = {
                'cme_outcome_level': row['cme_outcome_level'],
                'data_response_type': row['data_response_type'],
                'stem_type': row['stem_type'],
                'lead_in_type': row['lead_in_type'],
                'answer_format': row['answer_format'],
                'answer_length_pattern': row['answer_length_pattern'],
                'distractor_homogeneity': row['distractor_homogeneity'],
                'flaw_absolute_terms': self._str_to_bool(row['flaw_absolute_terms']),
                'flaw_grammatical_cue': self._str_to_bool(row['flaw_grammatical_cue']),
                'flaw_implausible_distractor': self._str_to_bool(row['flaw_implausible_distractor']),
                'flaw_clang_association': self._str_to_bool(row['flaw_clang_association']),
                'flaw_convergence_vulnerability': self._str_to_bool(row['flaw_convergence_vulnerability']),
                'flaw_double_negative': self._str_to_bool(row['flaw_double_negative']),
                'answer_option_count': row['answer_option_count'] or 4,
            }

            # Extract CME level (3 or 4)
            cme_level = 4  # Default to Level 4 (Competence)
            if tags['cme_outcome_level']:
                cme_str = str(tags['cme_outcome_level']).lower()
                if '3' in cme_str or 'knowledge' in cme_str:
                    cme_level = 3

            # Calculate score
            result = calculate_qcore_score(tags, cme_level=cme_level)

            # Store score in database
            import json
            cursor.execute("""
                UPDATE tags
                SET qcore_score = ?, qcore_grade = ?, qcore_breakdown = ?, qcore_scored_at = CURRENT_TIMESTAMP
                WHERE question_id = ?
            """, (
                result['total_score'],
                result['grade'],
                json.dumps(result['breakdown']),
                question_id
            ))
            conn.commit()

            return {
                'question_id': question_id,
                'score': result['total_score'],
                'grade': result['grade'],
                'breakdown': result['breakdown'],
                'ready_for_deployment': result['ready_for_deployment'],
            }

    def calculate_qcore_for_all_questions(self) -> Dict:
        """
        Calculate and store QCore scores for all questions with tags.

        Returns:
            Dict with counts of scored, skipped, and failed questions
        """
        from src.core.preprocessing.qcore_scorer import calculate_qcore_score
        import json

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get all questions with tags (exclude duplicates)
            cursor.execute("""
                SELECT
                    t.question_id,
                    t.cme_outcome_level, t.data_response_type, t.stem_type, t.lead_in_type,
                    t.answer_format, t.answer_length_pattern, t.distractor_homogeneity,
                    t.flaw_absolute_terms, t.flaw_grammatical_cue, t.flaw_implausible_distractor,
                    t.flaw_clang_association, t.flaw_convergence_vulnerability, t.flaw_double_negative,
                    t.answer_option_count
                FROM tags t
                JOIN questions q ON t.question_id = q.id
                WHERE (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
            """)
            rows = cursor.fetchall()

            scored = 0
            skipped = 0
            failed = 0

            for row in rows:
                try:
                    # Build tags dict
                    tags = {
                        'cme_outcome_level': row['cme_outcome_level'],
                        'data_response_type': row['data_response_type'],
                        'stem_type': row['stem_type'],
                        'lead_in_type': row['lead_in_type'],
                        'answer_format': row['answer_format'],
                        'answer_length_pattern': row['answer_length_pattern'],
                        'distractor_homogeneity': row['distractor_homogeneity'],
                        'flaw_absolute_terms': self._str_to_bool(row['flaw_absolute_terms']),
                        'flaw_grammatical_cue': self._str_to_bool(row['flaw_grammatical_cue']),
                        'flaw_implausible_distractor': self._str_to_bool(row['flaw_implausible_distractor']),
                        'flaw_clang_association': self._str_to_bool(row['flaw_clang_association']),
                        'flaw_convergence_vulnerability': self._str_to_bool(row['flaw_convergence_vulnerability']),
                        'flaw_double_negative': self._str_to_bool(row['flaw_double_negative']),
                        'answer_option_count': row['answer_option_count'] or 4,
                    }

                    # Skip if no quality fields are tagged
                    if not tags['stem_type'] and not tags['lead_in_type'] and not tags['answer_format']:
                        skipped += 1
                        continue

                    # Extract CME level
                    cme_level = 4
                    if tags['cme_outcome_level']:
                        cme_str = str(tags['cme_outcome_level']).lower()
                        if '3' in cme_str or 'knowledge' in cme_str:
                            cme_level = 3

                    # Calculate score
                    result = calculate_qcore_score(tags, cme_level=cme_level)

                    # Update database
                    cursor.execute("""
                        UPDATE tags
                        SET qcore_score = ?, qcore_grade = ?, qcore_breakdown = ?, qcore_scored_at = CURRENT_TIMESTAMP
                        WHERE question_id = ?
                    """, (
                        result['total_score'],
                        result['grade'],
                        json.dumps(result['breakdown']),
                        row['question_id']
                    ))
                    scored += 1

                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to score question {row['question_id']}: {e}")

            conn.commit()

            return {
                'total': len(rows),
                'scored': scored,
                'skipped': skipped,
                'failed': failed,
            }

    def get_qcore_stats(self) -> Dict:
        """
        Get QCore scoring statistics.

        Returns:
            Dict with score distribution, grade counts, etc.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get grade distribution
            cursor.execute("""
                SELECT
                    qcore_grade,
                    COUNT(*) as count,
                    AVG(qcore_score) as avg_score
                FROM tags t
                JOIN questions q ON t.question_id = q.id
                WHERE qcore_score IS NOT NULL
                  AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
                GROUP BY qcore_grade
                ORDER BY qcore_grade
            """)
            grade_rows = cursor.fetchall()

            # Get overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_scored,
                    AVG(qcore_score) as avg_score,
                    MIN(qcore_score) as min_score,
                    MAX(qcore_score) as max_score,
                    SUM(CASE WHEN qcore_score >= 80 THEN 1 ELSE 0 END) as ready_count
                FROM tags t
                JOIN questions q ON t.question_id = q.id
                WHERE qcore_score IS NOT NULL
                  AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
            """)
            stats_row = cursor.fetchone()

            # Count questions without scores
            cursor.execute("""
                SELECT COUNT(*) as unscored
                FROM tags t
                JOIN questions q ON t.question_id = q.id
                WHERE qcore_score IS NULL
                  AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
            """)
            unscored_row = cursor.fetchone()

            grade_distribution = {}
            for row in grade_rows:
                grade_distribution[row['qcore_grade']] = {
                    'count': row['count'],
                    'avg_score': round(row['avg_score'], 1) if row['avg_score'] else 0
                }

            return {
                'total_scored': stats_row['total_scored'] or 0,
                'total_unscored': unscored_row['unscored'] or 0,
                'avg_score': round(stats_row['avg_score'], 1) if stats_row['avg_score'] else 0,
                'min_score': stats_row['min_score'] or 0,
                'max_score': stats_row['max_score'] or 0,
                'ready_count': stats_row['ready_count'] or 0,
                'grade_distribution': grade_distribution,
            }


# Singleton instance
_db_instance: Optional[DatabaseService] = None


def get_database(db_path: Path = DEFAULT_DB_PATH) -> DatabaseService:
    """Get or create database service singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService(db_path)
    return _db_instance

