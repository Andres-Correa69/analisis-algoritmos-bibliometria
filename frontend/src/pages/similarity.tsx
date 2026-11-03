import { Play } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import { ArticleMultiSelect } from "@/components/article-multi-select"
import { ErrorAlert, Legend, Loading, PageHeader, Tex } from "@/components/common"
import { Heatmap } from "@/components/heatmap"
import { SimilarityExplain } from "@/components/similarity-explain"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { api } from "@/lib/api"
import { useCorpus } from "@/lib/corpus-context"
import { fmt } from "@/lib/format"
import { ALGORITHM_COLOR } from "@/lib/palette"
import type { CompareResponse, ExplainResponse, MatrixResponse } from "@/lib/types"
import { useAsync } from "@/lib/use-async"

const PRESETS = [
  { label: "IA generativa", ids: [11, 15, 16, 18, 19] },
  { label: "Evaluación", ids: [11, 13, 16, 17] },
  { label: "Mapeos del campo AIEd", ids: [5, 6, 9, 20] },
]

export default function SimilarityPage() {
  const { articles } = useCorpus()
  const [ids, setIds] = useState<number[]>([11, 16, 17, 19])
  const [granularity, setGranularity] = useState<"words" | "chars">("words")
  const [result, setResult] = useState<CompareResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [running, setRunning] = useState(false)

  const run = async (selection = ids) => {
    if (selection.length < 2) return
    setRunning(true)
    setError(null)
    try {
      setResult(await api.compare(selection, granularity))
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
    <div className="space-y-6">
      <PageHeader
        eyebrow="Requerimiento 1"
        title="Similitud textual: enfoques clásicos vs. IA"
        description="Seleccione dos o más artículos; sus abstracts se comparan con 4 algoritmos clásicos (programación dinámica, conjuntos y espacio vectorial) y 2 modelos de embeddings."
      />

      <Card>
        <CardContent className="grid gap-4 pt-6 lg:grid-cols-[1fr_auto]">
          <div className="space-y-2">
            <Label>Artículos a comparar</Label>
            <ArticleMultiSelect articles={articles} value={ids} onChange={setIds} />
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
              Conjuntos sugeridos:
              {PRESETS.map((p) => (
                <Button key={p.label} variant="outline" size="sm" className="h-7" onClick={() => setIds(p.ids)}>
                  {p.label}
                </Button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-3 lg:w-64">
            <div className="space-y-2">
              <Label>Levenshtein por</Label>
              <ToggleGroup type="single" variant="outline" value={granularity} onValueChange={(v) => v && setGranularity(v as "words" | "chars")} className="w-full">
                <ToggleGroupItem value="words" className="flex-1">
                  palabras
                </ToggleGroupItem>
                <ToggleGroupItem value="chars" className="flex-1">
                  caracteres
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
            <Button onClick={() => run()} disabled={ids.length < 2 || running} data-testid="compare-button">
              <Play className="size-4" /> {running ? "Comparando…" : "Comparar"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && <ErrorAlert error={error} />}
      {!result && running && <Loading />}
      {result && (
        <div className={running ? "opacity-60 transition-opacity" : undefined}>
          <Tabs defaultValue="results">
            <TabsList className="flex-wrap">
              <TabsTrigger value="results">Resultados</TabsTrigger>
              <TabsTrigger value="matrices">Matrices</TabsTrigger>
              <TabsTrigger value="explain">Paso a paso</TabsTrigger>
              <TabsTrigger value="corpus">Corpus completo</TabsTrigger>
              <TabsTrigger value="algorithms">Algoritmos</TabsTrigger>
            </TabsList>
            <TabsContent value="results" className="mt-4">
              <ResultsView result={result} />
            </TabsContent>
            <TabsContent value="matrices" className="mt-4">
              <MatricesView result={result} />
            </TabsContent>
            <TabsContent value="explain" className="mt-4">
              <ExplainTab key={result.pairs.map((p) => `${p.a}-${p.b}`).join(",")} result={result} />
            </TabsContent>
            <TabsContent value="corpus" className="mt-4">
              <CorpusMatrixView />
            </TabsContent>
            <TabsContent value="algorithms" className="mt-4">
              <AlgorithmsView result={result} />
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  )
}

function ResultsView({ result }: { result: CompareResponse }) {
  const codes = new Map(result.articles.map((a) => [a.id, a.code]))
  const config = Object.fromEntries(result.algorithms.map((a) => [a.key, { label: a.label, color: ALGORITHM_COLOR[a.key] }])) satisfies ChartConfig
  const data = result.pairs.map((p) => ({
    pair: `${codes.get(p.a)}–${codes.get(p.b)}`,
    ...Object.fromEntries(Object.entries(p.scores).map(([k, v]) => [k, v.value])),
  }))
  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Similitud por par y algoritmo</CardTitle>
          <CardDescription>Valores normalizados en [0, 1]. Los clásicos miden coincidencia léxica; los modelos de IA, cercanía semántica.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Legend items={result.algorithms.map((a) => ({ key: a.key, label: a.label, color: ALGORITHM_COLOR[a.key] }))} />
          <ChartContainer config={config} className="aspect-auto h-80 w-full">
            <BarChart data={data} margin={{ left: -12 }} barGap={2}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="pair" tickLine={false} axisLine={false} fontSize={11} />
              <YAxis domain={[0, 1]} tickLine={false} axisLine={false} fontSize={11} />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              {result.algorithms.map((a) => (
                <Bar key={a.key} dataKey={a.key} fill={`var(--color-${a.key})`} radius={[4, 4, 0, 0]} maxBarSize={20} />
              ))}
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Tabla de resultados</CardTitle>
          <CardDescription>Tiempo total de cálculo por algoritmo: {Object.entries(result.timings_ms).map(([k, v]) => `${k} ${v.toFixed(1)} ms`).join(" · ")}</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <Table data-testid="results-table">
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Par</TableHead>
                {result.algorithms.map((a) => (
                  <TableHead key={a.key} className="text-right">
                    {a.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody className="tabular">
              {result.pairs.map((p) => (
                <TableRow key={`${p.a}-${p.b}`}>
                  <TableCell className="pl-6 font-mono text-xs">
                    {codes.get(p.a)} – {codes.get(p.b)}
                  </TableCell>
                  {result.algorithms.map((a) => (
                    <TableCell key={a.key} className="text-right">
                      {fmt(p.scores[a.key].value, 4)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function MatricesView({ result }: { result: CompareResponse }) {
  const [alg, setAlg] = useState(result.algorithms[0].key)
  const labels = result.articles.map((a) => a.code)
  const titles = result.articles.map((a) => a.title)
  return (
    <Card>
      <CardHeader className="gap-3 md:flex md:flex-row md:items-start md:justify-between">
        <div className="space-y-1.5">
          <CardTitle>Matriz de similitud</CardTitle>
          <CardDescription>Escala de color relativa a los valores fuera de la diagonal del algoritmo elegido.</CardDescription>
        </div>
        <AlgorithmSelect value={alg} onChange={setAlg} options={result.algorithms} />
      </CardHeader>
      <CardContent>
        <Heatmap labels={labels} titles={titles} matrix={result.matrices[alg]} digits={3} />
      </CardContent>
    </Card>
  )
}

function AlgorithmSelect({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: { key: string; label: string }[] }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-60">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.key} value={o.key}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function ExplainTab({ result }: { result: CompareResponse }) {
  const codes = new Map(result.articles.map((a) => [a.id, a.code]))
  const [pairKey, setPairKey] = useState(`${result.pairs[0].a}-${result.pairs[0].b}`)
  const [a, b] = pairKey.split("-").map(Number)
  const { data, loading, error } = useAsync<ExplainResponse>(() => api.explain(a, b, 10), [a, b])
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Label>Par a analizar</Label>
        <Select value={pairKey} onValueChange={setPairKey}>
          <SelectTrigger className="w-48" data-testid="pair-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {result.pairs.map((p) => (
              <SelectItem key={`${p.a}-${p.b}`} value={`${p.a}-${p.b}`}>
                {codes.get(p.a)} vs {codes.get(p.b)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {error && <ErrorAlert error={error} />}
      {loading && !data && <Loading />}
      {data && <SimilarityExplain data={data} />}
    </div>
  )
}

function CorpusMatrixView() {
  const { articles } = useCorpus()
  const [alg, setAlg] = useState("sbert_cosine")
  const { data, loading, error } = useAsync<MatrixResponse>(() => api.matrix(alg), [alg])
  const options = useMemo(
    () => [
      { key: "levenshtein", label: "Levenshtein" },
      { key: "needleman_wunsch", label: "Needleman-Wunsch" },
      { key: "jaccard", label: "Jaccard" },
      { key: "tfidf_cosine", label: "Coseno TF-IDF" },
      { key: "glove_cosine", label: "GloVe + coseno" },
      { key: "sbert_cosine", label: "Sentence-BERT + coseno" },
    ],
    [],
  )
  const stats = useMemo(() => {
    if (!data) return null
    const v: number[] = []
    data.matrix.forEach((r, i) => r.forEach((x, j) => j > i && v.push(x)))
    const mean = v.reduce((s, x) => s + x, 0) / v.length
    const sd = Math.sqrt(v.reduce((s, x) => s + (x - mean) ** 2, 0) / v.length)
    let best = { i: 0, j: 1, v: -1 }
    data.matrix.forEach((r, i) => r.forEach((x, j) => j > i && x > best.v && (best = { i, j, v: x })))
    return { mean, sd, min: Math.min(...v), max: Math.max(...v), best }
  }, [data])
  return (
    <Card>
      <CardHeader className="gap-3 md:flex md:flex-row md:items-start md:justify-between">
        <div className="space-y-1.5">
          <CardTitle>Los 190 pares del corpus</CardTitle>
          <CardDescription>Matriz 20×20 completa; útil para comparar la capacidad de discriminación de cada algoritmo.</CardDescription>
        </div>
        <AlgorithmSelect value={alg} onChange={setAlg} options={options} />
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <ErrorAlert error={error} />}
        {loading && !data && <Loading />}
        {data && stats && (
          <>
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant="secondary">media {stats.mean.toFixed(3)}</Badge>
              <Badge variant="secondary">desv. estándar {stats.sd.toFixed(3)}</Badge>
              <Badge variant="secondary">
                rango [{stats.min.toFixed(3)}, {stats.max.toFixed(3)}]
              </Badge>
              <Badge variant="outline">
                par más similar: {data.codes[stats.best.i]}–{data.codes[stats.best.j]} ({stats.best.v.toFixed(3)})
              </Badge>
            </div>
            <Heatmap labels={data.codes} titles={articles.map((a) => a.title)} matrix={data.matrix} />
          </>
        )}
      </CardContent>
    </Card>
  )
}

function AlgorithmsView({ result }: { result: CompareResponse }) {
  const tex: Record<string, string> = {
    levenshtein: String.raw`sim=1-\frac{d(A,B)}{\max(|A|,|B|)}`,
    needleman_wunsch: String.raw`sim=\frac{\#\,\text{coincidencias}}{L_{\text{alineamiento}}}`,
    jaccard: String.raw`J=\frac{|A\cap B|}{|A\cup B|}`,
    tfidf_cosine: String.raw`\cos\theta=\frac{\vec w_A\cdot\vec w_B}{\lVert\vec w_A\rVert\lVert\vec w_B\rVert}`,
    glove_cosine: String.raw`\vec e(d)=\tfrac{1}{|W_d|}\textstyle\sum_{w}\vec v_w`,
    sbert_cosine: String.raw`\cos(\mathrm{SBERT}(A),\mathrm{SBERT}(B))`,
  }
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {result.algorithms.map((a) => (
        <Card key={a.key}>
          <CardHeader>
            <div className="flex items-center gap-2">
              <span className="size-2.5 rounded-sm" style={{ background: ALGORITHM_COLOR[a.key] }} />
              <CardTitle>{a.label}</CardTitle>
              <Badge variant={a.family === "IA" ? "default" : "secondary"} className="ml-auto">
                {a.family}
              </Badge>
            </div>
            <CardDescription>{a.technique}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Tex block>{tex[a.key]}</Tex>
            <p className="text-muted-foreground">
              Complejidad: <span className="font-mono">{a.complexity}</span>
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
