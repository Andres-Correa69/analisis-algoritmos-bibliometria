import { cn } from "@/lib/utils"

interface Props {
  rows: string[] // tokens de A (filas)
  cols: string[] // tokens de B (columnas)
  matrix: number[][]
  path?: [number, number][]
  caption?: string
}

/** Matriz de programación dinámica con la ruta óptima resaltada. */
export function DpMatrix({ rows, cols, matrix, path = [], caption }: Props) {
  const onPath = new Set(path.map(([i, j]) => `${i},${j}`))
  onPath.add("0,0")
  const last = `${rows.length},${cols.length}`
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-max border-collapse text-xs tabular">
        {caption && <caption className="caption-bottom p-2 text-left text-muted-foreground">{caption}</caption>}
        <thead>
          <tr>
            <th className="sticky left-0 bg-muted px-2 py-1.5" />
            <th className="bg-muted px-2 py-1.5 font-mono font-normal text-muted-foreground">ε</th>
            {cols.map((c, j) => (
              <th key={j} className="bg-muted px-2 py-1.5 font-mono font-medium" title={c}>
                {truncate(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <th className="sticky left-0 bg-muted px-2 py-1.5 text-left font-mono font-medium" title={i === 0 ? "ε" : rows[i - 1]}>
                {i === 0 ? <span className="font-normal text-muted-foreground">ε</span> : truncate(rows[i - 1])}
              </th>
              {row.map((v, j) => {
                const key = `${i},${j}`
                const isPath = onPath.has(key)
                const same = i > 0 && j > 0 && rows[i - 1] === cols[j - 1]
                return (
                  <td
                    key={j}
                    className={cn(
                      "min-w-9 border border-border/60 px-2 py-1.5 text-center",
                      isPath && "bg-[var(--series-1)]/20 font-semibold",
                      key === last && "ring-2 ring-[var(--series-1)] ring-inset",
                      same && !isPath && "bg-[var(--match-bg)]/50",
                    )}
                  >
                    {v}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function truncate(s: string, n = 9) {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s
}
