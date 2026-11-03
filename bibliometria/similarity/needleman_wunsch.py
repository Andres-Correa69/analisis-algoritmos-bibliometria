"""
Alineamiento global de Needleman-Wunsch (programación dinámica, 1970).

Dadas dos secuencias A (n) y B (m) y un esquema de puntuación
(coincidencia ``match``, discrepancia ``mismatch`` y hueco ``gap``):

    F[i][0] = i·gap,  F[0][j] = j·gap
    F[i][j] = max( F[i-1][j-1] + s(a_i, b_j),   # alinear a_i con b_j
                   F[i-1][j]   + gap,           # a_i frente a un hueco
                   F[i][j-1]   + gap )          # b_j frente a un hueco

con s(x, y) = match si x = y y mismatch en otro caso. F[n][m] es la puntuación
del mejor alineamiento global; el alineamiento se recupera con *traceback*.

Similitud normalizada (identidad del alineamiento, estándar en bioinformática):

    sim(A, B) = coincidencias / longitud_del_alineamiento

Complejidad: tiempo O(n·m) y memoria O(n·m) (se guarda la matriz para el
traceback).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

GAP = None  # marcador de hueco en las secuencias alineadas


@dataclass
class NWResult:
    score: int
    aligned_a: list = field(default_factory=list)
    aligned_b: list = field(default_factory=list)
    matches: int = 0
    mismatches: int = 0
    gaps: int = 0
    matrix: list[list[int]] | None = None

    @property
    def length(self) -> int:
        return len(self.aligned_a)

    @property
    def identity(self) -> float:
        return self.matches / self.length if self.length else 1.0


def needleman_wunsch(
    a: Sequence,
    b: Sequence,
    match: int = 1,
    mismatch: int = -1,
    gap: int = -1,
    keep_matrix: bool = False,
) -> NWResult:
    """Calcula el alineamiento global óptimo de ``a`` y ``b``."""
    n, m = len(a), len(b)
    F = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        F[i][0] = i * gap
    for j in range(1, m + 1):
        F[0][j] = j * gap

    for i in range(1, n + 1):
        ai = a[i - 1]
        row, up = F[i], F[i - 1]
        for j in range(1, m + 1):
            diag = up[j - 1] + (match if ai == b[j - 1] else mismatch)
            best = diag
            delete = up[j] + gap
            if delete > best:
                best = delete
            insert = row[j - 1] + gap
            if insert > best:
                best = insert
            row[j] = best

    # Traceback: se prefiere la diagonal, luego el hueco en B y luego en A.
    aligned_a: list = []
    aligned_b: list = []
    matches = mismatches = gaps = 0
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            s = match if a[i - 1] == b[j - 1] else mismatch
            if F[i][j] == F[i - 1][j - 1] + s:
                aligned_a.append(a[i - 1])
                aligned_b.append(b[j - 1])
                if s == match and a[i - 1] == b[j - 1]:
                    matches += 1
                else:
                    mismatches += 1
                i, j = i - 1, j - 1
                continue
        if i > 0 and F[i][j] == F[i - 1][j] + gap:
            aligned_a.append(a[i - 1])
            aligned_b.append(GAP)
            gaps += 1
            i -= 1
        else:
            aligned_a.append(GAP)
            aligned_b.append(b[j - 1])
            gaps += 1
            j -= 1
    aligned_a.reverse()
    aligned_b.reverse()
    return NWResult(
        score=F[n][m],
        aligned_a=aligned_a,
        aligned_b=aligned_b,
        matches=matches,
        mismatches=mismatches,
        gaps=gaps,
        matrix=F if keep_matrix else None,
    )


def needleman_wunsch_similarity(a: Sequence, b: Sequence, match: int = 1, mismatch: int = -1, gap: int = -1) -> float:
    """Identidad del alineamiento global óptimo (valor en [0, 1])."""
    return needleman_wunsch(a, b, match, mismatch, gap).identity
