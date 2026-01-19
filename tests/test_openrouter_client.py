"""
Unit tests for OpenRouterClient.

Tests the unified LLM client functionality:
- Model configuration loading
- API call handling
- Cost calculation
- Parallel model calls
- Web search
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.core.taggers.openrouter_client import (
    OpenRouterClient,
    ModelConfig,
    APIUsage,
    get_openrouter_client
)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_model_config_creation(self):
        """Test creating a ModelConfig instance."""
        config = ModelConfig(
            id="test/model",
            display_name="Test Model",
            context_window=100000,
            cost_per_m_input=1.0,
            cost_per_m_output=5.0
        )

        assert config.id == "test/model"
        assert config.display_name == "Test Model"
        assert config.context_window == 100000
        assert config.cost_per_m_input == 1.0
        assert config.cost_per_m_output == 5.0
        assert config.temperature == 0.1  # Default
        assert config.max_tokens == 1000  # Default


class TestOpenRouterClient:
    """Tests for OpenRouterClient class."""

    @pytest.fixture
    def client(self):
        """Create OpenRouter client with test API key."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            return OpenRouterClient(api_key="test-key")

    @pytest.fixture
    def client_no_key(self):
        """Create OpenRouter client without API key."""
        with patch.dict("os.environ", {}, clear=True):
            return OpenRouterClient(api_key=None)

    # ============== Initialization Tests ==============

    def test_client_initialization_with_key(self, client):
        """Test client initialization with API key."""
        assert client.api_key == "test-key"
        assert len(client.models) >= 4  # gpt, claude, gemini, search
        assert client.usage_log == []

    def test_client_initialization_without_key(self, client_no_key):
        """Test client initialization without API key logs warning."""
        assert client_no_key.api_key is None

    def test_default_models_present(self, client):
        """Test that default models are available."""
        assert "gpt" in client.models
        assert "claude" in client.models
        assert "gemini" in client.models
        assert "search" in client.models

    def test_model_config_values(self, client):
        """Test model configuration values are reasonable."""
        gpt = client.models["gpt"]
        assert gpt.context_window > 100000
        assert gpt.cost_per_m_input > 0
        assert gpt.cost_per_m_output > 0

    # ============== Cost Calculation Tests ==============

    def test_cost_calculation(self, client):
        """Test API cost calculation."""
        # Using default GPT model costs
        cost = client._calculate_cost(
            model_key="gpt",
            input_tokens=1000000,
            output_tokens=100000
        )

        # Should be input_cost + output_cost
        expected = (1000000 / 1_000_000) * client.models["gpt"].cost_per_m_input
        expected += (100000 / 1_000_000) * client.models["gpt"].cost_per_m_output
        assert cost == pytest.approx(expected)

    def test_cost_calculation_unknown_model(self, client):
        """Test cost calculation returns 0 for unknown model."""
        cost = client._calculate_cost(
            model_key="unknown",
            input_tokens=1000,
            output_tokens=100
        )
        assert cost == 0.0

    def test_cost_calculation_zero_tokens(self, client):
        """Test cost calculation with zero tokens."""
        cost = client._calculate_cost(
            model_key="gpt",
            input_tokens=0,
            output_tokens=0
        )
        assert cost == 0.0

    # ============== Generate Tests (Mocked) ==============

    @pytest.mark.asyncio
    async def test_generate_requires_api_key(self, client_no_key):
        """Test that generate raises error without API key."""
        with pytest.raises(ValueError, match="API key not configured"):
            await client_no_key.generate(
                model="gpt",
                messages=[{"role": "user", "content": "test"}]
            )

    @pytest.mark.asyncio
    async def test_generate_unknown_model(self, client):
        """Test that generate raises error for unknown model."""
        with pytest.raises(ValueError, match="Unknown model"):
            await client.generate(
                model="unknown_model",
                messages=[{"role": "user", "content": "test"}]
            )

    @pytest.mark.asyncio
    async def test_generate_success(self, client):
        """Test successful generate call with mocked response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"topic": "Test"}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        client._client = mock_client

        result = await client.generate(
            model="gpt",
            messages=[{"role": "user", "content": "test"}]
        )

        assert result["content"] == '{"topic": "Test"}'
        assert result["usage"]["input_tokens"] == 100
        assert result["usage"]["output_tokens"] == 50
        assert "cost" in result

        await client.close()

    # ============== Parallel Generate Tests ==============

    @pytest.mark.asyncio
    async def test_generate_parallel(self, client):
        """Test parallel generation across multiple models."""
        async def mock_generate(model, messages, **kwargs):
            return {
                "content": f'{{"model": "{model}"}}',
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "model": model,
                "cost": 0.04
            }

        client.generate = AsyncMock(side_effect=mock_generate)

        results = await client.generate_parallel(
            messages=[{"role": "user", "content": "test"}],
            models=["gpt", "claude", "gemini"]
        )

        assert "gpt" in results
        assert "claude" in results
        assert "gemini" in results
        assert client.generate.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_parallel_handles_errors(self, client):
        """Test that parallel generate handles individual model errors."""
        async def mock_generate_with_error(model, messages, **kwargs):
            if model == "gemini":
                raise Exception("Gemini error")
            return {
                "content": f'{{"model": "{model}"}}',
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "model": model,
                "cost": 0.04
            }

        client.generate = AsyncMock(side_effect=mock_generate_with_error)

        results = await client.generate_parallel(
            messages=[{"role": "user", "content": "test"}],
            models=["gpt", "claude", "gemini"]
        )

        # GPT and Claude should succeed
        assert results["gpt"]["content"] == '{"model": "gpt"}'
        assert results["claude"]["content"] == '{"model": "claude"}'
        # Gemini should have error info
        assert results["gemini"]["error"] == "Gemini error"
        assert results["gemini"]["content"] is None

    # ============== Web Search Tests ==============

    @pytest.mark.asyncio
    async def test_web_search(self, client):
        """Test web search functionality."""
        async def mock_generate(model, messages, **kwargs):
            if model == "search":
                return {
                    "content": "Search results for query",
                    "usage": {"input_tokens": 50, "output_tokens": 200},
                    "model": "search",
                    "cost": 0.01
                }
            raise ValueError("Should use search model")

        client.generate = AsyncMock(side_effect=mock_generate)

        result = await client.web_search(
            query="novel drug oncology trial",
            context="Looking up treatment information"
        )

        assert result["content"] == "Search results for query"
        client.generate.assert_called_once()

        # Check that search model was used with web_search=True
        call_kwargs = client.generate.call_args
        assert call_kwargs.kwargs.get("web_search") is True

    # ============== Usage Tracking Tests ==============

    def test_usage_log_empty_initially(self, client):
        """Test that usage log starts empty."""
        assert len(client.usage_log) == 0

    def test_get_total_cost_empty(self, client):
        """Test total cost is 0 when no calls made."""
        assert client.get_total_cost() == 0.0

    def test_get_total_cost_with_usage(self, client):
        """Test total cost calculation with usage entries."""
        from datetime import datetime

        client.usage_log.append(APIUsage(
            model="gpt",
            input_tokens=1000,
            output_tokens=100,
            cost=0.05,
            timestamp=datetime.utcnow()
        ))
        client.usage_log.append(APIUsage(
            model="claude",
            input_tokens=1000,
            output_tokens=100,
            cost=0.08,
            timestamp=datetime.utcnow()
        ))

        assert client.get_total_cost() == pytest.approx(0.13)

    def test_get_usage_summary(self, client):
        """Test usage summary generation."""
        from datetime import datetime

        client.usage_log.append(APIUsage(
            model="gpt",
            input_tokens=1000,
            output_tokens=100,
            cost=0.05,
            timestamp=datetime.utcnow()
        ))
        client.usage_log.append(APIUsage(
            model="gpt",
            input_tokens=2000,
            output_tokens=200,
            cost=0.10,
            timestamp=datetime.utcnow()
        ))
        client.usage_log.append(APIUsage(
            model="claude",
            input_tokens=1000,
            output_tokens=100,
            cost=0.08,
            timestamp=datetime.utcnow()
        ))

        summary = client.get_usage_summary()

        assert summary["total_calls"] == 3
        assert summary["total_cost"] == pytest.approx(0.23)
        assert summary["by_model"]["gpt"]["calls"] == 2
        assert summary["by_model"]["gpt"]["input_tokens"] == 3000
        assert summary["by_model"]["claude"]["calls"] == 1

    # ============== Model Info Tests ==============

    def test_get_model_info(self, client):
        """Test getting model information."""
        info = client.get_model_info("gpt")

        assert info is not None
        assert info["key"] == "gpt"
        assert "id" in info
        assert "display_name" in info
        assert "context_window" in info
        assert "cost_per_m_input" in info

    def test_get_model_info_unknown(self, client):
        """Test getting info for unknown model returns None."""
        info = client.get_model_info("unknown")
        assert info is None

    # ============== Client Lifecycle Tests ==============

    @pytest.mark.asyncio
    async def test_close_client(self, client):
        """Test closing the HTTP client."""
        # Create a mock client
        mock_http = AsyncMock()
        client._client = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_client_when_none(self, client):
        """Test closing when no client exists doesn't error."""
        client._client = None
        await client.close()  # Should not raise


class TestGetOpenRouterClient:
    """Tests for singleton client factory."""

    def test_get_client_returns_instance(self):
        """Test that get_openrouter_client returns an instance."""
        # Reset singleton
        import src.core.taggers.openrouter_client as module
        module._client_instance = None

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            client = get_openrouter_client()
            assert isinstance(client, OpenRouterClient)

    def test_get_client_returns_same_instance(self):
        """Test that repeated calls return the same instance."""
        import src.core.taggers.openrouter_client as module
        module._client_instance = None

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            client1 = get_openrouter_client()
            client2 = get_openrouter_client()
            assert client1 is client2
