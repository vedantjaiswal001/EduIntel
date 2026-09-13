"""Embedding model abstraction.

Primary: sentence-transformers (all-MiniLM-L6-v2, 384-dim) — true semantic
embeddings. Fallback: a deterministic feature-hashing embedding (also 384-dim)
used when the transformer weights cannot be loaded (e.g. offline), so the RAG
pipeline and pgvector search remain fully functional and reproducible.

Both produce L2-normalised vectors matching the pgvector column dimension, so
cosine similarity is directly comparable.
"""
from __future__ import annotations

import hashlib
import re
from typing import List

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9'-]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


class EmbeddingModel:
    """Loads sentence-transformers if possible; otherwise a hashing fallback."""

    _instance = None

    def __init__(self) -> None:
        self.dim = settings.EMBEDDING_DIM
        self.method = "hashing-fallback"
        self._st = None
        try:
            from sentence_transformers import SentenceTransformer

            self._st = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            self.dim = self._st.get_sentence_embedding_dimension()
            self.method = f"sentence-transformers:{settings.EMBEDDING_MODEL_NAME}"
            logger.info("Loaded embedding model %s (dim=%d)", self.method, self.dim)
        except Exception as exc:
            logger.warning(
                "sentence-transformers unavailable (%s); using deterministic "
                "hashing embeddings (dim=%d).", exc, self.dim)

    @classmethod
    def get(cls) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = EmbeddingModel()
        return cls._instance

    def encode(self, texts: List[str]) -> np.ndarray:
        if self._st is not None:
            return np.asarray(
                self._st.encode(texts, normalize_embeddings=True, show_progress_bar=False),
                dtype=np.float32,
            )
        return np.vstack([self._hash_embed(t) for t in texts]).astype(np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    def _hash_embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
