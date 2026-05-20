"""Embedding model for Muse MCP.

Uses sentence-transformers for semantic embeddings, matching Mind MCP's approach.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

# Lazy import to avoid loading the model until needed
_model = None
_model_name = None

# Default model - same as Mind MCP for consistency
DEFAULT_MODEL = "all-MiniLM-L6-v2"


class EmbeddingModel:
    """Embedding model wrapper using sentence-transformers."""

    def __init__(self, model_name: str | None = None):
        """Initialize embedding model.

        Args:
            model_name: Model name from sentence-transformers.
                       Defaults to all-MiniLM-L6-v2.
        """
        global _model, _model_name

        self.model_name = model_name or os.environ.get("MUSE_MODEL", DEFAULT_MODEL)

        # Reuse cached model if same name
        if _model is not None and _model_name == self.model_name:
            self.model = _model
        else:
            self._load_model()

    def _load_model(self) -> None:
        """Load the sentence-transformer model."""
        global _model, _model_name

        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(self.model_name)
        _model = self.model
        _model_name = self.model_name

    def encode_single(self, text: str, is_query: bool = True) -> np.ndarray:
        """Encode a single text string.

        Args:
            text: Text to encode
            is_query: If True, may apply query-specific processing

        Returns:
            Embedding vector as numpy array
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embedding.astype(np.float32)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """Encode multiple texts.

        Args:
            texts: List of texts to encode

        Returns:
            Array of embeddings (num_texts x embedding_dim)
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.astype(np.float32)

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score (-1 to 1)
        """
        # Embeddings are normalized, so dot product = cosine similarity
        return float(np.dot(embedding1, embedding2))

    def get_info(self) -> dict[str, Any]:
        """Get model information."""
        return {
            "name": self.model_name,
            "embedding_dim": self.model.get_sentence_embedding_dimension(),
            "max_seq_length": self.model.max_seq_length,
        }
