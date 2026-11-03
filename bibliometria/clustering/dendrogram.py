"""
Construcción y dibujo de dendrogramas (sin ``scipy.cluster.hierarchy.dendrogram``).

``dendrogram_layout`` calcula la geometría: el orden de las hojas se obtiene con
un recorrido en profundidad (primero el hijo izquierdo) desde la raíz; cada hoja
se ubica en x = 5 + 10·i y cada nodo interno en el punto medio de sus hijos, a
una altura igual a la distancia de fusión. Cada fusión se dibuja como una "U"
invertida con 4 puntos (convención ``icoord``/``dcoord``).

``render_dendrogram`` dibuja esa geometría con líneas de matplotlib y colorea
los grupos que resultan de cortar el árbol en k grupos.
"""

from __future__ import annotations

from pathlib import Path

from .agglomerative import Merge
from .evaluation import cut_tree

PALETTE = ["#2563eb", "#16a34a", "#ea580c", "#9333ea", "#0891b2", "#db2777", "#ca8a04", "#4f46e5", "#059669", "#dc2626"]
ABOVE_CUT = "#6b7280"


def leaf_order(merges: list[Merge], n: int) -> list[int]:
    if n == 1:
        return [0]
    root = n + len(merges) - 1
    children = {n + k: (m.left, m.right) for k, m in enumerate(merges)}
    order: list[int] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node < n:
            order.append(node)
        else:
            left, right = children[node]
            stack.append(right)  # se apila primero el derecho para visitar antes el izquierdo
            stack.append(left)
    return order


def cut_threshold(merges: list[Merge], k: int) -> float:
    """Altura de corte que produce k grupos (punto medio entre fusiones)."""
    n = len(merges) + 1
    if k <= 1:
        return merges[-1].distance * 1.05
    if k >= n:
        return 0.0
    lower = merges[n - k - 1].distance
    upper = merges[n - k].distance
    return (lower + upper) / 2


def dendrogram_layout(merges: list[Merge], n: int, labels: list[str], k: int | None = None) -> dict:
    order = leaf_order(merges, n)
    x: dict[int, float] = {leaf: 5.0 + 10.0 * pos for pos, leaf in enumerate(order)}
    y: dict[int, float] = {leaf: 0.0 for leaf in range(n)}
    groups = cut_tree(merges, n, k) if k else [0] * n
    node_group: dict[int, int] = {leaf: groups[leaf] for leaf in range(n)}
    threshold = cut_threshold(merges, k) if k else None

    links = []
    for idx, m in enumerate(merges):
        node = n + idx
        xl, xr = x[m.left], x[m.right]
        x[node] = (xl + xr) / 2
        y[node] = m.distance
        same = node_group.get(m.left) is not None and node_group.get(m.left) == node_group.get(m.right)
        below = threshold is not None and m.distance <= threshold
        group = node_group[m.left] if (same and below) else None
        node_group[node] = group if group is not None else -1
        links.append(
            {
                "id": node,
                "left": m.left,
                "right": m.right,
                "height": m.distance,
                "size": m.size,
                "icoord": [xl, xl, xr, xr],
                "dcoord": [y[m.left], m.distance, m.distance, y[m.right]],
                "group": group,
            }
        )
    return {
        "n": n,
        "order": order,
        "labels": [labels[i] for i in order],
        "leaf_groups": [groups[i] for i in order],
        "links": links,
        "threshold": threshold,
        "k": k,
        "max_height": merges[-1].distance if merges else 0.0,
    }


def render_dendrogram(layout: dict, path: Path, title: str, ylabel: str = "Distancia") -> Path:
    """Dibuja el dendrograma con matplotlib (sólo primitivas de línea y texto)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = layout["n"]
    fig, ax = plt.subplots(figsize=(max(9.0, 0.55 * n), 6.2), dpi=180)
    for link in layout["links"]:
        g = link["group"]
        color = PALETTE[g % len(PALETTE)] if g is not None else ABOVE_CUT
        ax.plot(link["icoord"], link["dcoord"], color=color, linewidth=1.6, solid_capstyle="round")
    if layout["threshold"] is not None:
        ax.axhline(layout["threshold"], color="#ef4444", linestyle="--", linewidth=1.0, alpha=0.8)
        ax.text(
            10 * n + 2,
            layout["threshold"],
            f" corte k={layout['k']}",
            color="#ef4444",
            fontsize=8,
            va="bottom",
            ha="right",
        )
    ticks = [5 + 10 * i for i in range(n)]
    ax.set_xticks(ticks)
    ax.set_xticklabels(layout["labels"], rotation=90, fontsize=8, color="#111827")
    # La identidad del grupo se marca con un punto de color en cada hoja (no con el color del texto).
    leaf_colors = [PALETTE[g % len(PALETTE)] if layout["k"] else ABOVE_CUT for g in layout["leaf_groups"]]
    ax.scatter(ticks, [0] * n, s=26, c=leaf_colors, edgecolors="white", linewidths=1.2, zorder=5, clip_on=False)
    ax.set_xlim(0, 10 * n)
    ax.set_ylim(0, layout["max_height"] * 1.08)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11, loc="left")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path
