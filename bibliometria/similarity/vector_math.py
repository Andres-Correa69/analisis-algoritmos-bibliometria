"""
Operaciones vectoriales implementadas con ciclos explícitos.

Vectores densos: ``list[float]``. Vectores dispersos: ``dict[str, float]``.

    cos(u, v) = (u · v) / (||u|| · ||v||)
    d_E(u, v) = sqrt( Σ (u_i - v_i)^2 )
"""

from __future__ import annotations

import math
from typing import Sequence

# ---------------------------------------------------------------------- #
# Vectores densos
# ---------------------------------------------------------------------- #


def dot(u: Sequence[float], v: Sequence[float]) -> float:
    if len(u) != len(v):
        raise ValueError("Los vectores deben tener la misma dimensión")
    total = 0.0
    for i in range(len(u)):
        total += u[i] * v[i]
    return total


def norm(u: Sequence[float]) -> float:
    total = 0.0
    for x in u:
        total += x * x
    return math.sqrt(total)


def cosine(u: Sequence[float], v: Sequence[float]) -> float:
    nu, nv = norm(u), norm(v)
    if nu == 0.0 or nv == 0.0:
        return 0.0
    value = dot(u, v) / (nu * nv)
    # Corrige errores de redondeo fuera de [-1, 1].
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return value


def euclidean(u: Sequence[float], v: Sequence[float]) -> float:
    if len(u) != len(v):
        raise ValueError("Los vectores deben tener la misma dimensión")
    total = 0.0
    for i in range(len(u)):
        diff = u[i] - v[i]
        total += diff * diff
    return math.sqrt(total)


def mean_vector(vectors: list[Sequence[float]]) -> list[float]:
    if not vectors:
        raise ValueError("Se requiere al menos un vector")
    dim = len(vectors[0])
    acc = [0.0] * dim
    for vec in vectors:
        for i in range(dim):
            acc[i] += vec[i]
    k = float(len(vectors))
    return [x / k for x in acc]


def l2_normalize(u: Sequence[float]) -> list[float]:
    n = norm(u)
    if n == 0.0:
        return [0.0 for _ in u]
    return [x / n for x in u]


# ---------------------------------------------------------------------- #
# Vectores dispersos (diccionarios término -> peso)
# ---------------------------------------------------------------------- #


def sparse_dot(u: dict[str, float], v: dict[str, float]) -> float:
    if len(u) > len(v):  # se recorre el vector con menos entradas
        u, v = v, u
    total = 0.0
    for term, weight in u.items():
        other = v.get(term)
        if other is not None:
            total += weight * other
    return total


def sparse_norm(u: dict[str, float]) -> float:
    total = 0.0
    for w in u.values():
        total += w * w
    return math.sqrt(total)


def sparse_cosine(u: dict[str, float], v: dict[str, float]) -> float:
    nu, nv = sparse_norm(u), sparse_norm(v)
    if nu == 0.0 or nv == 0.0:
        return 0.0
    value = sparse_dot(u, v) / (nu * nv)
    return 1.0 if value > 1.0 else value


def sparse_euclidean(u: dict[str, float], v: dict[str, float]) -> float:
    total = 0.0
    for term, w in u.items():
        diff = w - v.get(term, 0.0)
        total += diff * diff
    for term, w in v.items():
        if term not in u:
            total += w * w
    return math.sqrt(total)


def angle_degrees(cos_value: float) -> float:
    """Ángulo θ = arccos(cos) expresado en grados."""
    cos_value = 1.0 if cos_value > 1.0 else (-1.0 if cos_value < -1.0 else cos_value)
    return math.degrees(math.acos(cos_value))
