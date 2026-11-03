"""
Métricas de evaluación interna del agrupamiento jerárquico.

1. Coeficiente de correlación cofenética (CPCC, Sokal y Rohlf, 1962): correlación
   de Pearson entre las distancias originales d(i,j) y las distancias cofenéticas
   c(i,j) (altura a la que i y j quedan por primera vez en el mismo clúster):

       CPCC = Σ (d - d̄)(c - c̄) / sqrt( Σ (d - d̄)² · Σ (c - c̄)² )

   Mide qué tan fielmente el dendrograma conserva las distancias reales.

2. Coeficiente de silueta (Rousseeuw, 1987), para un corte del árbol en k grupos:

       a(i) = distancia media de i a los demás miembros de su grupo
       b(i) = mínima distancia media de i a los miembros de otro grupo
       s(i) = (b(i) - a(i)) / max(a(i), b(i))        (s(i) = 0 si el grupo es unitario)
       S    = (1/n) Σ s(i)  ∈ [-1, 1]

   Valores altos indican grupos compactos y bien separados.

Complejidad: matriz cofenética O(n²) (cada par se asigna una sola vez), CPCC
O(n²) y silueta O(n²) por cada valor de k.
"""

from __future__ import annotations

import math

from .agglomerative import Merge


def cophenetic_matrix(merges: list[Merge], n: int) -> list[list[float]]:
    members: dict[int, list[int]] = {i: [i] for i in range(n)}
    C = [[0.0] * n for _ in range(n)]
    for idx, m in enumerate(merges):
        left, right = members[m.left], members[m.right]
        for x in left:
            for y in right:
                C[x][y] = C[y][x] = m.distance
        members[n + idx] = left + right
    return C


def _upper(M: list[list[float]]) -> list[float]:
    n = len(M)
    return [M[i][j] for i in range(n) for j in range(i + 1, n)]


def pearson(x: list[float], y: list[float]) -> float:
    k = len(x)
    if k != len(y) or k < 2:
        raise ValueError("Se requieren dos listas de igual longitud (>= 2)")
    mx = sum(x) / k
    my = sum(y) / k
    sxy = sxx = syy = 0.0
    for i in range(k):
        dx, dy = x[i] - mx, y[i] - my
        sxy += dx * dy
        sxx += dx * dx
        syy += dy * dy
    if sxx == 0 or syy == 0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def cophenetic_correlation(D: list[list[float]], merges: list[Merge]) -> float:
    C = cophenetic_matrix(merges, len(D))
    return pearson(_upper(D), _upper(C))


def cut_tree(merges: list[Merge], n: int, k: int) -> list[int]:
    """Etiquetas de grupo al cortar el dendrograma en k grupos (aplica n-k fusiones)."""
    if not 1 <= k <= n:
        raise ValueError("k debe estar entre 1 y n")
    parent = list(range(2 * n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for idx in range(n - k):
        m = merges[idx]
        new = n + idx
        parent[find(m.left)] = new
        parent[find(m.right)] = new
    labels: list[int] = []
    remap: dict[int, int] = {}
    for leaf in range(n):
        root = find(leaf)
        if root not in remap:
            remap[root] = len(remap)
        labels.append(remap[root])
    return labels


def silhouette_samples(D: list[list[float]], labels: list[int]) -> list[float]:
    n = len(D)
    groups: dict[int, list[int]] = {}
    for i, g in enumerate(labels):
        groups.setdefault(g, []).append(i)
    if len(groups) < 2 or len(groups) > n - 1:
        raise ValueError("La silueta requiere 2 <= k <= n-1 grupos")
    scores: list[float] = []
    for i in range(n):
        own = groups[labels[i]]
        if len(own) == 1:
            scores.append(0.0)
            continue
        a = sum(D[i][j] for j in own if j != i) / (len(own) - 1)
        b = math.inf
        for g, members in groups.items():
            if g == labels[i]:
                continue
            avg = sum(D[i][j] for j in members) / len(members)
            if avg < b:
                b = avg
        denom = a if a > b else b
        scores.append(0.0 if denom == 0 else (b - a) / denom)
    return scores


def silhouette_score(D: list[list[float]], labels: list[int]) -> float:
    s = silhouette_samples(D, labels)
    return sum(s) / len(s)
