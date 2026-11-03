"""
Algoritmo Boyer-Moore (1977) con las dos heurísticas de desplazamiento.

El patrón se compara de DERECHA a IZQUIERDA. Ante una discrepancia en la
posición j del patrón (con el carácter c = T[s+j] del texto):

* Regla del carácter malo:  δ_bc = j - última(c),  donde última(c) es la
  última posición de c en el patrón (-1 si no aparece).
* Regla del sufijo bueno: si el sufijo P[j+1..m-1] ya coincidió, se desplaza
  hasta la siguiente aparición de ese sufijo precedida por un carácter distinto
  de P[j] (sufijo bueno fuerte) o, si no existe, hasta el prefijo más largo del
  patrón que sea sufijo de lo emparejado.  δ_gs = gs[j+1].

Desplazamiento:  s ← s + max(δ_bc, δ_gs).  Tras una ocurrencia: s ← s + gs[0].

Complejidad: preprocesamiento O(m + σ) (σ = tamaño del alfabeto presente).
Búsqueda: mejor caso Θ(n/m) (saltos de longitud m), caso típico sublineal y
peor caso O(n·m) (p. ej. P = a^m sobre T = a^n, sin la regla de Galil).
"""

from __future__ import annotations

import time

from .base import DEFAULT_MAX_TRACE, MatchResult, Tracer, validate


def bad_character_table(pattern: str) -> dict[str, int]:
    """Última aparición de cada carácter del patrón: O(m)."""
    last: dict[str, int] = {}
    for idx in range(len(pattern)):
        last[pattern[idx]] = idx
    return last


def good_suffix_table(pattern: str) -> tuple[list[int], list[int]]:
    """Tabla del sufijo bueno ``shift`` (tamaño m+1) y bordes ``bpos``: O(m).

    ``shift[j+1]`` es el desplazamiento cuando falla P[j] tras emparejar
    P[j+1..m-1]; ``shift[0]`` se usa tras una ocurrencia completa.
    """
    m = len(pattern)
    shift = [0] * (m + 1)
    bpos = [0] * (m + 1)

    # Caso 1: el sufijo emparejado aparece en otra parte del patrón (sufijo bueno fuerte).
    i, j = m, m + 1
    bpos[i] = j
    while i > 0:
        while j <= m and pattern[i - 1] != pattern[j - 1]:
            if shift[j] == 0:
                shift[j] = j - i
            j = bpos[j]
        i -= 1
        j -= 1
        bpos[i] = j

    # Caso 2: sólo un prefijo del patrón coincide con una parte del sufijo emparejado.
    j = bpos[0]
    for i in range(m + 1):
        if shift[i] == 0:
            shift[i] = j
        if i == j:
            j = bpos[j]
    return shift, bpos


def boyer_moore_search(text: str, pattern: str, trace: bool = False, max_trace: int = DEFAULT_MAX_TRACE) -> MatchResult:
    validate(text, pattern)
    n, m = len(text), len(pattern)
    tracer = Tracer(trace, max_trace)

    t0 = time.perf_counter_ns()
    last = bad_character_table(pattern)
    gs, bpos = good_suffix_table(pattern)
    t1 = time.perf_counter_ns()

    positions: list[int] = []
    comparisons = 0
    alignments = 0
    bc_wins = gs_wins = 0
    s = 0
    while s <= n - m:
        alignments += 1
        j = m - 1
        while j >= 0:
            comparisons += 1
            match = pattern[j] == text[s + j]
            tracer.add(type="compare", i=s + j, j=j, alignment=s, match=match)
            if not match:
                break
            j -= 1
        if j < 0:
            positions.append(s)
            tracer.add(type="found", position=s)
            shift = gs[0]
            gs_wins += 1
            tracer.add(type="shift", from_alignment=s, to_alignment=s + shift, rule="sufijo bueno (ocurrencia)", bc_shift=None, gs_shift=gs[0])
        else:
            c = text[s + j]
            bc = j - last.get(c, -1)
            gsv = gs[j + 1]
            if bc >= gsv:
                shift, rule = bc, "carácter malo"
                bc_wins += 1
            else:
                shift, rule = gsv, "sufijo bueno"
                gs_wins += 1
            tracer.add(
                type="shift",
                from_alignment=s,
                to_alignment=s + shift,
                rule=rule,
                bad_char=c,
                mismatch_j=j,
                bc_shift=bc,
                gs_shift=gsv,
            )
        s += shift
    t2 = time.perf_counter_ns()

    return MatchResult(
        algorithm="boyer_moore",
        pattern=pattern,
        text_length=n,
        positions=positions,
        comparisons=comparisons,
        preprocessing_ns=t1 - t0,
        search_ns=t2 - t1,
        alignments=alignments,
        extra={"bad_character_wins": bc_wins, "good_suffix_wins": gs_wins},
        tables={"bad_character": last, "good_suffix": gs, "border_positions": bpos},
        trace=tracer.events,
        trace_truncated=tracer.truncated,
    )
