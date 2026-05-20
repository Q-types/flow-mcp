"""Embedding model wrapper for Mind MCP v2."""

from __future__ import annotations

import os
from typing import Sequence

import numpy as np

# Default model - nomic-embed-text-v1.5 for best quality/size tradeoff
DEFAULT_MODEL = "nomic-ai/nomic-embed-text-v1.5"


class EmbeddingModel:
    """Wrapper for sentence-transformers embedding model.

    Uses nomic-embed-text-v1.5 by default:
    - 137M parameters, ~275MB
    - 8192 token context (critical for full memories)
    - 768 dimensions
    - 81.2% accuracy on benchmarks
    - Apache 2.0 license

    Nomic requires specific prefixes:
    - "search_document: " for documents being stored
    - "search_query: " for queries
    """

    def __init__(self, model_name: str | None = None):
        """Initialize embedding model.

        Args:
            model_name: Model name or path. Defaults to nomic-embed-text-v1.5
        """
        self.model_name = model_name or os.environ.get("MIND_MODEL", DEFAULT_MODEL)
        self._model = None
        self._dimension: int | None = None

    @property
    def model(self):
        """Lazy load the model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.model_name,
                trust_remote_code=True,  # Required for nomic
            )
            # Get embedding dimension from model
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            _ = self.model  # Trigger lazy load
        return self._dimension or 768

    def encode_documents(self, texts: Sequence[str]) -> np.ndarray:
        """Encode documents for storage.

        Args:
            texts: List of document texts to encode

        Returns:
            Numpy array of shape (n_texts, dimension)
        """
        # Nomic requires "search_document: " prefix for documents
        prefixed = [f"search_document: {text}" for text in texts]
        embeddings = self.model.encode(
            prefixed,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
        )
        return embeddings.astype(np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a query for retrieval.

        Args:
            query: Query text to encode

        Returns:
            Numpy array of shape (dimension,)
        """
        # Nomic requires "search_query: " prefix for queries
        prefixed = f"search_query: {query}"
        embedding = self.model.encode(
            prefixed,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embedding.astype(np.float32)

    def encode_single(self, text: str, is_query: bool = False) -> np.ndarray:
        """Encode a single text.

        Args:
            text: Text to encode
            is_query: If True, use query prefix; otherwise use document prefix

        Returns:
            Numpy array of shape (dimension,)
        """
        if is_query:
            return self.encode_query(text)
        return self.encode_documents([text])[0]

    def get_info(self) -> dict:
        """Get model information."""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "loaded": self._model is not None,
        }


def cosine_similarity(query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query and documents.

    Since embeddings are L2-normalized, cosine similarity = dot product.

    Args:
        query_embedding: Query vector of shape (dimension,)
        doc_embeddings: Document matrix of shape (n_docs, dimension)

    Returns:
        Similarity scores of shape (n_docs,)
    """
    if doc_embeddings.size == 0:
        return np.array([])

    # Ensure query is 1D
    if query_embedding.ndim > 1:
        query_embedding = query_embedding.flatten()

    # Dot product (equivalent to cosine similarity for normalized vectors)
    similarities = np.dot(doc_embeddings, query_embedding)

    return similarities
