"""
OpenRouter API Client for V3 3-Model Voting System.

Provides a unified interface to call multiple LLM models through OpenRouter:
- GPT-5.2 (openai/gpt-5.2)
- Claude Opus 4.5 (anthropic/claude-opus-4.5)
- Gemini 2.5 Pro (google/gemini-2.5-pro)
- Perplexity Sonar for web search (perplexity/sonar)

All models are accessed through a single API key.
"""

import httpx
import asyncio
import logging
import os
import random
import yaml
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd

    # Retryable error conditions
    retryable_status_codes: tuple = field(default_factory=lambda: (
        408,  # Request Timeout
        429,  # Too Many Requests (rate limit)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    ))
    retryable_exceptions: tuple = field(default_factory=lambda: (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadError,
        ConnectionError,
        OSError,  # Includes SSL errors
    ))

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "models.yaml"


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    id: str
    display_name: str
    context_window: int
    cost_per_m_input: float
    cost_per_m_output: float
    temperature: float = 0.1
    max_tokens: int = 1000


@dataclass
class APIUsage:
    """Track API usage for cost estimation."""
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime


class OpenRouterClient:
    """
    Unified client for all LLM models via OpenRouter.

    Usage:
        client = OpenRouterClient()
        response = await client.generate("gpt", messages)
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Default model configurations (fallback if config file not found)
    DEFAULT_MODELS = {
        "gpt": ModelConfig(
            id="openai/gpt-5.2",
            display_name="GPT-5.2",
            context_window=400000,
            cost_per_m_input=1.75,
            cost_per_m_output=14.00,
            temperature=0.1,
            max_tokens=1000
        ),
        "claude": ModelConfig(
            id="anthropic/claude-opus-4.5",
            display_name="Claude Opus 4.5",
            context_window=200000,
            cost_per_m_input=5.00,
            cost_per_m_output=25.00,
            temperature=0.1,
            max_tokens=1000
        ),
        "gemini": ModelConfig(
            id="google/gemini-2.5-pro",
            display_name="Gemini 2.5 Pro",
            context_window=1048576,
            cost_per_m_input=1.25,
            cost_per_m_output=10.00,
            temperature=0.1,
            max_tokens=1000
        ),
        "search": ModelConfig(
            id="perplexity/sonar",
            display_name="Perplexity Sonar",
            context_window=127072,
            cost_per_m_input=1.00,
            cost_per_m_output=1.00,
            temperature=0.2,
            max_tokens=2000
        )
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key. If not provided, reads from OPENROUTER_API_KEY env var.
            retry_config: Configuration for retry logic. Uses defaults if not provided.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("No OpenRouter API key provided. Set OPENROUTER_API_KEY environment variable.")

        self.models = self._load_model_config()
        self.usage_log: List[APIUsage] = []
        self._client: Optional[httpx.AsyncClient] = None
        self.retry_config = retry_config or RetryConfig()

        # Track retry statistics
        self.retry_stats = {"total_retries": 0, "successful_retries": 0, "failed_after_retries": 0}

        # Site info for OpenRouter headers
        self.site_url = "https://cme-outcomes-dashboard.local"
        self.site_name = "CME Outcomes Tagger V3"

    def _load_model_config(self) -> Dict[str, ModelConfig]:
        """Load model configuration from YAML file."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r") as f:
                    config = yaml.safe_load(f)

                models = {}
                for key, model_data in config.get("models", {}).items():
                    models[key] = ModelConfig(
                        id=model_data["id"],
                        display_name=model_data["display_name"],
                        context_window=model_data["context_window"],
                        cost_per_m_input=model_data["cost_per_m_input"],
                        cost_per_m_output=model_data["cost_per_m_output"],
                        temperature=model_data.get("temperature", 0.1),
                        max_tokens=model_data.get("max_tokens", 1000)
                    )

                logger.info(f"Loaded model config from {CONFIG_PATH}")
                return models
            except Exception as e:
                logger.warning(f"Failed to load model config: {e}. Using defaults.")

        return self.DEFAULT_MODELS

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)  # 2 minute timeout
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _calculate_cost(self, model_key: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for API call."""
        model = self.models.get(model_key)
        if not model:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * model.cost_per_m_input
        output_cost = (output_tokens / 1_000_000) * model.cost_per_m_output
        return input_cost + output_cost

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt using exponential backoff.

        Args:
            attempt: The retry attempt number (0-indexed)

        Returns:
            Delay in seconds before the next retry
        """
        delay = self.retry_config.base_delay * (
            self.retry_config.exponential_base ** attempt
        )
        delay = min(delay, self.retry_config.max_delay)

        if self.retry_config.jitter:
            # Add up to 25% jitter to prevent thundering herd
            jitter = delay * 0.25 * random.random()
            delay += jitter

        return delay

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable."""
        # Check for retryable exception types
        if isinstance(error, self.retry_config.retryable_exceptions):
            return True

        # Check for retryable HTTP status codes
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in self.retry_config.retryable_status_codes

        # Check for SSL errors (often wrapped in other exceptions)
        error_str = str(error).lower()
        ssl_indicators = ["ssl", "certificate", "handshake", "connection reset", "connection aborted"]
        if any(indicator in error_str for indicator in ssl_indicators):
            return True

        return False

    async def generate(
        self,
        model: Literal["gpt", "claude", "gemini", "search"],
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        web_search: bool = False
    ) -> Dict[str, Any]:
        """
        Call any model through OpenRouter with automatic retry on transient errors.

        Args:
            model: Model key (gpt, claude, gemini, search)
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: Optional JSON schema for structured output
            web_search: Enable web search (for Perplexity Sonar)

        Returns:
            Dict with 'content', 'usage', 'model', 'cost', and 'retries' keys
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")

        model_config = self.models.get(model)
        if not model_config:
            raise ValueError(f"Unknown model: {model}. Available: {list(self.models.keys())}")

        client = await self._get_client()

        # Build request payload
        payload = {
            "model": model_config.id,
            "messages": messages,
            "temperature": temperature if temperature is not None else model_config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else model_config.max_tokens
        }

        # Add response format if provided (for JSON mode)
        if response_format:
            payload["response_format"] = response_format

        # Add web search options for Perplexity
        if web_search and model == "search":
            payload["web_search_options"] = {
                "search_context_size": "high"
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "Content-Type": "application/json"
        }

        last_error = None
        retries_used = 0

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_backoff_delay(attempt - 1)
                    logger.info(
                        f"Retry {attempt}/{self.retry_config.max_retries} for {model_config.display_name} "
                        f"after {delay:.1f}s delay"
                    )
                    await asyncio.sleep(delay)
                    self.retry_stats["total_retries"] += 1

                logger.debug(f"Calling {model_config.display_name} with {len(messages)} messages (attempt {attempt + 1})")

                response = await client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                data = response.json()

                # Extract response content
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Extract usage info
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)

                # Calculate cost
                cost = self._calculate_cost(model, input_tokens, output_tokens)

                # Log usage
                self.usage_log.append(APIUsage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    timestamp=datetime.utcnow()
                ))

                if attempt > 0:
                    self.retry_stats["successful_retries"] += 1
                    logger.info(f"{model_config.display_name} succeeded after {attempt} retries")

                logger.debug(f"{model_config.display_name}: {input_tokens} in, {output_tokens} out, ${cost:.4f}")

                return {
                    "content": content,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    },
                    "model": model_config.display_name,
                    "model_id": model_config.id,
                    "cost": cost,
                    "retries": attempt
                }

            except Exception as e:
                last_error = e
                retries_used = attempt

                # Check if error is retryable and we have retries left
                if self._is_retryable_error(e) and attempt < self.retry_config.max_retries:
                    logger.warning(
                        f"Retryable error from {model_config.display_name} (attempt {attempt + 1}): {e}"
                    )
                    continue
                else:
                    # Non-retryable error or out of retries
                    break

        # All retries exhausted or non-retryable error
        self.retry_stats["failed_after_retries"] += 1

        if isinstance(last_error, httpx.HTTPStatusError):
            logger.error(
                f"OpenRouter API error after {retries_used + 1} attempts: "
                f"{last_error.response.status_code} - {last_error.response.text}"
            )
        else:
            logger.error(
                f"Error calling {model_config.display_name} after {retries_used + 1} attempts: {last_error}"
            )
        raise last_error

    async def generate_parallel(
        self,
        messages: List[Dict[str, str]],
        models: List[str] = ["gpt", "claude", "gemini"],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Call multiple models in parallel.

        Args:
            messages: Messages to send to all models
            models: List of model keys to call
            temperature: Override temperature for all models
            max_tokens: Override max tokens for all models
            response_format: Optional JSON schema

        Returns:
            Dict mapping model key to response dict
        """
        tasks = [
            self.generate(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            for model in models
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = {}
        for model, result in zip(models, results):
            if isinstance(result, Exception):
                logger.error(f"Error from {model}: {result}")
                responses[model] = {
                    "content": None,
                    "error": str(result),
                    "model": model
                }
            else:
                responses[model] = result

        return responses

    async def web_search(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform web search using Perplexity Sonar.

        Args:
            query: Search query
            context: Optional context to include

        Returns:
            Dict with search results and citations
        """
        messages = []

        if context:
            messages.append({
                "role": "system",
                "content": f"Context: {context}"
            })

        messages.append({
            "role": "user",
            "content": query
        })

        return await self.generate(
            model="search",
            messages=messages,
            web_search=True
        )

    def get_total_cost(self) -> float:
        """Get total cost of all API calls in this session."""
        return sum(u.cost for u in self.usage_log)

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of API usage including retry statistics."""
        by_model = {}
        for usage in self.usage_log:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0
                }
            by_model[usage.model]["calls"] += 1
            by_model[usage.model]["input_tokens"] += usage.input_tokens
            by_model[usage.model]["output_tokens"] += usage.output_tokens
            by_model[usage.model]["cost"] += usage.cost

        return {
            "total_calls": len(self.usage_log),
            "total_cost": self.get_total_cost(),
            "by_model": by_model,
            "retry_stats": self.retry_stats.copy()
        }

    def get_retry_stats(self) -> Dict[str, int]:
        """Get retry statistics."""
        return self.retry_stats.copy()

    def reset_retry_stats(self):
        """Reset retry statistics."""
        self.retry_stats = {"total_retries": 0, "successful_retries": 0, "failed_after_retries": 0}

    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model."""
        config = self.models.get(model)
        if not config:
            return None

        return {
            "key": model,
            "id": config.id,
            "display_name": config.display_name,
            "context_window": config.context_window,
            "cost_per_m_input": config.cost_per_m_input,
            "cost_per_m_output": config.cost_per_m_output,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }


# Singleton instance
_client_instance: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create OpenRouter client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenRouterClient()
    return _client_instance
