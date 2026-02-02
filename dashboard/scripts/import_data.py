"""
Data import script for CME Question Explorer.

Imports questions from Excel files into SQLite database, including:
- Question text and answers
- Tags (Topic, Disease State, etc.) with confidence scores
- Performance metrics (pre/post scores by segment)
- Activity associations

When importing untagged questions, runs the tagging pipeline and stores
per-tag confidence scores for QC review.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import logging
from typing import Optional, List, Dict, Any

from dashboard.backend.services.database import DatabaseService
from src.utils.qc_flags import needs_review, aggregate_tag_confidences

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataImporter:
    """Import data from Excel files into the database."""

    def __init__(self, db: DatabaseService, use_auto_tagging: bool = False, use_llm_fallback: bool = False):
        """
        Initialize data importer.

        Args:
            db: Database service instance
            use_auto_tagging: If True, run taggers on questions without existing tags
            use_llm_fallback: If True and use_auto_tagging, use LLM fallback for low-confidence
        """
        self.db = db
        self.use_auto_tagging = use_auto_tagging
        self.use_llm_fallback = use_llm_fallback
        self._tagger = None

    def _get_tagger(self):
        """Lazy-load the UnifiedTagger only when needed."""
        if self._tagger is None and self.use_auto_tagging:
            try:
                from src.services.unified_tagger import UnifiedTagger
                logger.info("Initializing UnifiedTagger for auto-tagging...")
                self._tagger = UnifiedTagger(use_llm_fallback=self.use_llm_fallback)
                logger.info("UnifiedTagger initialized")
            except ImportError as e:
                logger.warning(f"Could not import UnifiedTagger: {e}. Auto-tagging disabled.")
                self.use_auto_tagging = False
        return self._tagger
    
    def import_training_data(self, file_path: Path) -> int:
        """
        Import a training data file (with tags, minimal performance data).
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Number of questions imported
        """
        logger.info(f"Importing training data from {file_path.name}...")
        
        df = pd.read_excel(file_path)
        logger.info(f"  Found {len(df)} rows, columns: {list(df.columns)}")
        
        # Standardize column names (case-insensitive)
        col_map = {c.lower().strip(): c for c in df.columns}
        
        # Find key columns
        question_col = self._find_column(col_map, ['questiontext', 'question', 'questions', 'question stem'])
        correct_answer_col = self._find_column(col_map, ['canswer1', 'correct answer', 'answer 1', 'answer'])
        
        if not question_col:
            logger.warning(f"  Could not find question column, skipping file")
            return 0
        
        count = 0
        for idx, row in df.iterrows():
            question_stem = str(row[question_col]).strip() if pd.notna(row[question_col]) else None
            if not question_stem or question_stem == 'nan':
                continue
            
            # Get correct answer
            correct_answer = None
            if correct_answer_col and pd.notna(row.get(correct_answer_col)):
                correct_answer = str(row[correct_answer_col]).strip()
            
            # Get incorrect answers
            incorrect_answers = self._extract_incorrect_answers(row, col_map)
            
            # Insert question
            question_id = self.db.insert_question(
                question_stem=question_stem,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers,
                source_file=file_path.name
            )
            
            # Insert tags (pass question text for potential auto-tagging)
            self._insert_tags_from_row(
                question_id, row, col_map,
                question_stem=question_stem,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers
            )

            # Insert activities
            self._insert_activities_from_row(question_id, row, col_map)

            count += 1

        logger.info(f"  Imported {count} questions from {file_path.name}")
        return count

    def import_untagged_with_performance(self, file_path: Path) -> int:
        """
        Import an untagged file with performance metrics (like Hematologic Malignancies).
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Number of questions imported
        """
        logger.info(f"Importing untagged data with performance from {file_path.name}...")
        
        df = pd.read_excel(file_path)
        logger.info(f"  Found {len(df)} rows, columns: {list(df.columns)}")
        
        # Standardize column names
        col_map = {c.lower().strip(): c for c in df.columns}
        
        # Find question column
        question_col = self._find_column(col_map, ['questiontext', 'question', 'questions'])
        correct_answer_col = self._find_column(col_map, ['canswer1', 'correct answer'])
        
        if not question_col:
            logger.warning(f"  Could not find question column, skipping file")
            return 0
        
        count = 0
        for idx, row in df.iterrows():
            question_stem = str(row[question_col]).strip() if pd.notna(row[question_col]) else None
            if not question_stem or question_stem == 'nan':
                continue
            
            # Get correct answer
            correct_answer = None
            if correct_answer_col and pd.notna(row.get(correct_answer_col)):
                correct_answer = str(row[correct_answer_col]).strip()
            
            # Get incorrect answers
            incorrect_answers = self._extract_incorrect_answers(row, col_map)
            
            # Insert question
            question_id = self.db.insert_question(
                question_stem=question_stem,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers,
                source_file=file_path.name
            )

            # Insert tags (if any in row, otherwise auto-tag if enabled)
            self._insert_tags_from_row(
                question_id, row, col_map,
                question_stem=question_stem,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers
            )

            # Insert performance data
            self._insert_performance_from_row(question_id, row, df.columns.tolist())

            # Insert activities
            self._insert_activities_from_row(question_id, row, col_map)

            count += 1

        logger.info(f"  Imported {count} questions from {file_path.name}")
        return count

    def import_oncology_questions(self, file_path: Path) -> int:
        """
        Import the AllQuestionsOncology file with:
        - Up to 15 activities per question with individual dates
        - 7 audience segment scores per question
        - Auto-tagging with all 8 taggers (topic, disease_state, disease_stage,
          disease_type, treatment_line, treatment, biomarker, trial)
        - Per-tag confidence scores stored for QC

        Args:
            file_path: Path to AllQuestionsOncology*.xlsx file

        Returns:
            Number of questions imported
        """
        logger.info(f"Importing oncology questions from {file_path.name}...")

        df = pd.read_excel(file_path)
        logger.info(f"  Found {len(df)} rows, columns: {len(df.columns)}")

        # Audience segment mapping: segment_name -> column prefix
        SEGMENTS = {
            'overall': 'OS_',
            'medical_oncologist': 'MOS_',
            'app': 'APP_',
            'academic': 'ACADEMIC_',
            'community': 'COMMUNITY_',
            'surgical_oncologist': 'SURGICAL_',
            'radiation_oncologist': 'RADIATION_',
        }

        count = 0
        tagged_count = 0

        for idx, row in df.iterrows():
            # Extract question text
            question_stem = str(row['OPTIMIZEDQUESTION']).strip() if pd.notna(row.get('OPTIMIZEDQUESTION')) else None
            if not question_stem or question_stem == 'nan':
                continue

            correct_answer = str(row['OPTIMIZEDANSWER']).strip() if pd.notna(row.get('OPTIMIZEDANSWER')) else None

            # Extract incorrect answers (up to 9)
            incorrect_answers = []
            for i in range(1, 10):
                col_name = f'INCORRECTANSWER{i}'
                ans = row.get(col_name)
                if pd.notna(ans) and str(ans).strip() and str(ans).strip().lower() != 'nan':
                    incorrect_answers.append(str(ans).strip())

            # 1. Insert question
            question_id = self.db.insert_question(
                question_stem=question_stem,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers if incorrect_answers else None,
                source_file=file_path.name
            )

            # 2. Insert activities with dates (up to 15)
            first_activity = None
            for i in range(1, 16):
                activity_name = row.get(f'ACTIVITYNAME{i}')
                activity_date = row.get(f'ACTIVITYDATE{i}')

                if pd.notna(activity_name) and str(activity_name).strip():
                    activity_str = str(activity_name).strip()
                    if first_activity is None:
                        first_activity = activity_str

                    # Convert pandas Timestamp to date if needed
                    date_val = None
                    if pd.notna(activity_date):
                        if hasattr(activity_date, 'date'):
                            date_val = activity_date.date()
                        else:
                            date_val = activity_date

                    self.db.insert_activity_with_date(question_id, activity_str, date_val)

            # 3. Insert performance for each audience segment
            for segment_name, prefix in SEGMENTS.items():
                pre_score = self._safe_float(row.get(f'{prefix}PRESCORECALC'))
                post_score = self._safe_float(row.get(f'{prefix}POSTSCORECALC'))
                pre_n = self._safe_int(row.get(f'{prefix}PRESCOREN'))
                post_n = self._safe_int(row.get(f'{prefix}POSTSCOREN'))

                # Only insert if we have at least one score
                if pre_score is not None or post_score is not None:
                    self.db.insert_performance(
                        question_id=question_id,
                        segment=segment_name,
                        pre_score=pre_score,
                        post_score=post_score,
                        pre_n=pre_n,
                        post_n=post_n
                    )

            # 4. Run auto-tagging if enabled
            if self.use_auto_tagging:
                success = self._run_auto_tagging(
                    question_id=question_id,
                    question_stem=question_stem,
                    correct_answer=correct_answer,
                    incorrect_answers=incorrect_answers if incorrect_answers else None,
                    activity_name=first_activity
                )
                if success:
                    tagged_count += 1

            count += 1
            if count % 500 == 0:
                logger.info(f"  Processed {count}/{len(df)} questions...")

        logger.info(f"  Imported {count} questions from {file_path.name}")
        if self.use_auto_tagging:
            logger.info(f"  Auto-tagged {tagged_count} questions with confidence scores")
        return count

    def _find_column(self, col_map: Dict[str, str], candidates: List[str]) -> Optional[str]:
        """Find the first matching column from candidates."""
        for candidate in candidates:
            if candidate in col_map:
                return col_map[candidate]
        return None
    
    def _extract_incorrect_answers(self, row: pd.Series, col_map: Dict[str, str]) -> List[str]:
        """Extract incorrect answers from various column formats."""
        incorrect = []
        
        # Try INCANSWER format
        for i in range(1, 10):
            col_name = f'incanswer{i}'
            if col_name in col_map:
                val = row.get(col_map[col_name])
                if pd.notna(val) and str(val).strip():
                    incorrect.append(str(val).strip())
        
        # Try ANSWER format (where ANSWER1+ are incorrect, CANSWER is correct)
        if not incorrect:
            for i in range(1, 20):
                col_name = f'answer{i}'
                if col_name in col_map:
                    val = row.get(col_map[col_name])
                    if pd.notna(val) and str(val).strip():
                        incorrect.append(str(val).strip())
        
        return incorrect
    
    def _run_auto_tagging(
        self,
        question_id: int,
        question_stem: str,
        correct_answer: Optional[str],
        incorrect_answers: Optional[List[str]],
        activity_name: Optional[str] = None
    ) -> bool:
        """
        Run the unified tagger on a question and store results with confidence scores.

        Args:
            question_id: The database ID of the question
            question_stem: Question text
            correct_answer: Correct answer text
            incorrect_answers: List of incorrect answers
            activity_name: Optional activity name for context

        Returns:
            True if tagging was successful
        """
        tagger = self._get_tagger()
        if tagger is None:
            return False

        try:
            # Run all 8 taggers
            result = tagger.tag_question(
                question_stem=question_stem,
                correct_answer=correct_answer or "",
                incorrect_answers=incorrect_answers,
                activity_name=activity_name
            )

            # Collect tag confidences for aggregate review flagging
            tag_confidences = {}
            if result.topic.value:
                tag_confidences['topic'] = result.topic.confidence
            if result.disease_state.value:
                tag_confidences['disease_state'] = result.disease_state.confidence
            if result.disease_stage.value:
                tag_confidences['disease_stage'] = result.disease_stage.confidence
            if result.disease_type.value:
                tag_confidences['disease_type'] = result.disease_type.confidence
            if result.treatment.value:
                tag_confidences['treatment'] = result.treatment.confidence
            if result.biomarker.value:
                tag_confidences['biomarker'] = result.biomarker.confidence
            if result.trial.value:
                tag_confidences['trial'] = result.trial.confidence

            # Aggregate to determine if any tag needs review
            agg = aggregate_tag_confidences(tag_confidences)
            question_needs_review = agg['any_needs_review']

            # Collect review flags from all tags
            all_review_flags = result.all_review_flags or []

            # Store tags with confidence scores
            self.db.insert_tags(
                question_id=question_id,
                topic=result.topic.value,
                topic_confidence=result.topic.confidence,
                topic_method=result.topic.method,
                disease_state=result.disease_state.value,
                disease_state_confidence=result.disease_state.confidence,
                disease_stage=result.disease_stage.value,
                disease_stage_confidence=result.disease_stage.confidence,
                disease_type=result.disease_type.value,
                disease_type_confidence=result.disease_type.confidence,
                treatment_line=result.treatment_line.value,
                treatment_line_confidence=result.treatment_line.confidence,
                treatment=result.treatment.value,
                treatment_confidence=result.treatment.confidence,
                biomarker=result.biomarker.value,
                biomarker_confidence=result.biomarker.confidence,
                trial=result.trial.value,
                trial_confidence=result.trial.confidence,
                review_flags=all_review_flags if all_review_flags else None,
                needs_review=question_needs_review,
                overall_confidence=result.overall_confidence,
                llm_calls_made=result.llm_calls_made
            )

            return True

        except Exception as e:
            logger.error(f"Error auto-tagging question {question_id}: {e}")
            return False

    def _insert_tags_from_row(
        self,
        question_id: int,
        row: pd.Series,
        col_map: Dict[str, str],
        question_stem: Optional[str] = None,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[List[str]] = None
    ):
        """
        Insert tags from a row. If no tags found and auto-tagging is enabled,
        runs the tagger pipeline.

        Args:
            question_id: Database question ID
            row: DataFrame row with tag columns
            col_map: Column name mapping (lowercase -> original)
            question_stem: Question text (for auto-tagging fallback)
            correct_answer: Correct answer text (for auto-tagging fallback)
            incorrect_answers: Incorrect answers (for auto-tagging fallback)
        """
        # Map tag column names
        tag_cols = {
            'topic': self._find_column(col_map, ['topic', 'educationalgap']),
            'disease_state': self._find_column(col_map, ['diseasestate', 'disease state']),
            'disease_stage': self._find_column(col_map, ['diseasestage', 'disease stage', 'stage']),
            'disease_type': self._find_column(col_map, ['diseasetype', 'disease type']),
            'treatment': self._find_column(col_map, ['treatment']),
            'biomarker': self._find_column(col_map, ['biomarker']),
            'trial': self._find_column(col_map, ['trial']),
        }

        # Extract tag values from row
        tags = {}
        for tag_name, col in tag_cols.items():
            if col and pd.notna(row.get(col)):
                val = str(row[col]).strip()
                if val and val.lower() != 'nan':
                    tags[tag_name] = val

        # If we have tags from the row, insert them (with 1.0 confidence as they're manual)
        if tags:
            # Manual tags get high confidence since they're from training data
            self.db.insert_tags(
                question_id,
                topic=tags.get('topic'),
                topic_confidence=1.0 if 'topic' in tags else None,
                disease_state=tags.get('disease_state'),
                disease_state_confidence=1.0 if 'disease_state' in tags else None,
                disease_stage=tags.get('disease_stage'),
                disease_stage_confidence=1.0 if 'disease_stage' in tags else None,
                disease_type=tags.get('disease_type'),
                disease_type_confidence=1.0 if 'disease_type' in tags else None,
                treatment=tags.get('treatment'),
                treatment_confidence=1.0 if 'treatment' in tags else None,
                biomarker=tags.get('biomarker'),
                biomarker_confidence=1.0 if 'biomarker' in tags else None,
                trial=tags.get('trial'),
                trial_confidence=1.0 if 'trial' in tags else None,
                needs_review=False,
                overall_confidence=1.0
            )
        elif self.use_auto_tagging and question_stem:
            # No tags in row - run auto-tagging
            self._run_auto_tagging(
                question_id=question_id,
                question_stem=question_stem,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers
            )
    
    def _insert_performance_from_row(self, question_id: int, row: pd.Series, columns: List[str], activity_id: Optional[int] = None):
        """Insert performance metrics from a row with segment columns."""
        # Define segment mappings
        # The file has: PRESCOREAVE, POSTSCOREAVE (overall), 
        # then .1 suffix for first segment, .2 for second, etc.
        
        segments = []
        
        # Overall metrics
        if 'PRESCOREAVE' in columns or 'POSTSCOREAVE' in columns:
            segments.append({
                'segment': 'overall',
                'pre_col': 'PRESCOREAVE',
                'post_col': 'POSTSCOREAVE',
                'pre_n_col': 'PRESCOREN',
                'post_n_col': 'POSTSCOREN'
            })
        
        # Find segment label columns and their corresponding metric columns
        # Pattern: Specialty, Setting, Setting.1 are labels; metrics have .1, .2, .3 suffixes
        segment_labels = []
        for col in columns:
            if col in ['Specialty', 'Setting', 'Setting.1']:
                segment_labels.append(col)
        
        # Map each label to its metric suffix
        suffix_map = {
            'Specialty': '.1',
            'Setting': '.2', 
            'Setting.1': '.3'
        }
        
        for label_col in segment_labels:
            if label_col in row.index and pd.notna(row[label_col]):
                segment_name = str(row[label_col]).strip().lower().replace(' ', '_')
                suffix = suffix_map.get(label_col, '')
                
                segments.append({
                    'segment': segment_name,
                    'pre_col': f'PRESCOREAVE{suffix}',
                    'post_col': f'POSTSCOREAVE{suffix}',
                    'pre_n_col': f'PRESCOREN{suffix}',
                    'post_n_col': f'POSTSCOREN{suffix}'
                })
        
        # Insert each segment's performance data
        for seg in segments:
            pre_score = self._safe_float(row.get(seg['pre_col']))
            post_score = self._safe_float(row.get(seg['post_col']))
            pre_n = self._safe_int(row.get(seg['pre_n_col']))
            post_n = self._safe_int(row.get(seg['post_n_col']))
            
            # Only insert if we have at least one metric
            if any(v is not None for v in [pre_score, post_score, pre_n, post_n]):
                self.db.insert_performance(
                    question_id=question_id,
                    segment=seg['segment'],
                    pre_score=pre_score,
                    post_score=post_score,
                    pre_n=pre_n,
                    post_n=post_n
                )
        
        # Also insert demographic performance data for granular reporting
        self._insert_demographic_performance_from_row(question_id, row, columns, activity_id)
    
    def _insert_demographic_performance_from_row(
        self, 
        question_id: int, 
        row: pd.Series, 
        columns: List[str],
        activity_id: Optional[int] = None
    ):
        """Insert granular demographic performance data for reporting."""
        # Extract demographic values from row
        specialty = None
        practice_setting = None
        practice_state = None
        
        # Look for specialty column
        if 'Specialty' in columns and pd.notna(row.get('Specialty')):
            specialty = str(row['Specialty']).strip()
        
        # Look for practice setting column (might be 'Setting' or 'Practice Setting')
        for col in ['Setting', 'Practice Setting', 'PracticeSetting']:
            if col in columns and pd.notna(row.get(col)):
                practice_setting = str(row[col]).strip()
                break
        
        # Look for state column (might be 'State', 'Practice State', etc.)
        for col in ['State', 'Practice State', 'PracticeState']:
            if col in columns and pd.notna(row.get(col)):
                practice_state = str(row[col]).strip()
                break
        
        # Get overall scores for demographic record
        pre_score = self._safe_float(row.get('PRESCOREAVE'))
        post_score = self._safe_float(row.get('POSTSCOREAVE'))
        n_respondents = self._safe_int(row.get('PRESCOREN')) or self._safe_int(row.get('POSTSCOREN'))
        
        # Only insert if we have demographic data and at least some scores
        if (specialty or practice_setting or practice_state) and (pre_score is not None or post_score is not None):
            self.db.insert_demographic_performance(
                question_id=question_id,
                activity_id=activity_id,
                specialty=specialty,
                practice_setting=practice_setting,
                practice_state=practice_state,
                pre_score=pre_score,
                post_score=post_score,
                n_respondents=n_respondents
            )
    
    def import_demographic_data(self, file_path: Path) -> int:
        """
        Import a file with granular demographic performance data.
        
        Expected columns: Question identifier, Specialty, Practice Setting, State/Region,
        Pre-Score, Post-Score, N, Activity Name
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Number of records imported
        """
        logger.info(f"Importing demographic data from {file_path.name}...")
        
        df = pd.read_excel(file_path)
        logger.info(f"  Found {len(df)} rows, columns: {list(df.columns)}")
        
        # Standardize column names
        col_map = {c.lower().strip(): c for c in df.columns}
        
        # Find columns
        question_col = self._find_column(col_map, ['question_id', 'questionid', 'question'])
        specialty_col = self._find_column(col_map, ['specialty'])
        setting_col = self._find_column(col_map, ['practice_setting', 'setting', 'practice setting'])
        state_col = self._find_column(col_map, ['state', 'practice_state', 'practice state'])
        pre_col = self._find_column(col_map, ['pre_score', 'prescoreave', 'pre score'])
        post_col = self._find_column(col_map, ['post_score', 'postscoreave', 'post score'])
        n_col = self._find_column(col_map, ['n', 'n_respondents', 'count', 'sample_size'])
        activity_col = self._find_column(col_map, ['activity', 'activity_name', 'activityname'])
        
        count = 0
        for idx, row in df.iterrows():
            # Get question ID (may need to look up by text)
            question_id = None
            if question_col:
                q_val = row.get(question_col)
                if pd.notna(q_val):
                    try:
                        question_id = int(q_val)
                    except ValueError:
                        # Might be question text - would need to look up
                        pass
            
            if not question_id:
                continue
            
            # Get activity ID if activity column exists
            activity_id = None
            if activity_col and pd.notna(row.get(activity_col)):
                activity_name = str(row[activity_col]).strip()
                activity = self.db.get_activity_by_name(activity_name)
                if activity:
                    activity_id = activity['id']
            
            # Get demographic values
            specialty = str(row[specialty_col]).strip() if specialty_col and pd.notna(row.get(specialty_col)) else None
            practice_setting = str(row[setting_col]).strip() if setting_col and pd.notna(row.get(setting_col)) else None
            practice_state = str(row[state_col]).strip() if state_col and pd.notna(row.get(state_col)) else None
            
            # Get scores
            pre_score = self._safe_float(row.get(pre_col)) if pre_col else None
            post_score = self._safe_float(row.get(post_col)) if post_col else None
            n_respondents = self._safe_int(row.get(n_col)) if n_col else None
            
            # Insert demographic performance record
            if specialty or practice_setting or practice_state:
                self.db.insert_demographic_performance(
                    question_id=question_id,
                    activity_id=activity_id,
                    specialty=specialty,
                    practice_setting=practice_setting,
                    practice_state=practice_state,
                    pre_score=pre_score,
                    post_score=post_score,
                    n_respondents=n_respondents
                )
                count += 1
        
        logger.info(f"  Imported {count} demographic records from {file_path.name}")
        return count
    
    def _insert_activities_from_row(self, question_id: int, row: pd.Series, col_map: Dict[str, str]):
        """Insert activity associations from a row."""
        # Look for ACTIVITY1, ACTIVITY2, etc. columns
        for i in range(1, 10):
            col_name = f'activity{i}'
            if col_name in col_map:
                val = row.get(col_map[col_name])
                if pd.notna(val) and str(val).strip():
                    self.db.insert_activity(question_id, str(val).strip())
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float."""
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int."""
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


def main(use_auto_tagging: bool = False, use_llm_fallback: bool = False):
    """
    Main import function.

    Args:
        use_auto_tagging: If True, run taggers on questions without existing tags
        use_llm_fallback: If True and use_auto_tagging, use LLM for low-confidence predictions
    """
    import argparse

    parser = argparse.ArgumentParser(description="Import CME questions into database")
    parser.add_argument(
        "--auto-tag",
        action="store_true",
        help="Run auto-tagging on questions without existing tags (stores confidence scores)"
    )
    parser.add_argument(
        "--llm-fallback",
        action="store_true",
        help="Use LLM fallback for low-confidence predictions (requires --auto-tag)"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear the database before import (append mode)"
    )
    args = parser.parse_args()

    # Use command line args or function parameters
    use_auto_tagging = args.auto_tag or use_auto_tagging
    use_llm_fallback = args.llm_fallback or use_llm_fallback

    # Paths
    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    db_path = Path(__file__).parent.parent / "data" / "questions.db"

    logger.info(f"Database path: {db_path}")
    logger.info(f"Data directory: {data_dir}")
    if use_auto_tagging:
        logger.info(f"Auto-tagging: ENABLED (LLM fallback: {'ON' if use_llm_fallback else 'OFF'})")
    else:
        logger.info("Auto-tagging: DISABLED")

    # Initialize database
    db = DatabaseService(db_path)

    # Clear existing data unless --no-clear specified
    if not args.no_clear:
        logger.info("Clearing existing database...")
        db.clear_database()
    else:
        logger.info("Append mode: keeping existing data")

    importer = DataImporter(db, use_auto_tagging=use_auto_tagging, use_llm_fallback=use_llm_fallback)
    total_imported = 0
    auto_tagged_count = 0

    # Import training data files
    training_files = list(raw_dir.glob("Training Data*.xlsx"))
    logger.info(f"\nFound {len(training_files)} training data files")

    for file_path in training_files:
        count = importer.import_training_data(file_path)
        total_imported += count

    # Import untagged files with performance data
    untagged_files = list(data_dir.glob("To Be Tagged*.xlsx"))
    logger.info(f"\nFound {len(untagged_files)} untagged files")

    for file_path in untagged_files:
        count = importer.import_untagged_with_performance(file_path)
        total_imported += count

    # Import oncology questions (new format with 7 audience segments)
    oncology_files = list(raw_dir.glob("AllQuestions*.xlsx"))
    logger.info(f"\nFound {len(oncology_files)} oncology question files")

    for file_path in oncology_files:
        count = importer.import_oncology_questions(file_path)
        total_imported += count

    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Import complete!")
    stats = db.get_stats()
    logger.info(f"Total questions: {stats['total_questions']}")
    logger.info(f"Tagged questions: {stats['tagged_questions']}")
    logger.info(f"Questions with performance data: {stats['questions_with_performance']}")
    logger.info(f"Total activities: {stats['total_activities']}")
    logger.info(f"Activities with dates: {stats.get('activities_with_dates', 0)}")
    logger.info(f"Demographic records: {stats.get('demographic_records', 0)}")

    # Show sample filter options
    options = db.get_filter_options()
    logger.info(f"\nAvailable topics: {len(options['topics'])}")
    logger.info(f"Available disease states: {len(options['disease_states'])}")
    logger.info(f"Available treatments: {len(options['treatments'])}")

    # Show demographic options
    demo_options = db.get_demographic_options()
    logger.info(f"\nDemographic options available:")
    logger.info(f"  Specialties: {len(demo_options.get('specialties', []))}")
    logger.info(f"  Practice settings: {len(demo_options.get('practice_settings', []))}")
    logger.info(f"  Regions: {len(demo_options.get('regions', []))}")

    # Show audience segment info
    try:
        segments = db.get_available_segments()
        if segments:
            logger.info(f"\nAudience segments available:")
            for seg in segments:
                logger.info(f"  {seg['segment']}: {seg['count']} questions")
    except Exception:
        pass  # get_available_segments may not exist in older databases

    # If auto-tagging was used, show confidence stats
    if use_auto_tagging:
        logger.info(f"\n{'='*50}")
        logger.info("Auto-tagging summary:")
        logger.info("  Per-tag confidence scores have been stored.")
        logger.info("  Tags below threshold are flagged for review.")
        logger.info("  View flagged questions in the dashboard with 'Needs Review' filter.")


if __name__ == "__main__":
    main()

