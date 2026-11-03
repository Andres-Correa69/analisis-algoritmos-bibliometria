export const fmt = (x: number | null | undefined, digits = 3) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : x.toFixed(digits)

export const fmtInt = (x: number) => x.toLocaleString("es-CO")

/** Microsegundos legibles a partir de nanosegundos. */
export const fmtNs = (ns: number) => {
  if (ns < 1_000) return `${ns} ns`
  if (ns < 1_000_000) return `${(ns / 1_000).toFixed(1)} µs`
  return `${(ns / 1_000_000).toFixed(2)} ms`
}

export const fmtUs = (us: number) => (us < 1000 ? `${us.toFixed(1)} µs` : `${(us / 1000).toFixed(2)} ms`)

export const authorsShort = (authors: string[], max = 2) =>
  authors.length <= max ? authors.join(", ") : `${authors.slice(0, max).join(", ")} et al.`
