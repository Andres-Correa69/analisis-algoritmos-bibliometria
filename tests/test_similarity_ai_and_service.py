"""Pruebas de los modelos de IA y del servicio de similitud (Requerimiento 1)."""

import importlib.util

import numpy as np
import pytest

from bibliometria.similarity.embeddings import content_words
from bibliometria.similarity.service import ALGORITHMS


def test_glove_document_vector_is_mean_of_word_vectors(engine):
    art = engine.corpus.get(1)
    emb = engine.glove_embeddings[1]
    expected = np.mean([engine.glove.vectors[w] for w in emb.used_tokens], axis=0)
    assert np.allclose(emb.vector, expected, atol=1e-9)
    assert emb.coverage > 0.95
    assert set(emb.used_tokens) | set(emb.oov_tokens) == set(content_words(art.abstract))


def test_glove_known_out_of_vocabulary_terms(engine):
    oov = set()
    for e in engine.glove_embeddings.values():
        oov |= set(e.oov_tokens)
    assert {"chatgpt", "genai"} <= oov  # términos posteriores al entrenamiento de GloVe (2014)


def test_sbert_vectors_are_normalized_and_complete(engine):
    assert engine.sbert.dim == 384
    assert set(engine.sbert.vectors) == set(engine.corpus.ids)
    for v in engine.sbert.vectors.values():
        assert np.linalg.norm(v) == pytest.approx(1.0, abs=1e-4)
    assert max(engine.sbert.token_counts.values()) <= engine.sbert.max_seq_length  # sin truncamiento


@pytest.mark.skipif(importlib.util.find_spec("sentence_transformers") is None, reason="requiere requirements-ai.txt")
def test_sbert_precomputed_embeddings_are_reproducible(engine):
    vec = engine.sbert.encode(engine.corpus.get(19).abstract)
    assert float(np.dot(vec, engine.sbert.vector_for(19))) > 0.9999


def test_compare_returns_symmetric_matrices_in_unit_interval(engine):
    res = engine.compare([3, 11, 16, 19])
    assert len(res["pairs"]) == 6
    assert [a["key"] for a in res["algorithms"]] == list(ALGORITHMS)
    for M in res["matrices"].values():
        for i in range(4):
            assert M[i][i] == 1.0
            for j in range(4):
                assert M[i][j] == M[j][i]
                assert -1e-9 <= M[i][j] <= 1.0 + 1e-9


def test_identical_documents_score_one_for_every_algorithm(engine):
    for alg in engine.available_algorithms():
        assert engine.score(alg, 5, 5) == pytest.approx(1.0)


def test_compare_validates_input(engine):
    with pytest.raises(ValueError):
        engine.compare([1])
    with pytest.raises(ValueError):
        engine.compare([2, 2])
    with pytest.raises(KeyError):
        engine.compare([1, 999])
    with pytest.raises(ValueError):
        engine.compare([1, 2], algorithms=["no_existe"])


def test_explain_values_agree_with_compare(engine):
    ex = engine.explain(11, 16)
    pair = engine.compare([11, 16])["pairs"][0]["scores"]
    assert ex["levenshtein"]["similarity"] == pytest.approx(pair["levenshtein"]["value"], abs=1e-6)
    assert ex["needleman_wunsch"]["similarity"] == pytest.approx(pair["needleman_wunsch"]["value"], abs=1e-6)
    assert ex["jaccard"]["similarity"] == pytest.approx(pair["jaccard"]["value"], abs=1e-6)
    assert ex["tfidf"]["cosine"] == pytest.approx(pair["tfidf_cosine"]["value"], abs=1e-6)
    assert ex["glove"]["cosine"] == pytest.approx(pair["glove_cosine"]["value"], abs=1e-6)
    assert ex["sbert"]["cosine"] == pytest.approx(pair["sbert_cosine"]["value"], abs=1e-6)
    lev = ex["levenshtein"]
    assert lev["matrix"][len(lev["window_a"])][len(lev["window_b"])] == lev["window_distance"]
    assert sum(t["product"] for t in ex["tfidf"]["terms"]) == pytest.approx(ex["tfidf"]["cosine"], abs=1e-4)


def test_character_granularity_is_supported(engine):
    words = engine.score("levenshtein", 1, 2, "words")
    chars = engine.score("levenshtein", 1, 2, "chars")
    assert 0 < words < 1 and 0 < chars < 1 and words != chars
