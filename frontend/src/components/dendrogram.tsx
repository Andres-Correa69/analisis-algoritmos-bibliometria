import { useMemo, useState } from "react"

import { SERIES } from "@/lib/palette"
import type { MethodResult } from "@/lib/types"

interface Props {
  result: MethodResult
  k: number
  titles: Record<string, string> // etiqueta de hoja -> título completo
  height?: number
}

/** Corta el árbol en k grupos aplicando las primeras n-k fusiones (unión-búsqueda). */
export function cutGroups(result: MethodResult, k: number) {
  const n = result.dendrogram.n
  const parent = Array.from({ length: 2 * n }, (_, i) => i)
  const find = (x: number): number => {
    while (parent[x] !== x) {
      parent[x] = parent[parent[x]]
      x = parent[x]
    }
    return x
  }
  for (let idx = 0; idx < n - k; idx++) {
    const m = result.merges[idx]
    parent[find(m.left)] = n + idx
    parent[find(m.right)] = n + idx
  }
  const remap = new Map<number, number>()
  const leafGroup: number[] = []
  for (let leaf = 0; leaf < n; leaf++) {
    const root = find(leaf)
    if (!remap.has(root)) remap.set(root, remap.size)
    leafGroup.push(remap.get(root)!)
  }
  const heights = result.merges.map((m) => m.distance)
  const threshold = k <= 1 ? heights[heights.length - 1] * 1.04 : k >= n ? 0 : (heights[n - k - 1] + heights[n - k]) / 2
  return { leafGroup, threshold }
}

export function Dendrogram({ result, k, titles, height = 470 }: Props) {
  const [hoverLeaf, setHoverLeaf] = useState<number | null>(null)
  const d = result.dendrogram
  const n = d.n
  const { leafGroup, threshold } = useMemo(() => cutGroups(result, k), [result, k])

  // Grupo de cada nodo interno (sólo si está por debajo del corte).
  const nodeGroup = useMemo(() => {
    const g = new Map<number, number>()
    for (let leaf = 0; leaf < n; leaf++) g.set(leaf, leafGroup[leaf])
    result.merges.forEach((m, idx) => {
      const node = n + idx
      const gl = g.get(m.left)
      const same = gl !== undefined && gl >= 0 && gl === g.get(m.right)
      g.set(node, same && idx < n - k ? gl! : -1)
    })
    return g
  }, [result, leafGroup, n, k])

  const labelBand = 150
  const padL = 92
  const padT = 12
  const plotH = height - labelBand - padT
  const width = Math.max(760, n * 46 + padL + 24)
  const maxH = d.max_height * 1.06 || 1
  const sx = (x: number) => padL + ((x - 5) / (10 * n - 10)) * (width - padL - 24) + 4
  const sy = (y: number) => padT + plotH - (y / maxH) * plotH
  const ticks = niceTicks(maxH, 5)
  const tickX = padL - 8
  const color = (g: number | undefined) => (g === undefined || g < 0 ? "var(--muted-ink)" : SERIES[g % SERIES.length])

  return (
    <div className="relative w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ minWidth: 640, maxHeight: height + 80 }}
        role="img"
        aria-label={`Dendrograma ${result.label}`}
        className="block"
      >
        {ticks.map((t) => (
          <g key={t}>
            <line x1={padL} x2={width - 8} y1={sy(t)} y2={sy(t)} stroke="var(--grid-line)" strokeWidth={1} />
            <text x={tickX} y={sy(t) + 4} textAnchor="end" fontSize={10} className="fill-muted-foreground tabular">
              {t.toFixed(2)}
            </text>
          </g>
        ))}
        {d.links.map((link, idx) => {
          const node = link.id
          const g = nodeGroup.get(node)
          const pts = link.icoord.map((x, i) => `${sx(x)},${sy(link.dcoord[i])}`).join(" ")
          return (
            <polyline
              key={idx}
              points={pts}
              fill="none"
              stroke={color(g)}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            >
              <title>{`Fusión a distancia ${link.height.toFixed(4)} (${link.size} documentos)`}</title>
            </polyline>
          )
        })}
        {k > 1 && k < n && (
          <g>
            <line x1={padL} x2={width - 8} y1={sy(threshold)} y2={sy(threshold)} stroke="var(--series-8)" strokeWidth={1} />
            <text x={width - 10} y={sy(threshold) - 4} textAnchor="end" fontSize={10} className="fill-muted-foreground">
              corte · k = {k}
            </text>
          </g>
        )}
        {d.order.map((leaf, pos) => {
          const x = sx(5 + 10 * pos)
          const label = d.labels[pos]
          return (
            <g
              key={leaf}
              onMouseEnter={() => setHoverLeaf(pos)}
              onMouseLeave={() => setHoverLeaf(null)}
              className="cursor-default"
            >
              <circle cx={x} cy={sy(0)} r={4} fill={color(leafGroup[leaf])} stroke="var(--background)" strokeWidth={2} />
              <rect x={x - 10} y={sy(0) + 4} width={20} height={labelBand - 10} fill="transparent" />
              <text
                x={x}
                y={sy(0) + 12}
                fontSize={11}
                textAnchor="end"
                transform={`rotate(-60 ${x} ${sy(0) + 12})`}
                className="fill-foreground font-mono"
              >
                {label}
              </text>
            </g>
          )
        })}
      </svg>
      {hoverLeaf !== null && (
        <div className="pointer-events-none absolute top-2 right-2 max-w-sm rounded-md border bg-popover px-3 py-2 text-xs shadow-md">
          <p className="font-mono font-medium">{d.labels[hoverLeaf]}</p>
          <p className="text-muted-foreground">{titles[d.labels[hoverLeaf]]}</p>
        </div>
      )}
    </div>
  )
}

function niceTicks(max: number, count: number) {
  const raw = max / count
  const pow = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= raw) ?? raw
  const out: number[] = []
  for (let t = 0; t <= max + 1e-9; t += step) out.push(Number(t.toFixed(6)))
  return out
}
