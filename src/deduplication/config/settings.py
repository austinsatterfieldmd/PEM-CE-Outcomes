"""
Configuration settings for the deduplication pipeline.
Adjust thresholds based on your data after initial testing.
"""

# Embedding model selection
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI's affordable model
EMBEDDING_DIMENSIONS = 1536  # Dimensions for text-embedding-3-small
EMBEDDING_PROVIDER = "openai"  # Options: openai, voyage

# Similarity thresholds (tune after reviewing sample clusters)
SIMILARITY_THRESHOLD_AUTO_MERGE = 0.95    # Auto-dedupe without review (≥95% similar)
SIMILARITY_THRESHOLD_REVIEW = 0.88        # Flag for human review (88-95% similar)
SIMILARITY_THRESHOLD_RELATED = 0.80       # Possibly related, likely distinct (<88% similar)

# Batch processing
EMBEDDING_BATCH_SIZE = 2000  # OpenAI allows up to 2048 per request
PROCESSING_BATCH_SIZE = 1000  # For memory management during clustering

# Source quality rankings (higher = better, used in canonicalization)
SOURCE_QUALITY_SCORES = {
    "journal": 15,
    "enduring": 10,
    "online": 5,
    "webinar": 5,
    "live": 0,
    "slide": -5,
}

# File paths (relative to project root)
RAW_DATA_PATH = "data/raw/"
PROCESSED_DATA_PATH = "data/dedup_processed/"
OUTPUT_DATA_PATH = "data/dedup_output/"
