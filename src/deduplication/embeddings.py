"""
Generate embeddings for question text using OpenAI text-embedding-3-small.

Cost: ~$0.004 per 1000 questions (or $0.04 per 10K questions)
"""

import os
import logging
from typing import List, Dict
import numpy as np
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

from .config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
)

logger = logging.getLogger(__name__)


def get_openai_client():
    """Initialize OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return OpenAI(api_key=api_key)


def prepare_question_text(question: Dict) -> str:
    """
    Combine question stem and options into a single text for embedding.

    Args:
        question: Dict with 'stem' and 'options' keys

    Returns:
        Combined text string

    Example:
        >>> question = {
        ...     "stem": "What is the preferred first-line treatment for EGFR+ NSCLC?",
        ...     "options": ["Osimertinib", "Chemotherapy", "Erlotinib", "Observation"]
        ... }
        >>> prepare_question_text(question)
        'What is the preferred first-line treatment for EGFR+ NSCLC? Options: Osimertinib | Chemotherapy | Erlotinib | Observation'
    """
    stem = question.get("stem", "")
    options = question.get("options", [])

    # Combine stem with options
    if isinstance(options, list):
        options_text = " | ".join(str(opt) for opt in options if opt)
    else:
        options_text = str(options)

    return f"{stem} Options: {options_text}"


def get_embeddings_batch(
    texts: List[str],
    client: OpenAI = None,
    model: str = EMBEDDING_MODEL
) -> List[List[float]]:
    """
    Get embeddings for a batch of texts.

    Args:
        texts: List of text strings to embed
        client: OpenAI client instance
        model: Embedding model name

    Returns:
        List of embedding vectors

    Raises:
        Exception: If API call fails
    """
    if client is None:
        client = get_openai_client()

    try:
        response = client.embeddings.create(
            input=texts,
            model=model
        )

        embeddings = [item.embedding for item in response.data]
        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings

    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise


def generate_all_embeddings(
    questions: List[Dict],
    show_progress: bool = True
) -> np.ndarray:
    """
    Generate embeddings for all questions with batching.

    Args:
        questions: List of question dictionaries
        show_progress: Whether to show progress bar

    Returns:
        NumPy array of embeddings (n_questions x embedding_dim)

    Example:
        >>> questions = [{"stem": "Q1?", "options": ["A", "B"]}, ...]
        >>> embeddings = generate_all_embeddings(questions)
        >>> embeddings.shape
        (1000, 1536)  # 1000 questions, 1536 dimensions
    """
    client = get_openai_client()

    # Prepare texts
    logger.info(f"Preparing {len(questions)} questions for embedding...")
    texts = [prepare_question_text(q) for q in questions]

    # Process in batches
    all_embeddings = []

    iterator = range(0, len(texts), EMBEDDING_BATCH_SIZE)
    if show_progress:
        iterator = tqdm(iterator, desc="Generating embeddings", unit="batch")

    for i in iterator:
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        batch_embeddings = get_embeddings_batch(batch, client)
        all_embeddings.extend(batch_embeddings)

    result = np.array(all_embeddings)
    logger.info(f"Generated embeddings with shape: {result.shape}")

    return result


def embed_single_question(question: Dict, client: OpenAI = None) -> np.ndarray:
    """
    Generate embedding for a single question (for new question processing).

    Args:
        question: Question dictionary
        client: Optional pre-initialized client

    Returns:
        Embedding vector as NumPy array

    Example:
        >>> question = {"stem": "What is the treatment?", "options": ["A", "B", "C"]}
        >>> embedding = embed_single_question(question)
        >>> embedding.shape
        (1536,)
    """
    if client is None:
        client = get_openai_client()

    text = prepare_question_text(question)
    embeddings = get_embeddings_batch([text], client)

    return np.array(embeddings[0])
