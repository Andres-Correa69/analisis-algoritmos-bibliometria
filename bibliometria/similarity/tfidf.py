"""
Modelo de espacio vectorial TF-IDF implementado desde cero.

Para un corpus de N documentos y un término t:

    tf(t, d)  = número de apariciones de t en d
    df(t)     = número de documentos que contienen t
    idf(t)    = ln( (1 + N) / (1 + df(t)) ) + 1          (idf suavizado)
    w(t, d)   = tf(t, d) · idf(t)

Cada documento se representa como un vector disperso w(·, d) que luego se
normaliza con la norma L2. La similitud es el coseno del ángulo entre vectores:

    cos θ = (w_A · w_B) / (||w_A|| · ||w_B||)

El idf suavizado coincide con la convención de scikit-learn
(``smooth_idf=True``), lo que permite validar la implementación contra esa
librería en las pruebas; con ``smooth_idf=False`` se usa idf = ln(N / df).

Complejidad: construir el modelo es O(Σ|d|) (una pasada por todos los tokens);
el coseno entre dos vectores dispersos es O(min(|A|, |B|)) búsquedas en tabla hash.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .vector_math import sparse_cosine, sparse_dot, sparse_norm


@dataclass
class TermWeight:
    term: str
    tf_a: int
    tf_b: int
    df: int
    idf: float
    w_a: float  # peso normalizado (L2) en A
    w_b: float  # peso normalizado (L2) en B

    @property
    def product(self) -> float:
        return self.w_a * self.w_b


class TfidfModel:
    """Ajusta df/idf sobre un corpus de documentos tokenizados."""

    def __init__(self, documents: list[list[str]], smooth_idf: bool = True) -> None:
        self.n_docs = len(documents)
        self.smooth_idf = smooth_idf
        self.df: dict[str, int] = {}
        for doc in documents:
            seen: dict[str, bool] = {}
            for term in doc:
                if term not in seen:
                    seen[term] = True
                    self.df[term] = self.df.get(term, 0) + 1
        self.idf: dict[str, float] = {term: self._idf_value(df) for term, df in self.df.items()}

    def _idf_value(self, df: int) -> float:
        n = self.n_docs
        if self.smooth_idf:
            return math.log((1 + n) / (1 + df)) + 1.0
        if df == 0:
            return 0.0
        return math.log(n / df)

    def idf_of(self, term: str) -> float:
        value = self.idf.get(term)
        return value if value is not None else self._idf_value(0)

    @staticmethod
    def term_frequencies(tokens: list[str]) -> dict[str, int]:
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        return tf

    def vector(self, tokens: list[str], normalize: bool = True) -> dict[str, float]:
        """Vector TF-IDF disperso de un documento (opcionalmente normalizado L2)."""
        tf = self.term_frequencies(tokens)
        vec = {term: count * self.idf_of(term) for term, count in tf.items()}
        if normalize:
            n = sparse_norm(vec)
            if n > 0:
                vec = {term: w / n for term, w in vec.items()}
        return vec

    def cosine(self, tokens_a: list[str], tokens_b: list[str]) -> float:
        return sparse_cosine(self.vector(tokens_a), self.vector(tokens_b))

    def explain(self, tokens_a: list[str], tokens_b: list[str]) -> dict:
        """Desglose completo del cálculo del coseno entre dos documentos."""
        tf_a, tf_b = self.term_frequencies(tokens_a), self.term_frequencies(tokens_b)
        raw_a = {t: c * self.idf_of(t) for t, c in tf_a.items()}
        raw_b = {t: c * self.idf_of(t) for t, c in tf_b.items()}
        norm_raw_a, norm_raw_b = sparse_norm(raw_a), sparse_norm(raw_b)
        dot_raw = sparse_dot(raw_a, raw_b)
        cos = dot_raw / (norm_raw_a * norm_raw_b) if norm_raw_a and norm_raw_b else 0.0

        terms: list[TermWeight] = []
        vocab: dict[str, bool] = {}
        for t in tf_a:
            vocab[t] = True
        for t in tf_b:
            vocab[t] = True
        for t in vocab:
            terms.append(
                TermWeight(
                    term=t,
                    tf_a=tf_a.get(t, 0),
                    tf_b=tf_b.get(t, 0),
                    df=self.df.get(t, 0),
                    idf=self.idf_of(t),
                    w_a=raw_a.get(t, 0.0) / norm_raw_a if norm_raw_a else 0.0,
                    w_b=raw_b.get(t, 0.0) / norm_raw_b if norm_raw_b else 0.0,
                )
            )
        return {
            "n_docs": self.n_docs,
            "terms": terms,
            "dot_raw": dot_raw,
            "norm_a": norm_raw_a,
            "norm_b": norm_raw_b,
            "cosine": 1.0 if cos > 1.0 else cos,
        }
