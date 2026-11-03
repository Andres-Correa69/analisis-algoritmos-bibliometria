import { useState } from "react"

import { useIsDark } from "@/components/theme-toggle"
import { inkOn, sequential } from "@/lib/palette"

interface Props {
  labels: string[]
  titles?: string[]
  matrix: number[][]
  /** Rango de la escala (por defecto min/max fuera de la diagonal). */
  domain?: [number, number]
  showValues?: boolean
  digits?: number
  cell?: number
}

export function Heatmap({ labels, titles, matrix, domain, showValues, digits = 2, cell }: Props) {
  const dark = useIsDark()
  const [hover, setHover] = useState<{ r: number; c: number; x: number; y: number } | null>(null)
  const n = labels.length
  const size = cell ?? (n <= 6 ? 64 : n <= 10 ? 44 : 26)
  const values = shouldShow(showValues, n)
  let lo = domain?.[0]
  let hi = domain?.[1]
  if (lo === undefined || hi === undefined) {
    const off: number[] = []
    matrix.forEach((row, i) => row.forEach((v, j) => i !== j && off.push(v)))
    lo = off.length ? Math.min(...off) : 0
    hi = off.length ? Math.max(...off) : 1
    if (hi - lo < 1e-9) hi = lo + 1e-9
  }
  const left = 48
  const top = 8
  const width = left + n * size + 8
  const height = top + n * size + 40

  return (
    <div className="relative w-full overflow-x-auto">
      <svg width={width} height={height} role="img" aria-label="Mapa de calor de similitudes" className="block">
        {matrix.map((row, i) =>
          row.map((v, j) => {
            const t = (v - lo!) / (hi! - lo!)
            const fill = i === j ? "var(--muted)" : sequential(t, dark)
            return (
              <g key={`${i}-${j}`}>
                <rect
                  x={left + j * size + 1}
                  y={top + i * size + 1}
                  width={size - 2}
                  height={size - 2}
                  rx={3}
                  fill={fill}
                  onMouseEnter={(e) => setHover({ r: i, c: j, x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY })}
                  onMouseLeave={() => setHover(null)}
                  className="cursor-crosshair"
                />
                {values && i !== j && (
                  <text
                    x={left + j * size + size / 2}
                    y={top + i * size + size / 2 + 4}
                    textAnchor="middle"
                    fontSize={size >= 60 ? 12 : 10}
                    fill={inkOn(fill)}
                    pointerEvents="none"
                    className="tabular"
                  >
                    {v.toFixed(digits)}
                  </text>
                )}
              </g>
            )
          }),
        )}
        {labels.map((l, i) => (
          <text key={`r${i}`} x={left - 6} y={top + i * size + size / 2 + 4} textAnchor="end" fontSize={11} className="fill-muted-foreground font-mono">
            {l}
          </text>
        ))}
        {labels.map((l, j) => (
          <text
            key={`c${j}`}
            x={left + j * size + size / 2}
            y={top + n * size + 14}
            textAnchor="end"
            fontSize={11}
            transform={`rotate(-45 ${left + j * size + size / 2} ${top + n * size + 14})`}
            className="fill-muted-foreground font-mono"
          >
            {l}
          </text>
        ))}
      </svg>
      <ScaleLegend lo={lo} hi={hi} dark={dark} />
      {hover && hover.r !== hover.c && (
        <div
          className="pointer-events-none absolute z-10 max-w-72 rounded-md border bg-popover px-3 py-2 text-xs shadow-md"
          style={{ left: Math.min(hover.x + 14, width - 200), top: hover.y + 14 }}
        >
          <p className="text-base font-semibold tabular">{matrix[hover.r][hover.c].toFixed(4)}</p>
          <p className="text-muted-foreground">
            {labels[hover.r]} vs {labels[hover.c]}
          </p>
          {titles && (
            <p className="mt-1 text-muted-foreground">
              {titles[hover.r]} <br />— {titles[hover.c]}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function shouldShow(flag: boolean | undefined, n: number) {
  return flag ?? n <= 8
}

function ScaleLegend({ lo, hi, dark }: { lo: number; hi: number; dark: boolean }) {
  const stops = Array.from({ length: 12 }, (_, i) => sequential(i / 11, dark))
  return (
    <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
      <span className="tabular">{lo.toFixed(2)}</span>
      <div className="h-2 w-40 rounded-full" style={{ background: `linear-gradient(90deg, ${stops.join(",")})` }} />
      <span className="tabular">{hi.toFixed(2)}</span>
      <span>· menor → mayor similitud</span>
    </div>
  )
}
