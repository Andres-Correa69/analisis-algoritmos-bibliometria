"""
Modelos de similitud basados en IA (embeddings densos).

1. GloVe (Pennington et al., 2014) — embeddings estáticos de palabras
   preentrenados (``glove-wiki-gigaword-100``: 400 000 palabras, 100 dimensiones,
   entrenados sobre Wikipedia 2014 + Gigaword 5). El abstract se representa con
   el promedio (mean pooling) de los vectores de sus palabras de contenido:

       e(d) = (1 / |W_d|) · Σ_{w ∈ W_d} v_w

2. Sentence-BERT (Reimers y Gurevych, 2019) — modelo transformer
   ``all-MiniLM-L6-v2`` (6 capas, 384 dimensiones) que produce un embedding
   contextual por texto completo (mean pooling sobre los tokens + normalización L2).

En ambos casos el modelo preentrenado sólo genera los vectores; la similitud
(coseno) y la distancia euclidiana se calculan con ``vector_math`` (código propio).

Para que la aplicación desplegada no dependa de PyTorch ni de descargas de
cientos de MB, los vectores se generan una vez con ``scripts/build_embeddings.py``
y se almacenan en ``data/``:
- ``data/models/glove-wiki-gigaword-100.subset.json``: vectores GloVe de las
  palabras que aparecen en el corpus (subconjunto del modelo original).
- ``data/processed/embeddings_sbert.json``: embedding SBERT de cada abstract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..config import GLOVE_SUBSET_JSON, SBERT_EMBEDDINGS_JSON, SBERT_MODEL_NAME
from ..preprocessing.stopwords import DEFAULT_STOPWORDS
from ..preprocessing.tokenizer import normalize_text, tokenize
from .vector_math import cosine, euclidean, l2_normalize, mean_vector


@dataclass
class EmbeddingResult:
    vector: list[float]
    used_tokens: list[str] = field(default_factory=list)
    oov_tokens: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        total = len(self.used_tokens) + len(self.oov_tokens)
        return len(self.used_tokens) / total if total else 0.0


def content_words(text: str) -> list[str]:
    """Palabras de contenido para GloVe: minúsculas, sin stopwords ni números.

    No se aplica stemming porque GloVe tiene vectores para palabras completas.
    """
    words: list[str] = []
    for t in tokenize(normalize_text(text)):
        if len(t) < 2 or t in DEFAULT_STOPWORDS:
            continue
        if t.isdigit():
            continue
        words.append(t)
    return words


class GloveModel:
    """Embeddings de documento por promedio de vectores GloVe."""

    def __init__(self, path: Path = GLOVE_SUBSET_JSON) -> None:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.name: str = payload.get("model", "glove-wiki-gigaword-100")
        self.dim: int = int(payload["dim"])
        self.vectors: dict[str, list[float]] = payload["vectors"]

    def embed(self, text: str) -> EmbeddingResult:
        used, oov, vecs = [], [], []
        for w in content_words(text):
            v = self.vectors.get(w)
            if v is None:
                oov.append(w)
            else:
                used.append(w)
                vecs.append(v)
        vector = mean_vector(vecs) if vecs else [0.0] * self.dim
        return EmbeddingResult(vector=vector, used_tokens=used, oov_tokens=oov)


class SbertModel:
    """Embeddings Sentence-BERT precalculados por artículo (con codificación
    en línea opcional si ``sentence-transformers`` está instalado)."""

    def __init__(self, path: Path = SBERT_EMBEDDINGS_JSON) -> None:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.name: str = payload.get("model", SBERT_MODEL_NAME)
        self.dim: int = int(payload["dim"])
        self.max_seq_length: int | None = payload.get("max_seq_length")
        self.vectors: dict[int, list[float]] = {int(k): v for k, v in payload["vectors"].items()}
        self.token_counts: dict[int, int] = {int(k): v for k, v in payload.get("token_counts", {}).items()}
        self._encoder = None

    def vector_for(self, article_id: int) -> list[float]:
        return self.vectors[article_id]

    def encode(self, text: str) -> list[float]:
        """Codifica un texto nuevo (requiere ``pip install -r requirements-ai.txt``)."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer  # importación diferida

            self._encoder = SentenceTransformer(self.name)
            if self.max_seq_length:
                self._encoder.max_seq_length = self.max_seq_length
        vec = self._encoder.encode([text], normalize_embeddings=True)[0]
        return [float(x) for x in vec]


def compare_vectors(u: list[float], v: list[float]) -> dict:
    """Coseno y distancia euclidiana entre dos embeddings (y entre sus versiones L2)."""
    nu, nv = l2_normalize(u), l2_normalize(v)
    return {
        "cosine": cosine(u, v),
        "euclidean": euclidean(u, v),
        "euclidean_normalized": euclidean(nu, nv),
    }
