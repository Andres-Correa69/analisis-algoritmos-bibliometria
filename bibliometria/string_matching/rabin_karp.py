"""
Algoritmo Rabin-Karp (1987): huella digital (hash) con aritmética modular.

Cada cadena de longitud m se interpreta como un número en base d (aquí el
código Unicode de cada carácter es un "dígito") reducido módulo un primo q:

    H(S) = ( S[0]·d^(m-1) + S[1]·d^(m-2) + ... + S[m-1] ) mod q      (regla de Horner)

Rolling hash: el hash de la ventana siguiente se obtiene en O(1) a partir del
anterior, quitando el carácter que sale y agregando el que entra:

    t_{s+1} = ( d·(t_s - T[s]·h) + T[s+m] ) mod q,     h = d^(m-1) mod q

Si t_s = H(P) la ventana es candidata y se verifica carácter por carácter;
si no coincide, fue una colisión (coincidencia espuria).

Complejidad: preprocesamiento Θ(m); búsqueda esperada O(n + m) con q grande;
peor caso O(n·m) cuando casi todas las ventanas coinciden en hash (muchas
ocurrencias o un módulo pequeño que provoca muchas colisiones).
"""

from __future__ import annotations

import time

from .base import DEFAULT_MAX_TRACE, MatchResult, Tracer, validate

DEFAULT_BASE = 256
DEFAULT_MODULUS = 1_000_000_007  # primo grande -> colisiones muy improbables


def rabin_karp_search(
    text: str,
    pattern: str,
    base: int = DEFAULT_BASE,
    modulus: int = DEFAULT_MODULUS,
    trace: bool = False,
    max_trace: int = DEFAULT_MAX_TRACE,
) -> MatchResult:
    validate(text, pattern)
    if base < 2 or modulus < 2:
        raise ValueError("La base y el módulo deben ser >= 2")
    n, m = len(text), len(pattern)
    tracer = Tracer(trace, max_trace)

    t0 = time.perf_counter_ns()
    h = 1
    for _ in range(m - 1):  # h = d^(m-1) mod q por multiplicaciones sucesivas
        h = (h * base) % modulus
    p_hash = 0
    pattern_steps = []
    for idx in range(m):
        p_hash = (p_hash * base + ord(pattern[idx])) % modulus
        if trace:
            pattern_steps.append({"index": idx, "char": pattern[idx], "code": ord(pattern[idx]), "hash": p_hash})
    t1 = time.perf_counter_ns()

    positions: list[int] = []
    comparisons = 0
    hash_hits = spurious = 0
    alignments = 0
    if n >= m:
        t_hash = 0
        for idx in range(m):
            t_hash = (t_hash * base + ord(text[idx])) % modulus
        for s in range(n - m + 1):
            alignments += 1
            equal = t_hash == p_hash
            verified = None
            if equal:
                hash_hits += 1
                j = 0
                while j < m:
                    comparisons += 1
                    if text[s + j] != pattern[j]:
                        break
                    j += 1
                verified = j == m
                if verified:
                    positions.append(s)
                else:
                    spurious += 1
            next_hash = None
            if s < n - m:
                out_c, in_c = text[s], text[s + m]
                next_hash = (base * (t_hash - ord(out_c) * h) + ord(in_c)) % modulus
            tracer.add(
                type="window",
                alignment=s,
                window_hash=t_hash,
                pattern_hash=p_hash,
                hash_match=equal,
                verified=verified,
                out_char=text[s] if s < n - m else None,
                in_char=text[s + m] if s < n - m else None,
                next_hash=next_hash,
            )
            if verified:
                tracer.add(type="found", position=s)
            elif equal:
                tracer.add(type="spurious", position=s)
            if next_hash is not None:
                t_hash = next_hash
    t2 = time.perf_counter_ns()

    return MatchResult(
        algorithm="rabin_karp",
        pattern=pattern,
        text_length=n,
        positions=positions,
        comparisons=comparisons,
        preprocessing_ns=t1 - t0,
        search_ns=t2 - t1,
        alignments=alignments,
        extra={"hash_hits": hash_hits, "spurious_hits": spurious, "base": base, "modulus": modulus},
        tables={"h": h, "pattern_hash": p_hash, "pattern_hash_steps": pattern_steps},
        trace=tracer.events,
        trace_truncated=tracer.truncated,
    )
