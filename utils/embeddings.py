from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_texts(texts: list[str], model_name: str) -> np.ndarray:
    if not texts:
        return np.array([])
    model = _load_model(model_name)
    vectors = model.encode(texts, normalize_embeddings=True)
    return np.array(vectors)
