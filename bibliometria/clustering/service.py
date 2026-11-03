"""
Servicio del Requerimiento 2: preprocesamiento -> vectorización -> matriz de
distancias -> agrupamiento jerárquico -> evaluación -> dendrograma.

Representaciones disponibles:
- ``tfidf``: vectores TF-IDF (clásico) construidos con el mismo preprocesamiento
  del Requerimiento 1.
- ``sbert``: embeddings Sentence-BERT (IA), para contrastar.

Single, complete y average usan la distancia coseno d = 1 - cos(u, v). Ward
requiere distancia euclidiana; como los vectores están normalizados (||u|| = 1),
d_E(u, v) = sqrt(2 - 2·cos(u, v)), que ordena los pares igual que la coseno.
La silueta de todos los métodos se calcula con la distancia coseno para tener
una vara de medida común.
"""

from __future__ import annotations

import math

from ..config import OUTPUTS_DIR
from ..corpus import Corpus
from ..similarity.service import SimilarityEngine, get_engine
from ..similarity.vector_math import cosine, sparse_cosine
from .agglomerative import METHOD_INFO, METHODS, agglomerative_clustering, cluster_members, linkage_matrix
from .dendrogram import dendrogram_layout, render_dendrogram
from .evaluation import cophenetic_correlation, cut_tree, silhouette_samples

REQUIRED_METHODS = ("single", "complete", "average")  # los tres exigidos; ward es adicional
REPRESENTATIONS = {
    "tfidf": "TF-IDF (raíces de Porter, idf suavizado, normalización L2)",
    "sbert": "Sentence-BERT all-MiniLM-L6-v2 (384 dimensiones, normalizado)",
}


def _r(x: float, nd: int = 6) -> float:
    return float(round(x, nd))


class ClusteringEngine:
    def __init__(self, corpus: Corpus, similarity: SimilarityEngine) -> None:
        self.corpus = corpus
        self.similarity = similarity
        self.ids = corpus.ids
        self.n = len(self.ids)
        self._cache: dict[tuple, dict] = {}

    # ------------------------------------------------------------ distancias
    def cosine_similarity_matrix(self, representation: str) -> list[list[float]]:
        n = self.n
        S = [[1.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                a, b = self.ids[i], self.ids[j]
                if representation == "tfidf":
                    s = sparse_cosine(self.similarity.tfidf_vectors[a], self.similarity.tfidf_vectors[b])
                elif representation == "sbert":
                    if self.similarity.sbert is None:
                        raise RuntimeError("Embeddings SBERT no disponibles")
                    s = cosine(self.similarity.sbert.vector_for(a), self.similarity.sbert.vector_for(b))
                else:
                    raise ValueError(f"Representación desconocida: {representation}")
                S[i][j] = S[j][i] = s
        return S

    def distance_matrices(self, representation: str) -> tuple[list[list[float]], list[list[float]]]:
        S = self.cosine_similarity_matrix(representation)
        n = self.n
        D_cos = [[0.0 if i == j else max(0.0, 1.0 - S[i][j]) for j in range(n)] for i in range(n)]
        D_euc = [[0.0 if i == j else math.sqrt(max(0.0, 2.0 - 2.0 * S[i][j])) for j in range(n)] for i in range(n)]
        return D_cos, D_euc

    # ----------------------------------------------------------------- run
    def leaf_labels(self) -> list[str]:
        labels = []
        for aid in self.ids:
            a = self.corpus.get(aid)
            labels.append(f"{a.code} {a.first_author_surname} {a.year or ''}".strip())
        return labels

    def run(
        self,
        representation: str = "tfidf",
        methods: tuple[str, ...] = METHODS,
        k_min: int = 2,
        k_max: int = 8,
        display_k: int = 4,
    ) -> dict:
        """Ejecuta los criterios de enlace y los evalúa.

        ``best_k`` es el k con mayor silueta en [k_min, k_max]; ``display_k`` es el
        número de grupos con que se colorea el dendrograma (igual para todos los
        métodos, para poder compararlos visualmente).
        """
        key = (representation, tuple(methods), k_min, k_max, display_k)
        if key in self._cache:
            return self._cache[key]
        D_cos, D_euc = self.distance_matrices(representation)
        labels = self.leaf_labels()
        results = {}
        for method in methods:
            D = D_euc if method == "ward" else D_cos
            res = agglomerative_clustering(D, method, trace=True)
            merges = res["merges"]
            cpcc = cophenetic_correlation(D, merges)
            sil = {}
            for k in range(k_min, k_max + 1):
                labs = cut_tree(merges, self.n, k)
                samples = silhouette_samples(D_cos, labs)
                sil[k] = sum(samples) / len(samples)
            best_k = max(sil, key=lambda kk: (sil[kk], -kk))
            groups = cut_tree(merges, self.n, best_k)
            members = cluster_members(merges, self.n)
            results[method] = {
                "method": method,
                **METHOD_INFO[method],
                "required": method in REQUIRED_METHODS,
                "distance": "euclidiana" if method == "ward" else "coseno",
                "merges": [
                    {
                        "step": m.step,
                        "left": m.left,
                        "right": m.right,
                        "distance": _r(m.distance),
                        "size": m.size,
                        "members": [self.ids[x] for x in members[self.n + idx]],
                    }
                    for idx, m in enumerate(merges)
                ],
                "linkage": [[_r(v) for v in row] for row in linkage_matrix(merges)],
                "cophenetic_correlation": _r(cpcc),
                "silhouette": {str(k): _r(v) for k, v in sil.items()},
                "silhouette_mean": _r(sum(sil.values()) / len(sil)),
                "best_k": best_k,
                "best_silhouette": _r(sil[best_k]),
                "clusters": self._clusters(groups),
                "display_k": display_k,
                "display_clusters": self._clusters(cut_tree(merges, self.n, display_k)),
                "dendrogram": dendrogram_layout(merges, self.n, labels, k=display_k),
                "pair_comparisons": res["pair_comparisons"],
            }
        ranking = sorted(
            results.values(),
            key=lambda r: (r["silhouette_mean"], r["best_silhouette"], r["cophenetic_correlation"]),
            reverse=True,
        )
        required_ranking = [r["method"] for r in ranking if r["required"]]
        out = {
            "representation": representation,
            "representation_label": REPRESENTATIONS[representation],
            "n": self.n,
            "ids": self.ids,
            "labels": labels,
            "k_range": [k_min, k_max],
            "methods": results,
            "ranking": [r["method"] for r in ranking],
            "best_required_method": required_ranking[0] if required_ranking else None,
            "best_method": ranking[0]["method"],
            "distance_matrix": [[_r(v, 5) for v in row] for row in D_cos],
        }
        self._cache[key] = out
        return out

    def _clusters(self, groups: list[int]) -> list[dict]:
        buckets: dict[int, list[int]] = {}
        for idx, g in enumerate(groups):
            buckets.setdefault(g, []).append(self.ids[idx])
        clusters = []
        for g, members in sorted(buckets.items()):
            clusters.append(
                {
                    "group": g,
                    "size": len(members),
                    "articles": [
                        {"id": m, "code": self.corpus.get(m).code, "title": self.corpus.get(m).title, "year": self.corpus.get(m).year}
                        for m in members
                    ],
                }
            )
        return clusters

    # -------------------------------------------------------------- salidas
    def export_outputs(self, representation: str = "tfidf") -> list[str]:
        """Guarda dendrogramas PNG y métricas CSV en ``outputs/clustering``."""
        result = self.run(representation)
        out_dir = OUTPUTS_DIR / "clustering"
        out_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for method, r in result["methods"].items():
            png = out_dir / f"dendrograma_{representation}_{method}.png"
            title = (
                f"{r['label']} — {representation.upper()}  |  CPCC = {r['cophenetic_correlation']:.3f}  |  "
                f"silueta máx. = {r['best_silhouette']:.3f} (k = {r['best_k']})"
            )
            ylabel = "Distancia euclidiana" if method == "ward" else "Distancia coseno (1 - cos)"
            render_dendrogram(r["dendrogram"], png, title, ylabel)
            written.append(str(png))
        csv_path = out_dir / f"metricas_{representation}.csv"
        with open(csv_path, "w", encoding="utf-8") as fh:
            fh.write("metodo,cpcc,k,silueta\n")
            for method, r in result["methods"].items():
                for k, v in r["silhouette"].items():
                    fh.write(f"{method},{r['cophenetic_correlation']},{k},{v}\n")
        written.append(str(csv_path))
        return written


_ENGINE: ClusteringEngine | None = None


def get_clustering_engine() -> ClusteringEngine:
    global _ENGINE
    if _ENGINE is None:
        sim = get_engine()
        _ENGINE = ClusteringEngine(sim.corpus, sim)
    return _ENGINE
