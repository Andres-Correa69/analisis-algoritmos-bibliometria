"""
Distancia de edición de Levenshtein (programación dinámica).

La distancia d(A, B) es el número mínimo de inserciones, eliminaciones y
sustituciones para transformar A en B. Recurrencia (Wagner-Fischer, 1974):

    D[i][0] = i,  D[0][j] = j
    D[i][j] = min( D[i-1][j] + 1,                       # eliminación
                   D[i][j-1] + 1,                       # inserción
                   D[i-1][j-1] + [a_i != b_j] )         # sustitución / coincidencia

Similitud normalizada:  sim(A, B) = 1 - d(A, B) / max(|A|, |B|)

Las funciones aceptan cualquier secuencia indexable con ``==``: un ``str``
(comparación por caracteres) o una ``list[str]`` (comparación por palabras).

Complejidad: tiempo O(n·m); memoria O(min(n, m)) para la distancia
(dos filas) y O(n·m) cuando se requiere la matriz completa o el alineamiento.
"""

from __future__ import annotations

from typing import Sequence


def levenshtein_distance(a: Sequence, b: Sequence) -> int:
    """Distancia de Levenshtein usando sólo dos filas de la matriz."""
    n, m = len(a), len(b)
    if n < m:  # la fila se construye sobre la secuencia más corta
        a, b, n, m = b, a, m, n
    if m == 0:
        return n
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        ai = a[i - 1]
        for j in range(1, m + 1):
            best = prev[j - 1] if ai == b[j - 1] else prev[j - 1] + 1  # sustitución/coincidencia
            deletion = prev[j] + 1
            if deletion < best:
                best = deletion
            insertion = cur[j - 1] + 1
            if insertion < best:
                best = insertion
            cur[j] = best
        prev = cur
    return prev[m]


def levenshtein_similarity(a: Sequence, b: Sequence) -> float:
    """Similitud normalizada en [0, 1]: 1 - d / max(|A|, |B|)."""
    longest = len(a) if len(a) > len(b) else len(b)
    if longest == 0:
        return 1.0
    return 1.0 - levenshtein_distance(a, b) / longest


def levenshtein_matrix(a: Sequence, b: Sequence) -> list[list[int]]:
    """Matriz completa D de tamaño (n+1) x (m+1) (para demostraciones)."""
    n, m = len(a), len(b)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = i
    for j in range(m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            best = D[i - 1][j - 1] + cost
            if D[i - 1][j] + 1 < best:
                best = D[i - 1][j] + 1
            if D[i][j - 1] + 1 < best:
                best = D[i][j - 1] + 1
            D[i][j] = best
    return D


def levenshtein_alignment(a: Sequence, b: Sequence, D: list[list[int]] | None = None) -> list[dict]:
    """Reconstruye (traceback) una secuencia óptima de operaciones de edición.

    Devuelve una lista de pasos ``{"op", "a", "b", "i", "j"}`` donde ``op`` es
    ``match``, ``substitute``, ``delete`` o ``insert`` e ``(i, j)`` es la celda
    de la matriz alcanzada tras la operación.
    """
    if D is None:
        D = levenshtein_matrix(a, b)
    i, j = len(a), len(b)
    steps: list[dict] = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1] and D[i][j] == D[i - 1][j - 1]:
            steps.append({"op": "match", "a": a[i - 1], "b": b[j - 1], "i": i, "j": j})
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + 1:
            steps.append({"op": "substitute", "a": a[i - 1], "b": b[j - 1], "i": i, "j": j})
            i, j = i - 1, j - 1
        elif i > 0 and D[i][j] == D[i - 1][j] + 1:
            steps.append({"op": "delete", "a": a[i - 1], "b": None, "i": i, "j": j})
            i -= 1
        else:
            steps.append({"op": "insert", "a": None, "b": b[j - 1], "i": i, "j": j})
            j -= 1
    steps.reverse()
    return steps
