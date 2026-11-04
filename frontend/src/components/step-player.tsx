import { ChevronFirst, ChevronLast, ChevronLeft, ChevronRight, Pause, Play } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { Tex } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import type { TraceEvent, TraceResponse } from "@/lib/types"
import { cn } from "@/lib/utils"

type Shift = Extract<TraceEvent, { type: "shift" }>
type Window = Extract<TraceEvent, { type: "window" }>

interface Attempt {
  alignment: number
  compares: { i: number; j: number; match: boolean }[]
  shift?: Shift
  window?: Window
  found?: boolean
  spurious?: boolean
}

export function buildAttempts(trace: TraceEvent[]): Attempt[] {
  const out: Attempt[] = []
  let cur: Attempt | null = null
  const close = () => {
    if (cur) out.push(cur)
    cur = null
  }
  for (const e of trace) {
    if (e.type === "window") {
      close()
      cur = { alignment: e.alignment, compares: [], window: e }
    } else if (e.type === "compare") {
      if (cur && cur.alignment !== e.alignment && !cur.window) close()
      if (!cur) cur = { alignment: e.alignment, compares: [] }
      cur.compares.push({ i: e.i, j: e.j, match: e.match })
    } else if (e.type === "found") {
      if (!cur) cur = { alignment: e.position, compares: [] }
      cur.found = true
    } else if (e.type === "spurious") {
      if (cur) cur.spurious = true
    } else if (e.type === "shift") {
      if (!cur) cur = { alignment: e.from_alignment, compares: [] }
      cur.shift = e
      close()
    }
  }
  close()
  return out
}

const CELL = 20

export function StepPlayer({ data }: { data: TraceResponse }) {
  const attempts = useMemo(() => buildAttempts(data.trace), [data])
  const [idx, setIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const m = data.pattern.length
  const text = data.text

  useEffect(() => {
    if (!playing) return
    const t = setInterval(() => setIdx((i) => (i + 1 < attempts.length ? i + 1 : (setPlaying(false), i))), 650)
    return () => clearInterval(t)
  }, [playing, attempts.length])

  if (attempts.length === 0) return <p className="text-sm text-muted-foreground">No hay pasos para mostrar.</p>
  const a = attempts[Math.min(idx, attempts.length - 1)]
  const start = Math.max(0, Math.min(a.alignment - 24, text.length - 60))
  const end = Math.min(text.length, Math.max(start + 60, a.alignment + m + 24))
  const cmp = new Map(a.compares.map((c) => [c.i, c.match]))
  const isMatchWindow = a.found
  const foundBefore = new Set(attempts.slice(0, idx + 1).filter((x) => x.found).map((x) => x.alignment))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="icon" variant="outline" aria-label="Primer paso" onClick={() => setIdx(0)}>
          <ChevronFirst className="size-4" />
        </Button>
        <Button size="icon" variant="outline" aria-label="Paso anterior" onClick={() => setIdx((i) => Math.max(0, i - 1))}>
          <ChevronLeft className="size-4" />
        </Button>
        <Button size="icon" variant={playing ? "secondary" : "default"} aria-label={playing ? "Pausar" : "Reproducir"} onClick={() => setPlaying((p) => !p)}>
          {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
        </Button>
        <Button size="icon" variant="outline" aria-label="Paso siguiente" onClick={() => setIdx((i) => Math.min(attempts.length - 1, i + 1))}>
          <ChevronRight className="size-4" />
        </Button>
        <Button size="icon" variant="outline" aria-label="Último paso" onClick={() => setIdx(attempts.length - 1)}>
          <ChevronLast className="size-4" />
        </Button>
        <span className="ml-2 text-sm tabular text-muted-foreground" data-testid="step-counter">
          Paso {idx + 1} de {attempts.length} · alineación s = {a.alignment}
        </span>
        {data.trace_truncated && <Badge variant="outline">traza truncada</Badge>}
      </div>
      <Slider value={[idx]} min={0} max={attempts.length - 1} step={1} onValueChange={([v]) => setIdx(v)} aria-label="Paso" />

      <div className="overflow-x-auto rounded-lg border bg-background p-3">
        <div className="relative font-mono text-sm" style={{ width: (end - start) * CELL + 8 }}>
          <div className="flex">
            {Array.from({ length: end - start }, (_, k) => start + k).map((pos) => (
              <span key={pos} className="text-center text-[9px] text-muted-foreground" style={{ width: CELL }}>
                {pos % 5 === 0 ? pos : ""}
              </span>
            ))}
          </div>
          <div className="flex">
            {Array.from({ length: end - start }, (_, k) => start + k).map((pos) => {
              const inWindow = pos >= a.alignment && pos < a.alignment + m
              const compared = cmp.get(pos)
              return (
                <span
                  key={pos}
                  className={cn(
                    "flex h-7 items-center justify-center border-y border-l border-border/50 last:border-r",
                    inWindow && "bg-muted",
                    compared === true && "bg-[var(--match-bg)] text-[var(--match-fg)] font-semibold",
                    compared === false && "bg-[var(--miss-bg)] text-[var(--miss-fg)] font-semibold",
                    isMatchWindow && inWindow && "bg-[var(--match-bg)] text-[var(--match-fg)]",
                    !inWindow && [...foundBefore].some((f) => pos >= f && pos < f + m) && "underline decoration-2 underline-offset-4",
                  )}
                  style={{ width: CELL }}
                >
                  {text[pos] === " " ? "·" : text[pos]}
                </span>
              )
            })}
          </div>
          <div className="mt-1 flex" style={{ paddingLeft: (a.alignment - start) * CELL }}>
            {data.pattern.split("").map((ch, j) => {
              const c = a.compares.find((x) => x.j === j)
              return (
                <span
                  key={j}
                  className={cn(
                    "flex h-7 items-center justify-center rounded-sm border border-primary/50 bg-primary/10",
                    c?.match === true && "bg-[var(--match-bg)] text-[var(--match-fg)]",
                    c?.match === false && "bg-[var(--miss-bg)] text-[var(--miss-fg)]",
                  )}
                  style={{ width: CELL }}
                >
                  {ch === " " ? "·" : ch}
                </span>
              )
            })}
          </div>
        </div>
      </div>

      <StepExplanation data={data} attempt={a} />
    </div>
  )
}

function StepExplanation({ data, attempt }: { data: TraceResponse; attempt: Attempt }) {
  const a = attempt
  const items: React.ReactNode[] = []
  if (a.window) {
    const w = a.window
    items.push(
      <p key="h">
        <Tex>{`t_{${w.alignment}} = ${w.window_hash} \\quad H(P) = ${w.pattern_hash}`}</Tex>{" "}
        {w.hash_match ? (
          <Badge className="ml-1">hashes iguales → verificar</Badge>
        ) : (
          <Badge variant="outline" className="ml-1">
            hashes distintos → descartar sin comparar
          </Badge>
        )}
      </p>,
    )
    if (w.verified === true) items.push(<p key="v">Verificación carácter a carácter exitosa: ocurrencia en s = {w.alignment}.</p>)
    if (w.verified === false) items.push(<p key="v">Verificación fallida: <strong>colisión (coincidencia espuria)</strong>.</p>)
    if (w.next_hash !== null && w.out_char !== null && w.in_char !== null) {
      const d = data.extra.base
      const q = data.extra.modulus
      items.push(
        <Tex key="r" block>
          {`t_{${w.alignment + 1}} = (${d}\\,(${w.window_hash} - ${w.out_char.charCodeAt(0)}\\cdot ${data.tables.h}) + ${w.in_char.charCodeAt(0)}) \\bmod ${q} = ${w.next_hash}`}
        </Tex>,
      )
    }
  } else {
    const matches = a.compares.filter((c) => c.match).length
    items.push(
      <p key="c">
        {a.compares.length} comparaciones en este intento ({matches} coincidencias
        {a.compares.length - matches ? `, ${a.compares.length - matches} discrepancia` : ""}).
        {a.found && <strong> Ocurrencia encontrada en s = {a.alignment}.</strong>}
      </p>,
    )
    if (a.shift) {
      const s = a.shift
      if (data.algorithm === "boyer_moore") {
        items.push(
          <p key="s">
            {s.bad_char !== undefined ? (
              <>
                Carácter malo <code className="rounded bg-muted px-1">{s.bad_char === " " ? "␠" : s.bad_char}</code> en j = {s.mismatch_j}: δ
                <sub>bc</sub> = {s.bc_shift}; sufijo bueno: δ<sub>gs</sub> = {s.gs_shift}.{" "}
              </>
            ) : (
              <>Patrón completo emparejado: se aplica gs[0] = {s.gs_shift}. </>
            )}
            Se desplaza <strong>{s.to_alignment - s.from_alignment}</strong> posiciones por la regla de <em>{s.rule}</em> (s: {s.from_alignment} → {s.to_alignment}).
          </p>,
        )
      } else {
        items.push(
          <p key="s">
            Desplazamiento s: {s.from_alignment} → {s.to_alignment} ({s.reason ?? "avanzar 1"}).
          </p>,
        )
      }
    } else if (data.algorithm === "naive") {
      items.push(<p key="n">La fuerza bruta siempre desplaza el patrón una posición.</p>)
    }
  }
  return <div className="space-y-1.5 rounded-lg bg-muted/50 p-3 text-sm">{items}</div>
}
