// Paleta categórica validada (orden fijo, nunca cíclico) y rampa secuencial azul.
// Los valores reales viven en index.css como variables CSS (--series-N) con su
// versión para modo oscuro; aquí sólo se referencian por rol.

export const SERIES = Array.from({ length: 8 }, (_, i) => `var(--series-${i + 1})`)

/** Color fijo por entidad: el color sigue al algoritmo, no a su posición. */
export const ALGORITHM_COLOR: Record<string, string> = {
  levenshtein: SERIES[0],
  needleman_wunsch: SERIES[1],
  jaccard: SERIES[2],
  tfidf_cosine: SERIES[3],
  glove_cosine: SERIES[4],
  sbert_cosine: SERIES[5],
  kmp: SERIES[0],
  boyer_moore: SERIES[1],
  rabin_karp: SERIES[2],
  naive: "var(--muted-ink)",
  single: SERIES[0],
  complete: SERIES[1],
  average: SERIES[2],
  ward: SERIES[6],
}

const BLUE_RAMP = [
  "#cde2fb",
  "#b7d3f6",
  "#9ec5f4",
  "#86b6ef",
  "#6da7ec",
  "#5598e7",
  "#3987e5",
  "#2a78d6",
  "#256abf",
  "#1c5cab",
  "#184f95",
  "#104281",
  "#0d366b",
]

function hexToRgb(hex: string): [number, number, number] {
  const v = parseInt(hex.slice(1), 16)
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255]
}

/** Color secuencial para t ∈ [0, 1]. En modo oscuro "más" es más claro. */
export function sequential(t: number, dark: boolean): string {
  const x = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0))
  const pos = (dark ? 1 - x : x) * (BLUE_RAMP.length - 1)
  const lo = Math.floor(pos)
  const hi = Math.min(BLUE_RAMP.length - 1, lo + 1)
  const f = pos - lo
  const [r1, g1, b1] = hexToRgb(BLUE_RAMP[lo])
  const [r2, g2, b2] = hexToRgb(BLUE_RAMP[hi])
  const mix = (a: number, b: number) => Math.round(a + (b - a) * f)
  return `rgb(${mix(r1, r2)}, ${mix(g1, g2)}, ${mix(b1, b2)})`
}

/** Tinta legible (blanca o negra) sobre un color de relleno rgb(...). */
export function inkOn(fill: string): string {
  const m = fill.match(/\d+/g)
  if (!m) return "#0b0b0b"
  const [r, g, b] = m.map(Number).map((c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  })
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return lum > 0.35 ? "#0b0b0b" : "#ffffff"
}
