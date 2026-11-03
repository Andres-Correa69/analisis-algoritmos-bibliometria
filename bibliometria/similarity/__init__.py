"""Requerimiento 1: similitud textual (4 algoritmos clásicos + 2 modelos de IA)."""

from .jaccard import jaccard, jaccard_similarity
from .levenshtein import levenshtein_distance, levenshtein_matrix, levenshtein_similarity
from .needleman_wunsch import needleman_wunsch, needleman_wunsch_similarity
from .tfidf import TfidfModel
from .vector_math import cosine, euclidean

__all__ = [
    "jaccard",
    "jaccard_similarity",
    "levenshtein_distance",
    "levenshtein_matrix",
    "levenshtein_similarity",
    "needleman_wunsch",
    "needleman_wunsch_similarity",
    "TfidfModel",
    "cosine",
    "euclidean",
]
