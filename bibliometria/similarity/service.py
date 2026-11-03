"""
Servicio del Requerimiento 1: compara dos o más abstracts seleccionados con los
seis algoritmos y genera la demostración paso a paso de un par.

Todos los algoritmos clásicos usan la misma representación (raíces de Porter
sin stopwords). Los modelos de IA trabajan sobre el texto (GloVe: palabras de
contenido; SBERT: abstract completo).
"""

from __future__ import annotations

import time
from itertools import combinations

from ..config import GLOVE_SUBSET_JSON, SBERT_EMBEDDINGS_JSON
from ..corpus import Article, Corpus
from ..preprocessing import default_preprocessor
from ..preprocessing.tokenizer import normalize_text
from .embeddings import GloveModel, SbertModel
from .jaccard import jaccard
from .levenshtein import levenshtein_alignment, levenshtein_distance, levenshtein_matrix
from .needleman_wunsch import GAP, needleman_wunsch
from .tfidf import TfidfModel
from .vector_math import angle_degrees, cosine, dot, euclidean, l2_normalize, norm, sparse_cosine

ALGORITHMS: dict[str, dict] = {
    "levenshtein": {
        "label": "Levenshtein",
        "family": "clásico",
        "technique": "Programación dinámica — distancia de edición",
        "formula": "1 - d(A,B) / max(|A|,|B|)",
        "complexity": "O(n·m)",
    },
    "needleman_wunsch": {
        "label": "Needleman-Wunsch",
        "family": "clásico",
        "technique": "Programación dinámica — alineamiento global",
        "formula": "coincidencias / longitud del alineamiento",
        "complexity": "O(n·m)",
    },
    "jaccard": {
        "label": "Jaccard",
        "family": "clásico",
        "technique": "Teoría de conjuntos",
        "formula": "|A ∩ B| / |A ∪ B|",
        "complexity": "O(n + m)",
    },
    "tfidf_cosine": {
        "label": "Coseno TF-IDF",
        "family": "clásico",
        "technique": "Modelo de espacio vectorial",
        "formula": "(w_A · w_B) / (||w_A|| ||w_B||)",
        "complexity": "O(n + m)",
    },
    "glove_cosine": {
        "label": "GloVe + coseno",
        "family": "IA",
        "technique": "Embeddings estáticos de palabras (promedio)",
        "formula": "cos(mean(v_w), mean(v_w'))",
        "complexity": "O((n + m)·d)",
    },
    "sbert_cosine": {
        "label": "Sentence-BERT + coseno",
        "family": "IA",
        "technique": "Embeddings contextuales (transformer)",
        "formula": "cos(SBERT(A), SBERT(B))",
        "complexity": "O(L²·d) por texto (atención)",
    },
}

CLASSIC = ("levenshtein", "needleman_wunsch", "jaccard", "tfidf_cosine")
AI = ("glove_cosine", "sbert_cosine")


def _round(x: float, nd: int = 6) -> float:
    return float(round(x, nd))


class SimilarityEngine:
    """Precalcula las representaciones del corpus y responde comparaciones."""

    def __init__(self, corpus: Corpus) -> None:
        self.corpus = corpus
        pre = default_preprocessor()
        self.processed = {a.id: pre.process(a.abstract) for a in corpus}
        self.stems = {aid: p.stems for aid, p in self.processed.items()}
        self.chars = {a.id: normalize_text(a.abstract).lower() for a in corpus}
        self.tfidf = TfidfModel([self.stems[aid] for aid in corpus.ids])
        self.tfidf_vectors = {aid: self.tfidf.vector(self.stems[aid]) for aid in corpus.ids}
        self.glove = GloveModel() if GLOVE_SUBSET_JSON.exists() else None
        self.glove_embeddings = {a.id: self.glove.embed(a.abstract) for a in corpus} if self.glove else {}
        self.sbert = SbertModel() if SBERT_EMBEDDINGS_JSON.exists() else None

    # ------------------------------------------------------------ disponibilidad
    def available_algorithms(self) -> list[str]:
        keys = list(CLASSIC)
        if self.glove is not None:
            keys.append("glove_cosine")
        if self.sbert is not None:
            keys.append("sbert_cosine")
        return keys

    # --------------------------------------------------------------- puntajes
    def score(self, algorithm: str, a: int, b: int, granularity: str = "words") -> float:
        if algorithm == "levenshtein":
            if granularity == "chars":
                sa, sb = self.chars[a], self.chars[b]
            else:
                sa, sb = self.stems[a], self.stems[b]
            longest = max(len(sa), len(sb))
            return 1.0 if longest == 0 else 1.0 - levenshtein_distance(sa, sb) / longest
        if algorithm == "needleman_wunsch":
            return needleman_wunsch(self.stems[a], self.stems[b]).identity
        if algorithm == "jaccard":
            return jaccard(self.stems[a], self.stems[b]).similarity
        if algorithm == "tfidf_cosine":
            return sparse_cosine(self.tfidf_vectors[a], self.tfidf_vectors[b])
        if algorithm == "glove_cosine":
            if self.glove is None:
                raise RuntimeError("El modelo GloVe no está disponible")
            return cosine(self.glove_embeddings[a].vector, self.glove_embeddings[b].vector)
        if algorithm == "sbert_cosine":
            if self.sbert is None:
                raise RuntimeError("Los embeddings SBERT no están disponibles")
            return cosine(self.sbert.vector_for(a), self.sbert.vector_for(b))
        raise ValueError(f"Algoritmo desconocido: {algorithm}")

    def compare(self, ids: list[int], algorithms: list[str] | None = None, granularity: str = "words") -> dict:
        """Compara todos los pares de los artículos seleccionados."""
        if len(ids) < 2:
            raise ValueError("Seleccione al menos dos artículos")
        unique: list[int] = []
        for i in ids:
            self.corpus.get(i)  # valida existencia
            if i not in unique:
                unique.append(i)
        if len(unique) < 2:
            raise ValueError("Seleccione al menos dos artículos distintos")
        algs = algorithms or self.available_algorithms()
        for alg in algs:
            if alg not in ALGORITHMS:
                raise ValueError(f"Algoritmo desconocido: {alg}")

        pairs = []
        index = {aid: k for k, aid in enumerate(unique)}
        matrices = {alg: [[1.0 if r == c else 0.0 for c in range(len(unique))] for r in range(len(unique))] for alg in algs}
        timings = {alg: 0.0 for alg in algs}
        for a, b in combinations(unique, 2):
            scores = {}
            for alg in algs:
                t0 = time.perf_counter()
                value = self.score(alg, a, b, granularity)
                ms = (time.perf_counter() - t0) * 1000
                timings[alg] += ms
                scores[alg] = {"value": _round(value), "ms": _round(ms, 3)}
                matrices[alg][index[a]][index[b]] = _round(value)
                matrices[alg][index[b]][index[a]] = _round(value)
            pairs.append({"a": a, "b": b, "scores": scores})

        return {
            "articles": [self._article_summary(self.corpus.get(i)) for i in unique],
            "algorithms": [{"key": k, **ALGORITHMS[k]} for k in algs],
            "granularity": granularity,
            "pairs": pairs,
            "matrices": matrices,
            "timings_ms": {k: _round(v, 3) for k, v in timings.items()},
        }

    def full_matrix(self, algorithm: str, granularity: str = "words") -> list[list[float]]:
        ids = self.corpus.ids
        n = len(ids)
        M = [[1.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                v = self.score(algorithm, ids[i], ids[j], granularity)
                M[i][j] = M[j][i] = v
        return M

    # ------------------------------------------------------------ paso a paso
    def explain(self, a: int, b: int, window: int = 10, nw_params: tuple[int, int, int] = (1, -1, -1)) -> dict:
        """Desglose matemático de los seis algoritmos para el par (a, b)."""
        art_a, art_b = self.corpus.get(a), self.corpus.get(b)
        pa, pb = self.processed[a], self.processed[b]
        sa, sb = pa.stems, pb.stems
        out: dict = {
            "a": self._article_summary(art_a, include_abstract=True),
            "b": self._article_summary(art_b, include_abstract=True),
            "preprocessing": {
                "a": self._preprocessing_summary(pa),
                "b": self._preprocessing_summary(pb),
            },
        }

        # Levenshtein: matriz sobre una ventana de tokens + resultado completo.
        wa, wb = sa[:window], sb[:window]
        D = levenshtein_matrix(wa, wb)
        ops = levenshtein_alignment(wa, wb, D)
        dist_words = levenshtein_distance(sa, sb)
        dist_chars = levenshtein_distance(self.chars[a], self.chars[b])
        out["levenshtein"] = {
            "window_a": wa,
            "window_b": wb,
            "matrix": D,
            "path": [[op["i"], op["j"]] for op in ops],
            "operations": ops,
            "window_distance": D[len(wa)][len(wb)],
            "distance": dist_words,
            "len_a": len(sa),
            "len_b": len(sb),
            "similarity": _round(1 - dist_words / max(len(sa), len(sb), 1)),
            "chars": {
                "distance": dist_chars,
                "len_a": len(self.chars[a]),
                "len_b": len(self.chars[b]),
                "similarity": _round(1 - dist_chars / max(len(self.chars[a]), len(self.chars[b]), 1)),
            },
        }

        # Needleman-Wunsch: matriz de la ventana + alineamiento completo.
        match, mismatch, gap = nw_params
        nw_win = needleman_wunsch(wa, wb, match, mismatch, gap, keep_matrix=True)
        nw = needleman_wunsch(sa, sb, match, mismatch, gap)
        out["needleman_wunsch"] = {
            "params": {"match": match, "mismatch": mismatch, "gap": gap},
            "window_a": wa,
            "window_b": wb,
            "matrix": nw_win.matrix,
            "window_alignment": [[x, y] for x, y in zip(nw_win.aligned_a, nw_win.aligned_b)],
            "window_score": nw_win.score,
            "score": nw.score,
            "matches": nw.matches,
            "mismatches": nw.mismatches,
            "gaps": nw.gaps,
            "length": nw.length,
            "similarity": _round(nw.identity),
            "alignment": [[x, y] for x, y in zip(nw.aligned_a, nw.aligned_b)],
            "gap_symbol": GAP,
        }

        # Jaccard.
        jr = jaccard(sa, sb)
        out["jaccard"] = {
            "size_a": len(jr.intersection) + len(jr.only_a),
            "size_b": len(jr.intersection) + len(jr.only_b),
            "intersection": jr.intersection,
            "only_a": jr.only_a,
            "only_b": jr.only_b,
            "union_size": jr.union_size,
            "similarity": _round(jr.similarity),
            "display": {t: pa.stem_to_word.get(t) or pb.stem_to_word.get(t, t) for t in jr.intersection},
        }

        # TF-IDF + coseno.
        ex = self.tfidf.explain(sa, sb)
        terms = sorted(ex["terms"], key=lambda t: (-t.product, -(t.w_a + t.w_b), t.term))
        out["tfidf"] = {
            "n_docs": ex["n_docs"],
            "idf_formula": "ln((1+N)/(1+df)) + 1",
            "terms": [
                {
                    "term": t.term,
                    "word": pa.stem_to_word.get(t.term) or pb.stem_to_word.get(t.term, t.term),
                    "tf_a": t.tf_a,
                    "tf_b": t.tf_b,
                    "df": t.df,
                    "idf": _round(t.idf),
                    "w_a": _round(t.w_a),
                    "w_b": _round(t.w_b),
                    "product": _round(t.product),
                }
                for t in terms
            ],
            "shared_terms": sum(1 for t in terms if t.tf_a and t.tf_b),
            "dot_raw": _round(ex["dot_raw"]),
            "norm_a": _round(ex["norm_a"]),
            "norm_b": _round(ex["norm_b"]),
            "cosine": _round(ex["cosine"]),
            "angle_deg": _round(angle_degrees(ex["cosine"]), 3),
        }

        # Modelos de IA.
        if self.glove is not None:
            ga, gb = self.glove_embeddings[a], self.glove_embeddings[b]
            out["glove"] = self._vector_explain(ga.vector, gb.vector, self.glove.name, self.glove.dim)
            out["glove"].update(
                {
                    "used_a": len(ga.used_tokens),
                    "used_b": len(gb.used_tokens),
                    "oov_a": ga.oov_tokens,
                    "oov_b": gb.oov_tokens,
                    "sample_words_a": ga.used_tokens[:8],
                    "sample_vectors_a": [[_round(x, 4) for x in self.glove.vectors[w][:6]] for w in ga.used_tokens[:3]],
                }
            )
        if self.sbert is not None:
            va, vb = self.sbert.vector_for(a), self.sbert.vector_for(b)
            out["sbert"] = self._vector_explain(va, vb, self.sbert.name, self.sbert.dim)
            out["sbert"].update(
                {
                    "tokens_a": self.sbert.token_counts.get(a),
                    "tokens_b": self.sbert.token_counts.get(b),
                    "max_seq_length": self.sbert.max_seq_length,
                }
            )

        summary = []
        for key in self.available_algorithms():
            summary.append({"key": key, **ALGORITHMS[key], "value": _round(self.score(key, a, b))})
        out["summary"] = summary
        return out

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _vector_explain(u: list[float], v: list[float], model: str, dim: int) -> dict:
        d = dot(u, v)
        nu, nv = norm(u), norm(v)
        cos = cosine(u, v)
        return {
            "model": model,
            "dim": dim,
            "head_a": [_round(x, 4) for x in u[:8]],
            "head_b": [_round(x, 4) for x in v[:8]],
            "dot": _round(d),
            "norm_a": _round(nu),
            "norm_b": _round(nv),
            "cosine": _round(cos),
            "angle_deg": _round(angle_degrees(cos), 3),
            "euclidean": _round(euclidean(u, v)),
            "euclidean_normalized": _round(euclidean(l2_normalize(u), l2_normalize(v))),
        }

    @staticmethod
    def _preprocessing_summary(p) -> dict:
        return {
            "tokens": len(p.tokens),
            "filtered": len(p.filtered),
            "stems": len(p.stems),
            "unique_stems": len(p.stem_to_word),
            "sample_tokens": p.tokens[:20],
            "sample_filtered": p.filtered[:20],
            "sample_stems": p.stems[:20],
        }

    @staticmethod
    def _article_summary(a: Article, include_abstract: bool = False) -> dict:
        d = {
            "id": a.id,
            "code": a.code,
            "title": a.title,
            "short_title": a.short_title,
            "authors": list(a.authors),
            "year": a.year,
        }
        if include_abstract:
            d["abstract"] = a.abstract
        return d


_ENGINE: SimilarityEngine | None = None


def get_engine() -> SimilarityEngine:
    global _ENGINE
    if _ENGINE is None:
        from ..corpus import load_corpus

        _ENGINE = SimilarityEngine(load_corpus())
    return _ENGINE
