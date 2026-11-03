"""
Coeficiente de Jaccard sobre conjuntos de términos.

    J(A, B) = |T(A) ∩ T(B)| / |T(A) ∪ T(B)|

donde T(X) es el conjunto de raíces (sin repetición) del texto X.
Los conjuntos se construyen con una tabla hash explícita (diccionario) y la
intersección se cuenta recorriendo el conjunto más pequeño.

Complejidad: O(n + m) esperado (inserciones y búsquedas O(1) promedio).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class JaccardResult:
    intersection: list[str]
    only_a: list[str]
    only_b: list[str]
    union_size: int

    @property
    def similarity(self) -> float:
        if self.union_size == 0:
            return 1.0
        return len(self.intersection) / self.union_size


def _hash_set(items: Iterable[str]) -> dict[str, bool]:
    table: dict[str, bool] = {}
    for it in items:
        table[it] = True
    return table


def jaccard(a: Iterable[str], b: Iterable[str]) -> JaccardResult:
    set_a = _hash_set(a)
    set_b = _hash_set(b)
    small, large = (set_a, set_b) if len(set_a) <= len(set_b) else (set_b, set_a)
    intersection: list[str] = []
    for term in small:
        if term in large:
            intersection.append(term)
    only_a = [t for t in set_a if t not in set_b]
    only_b = [t for t in set_b if t not in set_a]
    union_size = len(set_a) + len(set_b) - len(intersection)
    intersection.sort()
    only_a.sort()
    only_b.sort()
    return JaccardResult(intersection=intersection, only_a=only_a, only_b=only_b, union_size=union_size)


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    return jaccard(a, b).similarity
