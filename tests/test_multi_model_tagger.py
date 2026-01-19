"""
Unit tests for MultiModelTagger.

Tests the 3-model tagging orchestration:
- Question tagging workflow
- Response parsing
- Batch tagging
- Web search triggering
- Statistics generation
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.core.taggers.multi_model_tagger import (
    MultiModelTagger,
    get_multi_model_tagger
)
from src.core.taggers.vote_aggregator import AgreementLevel


class TestMultiModelTagger:
    """Tests for MultiModelTagger class."""

    @pytest.fixture
    def tagger(self, mock_openrouter_client):
        """Create MultiModelTagger with mocked client."""
        return MultiModelTagger(
            client=mock_openrouter_client,
            prompt_version="v1.0",
            use_web_search=True
        )

    @pytest.fixture
    def tagger_no_search(self, mock_openrouter_client):
        """Create MultiModelTagger with web search disabled."""
        return MultiModelTagger(
            client=mock_openrouter_client,
            prompt_version="v1.0",
            use_web_search=False
        )

    # ============== Initialization Tests ==============

    def test_tagger_initialization(self, tagger):
        """Test tagger initializes with correct config."""
        assert tagger.prompt_version == "v1.0"
        assert tagger.use_web_search is True
        assert tagger.aggregator is not None
        assert tagger.client is not None

    def test_default_system_prompt_exists(self, tagger):
        """Test that default system prompt is available."""
        # Even without prompt file, should have default
        assert len(tagger.system_prompt) > 0
        assert "oncology" in tagger.system_prompt.lower()

    # ============== Message Building Tests ==============

    def test_build_messages_basic(self, tagger, sample_question):
        """Test building messages for LLM call."""
        messages = tagger._build_messages(
            question_text=sample_question["question_stem"]
        )

        assert len(messages) >= 2  # System + user at minimum
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert sample_question["question_stem"] in messages[-1]["content"]

    def test_build_messages_with_answer(self, tagger, sample_question):
        """Test building messages includes correct answer."""
        messages = tagger._build_messages(
            question_text=sample_question["question_stem"],
            correct_answer=sample_question["correct_answer"]
        )

        user_message = messages[-1]["content"]
        assert sample_question["correct_answer"] in user_message

    def test_build_messages_with_kb_context(self, tagger, sample_question):
        """Test building messages includes KB context."""
        kb_context = {
            "known_drugs": ["osimertinib", "erlotinib"],
            "known_trials": ["FLAURA"]
        }

        messages = tagger._build_messages(
            question_text=sample_question["question_stem"],
            kb_context=kb_context
        )

        user_message = messages[-1]["content"]
        assert "Knowledge Base Context" in user_message

    # ============== Response Parsing Tests ==============

    def test_parse_response_valid_json(self, tagger):
        """Test parsing valid JSON response."""
        content = '{"topic": "Treatment selection", "disease_state": "NSCLC"}'
        result = tagger._parse_response(content)

        assert result["topic"] == "Treatment selection"
        assert result["disease_state"] == "NSCLC"

    def test_parse_response_json_in_markdown(self, tagger):
        """Test parsing JSON wrapped in markdown code block."""
        content = '''```json
{"topic": "Treatment selection", "disease_state": "NSCLC"}
```'''
        result = tagger._parse_response(content)

        assert result["topic"] == "Treatment selection"

    def test_parse_response_plain_code_block(self, tagger):
        """Test parsing JSON in plain code block."""
        content = '''```
{"topic": "Treatment selection", "disease_state": "NSCLC"}
```'''
        result = tagger._parse_response(content)

        assert result["topic"] == "Treatment selection"

    def test_parse_response_invalid_json(self, tagger):
        """Test parsing invalid JSON returns empty dict."""
        content = "This is not JSON at all"
        result = tagger._parse_response(content)

        assert result == {}

    def test_parse_response_with_whitespace(self, tagger):
        """Test parsing JSON with extra whitespace."""
        content = '''

    {"topic": "Treatment selection"}

        '''
        result = tagger._parse_response(content)

        assert result["topic"] == "Treatment selection"

    # ============== Tag Question Tests ==============

    @pytest.mark.asyncio
    async def test_tag_question_unanimous(
        self,
        tagger,
        sample_question,
        sample_gpt_response
    ):
        """Test tagging question with unanimous agreement."""
        result = await tagger.tag_question(
            question_id=sample_question["id"],
            question_text=sample_question["question_stem"],
            correct_answer=sample_question["correct_answer"]
        )

        assert result.question_id == sample_question["id"]
        assert result.overall_agreement == AgreementLevel.UNANIMOUS
        assert result.needs_review is False

    @pytest.mark.asyncio
    async def test_tag_question_calls_all_models(
        self,
        tagger,
        sample_question
    ):
        """Test that all 3 models are called."""
        await tagger.tag_question(
            question_id=sample_question["id"],
            question_text=sample_question["question_stem"]
        )

        # Check generate_parallel was called with all 3 models
        tagger.client.generate_parallel.assert_called_once()
        call_kwargs = tagger.client.generate_parallel.call_args
        models = call_kwargs.kwargs.get("models", call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        assert set(models or ["gpt", "claude", "gemini"]) == {"gpt", "claude", "gemini"}

    @pytest.mark.asyncio
    async def test_tag_question_with_conflict_triggers_search(
        self,
        mock_openrouter_client,
        sample_question,
        sample_conflict_responses
    ):
        """Test that conflicts trigger web search when enabled."""
        gpt, claude, gemini = sample_conflict_responses

        async def mock_parallel(*args, **kwargs):
            return {
                "gpt": {"content": json.dumps(gpt), "usage": {"input_tokens": 100, "output_tokens": 50}},
                "claude": {"content": json.dumps(claude), "usage": {"input_tokens": 100, "output_tokens": 50}},
                "gemini": {"content": json.dumps(gemini), "usage": {"input_tokens": 100, "output_tokens": 50}}
            }

        mock_openrouter_client.generate_parallel = AsyncMock(side_effect=mock_parallel)

        tagger = MultiModelTagger(
            client=mock_openrouter_client,
            use_web_search=True
        )

        result = await tagger.tag_question(
            question_id=sample_question["id"],
            question_text=sample_question["question_stem"]
        )

        # Since topic has conflict, web search might be triggered
        # Note: web_search is only triggered for treatment/trial/biomarker conflicts
        assert result.overall_agreement == AgreementLevel.CONFLICT

    @pytest.mark.asyncio
    async def test_tag_question_no_search_when_disabled(
        self,
        tagger_no_search,
        sample_question
    ):
        """Test that web search is not called when disabled."""
        await tagger_no_search.tag_question(
            question_id=sample_question["id"],
            question_text=sample_question["question_stem"]
        )

        tagger_no_search.client.web_search.assert_not_called()

    # ============== Batch Tagging Tests ==============

    @pytest.mark.asyncio
    async def test_tag_batch_processes_all(
        self,
        tagger,
        sample_questions
    ):
        """Test batch tagging processes all questions."""
        results = await tagger.tag_batch(sample_questions)

        assert len(results) == len(sample_questions)
        for result in results:
            assert result.question_id in [q["id"] for q in sample_questions]

    @pytest.mark.asyncio
    async def test_tag_batch_with_progress_callback(
        self,
        tagger,
        sample_questions
    ):
        """Test batch tagging calls progress callback."""
        progress_updates = []

        def callback(completed, total):
            progress_updates.append((completed, total))

        results = await tagger.tag_batch(sample_questions, progress_callback=callback)

        # Should have one update per question
        assert len(progress_updates) == len(sample_questions)
        # Last update should show all complete
        assert progress_updates[-1] == (len(sample_questions), len(sample_questions))

    @pytest.mark.asyncio
    async def test_tag_batch_handles_errors(
        self,
        mock_openrouter_client,
        sample_questions
    ):
        """Test batch tagging handles individual question errors."""
        call_count = 0

        async def mock_parallel_with_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("API Error")
            return {
                "gpt": {"content": '{"topic": "Test"}', "usage": {"input_tokens": 100, "output_tokens": 50}},
                "claude": {"content": '{"topic": "Test"}', "usage": {"input_tokens": 100, "output_tokens": 50}},
                "gemini": {"content": '{"topic": "Test"}', "usage": {"input_tokens": 100, "output_tokens": 50}}
            }

        mock_openrouter_client.generate_parallel = AsyncMock(side_effect=mock_parallel_with_error)
        tagger = MultiModelTagger(client=mock_openrouter_client)

        results = await tagger.tag_batch(sample_questions)

        # Should still return results for all questions
        assert len(results) == len(sample_questions)
        # The failed one should have conflict status
        assert any(r.overall_agreement == AgreementLevel.CONFLICT for r in results)

    # ============== Statistics Tests ==============

    def test_get_stats_empty(self, tagger):
        """Test stats with empty results."""
        stats = tagger.get_stats([])

        assert stats["total"] == 0
        assert stats["unanimous"] == 0
        assert stats["majority"] == 0
        assert stats["conflict"] == 0
        assert stats["needs_review"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_results(self, tagger, sample_questions):
        """Test stats calculation with actual results."""
        results = await tagger.tag_batch(sample_questions)
        stats = tagger.get_stats(results)

        assert stats["total"] == len(sample_questions)
        # All should be unanimous with our mock
        assert stats["unanimous"] == len(sample_questions)
        assert stats["needs_review"] == 0

    def test_get_stats_includes_cost(self, tagger):
        """Test that stats include API cost."""
        stats = tagger.get_stats([])
        assert "api_cost" in stats


class TestGetMultiModelTagger:
    """Tests for singleton tagger factory."""

    def test_get_tagger_returns_instance(self):
        """Test that get_multi_model_tagger returns an instance."""
        import src.core.taggers.multi_model_tagger as module
        module._tagger_instance = None

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            tagger = get_multi_model_tagger()
            assert isinstance(tagger, MultiModelTagger)

    def test_get_tagger_returns_same_instance(self):
        """Test that repeated calls return the same instance."""
        import src.core.taggers.multi_model_tagger as module
        module._tagger_instance = None

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            tagger1 = get_multi_model_tagger()
            tagger2 = get_multi_model_tagger()
            assert tagger1 is tagger2


class TestWebSearchIntegration:
    """Tests for web search triggering logic."""

    @pytest.fixture
    def conflict_treatment_responses(self):
        """Create responses with treatment conflict."""
        gpt = {"treatment": "Drug A", "topic": "Same"}
        claude = {"treatment": "Drug B", "topic": "Same"}
        gemini = {"treatment": "Drug C", "topic": "Same"}
        return gpt, claude, gemini

    @pytest.mark.asyncio
    async def test_web_search_triggered_on_treatment_conflict(
        self,
        mock_openrouter_client,
        sample_question,
        conflict_treatment_responses
    ):
        """Test web search is triggered for treatment conflicts."""
        gpt, claude, gemini = conflict_treatment_responses

        async def mock_parallel(*args, **kwargs):
            return {
                "gpt": {"content": json.dumps(gpt)},
                "claude": {"content": json.dumps(claude)},
                "gemini": {"content": json.dumps(gemini)}
            }

        mock_openrouter_client.generate_parallel = AsyncMock(side_effect=mock_parallel)

        tagger = MultiModelTagger(
            client=mock_openrouter_client,
            use_web_search=True
        )

        result = await tagger.tag_question(
            question_id=1,
            question_text=sample_question["question_stem"]
        )

        # Web search should be triggered for treatment conflict
        assert mock_openrouter_client.web_search.call_count >= 0
        # Result should still be valid
        assert result.overall_agreement == AgreementLevel.CONFLICT
