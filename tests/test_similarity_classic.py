"""Pruebas de los 4 algoritmos clásicos de similitud (Requerimiento 1)."""

import math
from functools import lru_cache

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rapidfuzz.distance import Levenshtein as RFLevenshtein
from sklearn.feature_extraction.text import TfidfVectorizer

from bibliometria.similarity.jaccard import jaccard
from bibliometria.similarity.levenshtein import (
    levenshtein_alignment,
    levenshtein_distance,
    levenshtein_matrix,
    levenshtein_similarity,
)
from bibliometria.similarity.needleman_wunsch import GAP, needleman_wunsch
from bibliometria.similarity.tfidf import TfidfModel
from bibliometria.similarity.vector_math import angle_degrees, cosine, euclidean, sparse_cosine, sparse_euclidean

short_text = st.text(alphabet="abcde", max_size=12)
token_lists = st.lists(st.sampled_from(["ai", "learn", "educ", "model", "data", "student"]), max_size=10)

# --------------------------------------------------------------------------- #
# Levenshtein
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "a,b,d",
    [("kitten", "sitting", 3), ("flaw", "lawn", 2), ("", "abc", 3), ("abc", "", 3), ("same", "same", 0), ("intention", "execution", 5)],
)
def test_levenshtein_known_values(a, b, d):
    assert levenshtein_distance(a, b) == d
    assert levenshtein_matrix(a, b)[len(a)][len(b)] == d


def test_levenshtein_matrix_first_row_and_column():
    D = levenshtein_matrix("gato", "pato")
    assert D[0] == [0, 1, 2, 3, 4]
    assert [row[0] for row in D] == [0, 1, 2, 3, 4]
    assert D[4][4] == 1


def test_levenshtein_on_token_sequences():
    a = ["generative", "ai", "assessment"]
    b = ["generative", "model", "assessment", "design"]
    assert levenshtein_distance(a, b) == 2
    assert levenshtein_similarity(a, b) == pytest.approx(0.5)


@given(short_text, short_text)
@settings(max_examples=300, deadline=None)
def test_levenshtein_matches_rapidfuzz_oracle(a, b):
    assert levenshtein_distance(a, b) == RFLevenshtein.distance(a, b)


@given(short_text, short_text, short_text)
@settings(max_examples=200, deadline=None)
def test_levenshtein_metric_properties(a, b, c):
    dab = levenshtein_distance(a, b)
    assert dab == levenshtein_distance(b, a)  # simetría
    assert (dab == 0) == (a == b)  # identidad
    assert dab <= levenshtein_distance(a, c) + levenshtein_distance(c, b)  # desigualdad triangular
    assert abs(len(a) - len(b)) <= dab <= max(len(a), len(b))  # cotas
    assert 0.0 <= levenshtein_similarity(a, b) <= 1.0


@given(short_text, short_text)
@settings(max_examples=200, deadline=None)
def test_levenshtein_alignment_reconstructs_target(a, b):
    ops = levenshtein_alignment(a, b)
    rebuilt = "".join(op["b"] for op in ops if op["op"] != "delete")
    assert rebuilt == b
    assert sum(1 for op in ops if op["op"] != "match") == levenshtein_distance(a, b)


# --------------------------------------------------------------------------- #
# Needleman-Wunsch
# --------------------------------------------------------------------------- #


def _nw_score_oracle(a, b, match=1, mismatch=-1, gap=-1):
    """Oráculo recursivo con memoización (estrategia distinta a la tabla iterativa)."""

    @lru_cache(maxsize=None)
    def best(i, j):
        if i == 0:
            return j * gap
        if j == 0:
            return i * gap
        s = match if a[i - 1] == b[j - 1] else mismatch
        return max(best(i - 1, j - 1) + s, best(i - 1, j) + gap, best(i, j - 1) + gap)

    return best(len(a), len(b))


def test_needleman_wunsch_textbook_example():
    r = needleman_wunsch("GATTACA", "GCATGCU", match=1, mismatch=-1, gap=-1, keep_matrix=True)
    assert r.score == 0
    assert r.matrix[0] == [0, -1, -2, -3, -4, -5, -6, -7]


@given(short_text, short_text, st.sampled_from([(1, -1, -1), (2, -1, -2), (1, 0, -1)]))
@settings(max_examples=250, deadline=None)
def test_needleman_wunsch_score_is_optimal_and_alignment_consistent(a, b, params):
    match, mismatch, gap = params
    r = needleman_wunsch(a, b, match, mismatch, gap)
    assert r.score == _nw_score_oracle(a, b, match, mismatch, gap)
    assert "".join(x for x in r.aligned_a if x is not GAP) == a
    assert "".join(y for y in r.aligned_b if y is not GAP) == b
    recomputed = 0
    for x, y in zip(r.aligned_a, r.aligned_b):
        recomputed += gap if (x is GAP or y is GAP) else (match if x == y else mismatch)
    assert recomputed == r.score
    assert r.matches + r.mismatches + r.gaps == r.length
    assert 0.0 <= r.identity <= 1.0


def test_needleman_wunsch_identical_sequences_have_identity_one():
    toks = ["ai", "literacy", "higher", "education"]
    assert needleman_wunsch(toks, toks).identity == 1.0


# --------------------------------------------------------------------------- #
# Jaccard
# --------------------------------------------------------------------------- #


def test_jaccard_hand_example():
    r = jaccard(["ai", "learn", "educ", "ai"], ["learn", "educ", "model"])
    assert r.intersection == ["educ", "learn"]
    assert r.union_size == 4
    assert r.similarity == pytest.approx(0.5)


@given(token_lists, token_lists)
@settings(max_examples=300, deadline=None)
def test_jaccard_matches_python_sets(a, b):
    sa, sb = set(a), set(b)
    expected = 1.0 if not (sa | sb) else len(sa & sb) / len(sa | sb)
    assert jaccard(a, b).similarity == pytest.approx(expected)
    assert jaccard(a, b).similarity == pytest.approx(jaccard(b, a).similarity)


# --------------------------------------------------------------------------- #
# TF-IDF + coseno y operaciones vectoriales
# --------------------------------------------------------------------------- #


def test_tfidf_matches_sklearn_oracle(engine):
    """Oráculo: misma matriz de similitudes que scikit-learn con idf suavizado y norma L2."""
    docs = [engine.stems[i] for i in engine.corpus.ids]
    vec = TfidfVectorizer(analyzer=lambda d: d, smooth_idf=True, norm="l2", lowercase=False)
    X = vec.fit_transform(docs).toarray()
    sk = X @ X.T
    model = TfidfModel(docs)
    vectors = [model.vector(d) for d in docs]
    for i in range(len(docs)):
        for j in range(len(docs)):
            assert sparse_cosine(vectors[i], vectors[j]) == pytest.approx(sk[i, j], abs=1e-9)
    for term, idx in vec.vocabulary_.items():
        assert model.idf[term] == pytest.approx(vec.idf_[idx], abs=1e-12)


def test_tfidf_classic_idf_hand_example():
    docs = [["ai", "learn"], ["ai", "model"], ["educ"]]
    m = TfidfModel(docs, smooth_idf=False)
    assert m.idf["ai"] == pytest.approx(math.log(3 / 2))
    assert m.idf["educ"] == pytest.approx(math.log(3))
    v = m.vector(["ai", "ai", "learn"], normalize=False)
    assert v["ai"] == pytest.approx(2 * math.log(1.5))


def test_tfidf_explain_is_consistent_with_cosine():
    docs = [["ai", "learn", "learn"], ["ai", "model"], ["educ", "learn"]]
    m = TfidfModel(docs)
    ex = m.explain(docs[0], docs[2])
    assert ex["cosine"] == pytest.approx(m.cosine(docs[0], docs[2]))
    assert sum(t.product for t in ex["terms"]) == pytest.approx(ex["cosine"])


@given(st.lists(st.floats(-5, 5, allow_nan=False), min_size=3, max_size=3), st.lists(st.floats(-5, 5, allow_nan=False), min_size=3, max_size=3))
@settings(max_examples=200, deadline=None)
def test_vector_math_matches_numpy(u, v):
    nu, nv = np.array(u), np.array(v)
    assert euclidean(u, v) == pytest.approx(float(np.linalg.norm(nu - nv)), abs=1e-9)
    if np.linalg.norm(nu) > 1e-6 and np.linalg.norm(nv) > 1e-6:
        expected = float(nu @ nv / (np.linalg.norm(nu) * np.linalg.norm(nv)))
        assert cosine(u, v) == pytest.approx(max(-1.0, min(1.0, expected)), abs=1e-9)


def test_sparse_and_angle_helpers():
    u, v = {"a": 1.0, "b": 1.0}, {"a": 1.0}
    assert sparse_cosine(u, v) == pytest.approx(1 / math.sqrt(2))
    assert sparse_euclidean(u, v) == pytest.approx(1.0)
    assert angle_degrees(0.0) == pytest.approx(90.0)
