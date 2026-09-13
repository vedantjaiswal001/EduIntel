"""Embedding fallback unit tests."""
from __future__ import annotations

import numpy as np

from app.rag.embeddings import EmbeddingModel


def _hashing_model():
    m = EmbeddingModel.__new__(EmbeddingModel)
    m.dim = 384
    m.method = "hashing-fallback"
    m._st = None
    return m


def test_hashing_embedding_deterministic_and_normalized():
    m = _hashing_model()
    v1 = m.encode_one("dynamic programming and recursion")
    v2 = m.encode_one("dynamic programming and recursion")
    assert v1.shape == (384,)
    assert np.allclose(v1, v2)  # deterministic
    assert abs(np.linalg.norm(v1) - 1.0) < 1e-5  # L2-normalised


def test_similar_texts_more_similar_than_dissimilar():
    m = _hashing_model()
    a = m.encode_one("dynamic programming memoization tabulation")
    b = m.encode_one("dynamic programming overlapping subproblems")
    c = m.encode_one("photosynthesis chlorophyll sunlight leaves")
    assert float(a @ b) > float(a @ c)


def test_empty_text_gives_zero_vector():
    m = _hashing_model()
    v = m.encode_one("")
    assert v.shape == (384,)
    assert np.linalg.norm(v) == 0.0
