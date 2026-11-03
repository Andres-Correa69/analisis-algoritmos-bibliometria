"""
Algoritmo Knuth-Morris-Pratt (KMP, 1977).

Preprocesamiento — función de prefijos π (tabla de fallos):
    π[q] = longitud del prefijo propio más largo de P[0..q] que también es
           sufijo de P[0..q].
Se calcula en O(m) reutilizando valores previos: si P[k] ≠ P[q] se "retrocede"
k = π[k-1] hasta que coincidan o k = 0.

Búsqueda: se recorre el texto una sola vez (el índice i nunca retrocede).
Ante una discrepancia con q caracteres ya emparejados, el patrón se desplaza
para que su prefijo de longitud π[q-1] quede alineado con el texto, evitando
volver a comparar caracteres que ya se sabe que coinciden.

Complejidad: preprocesamiento Θ(m) y búsqueda Θ(n) (a lo sumo 2n
comparaciones, por análisis amortizado). Memoria O(m).
"""

from __future__ import annotations

import time

from .base import DEFAULT_MAX_TRACE, MatchResult, Tracer, validate


def prefix_function(pattern: str, steps: list[dict] | None = None) -> list[int]:
    """Calcula π. Si ``steps`` es una lista, registra cómo se obtuvo cada π[q]."""
    m = len(pattern)
    pi = [0] * m
    k = 0
    if steps is not None and m:
        steps.append({"q": 0, "char": pattern[0], "k_before": 0, "fallbacks": [], "pi": 0})
    for q in range(1, m):
        k_before = k
        fallbacks: list[int] = []
        while k > 0 and pattern[k] != pattern[q]:
            k = pi[k - 1]
            fallbacks.append(k)
        if pattern[k] == pattern[q]:
            k += 1
        pi[q] = k
        if steps is not None:
            steps.append({"q": q, "char": pattern[q], "k_before": k_before, "fallbacks": fallbacks, "pi": k})
    return pi


def kmp_search(text: str, pattern: str, trace: bool = False, max_trace: int = DEFAULT_MAX_TRACE) -> MatchResult:
    validate(text, pattern)
    n, m = len(text), len(pattern)
    tracer = Tracer(trace, max_trace)
    build_steps: list[dict] | None = [] if trace else None

    t0 = time.perf_counter_ns()
    pi = prefix_function(pattern, build_steps)
    t1 = time.perf_counter_ns()

    positions: list[int] = []
    comparisons = 0
    shifts = 0
    q = 0  # número de caracteres del patrón emparejados
    for i in range(n):
        while True:
            comparisons += 1
            if pattern[q] == text[i]:
                tracer.add(type="compare", i=i, j=q, alignment=i - q, match=True)
                q += 1
                break
            tracer.add(type="compare", i=i, j=q, alignment=i - q, match=False)
            if q == 0:
                shifts += 1
                tracer.add(type="shift", from_alignment=i, to_alignment=i + 1, reason="π no aplica (q = 0): avanzar 1")
                break
            shifts += 1
            tracer.add(
                type="shift",
                from_alignment=i - q,
                to_alignment=i - pi[q - 1],
                reason=f"π[{q - 1}] = {pi[q - 1]}",
            )
            q = pi[q - 1]
        if q == m:
            positions.append(i - m + 1)
            tracer.add(type="found", position=i - m + 1)
            if m > 0:
                shifts += 1
                tracer.add(
                    type="shift",
                    from_alignment=i - m + 1,
                    to_alignment=i + 1 - pi[m - 1],
                    reason=f"ocurrencia: continuar con π[{m - 1}] = {pi[m - 1]}",
                )
            q = pi[q - 1]
    t2 = time.perf_counter_ns()

    return MatchResult(
        algorithm="kmp",
        pattern=pattern,
        text_length=n,
        positions=positions,
        comparisons=comparisons,
        preprocessing_ns=t1 - t0,
        search_ns=t2 - t1,
        alignments=shifts + 1 if n >= m else 0,
        tables={"pi": pi, "pi_steps": build_steps or []},
        trace=tracer.events,
        trace_truncated=tracer.truncated,
    )
