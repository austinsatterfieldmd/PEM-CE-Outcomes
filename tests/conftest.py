"""
Pytest configuration and fixtures for Automated CE Outcomes Dashboard V3.

This module provides shared fixtures for:
- Database setup/teardown
- Mock OpenRouter client
- Sample data for testing
"""

import pytest
import asyncio
import sqlite3
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure we can import from src
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============== Async Event Loop ==============

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============== Sample Data Fixtures ==============

@pytest.fixture
def sample_question() -> Dict[str, Any]:
    """Sample oncology question for testing."""
    return {
        "id": 1,
        "question_stem": "A 65-year-old woman with metastatic NSCLC and EGFR exon 19 deletion is being considered for first-line therapy. Based on the FLAURA trial, which treatment would be most appropriate?",
        "correct_answer": "Osimertinib",
        "incorrect_answers": ["Erlotinib", "Gefitinib", "Afatinib"]
    }


@pytest.fixture
def sample_questions() -> List[Dict[str, Any]]:
    """Multiple sample questions for batch testing."""
    return [
        {
            "id": 1,
            "question_stem": "A 65-year-old woman with metastatic NSCLC and EGFR exon 19 deletion is being considered for first-line therapy. Based on the FLAURA trial, which treatment would be most appropriate?",
            "correct_answer": "Osimertinib"
        },
        {
            "id": 2,
            "question_stem": "In a patient with HER2-positive metastatic breast cancer who progressed on trastuzumab and pertuzumab, what is the preferred second-line treatment based on DESTINY-Breast03?",
            "correct_answer": "Trastuzumab deruxtecan (T-DXd)"
        },
        {
            "id": 3,
            "question_stem": "A patient with newly diagnosed chronic myeloid leukemia in chronic phase has a BCR-ABL transcript level of 10%. What is the recommended first-line treatment?",
            "correct_answer": "Imatinib or a second-generation TKI"
        }
    ]


@pytest.fixture
def sample_tags() -> Dict[str, Any]:
    """Sample tags for a question."""
    return {
        "topic": "Treatment selection",
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }


@pytest.fixture
def sample_gpt_response() -> Dict[str, Any]:
    """Sample GPT response tags."""
    return {
        "topic": "Treatment selection",
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }


@pytest.fixture
def sample_claude_response() -> Dict[str, Any]:
    """Sample Claude response tags."""
    return {
        "topic": "Treatment selection",
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }


@pytest.fixture
def sample_gemini_response() -> Dict[str, Any]:
    """Sample Gemini response tags."""
    return {
        "topic": "Treatment selection",
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }


@pytest.fixture
def sample_disagreement_responses() -> tuple:
    """Sample responses with majority disagreement."""
    gpt = {
        "topic": "Treatment selection",
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }
    claude = {
        "topic": "Treatment selection",
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }
    gemini = {
        "topic": "Clinical efficacy",  # Different
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }
    return gpt, claude, gemini


@pytest.fixture
def sample_conflict_responses() -> tuple:
    """Sample responses with all three models disagreeing."""
    gpt = {
        "topic": "Treatment selection",
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }
    claude = {
        "topic": "Clinical efficacy",  # Different
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }
    gemini = {
        "topic": "Emerging therapies",  # Different
        "disease_state": "NSCLC",
        "disease_stage": "Metastatic",
        "disease_type": "EGFR-mutated",
        "treatment_line": "First-line",
        "treatment": "osimertinib",
        "biomarker": "EGFR",
        "trial": "FLAURA"
    }
    return gpt, claude, gemini


# ============== Database Fixtures ==============

@pytest.fixture
def test_db_path(tmp_path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test_questions.db"


@pytest.fixture
def init_test_db(test_db_path) -> Path:
    """Initialize a test database with schema."""
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Create questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_stem TEXT NOT NULL,
            correct_answer TEXT,
            incorrect_answers TEXT,
            source_file TEXT,
            is_oncology INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create tags table
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
            overall_confidence REAL,
            needs_review INTEGER DEFAULT 0,
            review_flags TEXT,
            flagged_at TIMESTAMP,
            llm_calls_made INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    # Create performance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            segment TEXT,
            pre_score REAL,
            post_score REAL,
            pre_n INTEGER,
            post_n INTEGER,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    # Create question_activities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS question_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            activity_id INTEGER,
            activity_name TEXT,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    # Create activities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_name TEXT UNIQUE,
            activity_date DATE,
            quarter TEXT,
            target_audience TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create voting_results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voting_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            iteration INTEGER DEFAULT 1,
            prompt_version TEXT,
            gpt_tags TEXT,
            claude_tags TEXT,
            gemini_tags TEXT,
            aggregated_tags TEXT,
            agreement_level TEXT,
            needs_review INTEGER DEFAULT 0,
            web_searches TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    # Create review_corrections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            iteration INTEGER,
            original_tags TEXT,
            corrected_tags TEXT,
            disagreement_category TEXT,
            reviewer_notes TEXT,
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    # Create disagreement_patterns table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS disagreement_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            iteration INTEGER,
            category TEXT,
            frequency INTEGER,
            example_questions TEXT,
            recommended_action TEXT,
            implemented INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create novel_entities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS novel_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_name TEXT NOT NULL,
            normalized_name TEXT,
            entity_type TEXT NOT NULL,
            confidence REAL,
            occurrence_count INTEGER DEFAULT 1,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            reviewed_by TEXT,
            reviewed_at TIMESTAMP,
            drug_class TEXT,
            synonyms TEXT,
            notes TEXT
        )
    """)

    # Create novel_entity_occurrences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS novel_entity_occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            novel_entity_id INTEGER,
            question_id INTEGER,
            source_text TEXT,
            extraction_confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (novel_entity_id) REFERENCES novel_entities(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    # Create demographic_performance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS demographic_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            specialty TEXT,
            practice_setting TEXT,
            region TEXT,
            practice_state TEXT,
            pre_score REAL,
            post_score REAL,
            n INTEGER,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    conn.commit()
    conn.close()

    return test_db_path


@pytest.fixture
def populated_test_db(init_test_db, sample_questions) -> Path:
    """Initialize test database with sample data."""
    conn = sqlite3.connect(init_test_db)
    cursor = conn.cursor()

    # Insert sample questions
    for q in sample_questions:
        cursor.execute("""
            INSERT INTO questions (id, question_stem, correct_answer, incorrect_answers)
            VALUES (?, ?, ?, ?)
        """, (
            q["id"],
            q["question_stem"],
            q["correct_answer"],
            json.dumps(q.get("incorrect_answers", []))
        ))

        # Insert tags
        cursor.execute("""
            INSERT INTO tags (question_id, topic, disease_state)
            VALUES (?, ?, ?)
        """, (q["id"], None, None))

        # Insert performance data
        cursor.execute("""
            INSERT INTO performance (question_id, segment, pre_score, post_score, pre_n, post_n)
            VALUES (?, 'overall', 45.0, 75.0, 100, 100)
        """, (q["id"],))

    conn.commit()
    conn.close()

    return init_test_db


# ============== Mock Client Fixtures ==============

@pytest.fixture
def mock_openrouter_response():
    """Factory fixture to create mock OpenRouter responses."""
    def _create_response(tags: Dict[str, Any]):
        return {
            "content": json.dumps(tags),
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 200
            },
            "model": "test-model",
            "model_id": "test/model-id",
            "cost": 0.04
        }
    return _create_response


@pytest.fixture
def mock_openrouter_client(sample_gpt_response, sample_claude_response, sample_gemini_response):
    """Create a mock OpenRouter client for testing without API calls."""
    mock_client = MagicMock()
    mock_client.api_key = "test-api-key"

    async def mock_generate(model, messages, **kwargs):
        responses = {
            "gpt": sample_gpt_response,
            "claude": sample_claude_response,
            "gemini": sample_gemini_response
        }
        return {
            "content": json.dumps(responses.get(model, {})),
            "usage": {"input_tokens": 1000, "output_tokens": 200},
            "model": f"{model}-test",
            "model_id": f"test/{model}",
            "cost": 0.04
        }

    async def mock_generate_parallel(messages, models=None, **kwargs):
        models = models or ["gpt", "claude", "gemini"]
        result = {}
        for model in models:
            result[model] = await mock_generate(model, messages, **kwargs)
        return result

    mock_client.generate = AsyncMock(side_effect=mock_generate)
    mock_client.generate_parallel = AsyncMock(side_effect=mock_generate_parallel)
    mock_client.web_search = AsyncMock(return_value={"content": "Web search result"})
    mock_client.get_total_cost = MagicMock(return_value=0.12)
    mock_client.usage_log = []

    return mock_client


# ============== FastAPI Test Client Fixtures ==============

@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    from src.api.main import app
    return app


@pytest.fixture
def test_client(app):
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
async def async_test_client(app):
    """Create async test client for FastAPI app."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
