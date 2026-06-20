# backend/rag/embeddings.py

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Abstract base class for all embedding implementations."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass


class SentenceTransformerEmbedder(BaseEmbedder):
    """
    Local embeddings using sentence-transformers.
    Free, runs on CPU, no API key needed.
    Best for: development, portfolio projects, offline deployment.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Popular models:
        - all-MiniLM-L6-v2: Fast, 384-dim, good quality (RECOMMENDED for dev)
        - all-mpnet-base-v2: Slower, 768-dim, better quality
        - BAAI/bge-small-en-v1.5: Optimized for retrieval tasks
        - BAAI/bge-m3: Best quality, 1024-dim, multilingual
        """
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {model_name}")
        start = time.time()
        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        logger.info(f"Model loaded in {time.time() - start:.2f}s")

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text."""
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> list[list[float]]:
        """
        Efficiently embed multiple texts.
        
        Args:
            texts: List of text strings
            batch_size: Process this many at once (tune for your RAM)
            show_progress: Show tqdm progress bar
        """
        if not texts:
            return []

        logger.info(f"Embedding {len(texts)} texts in batches of {batch_size}")
        start = time.time()

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalize for cosine similarity
        )

        elapsed = time.time() - start
        logger.info(
            f"Embedded {len(texts)} texts in {elapsed:.2f}s "
            f"({len(texts)/elapsed:.1f} texts/sec)"
        )

        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    @property
    def model_name(self) -> str:
        return self._model_name


class GeminiEmbedder(BaseEmbedder):
    """
    Google Gemini embeddings via API.
    Free tier: 60 QPM (queries per minute).
    Best for: production, higher quality, when you have API access.
    """

    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model = model
        self._dim = 768  # text-embedding-004 outputs 768 dimensions

    def embed_text(self, text: str) -> list[float]:
        result = self._genai.embed_content(
            model=self._model,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    def embed_query(self, text: str) -> list[float]:
        """Use query task type for search queries (slightly different optimization)."""
        result = self._genai.embed_content(
            model=self._model,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts (no native batch API, sequential with rate limiting)."""
        embeddings = []
        for i, text in enumerate(texts):
            embeddings.append(self.embed_text(text))
            # Respect rate limits: 60 QPM = 1 per second to be safe
            if i < len(texts) - 1:
                time.sleep(1.0)
        return embeddings

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model


def get_embedder(provider: str = "local", **kwargs) -> BaseEmbedder:
    """
    Factory function to get the appropriate embedder.
    
    Args:
        provider: "local" for sentence-transformers, "gemini" for Google
        **kwargs: Provider-specific arguments
    """
    if provider == "local":
        model = kwargs.get("model_name", "all-MiniLM-L6-v2")
        return SentenceTransformerEmbedder(model)
    elif provider == "gemini":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("api_key required for Gemini embedder")
        return GeminiEmbedder(api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose 'local' or 'gemini'")