"""Pruebas del agrupamiento jerárquico (Requerimiento 2) con SciPy/scikit-learn como oráculos."""

import random

import numpy as np
import pytest
from scipy.cluster.hierarchy import cophenet, dendrogram, fcluster, linkage
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import silhouette_score as sk_silhouette

from bibliometria.clustering.agglomerative import METHODS, agglomerative_clustering, lance_williams
from bibliometria.clustering.dendrogram import cut_threshold, dendrogram_layout, leaf_order
from bibliometria.clustering.evaluation import cophenetic_correlation, cut_tree, silhouette_score


def _random_points(seed: int, n: int = 15, dim: int = 4) -> np.ndarray:
    return np.random.default_rng(seed).random((n, dim))


def _canonical(labels) -> list[int]:
    remap, out = {}, []
    for x in labels:
        remap.setdefault(x, len(remap))
        out.append(remap[x])
    return out


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("seed", range(6))
def test_linkage_matches_scipy(method, seed):
    X = _random_points(seed)
    D = squareform(pdist(X)).tolist()
    ours = agglomerative_clustering(D, method)["merges"]
    ref = linkage(pdist(X), method=method)
    assert len(ours) == len(ref)
    for m, row in zip(ours, ref):
        assert {m.left, m.right} == {int(row[0]), int(row[1])}
        assert m.distance == pytest.approx(row[2], rel=1e-9, abs=1e-12)
        assert m.size == int(row[3])


@pytest.mark.parametrize("method", METHODS)
def test_linkage_matches_scipy_on_corpus(clustering_engine, method):
    D_cos, D_euc = clustering_engine.distance_matrices("tfidf")
    D = D_euc if method == "ward" else D_cos
    ours = agglomerative_clustering(D, method)["merges"]
    ref = linkage(squareform(np.array(D), checks=False), method=method)
    for m, row in zip(ours, ref):
        assert {m.left, m.right} == {int(row[0]), int(row[1])}
        assert m.distance == pytest.approx(row[2], abs=1e-9)


@pytest.mark.parametrize("method", METHODS)
def test_cophenetic_correlation_matches_scipy(method):
    X = _random_points(42, n=18)
    y = pdist(X)
    D = squareform(y).tolist()
    merges = agglomerative_clustering(D, method)["merges"]
    c_ref, _ = cophenet(linkage(y, method=method), y)
    assert cophenetic_correlation(D, merges) == pytest.approx(c_ref, abs=1e-9)


@pytest.mark.parametrize("k", [2, 3, 5, 8])
def test_cut_tree_and_silhouette_match_scipy_and_sklearn(k):
    X = _random_points(7, n=20)
    y = pdist(X)
    D = squareform(y)
    merges = agglomerative_clustering(D.tolist(), "average")["merges"]
    labels = cut_tree(merges, 20, k)
    ref_labels = fcluster(linkage(y, "average"), t=k, criterion="maxclust")
    assert _canonical(labels) == _canonical(ref_labels)
    assert silhouette_score(D.tolist(), labels) == pytest.approx(sk_silhouette(D, labels, metric="precomputed"), abs=1e-12)


def test_dendrogram_geometry_matches_scipy():
    X = _random_points(3, n=12)
    y = pdist(X)
    merges = agglomerative_clustering(squareform(y).tolist(), "complete")["merges"]
    ref = dendrogram(linkage(y, "complete"), no_plot=True)
    assert leaf_order(merges, 12) == ref["leaves"]
    layout = dendrogram_layout(merges, 12, [str(i) for i in range(12)])
    ours = sorted(tuple(round(v, 9) for v in link["icoord"] + link["dcoord"]) for link in layout["links"])
    theirs = sorted(tuple(round(v, 9) for v in ic + dc) for ic, dc in zip(ref["icoord"], ref["dcoord"]))
    assert ours == theirs


def test_lance_williams_formulas_by_hand():
    assert lance_williams("single", 2.0, 5.0, 1.0, 1, 1, 1) == 2.0
    assert lance_williams("complete", 2.0, 5.0, 1.0, 1, 1, 1) == 5.0
    assert lance_williams("average", 2.0, 5.0, 1.0, 1, 2, 1) == pytest.approx(3.0)
    assert lance_williams("ward", 1.0, 1.0, 1.0, 1, 1, 1) == pytest.approx((4 / 3 - 1 / 3) ** 0.5)


def test_input_validation():
    with pytest.raises(ValueError):
        agglomerative_clustering([[0.0]], "average")
    with pytest.raises(ValueError):
        agglomerative_clustering([[0, 1], [2, 0]], "average")
    with pytest.raises(ValueError):
        agglomerative_clustering([[0, 1], [1, 0]], "centroid")


def test_merge_heights_are_monotone_and_threshold_gives_k_groups():
    random.seed(5)
    X = _random_points(11, n=16)
    D = squareform(pdist(X)).tolist()
    for method in METHODS:
        merges = agglomerative_clustering(D, method)["merges"]
        heights = [m.distance for m in merges]
        assert heights == sorted(heights)
        for k in (2, 4, 6):
            t = cut_threshold(merges, k)
            assert len(set(fcluster(linkage(pdist(X), method), t=t, criterion="distance"))) == k


def test_service_report(clustering_engine):
    res = clustering_engine.run("tfidf")
    assert res["n"] == 20 and set(res["methods"]) == set(METHODS)
    assert res["best_required_method"] in ("single", "complete", "average")
    for r in res["methods"].values():
        assert -1.0 <= r["cophenetic_correlation"] <= 1.0
        assert len(r["merges"]) == 19 and r["merges"][-1]["size"] == 20
        assert sum(c["size"] for c in r["clusters"]) == 20
        assert len(r["display_clusters"]) == 4
    sbert = clustering_engine.run("sbert")
    assert sbert["representation"] == "sbert"
