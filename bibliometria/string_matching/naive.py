"""
Búsqueda por fuerza bruta (algoritmo ingenuo). No es uno de los tres algoritmos
exigidos: se usa como línea base en el benchmark y como oráculo en las pruebas.

Complejidad: O((n - m + 1)·m) en el peor caso, sin preprocesamiento.
"""

from __future__ import annotations

import time

from .base import DEFAULT_MAX_TRACE, MatchResult, Tracer, validate


def naive_search(text: str, pattern: str, trace: bool = False, max_trace: int = DEFAULT_MAX_TRACE) -> MatchResult:
    validate(text, pattern)
    n, m = len(text), len(pattern)
    tracer = Tracer(trace, max_trace)
    positions: list[int] = []
    comparisons = 0
    alignments = 0
    t0 = time.perf_counter_ns()
    for s in range(n - m + 1):
        alignments += 1
        j = 0
        while j < m:
            comparisons += 1
            match = text[s + j] == pattern[j]
            tracer.add(type="compare", i=s + j, j=j, alignment=s, match=match)
            if not match:
                break
            j += 1
        if j == m:
            positions.append(s)
            tracer.add(type="found", position=s)
    t1 = time.perf_counter_ns()
    return MatchResult(
        algorithm="naive",
        pattern=pattern,
        text_length=n,
        positions=positions,
        comparisons=comparisons,
        preprocessing_ns=0,
        search_ns=t1 - t0,
        alignments=alignments,
        trace=tracer.events,
        trace_truncated=tracer.truncated,
    )
