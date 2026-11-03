"""Pruebas de integración de la API y pruebas de flujo de extremo a extremo."""

import json

import pytest

from bibliometria.config import CORPUS_JSON
from bibliometria.extraction.build_corpus import build_corpus

# --------------------------------------------------------------------------- #
# Integración de la API
# --------------------------------------------------------------------------- #


def test_health_and_meta(client):
    assert client.get("/api/health").json()["status"] == "ok"
    meta = client.get("/api/meta").json()
    assert meta["corpus_size"] == 20
    assert len(meta["similarity_algorithms"]) == 6
    assert {a["key"] for a in meta["string_matching_algorithms"]} == {"kmp", "boyer_moore", "rabin_karp"}


def test_corpus_endpoints(client):
    data = client.get("/api/corpus").json()
    assert data["count"] == 20 and all(a["abstract"] and a["authors"] and a["title"] for a in data["articles"])
    assert client.get("/api/corpus/7").json()["code"] == "A07"
    assert client.get("/api/corpus/0").status_code == 404
    pre = client.get("/api/corpus/7/preprocessing").json()
    assert pre["counts"]["stems"] > 50


def test_similarity_endpoints(client):
    r = client.post("/api/similarity/compare", json={"ids": [1, 2, 3], "granularity": "chars", "algorithms": ["levenshtein", "sbert_cosine"]})
    assert r.status_code == 200 and len(r.json()["pairs"]) == 3
    assert client.post("/api/similarity/compare", json={"ids": [1]}).status_code == 422
    assert client.post("/api/similarity/compare", json={"ids": [1, 2], "granularity": "x"}).status_code == 422
    assert client.post("/api/similarity/compare", json={"ids": [1, 77]}).status_code == 400
    ex = client.get("/api/similarity/explain", params={"a": 4, "b": 8, "window": 6}).json()
    assert len(ex["levenshtein"]["matrix"]) == 7
    assert client.get("/api/similarity/explain", params={"a": 4, "b": 4}).status_code == 400
    m = client.get("/api/similarity/matrix", params={"algorithm": "jaccard"}).json()
    assert len(m["matrix"]) == 20


def test_clustering_endpoint(client):
    for rep in ("tfidf", "sbert"):
        r = client.get("/api/clustering", params={"representation": rep, "display_k": 3}).json()
        assert r["methods"]["average"]["dendrogram"]["k"] == 3
    assert client.get("/api/clustering", params={"representation": "bow"}).status_code == 422


def test_search_endpoints(client):
    r = client.post("/api/search", json={"pattern": "assessment", "fields": ["abstract", "title", "keywords"]}).json()
    assert r["consistent"] and r["total_occurrences"] > 10
    t = client.post("/api/search/trace", json={"pattern": "ai", "article_id": 3, "algorithm": "rabin_karp", "modulus": 13}).json()
    assert t["extra"]["modulus"] == 13 and t["trace"]
    t2 = client.post("/api/search/trace", json={"pattern": "is", "text": "this is it", "algorithm": "kmp"}).json()
    assert t2["positions"] == [2, 5]
    assert client.post("/api/search/trace", json={"pattern": "x", "algorithm": "foo", "text": "x"}).status_code == 400
    assert client.post("/api/search", json={"pattern": ""}).status_code == 422
    bench = client.get("/api/search/benchmark").json()
    assert {"pattern_length", "text_length", "worst_case"} <= set(bench)


# --------------------------------------------------------------------------- #
# Flujo completo
# --------------------------------------------------------------------------- #


def test_corpus_rebuild_is_reproducible(tmp_path):
    """PDF -> extracción -> corpus.json: debe reproducir exactamente el corpus publicado."""
    out = tmp_path / "corpus.json"
    build_corpus(out_path=out)
    with open(out, encoding="utf-8") as fh:
        rebuilt = json.load(fh)
    with open(CORPUS_JSON, encoding="utf-8") as fh:
        published = json.load(fh)
    assert rebuilt == published


def test_user_flow_through_the_api(client):
    """Simula el recorrido de un usuario por los tres requerimientos."""
    articles = client.get("/api/corpus").json()["articles"]
    genai = [a["id"] for a in articles if "generative" in a["title"].lower() or "chatgpt" in a["title"].lower()]
    assert len(genai) >= 4

    # R1: comparar los artículos de IA generativa y profundizar en el par más similar según SBERT.
    cmp_ = client.post("/api/similarity/compare", json={"ids": genai}).json()
    best = max(cmp_["pairs"], key=lambda p: p["scores"]["sbert_cosine"]["value"])
    ex = client.get("/api/similarity/explain", params={"a": best["a"], "b": best["b"]}).json()
    assert ex["summary"][-1]["value"] == pytest.approx(best["scores"]["sbert_cosine"]["value"], abs=1e-6)

    # R2: los artículos de IA generativa deberían concentrarse en pocos grupos con SBERT + complete.
    cl = client.get("/api/clustering", params={"representation": "sbert", "display_k": 4}).json()
    groups = cl["methods"]["complete"]["display_clusters"]
    group_of = {art["id"]: g["group"] for g in groups for art in g["articles"]}
    assert len({group_of[i] for i in genai}) <= 2

    # R3: un término compartido por el par debe encontrarse en ambos abstracts.
    shared = ex["jaccard"]["intersection"][0]
    word = ex["jaccard"]["display"][shared]
    res = client.post("/api/search", json={"pattern": word}).json()
    ids_found = {r["id"] for r in res["results"]}
    assert {best["a"], best["b"]} <= ids_found
    tr = client.post("/api/search/trace", json={"pattern": word, "article_id": best["a"], "algorithm": "boyer_moore"}).json()
    assert tr["positions"]
