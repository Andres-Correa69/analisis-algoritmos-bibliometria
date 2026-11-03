"""
Agrupamiento jerárquico aglomerativo implementado desde cero.

Algoritmo genérico (Johnson, 1967):

1. Cada documento es un clúster unitario; se parte de la matriz de distancias D.
2. Repetir n-1 veces:
   a. Buscar el par de clústeres activos (i, j) con distancia mínima.
   b. Fusionarlos en un clúster nuevo k = i ∪ j y registrar la altura d(i, j).
   c. Actualizar la distancia de k a todo clúster activo h con la fórmula de
      Lance-Williams del criterio elegido:

      single   : d(h, k) = min(d(h,i), d(h,j))
      complete : d(h, k) = max(d(h,i), d(h,j))
      average  : d(h, k) = (n_i·d(h,i) + n_j·d(h,j)) / (n_i + n_j)      (UPGMA)
      ward     : d(h, k) = sqrt( ((n_h+n_i)·d(h,i)² + (n_h+n_j)·d(h,j)²
                                  - n_h·d(i,j)²) / (n_h + n_i + n_j) )

El resultado se devuelve en el mismo formato de "matriz de enlace" que usa
SciPy (filas ``[id_1, id_2, distancia, tamaño]``, con ids n, n+1, ... para los
clústeres nuevos), lo que permite contrastar la implementación con
``scipy.cluster.hierarchy.linkage`` en las pruebas (sin usarla en la aplicación).

Complejidad: la búsqueda del par mínimo cuesta O(k²) con k clústeres activos,
y la actualización O(k); en total Σ_{k=2}^{n} O(k²) = O(n³) en tiempo y O(n²)
en memoria. Para n = 20 abstracts son ~2 660 comparaciones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

METHODS = ("single", "complete", "average", "ward")

METHOD_INFO = {
    "single": {
        "label": "Single linkage (enlace simple)",
        "formula": "d(A,B) = min_{a∈A, b∈B} d(a,b)",
        "lance_williams": "α_i = α_j = 1/2, β = 0, γ = -1/2",
    },
    "complete": {
        "label": "Complete linkage (enlace completo)",
        "formula": "d(A,B) = max_{a∈A, b∈B} d(a,b)",
        "lance_williams": "α_i = α_j = 1/2, β = 0, γ = +1/2",
    },
    "average": {
        "label": "Average linkage (UPGMA)",
        "formula": "d(A,B) = (1/(|A||B|)) Σ_{a∈A} Σ_{b∈B} d(a,b)",
        "lance_williams": "α_i = n_i/(n_i+n_j), α_j = n_j/(n_i+n_j), β = γ = 0",
    },
    "ward": {
        "label": "Ward (mínima varianza)",
        "formula": "Δ(A,B) = (|A||B|/(|A|+|B|)) ||c_A - c_B||²",
        "lance_williams": "α_i = (n_h+n_i)/N, α_j = (n_h+n_j)/N, β = -n_h/N, γ = 0",
    },
}


@dataclass(frozen=True)
class Merge:
    step: int
    left: int
    right: int
    distance: float
    size: int

    def as_row(self) -> list[float]:
        return [float(self.left), float(self.right), float(self.distance), float(self.size)]


def _validate(D: list[list[float]]) -> int:
    n = len(D)
    if n < 2:
        raise ValueError("Se requieren al menos 2 elementos")
    for i in range(n):
        if len(D[i]) != n:
            raise ValueError("La matriz de distancias debe ser cuadrada")
        for j in range(i + 1, n):
            if abs(D[i][j] - D[j][i]) > 1e-9:
                raise ValueError("La matriz de distancias debe ser simétrica")
            if D[i][j] < -1e-12:
                raise ValueError("Las distancias deben ser no negativas")
    return n


def lance_williams(method: str, d_hi: float, d_hj: float, d_ij: float, n_h: int, n_i: int, n_j: int) -> float:
    """Distancia del clúster h al clúster fusionado i ∪ j."""
    if method == "single":
        return d_hi if d_hi < d_hj else d_hj
    if method == "complete":
        return d_hi if d_hi > d_hj else d_hj
    if method == "average":
        return (n_i * d_hi + n_j * d_hj) / (n_i + n_j)
    if method == "ward":
        total = n_h + n_i + n_j
        value = ((n_h + n_i) * d_hi * d_hi + (n_h + n_j) * d_hj * d_hj - n_h * d_ij * d_ij) / total
        return math.sqrt(value if value > 0 else 0.0)
    raise ValueError(f"Criterio de enlace desconocido: {method}")


def agglomerative_clustering(D: list[list[float]], method: str = "average", trace: bool = False) -> dict:
    """Ejecuta el agrupamiento y devuelve fusiones (y opcionalmente la traza).

    Retorna ``{"merges": [Merge, ...], "trace": [...]}``. La traza registra,
    para cada iteración, el par fusionado y las distancias actualizadas.
    """
    if method not in METHODS:
        raise ValueError(f"Criterio de enlace desconocido: {method}")
    n = _validate(D)

    size: dict[int, int] = {i: 1 for i in range(n)}
    dist: dict[int, dict[int, float]] = {i: {} for i in range(n)}
    for i in range(n):
        for j in range(n):
            if i != j:
                dist[i][j] = float(D[i][j])

    merges: list[Merge] = []
    steps: list[dict] = []
    next_id = n
    comparisons = 0
    for step in range(1, n):
        active = sorted(size)
        # (a) par más cercano: O(k²)
        best_d, best_i, best_j = math.inf, -1, -1
        for x in range(len(active)):
            i = active[x]
            row = dist[i]
            for y in range(x + 1, len(active)):
                j = active[y]
                comparisons += 1
                if row[j] < best_d:
                    best_d, best_i, best_j = row[j], i, j
        i, j = best_i, best_j
        n_i, n_j = size[i], size[j]
        k = next_id
        next_id += 1

        # (b)-(c) fusión y actualización Lance-Williams: O(k)
        dist[k] = {}
        updates = {}
        for h in active:
            if h == i or h == j:
                continue
            d_new = lance_williams(method, dist[h][i], dist[h][j], best_d, size[h], n_i, n_j)
            dist[k][h] = d_new
            dist[h][k] = d_new
            del dist[h][i]
            del dist[h][j]
            updates[h] = d_new
        del dist[i]
        del dist[j]
        del size[i]
        del size[j]
        size[k] = n_i + n_j
        merges.append(Merge(step=step, left=min(i, j), right=max(i, j), distance=best_d, size=n_i + n_j))
        if trace:
            steps.append(
                {
                    "step": step,
                    "merged": [min(i, j), max(i, j)],
                    "new_cluster": k,
                    "distance": best_d,
                    "size": n_i + n_j,
                    "active_before": len(active),
                    "updated_distances": updates,
                }
            )
    return {"merges": merges, "trace": steps, "pair_comparisons": comparisons}


def linkage_matrix(merges: list[Merge]) -> list[list[float]]:
    return [m.as_row() for m in merges]


def cluster_members(merges: list[Merge], n: int) -> dict[int, list[int]]:
    """Hojas (documentos) contenidas en cada clúster, incluidos los internos."""
    members: dict[int, list[int]] = {i: [i] for i in range(n)}
    for idx, m in enumerate(merges):
        members[n + idx] = members[m.left] + members[m.right]
    return members
