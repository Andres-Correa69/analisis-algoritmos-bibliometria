"""
Benchmark empírico de los algoritmos de búsqueda de patrones (Requerimiento 3).

Experimentos:
A. Longitud del patrón m (n fijo): patrones extraídos del propio corpus.
B. Longitud del texto n (m fijo): el corpus concatenado se replica 1x..16x.
C. Peor caso teórico: T = a^n con P = a^(m-1)b (sin ocurrencias) y P = a^m
   (ocurrencia en cada posición), donde se separan los comportamientos O(n) y O(n·m).

Para cada medición se reporta la mediana de varias repeticiones del tiempo de
preprocesamiento y de búsqueda (``time.perf_counter_ns``) y el número de
comparaciones de caracteres (métrica independiente de la máquina).
"""

from __future__ import annotations

import json
import platform
import random
import statistics
import sys
import time

from ..config import BENCHMARK_JSON
from ..corpus import load_corpus
from .service import fold_case, run_algorithm

ALGS = ("naive", "kmp", "boyer_moore", "rabin_karp")


def _measure(alg: str, text: str, pattern: str, repeats: int) -> dict:
    pre, search, comps, spur = [], [], 0, 0
    occ = 0
    for _ in range(repeats):
        r = run_algorithm(alg, text, pattern)
        pre.append(r.preprocessing_ns)
        search.append(r.search_ns)
        comps = r.comparisons
        spur = r.extra.get("spurious_hits", 0)
        occ = len(r.positions)
    return {
        "preprocessing_us": statistics.median(pre) / 1000,
        "search_us": statistics.median(search) / 1000,
        "total_us": (statistics.median(pre) + statistics.median(search)) / 1000,
        "comparisons": comps,
        "spurious_hits": spur,
        "occurrences": occ,
    }


def corpus_text() -> str:
    return fold_case(" ".join(a.abstract for a in load_corpus()))


def run_benchmark(repeats: int = 5, seed: int = 2026, quick: bool = False) -> dict:
    rng = random.Random(seed)
    base_text = corpus_text()
    started = time.time()

    # ---------------------------------------------------------- A: varía m
    text_a = base_text * (2 if quick else 4)
    lengths = [2, 4, 8, 16, 32, 64] if quick else [2, 4, 8, 16, 32, 64, 128]
    exp_a = []
    for m in lengths:
        patterns = []
        for _ in range(3 if quick else 5):
            start = rng.randrange(0, len(base_text) - m)
            patterns.append(base_text[start : start + m])
        row = {"m": m, "n": len(text_a), "patterns": patterns}
        for alg in ALGS:
            ms = [_measure(alg, text_a, p, repeats) for p in patterns]
            row[alg] = {k: statistics.mean(x[k] for x in ms) for k in ms[0]}
        exp_a.append(row)

    # ---------------------------------------------------------- B: varía n
    pattern_b = "intelligence"
    factors = [1, 2, 4] if quick else [1, 2, 4, 8, 16]
    exp_b = []
    for f in factors:
        text_b = base_text * f
        row = {"factor": f, "n": len(text_b), "m": len(pattern_b), "pattern": pattern_b}
        for alg in ALGS:
            row[alg] = _measure(alg, text_b, pattern_b, repeats)
        exp_b.append(row)

    # -------------------------------------------------- C: peor caso teórico
    n_c = 10_000 if quick else 20_000
    text_c = "a" * n_c
    exp_c = []
    for m in ([5, 10, 20, 40] if quick else [5, 10, 20, 40, 80]):
        for kind, pattern in (("sin_ocurrencias", "a" * (m - 1) + "b"), ("todas_las_posiciones", "a" * m)):
            row = {"m": m, "n": n_c, "case": kind}
            for alg in ALGS:
                row[alg] = _measure(alg, text_c, pattern, max(1, repeats // 2))
            exp_c.append(row)

    # --------------------------------------------- D: colisiones Rabin-Karp
    exp_d = []
    for q in (13, 101, 997, 10_007, 1_000_000_007):
        r = run_algorithm("rabin_karp", base_text, "learning", modulus=q)
        exp_d.append(
            {
                "modulus": q,
                "hash_hits": r.extra["hash_hits"],
                "spurious_hits": r.extra["spurious_hits"],
                "occurrences": len(r.positions),
                "comparisons": r.comparisons,
                "search_us": r.search_ns / 1000,
            }
        )

    result = {
        "meta": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "repeats": repeats,
            "seed": seed,
            "corpus_chars": len(base_text),
            "seconds": round(time.time() - started, 2),
            "quick": quick,
        },
        "pattern_length": exp_a,
        "text_length": exp_b,
        "worst_case": exp_c,
        "rabin_karp_collisions": exp_d,
    }
    return result


def save_benchmark(result: dict) -> None:
    BENCHMARK_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(BENCHMARK_JSON, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)


def load_benchmark() -> dict | None:
    if not BENCHMARK_JSON.exists():
        return None
    with open(BENCHMARK_JSON, encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    res = run_benchmark()
    save_benchmark(res)
    print(f"Benchmark guardado en {BENCHMARK_JSON} ({res['meta']['seconds']} s)")
