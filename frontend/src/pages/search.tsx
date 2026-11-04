import { CheckCircle2, Search as SearchIcon } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Bar, BarChart, CartesianGrid, LabelList, Line, LineChart, XAxis, YAxis } from "recharts"

import { ErrorAlert, Legend, Loading, Mono, PageHeader, Tex } from "@/components/common"
import { StepPlayer } from "@/components/step-player"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import { useCorpus } from "@/lib/corpus-context"
import { authorsShort, fmtInt, fmtNs, fmtUs } from "@/lib/format"
import { ALGORITHM_COLOR, PRIMARY } from "@/lib/palette"
import type { BenchMeasure, BenchmarkResponse, SearchResponse, TraceResponse } from "@/lib/types"
import { useAsync } from "@/lib/use-async"

const ALGS = ["kmp", "boyer_moore", "rabin_karp"] as const
const ALG_LABEL: Record<string, string> = { kmp: "KMP", boyer_moore: "Boyer-Moore", rabin_karp: "Rabin-Karp", naive: "Fuerza bruta" }
const FIELDS = [
  { key: "abstract", label: "Abstracts" },
  { key: "title", label: "Títulos" },
  { key: "authors", label: "Autores" },
  { key: "keywords", label: "Palabras clave" },
]

export default function SearchPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Requerimiento 3"
        title="Búsqueda de patrones: coincidencia exacta de cadenas"
        description="KMP, Boyer-Moore y Rabin-Karp implementados desde cero (sin find(), index() ni expresiones regulares). Cada carácter se compara explícitamente."
      />
      <Tabs defaultValue="search">
        <TabsList className="flex-wrap">
          <TabsTrigger value="search">Buscar en el corpus</TabsTrigger>
          <TabsTrigger value="trace">Paso a paso</TabsTrigger>
          <TabsTrigger value="benchmark">Rendimiento empírico</TabsTrigger>
          <TabsTrigger value="theory">Complejidad teórica</TabsTrigger>
        </TabsList>
        <TabsContent value="search" className="mt-4">
          <CorpusSearch />
        </TabsContent>
        <TabsContent value="trace" className="mt-4">
          <TraceTab />
        </TabsContent>
        <TabsContent value="benchmark" className="mt-4">
          <BenchmarkTab />
        </TabsContent>
        <TabsContent value="theory" className="mt-4">
          <TheoryTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// --------------------------------------------------------------------------- //
// Búsqueda en el corpus
// --------------------------------------------------------------------------- //

function CorpusSearch() {
  const [pattern, setPattern] = useState("generative artificial intelligence")
  const [fields, setFields] = useState<string[]>(["abstract", "title"])
  const [caseSensitive, setCaseSensitive] = useState(false)
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [running, setRunning] = useState(false)

  const run = async () => {
    if (!pattern.trim() || fields.length === 0) return
    setRunning(true)
    setError(null)
    try {
      setResult(await api.search({ pattern, fields, case_sensitive: caseSensitive }))
    } catch (e) {
      setError(e as Error)
    } finally {
      setRunning(false)
    }
  }
  useEffect(() => {
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4 pt-6">
          <form
            className="flex flex-col gap-3 md:flex-row"
            onSubmit={(e) => {
              e.preventDefault()
              run()
            }}
          >
            <div className="relative flex-1">
              <SearchIcon className="absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
              <Input value={pattern} onChange={(e) => setPattern(e.target.value)} placeholder="Patrón exacto, p. ej. «learning analytics»" className="pl-8" data-testid="pattern-input" />
            </div>
            <Button type="submit" disabled={running || !pattern.trim() || fields.length === 0} data-testid="search-button">
              {running ? "Buscando…" : "Buscar"}
            </Button>
          </form>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
            <span className="text-muted-foreground">Buscar en:</span>
            {FIELDS.map((f) => (
              <label key={f.key} className="inline-flex items-center gap-2">
                <Checkbox
                  checked={fields.includes(f.key)}
                  onCheckedChange={(c) => setFields((prev) => (c ? [...prev, f.key] : prev.filter((x) => x !== f.key)))}
                />
                {f.label}
              </label>
            ))}
            <label className="inline-flex items-center gap-2">
              <Switch checked={caseSensitive} onCheckedChange={setCaseSensitive} /> Distinguir mayúsculas
            </label>
          </div>
        </CardContent>
      </Card>
      {error && <ErrorAlert error={error} />}
      {result && <SearchResults result={result} />}
    </div>
  )
}

function SearchResults({ result }: { result: SearchResponse }) {
  const timeConfig = { pre: { label: "Preprocesamiento", color: "var(--series-2)" }, search: { label: "Búsqueda", color: "var(--series-1)" } } satisfies ChartConfig
  const timeRows = ALGS.map((a) => ({ alg: ALG_LABEL[a], pre: result.totals[a].preprocessing_ns / 1000, search: result.totals[a].search_ns / 1000 }))
  const cmpRows = ALGS.map((a) => ({ key: a, alg: ALG_LABEL[a], value: result.totals[a].comparisons }))
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="text-sm" data-testid="occurrences-badge">
          {result.total_occurrences} ocurrencias
        </Badge>
        <Badge variant="secondary">{result.documents_with_matches} artículos</Badge>
        <Badge variant="secondary">{fmtInt(result.scanned_chars)} caracteres recorridos</Badge>
        {result.consistent && (
          <Badge variant="outline" className="gap-1">
            <CheckCircle2 className="size-3" /> los 3 algoritmos coinciden
          </Badge>
        )}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Tiempo: preprocesamiento vs búsqueda</CardTitle>
            <CardDescription>Suma sobre todos los campos recorridos (µs). El preprocesamiento depende sólo de m.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Legend items={[{ key: "pre", label: "Preprocesamiento", color: "var(--series-2)" }, { key: "s", label: "Búsqueda", color: "var(--series-1)" }]} />
            <ChartContainer config={timeConfig} className="aspect-auto h-48 w-full">
              <BarChart data={timeRows} layout="vertical" margin={{ left: 16, right: 24 }}>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis type="category" dataKey="alg" width={90} tickLine={false} axisLine={false} fontSize={12} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent formatter={(v, n) => `${n === "pre" ? "Preproc." : "Búsqueda"}: ${Number(v).toFixed(1)} µs`} />} />
                <Bar dataKey="pre" stackId="t" fill="var(--color-pre)" maxBarSize={22} />
                <Bar dataKey="search" stackId="t" fill="var(--color-search)" radius={[0, 2, 2, 0]} maxBarSize={22} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Comparaciones de caracteres</CardTitle>
            <CardDescription>Métrica independiente de la máquina. Rabin-Karp sólo compara cuando los hashes coinciden.</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={{ value: { label: "Comparaciones" } }} className="aspect-auto h-48 w-full">
              <BarChart data={cmpRows} layout="vertical" margin={{ left: 16, right: 56 }}>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis type="category" dataKey="alg" width={90} tickLine={false} axisLine={false} fontSize={12} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent hideIndicator />} />
                <Bar dataKey="value" fill={PRIMARY} radius={[0, 2, 2, 0]} maxBarSize={22}>
                  <LabelList dataKey="value" position="right" fontSize={11} className="fill-foreground" formatter={(v: unknown) => fmtInt(Number(v))} />
                </Bar>
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Métricas por algoritmo</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Algoritmo</TableHead>
                <TableHead className="text-right">Ocurrencias</TableHead>
                <TableHead className="text-right">Comparaciones</TableHead>
                <TableHead className="text-right">Alineaciones</TableHead>
                <TableHead className="text-right">Preproc.</TableHead>
                <TableHead className="text-right">Búsqueda</TableHead>
                <TableHead className="pr-6 text-right">Colisiones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="tabular">
              {ALGS.map((a) => {
                const t = result.totals[a]
                return (
                  <TableRow key={a}>
                    <TableCell className="pl-6">{ALG_LABEL[a]}</TableCell>
                    <TableCell className="text-right">{t.occurrences}</TableCell>
                    <TableCell className="text-right">{fmtInt(t.comparisons)}</TableCell>
                    <TableCell className="text-right">{fmtInt(t.alignments)}</TableCell>
                    <TableCell className="text-right">{fmtNs(t.preprocessing_ns)}</TableCell>
                    <TableCell className="text-right">{fmtNs(t.search_ns)}</TableCell>
                    <TableCell className="pr-6 text-right">{a === "rabin_karp" ? t.spurious_hits : "—"}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ocurrencias encontradas</CardTitle>
          <CardDescription>Cada coincidencia se muestra con su contexto, junto al título y los autores del artículo.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3" data-testid="search-results">
          {result.results.length === 0 && <p className="text-sm text-muted-foreground">El patrón no aparece en los campos seleccionados.</p>}
          {result.results.map((r) => (
            <div key={`${r.id}-${r.field}`} className="rounded-lg border p-3">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="font-mono">
                  {r.code}
                </Badge>
                <Badge variant="secondary">{r.field_label}</Badge>
                <span className="text-sm font-medium">{r.title}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {authorsShort(r.authors)} ({r.year}) · {r.count}×
                </span>
              </div>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {r.occurrences.slice(0, 4).map((o) => (
                  <li key={o.position} className="leading-relaxed">
                    <span className="mr-1 font-mono text-[10px]">@{o.position}</span>…{o.before}
                    <mark className="hl font-medium text-foreground">{o.match}</mark>
                    {o.after}…
                  </li>
                ))}
                {r.occurrences.length > 4 && <li className="text-xs">y {r.occurrences.length - 4} más</li>}
              </ul>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

// --------------------------------------------------------------------------- //
// Paso a paso
// --------------------------------------------------------------------------- //

function sentences(text: string): string[] {
  const out: string[] = []
  let start = 0
  for (let i = 0; i < text.length; i++) {
    if (".!?".includes(text[i]) && (i + 1 >= text.length || (text[i + 1] === " " && /[A-Z]/.test(text[i + 2] ?? "")))) {
      out.push(text.slice(start, i + 1).trim())
      start = i + 1
    }
  }
  if (start < text.length) out.push(text.slice(start).trim())
  return out.filter(Boolean)
}

function TraceTab() {
  const { articles, byId } = useCorpus()
  const [algorithm, setAlgorithm] = useState("boyer_moore")
  const [articleId, setArticleId] = useState(16)
  const [fragment, setFragment] = useState("1")
  const [custom, setCustom] = useState("")
  const [pattern, setPattern] = useState("assessment")
  const [modulus, setModulus] = useState(13)
  const [data, setData] = useState<TraceResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const text = useMemo(() => {
    if (fragment === "custom") return custom
    const abs = byId.get(articleId)?.abstract ?? ""
    if (fragment === "all") return abs
    return sentences(abs).slice(0, Number(fragment)).join(" ")
  }, [fragment, custom, articleId, byId])

  const run = async () => {
    setError(null)
    try {
      setData(await api.trace({ pattern, algorithm, text, modulus }))
    } catch (e) {
      setError(e as Error)
    }
  }
  useEffect(() => {
    if (text) run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [algorithm, articleId, fragment])

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="grid gap-4 pt-6 md:grid-cols-2 xl:grid-cols-5">
          <div className="space-y-2">
            <Label>Algoritmo</Label>
            <Select value={algorithm} onValueChange={setAlgorithm}>
              <SelectTrigger className="w-full" data-testid="trace-algorithm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="kmp">Knuth-Morris-Pratt</SelectItem>
                <SelectItem value="boyer_moore">Boyer-Moore</SelectItem>
                <SelectItem value="rabin_karp">Rabin-Karp</SelectItem>
                <SelectItem value="naive">Fuerza bruta (referencia)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 xl:col-span-2">
            <Label>Texto: abstract del artículo</Label>
            <Select value={String(articleId)} onValueChange={(v) => setArticleId(Number(v))}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {articles.map((a) => (
                  <SelectItem key={a.id} value={String(a.id)}>
                    {a.code} · {a.short_title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Fragmento</Label>
            <Select value={fragment} onValueChange={setFragment}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Primera oración</SelectItem>
                <SelectItem value="2">Primeras 2 oraciones</SelectItem>
                <SelectItem value="3">Primeras 3 oraciones</SelectItem>
                <SelectItem value="all">Abstract completo</SelectItem>
                <SelectItem value="custom">Texto personalizado</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <form
            className="space-y-2"
            onSubmit={(e) => {
              e.preventDefault()
              run()
            }}
          >
            <Label>Patrón</Label>
            <div className="flex gap-2">
              <Input value={pattern} onChange={(e) => setPattern(e.target.value)} data-testid="trace-pattern" />
              <Button type="submit">Ir</Button>
            </div>
          </form>
          {fragment === "custom" && (
            <div className="space-y-2 md:col-span-2 xl:col-span-5">
              <Label>Texto personalizado</Label>
              <Textarea value={custom} onChange={(e) => setCustom(e.target.value)} rows={3} placeholder="Escriba o pegue un párrafo…" />
            </div>
          )}
          {algorithm === "rabin_karp" && (
            <div className="space-y-2">
              <Label>Módulo primo q</Label>
              <Input type="number" min={2} value={modulus} onChange={(e) => setModulus(Number(e.target.value) || 13)} />
              <p className="text-xs text-muted-foreground">Un q pequeño (13, 101) provoca colisiones a propósito.</p>
            </div>
          )}
        </CardContent>
      </Card>
      {error && <ErrorAlert error={error} />}
      {data && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
          <Card>
            <CardHeader>
              <CardTitle>Recorrido sobre el texto</CardTitle>
              <CardDescription>
                n = {data.text_length}, m = {data.pattern.length} · {data.occurrences} ocurrencias en [{data.positions.join(", ")}] · {data.comparisons} comparaciones
                {data.algorithm === "rabin_karp" && ` · ${data.extra.spurious_hits} colisiones`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <StepPlayer key={`${data.algorithm}|${data.pattern}|${data.text}|${data.extra.modulus ?? ""}`} data={data} />
            </CardContent>
          </Card>
          <PreprocessingTables data={data} />
        </div>
      )}
    </div>
  )
}

function PreprocessingTables({ data }: { data: TraceResponse }) {
  const p = data.pattern
  const t = data.tables
  return (
    <Card>
      <CardHeader>
        <CardTitle>Estructuras auxiliares</CardTitle>
        <CardDescription>Preprocesamiento: {fmtNs(data.preprocessing_ns)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {data.algorithm === "kmp" && t.pi && (
          <>
            <Tex block>{String.raw`\pi[q]=\max\{k<q+1:\ P[0..k-1]\ \text{es sufijo de}\ P[0..q]\}`}</Tex>
            <div className="overflow-x-auto">
              <table className="w-full text-xs tabular">
                <thead>
                  <tr className="text-muted-foreground">
                    <th className="py-1 text-left">q</th>
                    {p.split("").map((_, i) => (
                      <th key={i} className="px-1">
                        {i}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th className="py-1 text-left">P[q]</th>
                    {p.split("").map((c, i) => (
                      <td key={i} className="px-1 text-center font-mono">
                        {c === " " ? "␠" : c}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th className="py-1 text-left">π[q]</th>
                    {t.pi.map((v, i) => (
                      <td key={i} className="px-1 text-center font-semibold">
                        {v}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            <ul className="space-y-0.5 text-xs text-muted-foreground">
              {t.pi_steps?.slice(1).map((s) => (
                <li key={s.q}>
                  q={s.q} (‘{s.char}’): k={s.k_before}
                  {s.fallbacks.length > 0 && ` → retrocede a ${s.fallbacks.join(" → ")}`} ⇒ π[{s.q}] = {s.pi}
                </li>
              ))}
            </ul>
          </>
        )}
        {data.algorithm === "boyer_moore" && t.bad_character && t.good_suffix && (
          <>
            <div>
              <p className="mb-1 font-medium">Carácter malo: última aparición</p>
              <div className="flex flex-wrap gap-1">
                {Object.entries(t.bad_character).map(([c, v]) => (
                  <Mono key={c}>
                    {c === " " ? "␠" : c}:{v}
                  </Mono>
                ))}
                <Mono>otro:−1</Mono>
              </div>
              <Tex block>{String.raw`\delta_{bc}=j-\text{última}(T[s+j])`}</Tex>
            </div>
            <div>
              <p className="mb-1 font-medium">Sufijo bueno (gs)</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs tabular">
                  <thead>
                    <tr className="text-muted-foreground">
                      <th className="py-1 text-left">j</th>
                      {t.good_suffix.map((_, i) => (
                        <th key={i} className="px-1">
                          {i}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <th className="py-1 text-left">P</th>
                      {t.good_suffix.map((_, i) => (
                        <td key={i} className="px-1 text-center font-mono">
                          {p[i] ?? ""}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <th className="py-1 text-left">gs</th>
                      {t.good_suffix.map((v, i) => (
                        <td key={i} className="px-1 text-center font-semibold">
                          {v}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">Falla en P[j] ⇒ se usa gs[j+1]; ocurrencia completa ⇒ gs[0].</p>
            </div>
          </>
        )}
        {data.algorithm === "rabin_karp" && (
          <>
            <Tex block>{`h=d^{m-1}\\bmod q=${data.extra.base}^{${p.length - 1}}\\bmod ${data.extra.modulus}=${t.h}`}</Tex>
            <div className="overflow-x-auto">
              <table className="w-full text-xs tabular">
                <thead>
                  <tr className="text-muted-foreground">
                    <th className="py-1 text-left">i</th>
                    <th>P[i]</th>
                    <th>código</th>
                    <th className="text-right">H parcial</th>
                  </tr>
                </thead>
                <tbody>
                  {t.pattern_hash_steps?.map((s) => (
                    <tr key={s.index}>
                      <td className="py-0.5">{s.index}</td>
                      <td className="text-center font-mono">{s.char === " " ? "␠" : s.char}</td>
                      <td className="text-center">{s.code}</td>
                      <td className="text-right">{s.hash}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Tex block>{`H(P)=${t.pattern_hash}\\quad\\text{(regla de Horner)}`}</Tex>
            <RkWindows data={data} />
          </>
        )}
        {data.algorithm === "naive" && <p className="text-muted-foreground">La fuerza bruta no tiene preprocesamiento.</p>}
      </CardContent>
    </Card>
  )
}

function RkWindows({ data }: { data: TraceResponse }) {
  const windows = data.trace.filter((e) => e.type === "window") as Extract<TraceResponse["trace"][number], { type: "window" }>[]
  const hits = windows.filter((w) => w.hash_match)
  return (
    <div>
      <p className="mb-1 font-medium">Ventanas con hash igual al del patrón</p>
      <div className="max-h-56 overflow-y-auto rounded border">
        <table className="w-full text-xs tabular">
          <thead className="sticky top-0 bg-card text-muted-foreground">
            <tr>
              <th className="px-2 py-1 text-left">s</th>
              <th className="text-left">ventana</th>
              <th className="text-right">t_s</th>
              <th className="px-2 text-right">resultado</th>
            </tr>
          </thead>
          <tbody>
            {hits.map((w) => (
              <tr key={w.alignment} className="border-t">
                <td className="px-2 py-1">{w.alignment}</td>
                <td className="font-mono">{data.text.slice(w.alignment, w.alignment + data.pattern.length)}</td>
                <td className="text-right">{w.window_hash}</td>
                <td className="px-2 text-right">{w.verified ? <Badge>ocurrencia</Badge> : <Badge variant="destructive">colisión</Badge>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------- //
// Benchmark
// --------------------------------------------------------------------------- //

const BENCH_ALGS = ["naive", "kmp", "boyer_moore", "rabin_karp"] as const

function BenchmarkTab() {
  const { data, loading, error } = useAsync<BenchmarkResponse>(() => api.benchmark(), [])
  if (error) return <ErrorAlert error={error} />
  if (loading || !data) return <Loading label="Cargando benchmark…" />
  const metric = (row: Record<string, unknown>, alg: string, key: keyof BenchMeasure) => (row[alg] as BenchMeasure)[key]
  const series = (rows: Record<string, unknown>[], x: string, key: keyof BenchMeasure) =>
    rows.map((r) => ({ x: r[x] as number, ...Object.fromEntries(BENCH_ALGS.map((a) => [a, metric(r, a, key)])) }))
  const config = Object.fromEntries(BENCH_ALGS.map((a) => [a, { label: ALG_LABEL[a], color: ALGORITHM_COLOR[a] }])) satisfies ChartConfig
  const legend = <Legend items={BENCH_ALGS.map((a) => ({ key: a, label: ALG_LABEL[a], color: ALGORITHM_COLOR[a] }))} />

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Python {String(data.meta.python)} · {String(data.meta.machine)} · mediana de {String(data.meta.repeats)} repeticiones · texto base: {fmtInt(Number(data.meta.corpus_chars))} caracteres (los 20 abstracts concatenados).
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <BenchLine title="Tiempo de búsqueda vs longitud del patrón (m)" description={`n = ${fmtInt(data.pattern_length[0].n)} caracteres. Boyer-Moore se acelera cuando m crece (saltos más largos).`} data={series(data.pattern_length, "m", "search_us")} config={config} legend={legend} xLabel="m" unit="µs" />
        <BenchLine title="Comparaciones vs longitud del patrón (m)" description="KMP ≈ n; Boyer-Moore ≈ n/m; Rabin-Karp sólo verifica ventanas con hash igual." data={series(data.pattern_length, "m", "comparisons")} config={config} legend={legend} xLabel="m" unit="" />
        <BenchLine title="Tiempo de búsqueda vs longitud del texto (n)" description={`Patrón fijo «${data.text_length[0].pattern}». Todos crecen linealmente con n.`} data={series(data.text_length, "n", "search_us")} config={config} legend={legend} xLabel="n" unit="µs" />
        <BenchLine title="Tiempo de preprocesamiento vs m" description="Θ(m) en los tres algoritmos; despreciable frente a la búsqueda." data={series(data.pattern_length, "m", "preprocessing_us").map((r) => ({ ...r, naive: 0 }))} config={config} legend={legend} xLabel="m" unit="µs" />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Peor caso teórico: T = aⁿ</CardTitle>
          <CardDescription>Comparaciones con n = {fmtInt(data.worst_case[0].n)}. P = a^(m−1)b no aparece; P = aᵐ aparece en todas las posiciones.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Caso</TableHead>
                <TableHead className="text-right">m</TableHead>
                {BENCH_ALGS.map((a) => (
                  <TableHead key={a} className="text-right">
                    {ALG_LABEL[a]}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody className="tabular">
              {data.worst_case.map((r) => (
                <TableRow key={`${r.case}-${r.m}`}>
                  <TableCell className="pl-6">{r.case === "sin_ocurrencias" ? "a^(m−1)b" : "aᵐ"}</TableCell>
                  <TableCell className="text-right">{r.m}</TableCell>
                  {BENCH_ALGS.map((a) => (
                    <TableCell key={a} className="text-right">
                      {fmtInt(metric(r, a, "comparisons") as number)}
                      <span className="block text-[10px] text-muted-foreground">{fmtUs(metric(r, a, "search_us") as number)}</span>
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Rabin-Karp: colisiones según el módulo q</CardTitle>
          <CardDescription>Búsqueda de «learning» en el corpus: con q pequeño aparecen coincidencias espurias que obligan a verificar.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={{ spurious_hits: { label: "Colisiones", color: PRIMARY } }} className="aspect-auto h-56 w-full">
            <BarChart data={data.rabin_karp_collisions.map((r) => ({ ...r, q: String(r.modulus) }))} margin={{ left: -8, top: 16 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="q" tickLine={false} axisLine={false} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} fontSize={11} />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              <Bar dataKey="spurious_hits" fill="var(--color-spurious_hits)" radius={[2, 2, 0, 0]} maxBarSize={24}>
                <LabelList dataKey="spurious_hits" position="top" fontSize={11} className="fill-foreground" />
              </Bar>
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>
    </div>
  )
}

function BenchLine({
  title,
  description,
  data,
  config,
  legend,
  xLabel,
  unit,
}: {
  title: string
  description: string
  data: Record<string, number>[]
  config: ChartConfig
  legend: React.ReactNode
  xLabel: string
  unit: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {legend}
        <ChartContainer config={config} className="aspect-auto h-60 w-full">
          <LineChart data={data} margin={{ left: 4, right: 12 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="x" tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : String(v))} />
            <YAxis tickLine={false} axisLine={false} fontSize={11} width={56} tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(Math.round(v)))} />
            <ChartTooltip content={<ChartTooltipContent labelFormatter={(l) => `${xLabel} = ${l}`} formatter={(v, n) => `${ALG_LABEL[String(n)]}: ${Number(v).toFixed(unit ? 1 : 0)} ${unit}`} />} />
            {Object.keys(config).map((a) => (
              <Line key={a} dataKey={a} stroke={`var(--color-${a})`} strokeWidth={2} dot={{ r: 3 }} type="monotone" />
            ))}
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

// --------------------------------------------------------------------------- //
// Teoría
// --------------------------------------------------------------------------- //

function TheoryTab() {
  const rows = [
    { alg: "Fuerza bruta", pre: "—", best: "Θ(n)", avg: "Θ(n·m) peor", worst: "O((n−m+1)·m)", space: "O(1)" },
    { alg: "Knuth-Morris-Pratt", pre: "Θ(m)", best: "Θ(n)", avg: "Θ(n)", worst: "Θ(n)", space: "O(m)" },
    { alg: "Boyer-Moore", pre: "O(m + σ)", best: "Θ(n/m)", avg: "sublineal", worst: "O(n·m)", space: "O(m + σ)" },
    { alg: "Rabin-Karp", pre: "Θ(m)", best: "Θ(n)", avg: "O(n + m)", worst: "O(n·m)", space: "O(1)" },
  ]
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Complejidad asintótica</CardTitle>
          <CardDescription>n = longitud del texto, m = longitud del patrón, σ = tamaño del alfabeto.</CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Algoritmo</TableHead>
                <TableHead>Preprocesamiento</TableHead>
                <TableHead>Mejor caso</TableHead>
                <TableHead>Caso típico</TableHead>
                <TableHead>Peor caso</TableHead>
                <TableHead className="pr-6">Memoria</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="font-mono text-xs">
              {rows.map((r) => (
                <TableRow key={r.alg}>
                  <TableCell className="pl-6 font-sans text-sm">{r.alg}</TableCell>
                  <TableCell>{r.pre}</TableCell>
                  <TableCell>{r.best}</TableCell>
                  <TableCell>{r.avg}</TableCell>
                  <TableCell>{r.worst}</TableCell>
                  <TableCell className="pr-6">{r.space}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>KMP: análisis amortizado</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>El índice i del texto sólo avanza y q (caracteres emparejados) sube como máximo una vez por iteración; cada retroceso q ← π[q−1] reduce q. Por tanto hay a lo sumo 2n comparaciones.</p>
          <Tex block>{String.raw`T_{\text{búsqueda}}(n)\le 2n\Rightarrow\Theta(n),\qquad T_{\text{pre}}(m)\le 2m\Rightarrow\Theta(m)`}</Tex>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Rabin-Karp: probabilidad de colisión</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>Con q primo grande, la probabilidad de que una ventana distinta tenga el mismo hash es ≈ 1/q, así que el número esperado de verificaciones inútiles es (n−m+1)/q.</p>
          <Tex block>{String.raw`E[T(n,m)]=O\!\left(n+m+\frac{n\,m}{q}+\text{occ}\cdot m\right)`}</Tex>
        </CardContent>
      </Card>
    </div>
  )
}
