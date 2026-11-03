import { Trophy } from "lucide-react"
import { useMemo, useState } from "react"
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Line, LineChart, XAxis, YAxis } from "recharts"

import { cutGroups, Dendrogram } from "@/components/dendrogram"
import { ErrorAlert, Legend, Loading, PageHeader, Tex } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { api } from "@/lib/api"
import { useCorpus } from "@/lib/corpus-context"
import { fmt } from "@/lib/format"
import { ALGORITHM_COLOR, SERIES } from "@/lib/palette"
import type { ClusteringResponse, MethodResult } from "@/lib/types"
import { useAsync } from "@/lib/use-async"

const METHODS = ["single", "complete", "average", "ward"] as const
const METHOD_LABEL: Record<string, string> = { single: "Single", complete: "Complete", average: "Average", ward: "Ward" }

export default function ClusteringPage() {
  const [representation, setRepresentation] = useState("tfidf")
  const [method, setMethod] = useState<string>("average")
  const [k, setK] = useState(4)
  const { data, loading, error } = useAsync<ClusteringResponse>(() => api.clustering(representation, 4), [representation])

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Requerimiento 2"
        title="Agrupamiento jerárquico aglomerativo"
        description="Preprocesamiento → vectorización → matriz de distancias → fusión de clústeres con la fórmula de Lance-Williams → dendrograma y evaluación interna (correlación cofenética y silueta)."
      />
      <Card>
        <CardContent className="grid gap-5 pt-6 md:grid-cols-3">
          <div className="space-y-2">
            <Label>Representación de los abstracts</Label>
            <ToggleGroup type="single" variant="outline" value={representation} onValueChange={(v) => v && setRepresentation(v)} className="w-full">
              <ToggleGroupItem value="tfidf" className="flex-1">
                TF-IDF (clásico)
              </ToggleGroupItem>
              <ToggleGroupItem value="sbert" className="flex-1">
                SBERT (IA)
              </ToggleGroupItem>
            </ToggleGroup>
          </div>
          <div className="space-y-2">
            <Label>Criterio de enlace</Label>
            <Tabs value={method} onValueChange={setMethod}>
              <TabsList className="w-full">
                {METHODS.map((m) => (
                  <TabsTrigger key={m} value={m} className="flex-1" data-testid={`method-${m}`}>
                    {METHOD_LABEL[m]}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
          <div className="space-y-3">
            <Label>
              Número de grupos para el corte: <span className="tabular font-semibold">k = {k}</span>
            </Label>
            <Slider value={[k]} min={1} max={10} step={1} onValueChange={([v]) => setK(v)} aria-label="Número de grupos" />
          </div>
        </CardContent>
      </Card>

      {error && <ErrorAlert error={error} />}
      {loading && !data && <Loading label="Ejecutando los cuatro criterios de enlace…" />}
      {data && <ClusteringBody data={data} method={method} k={k} />}
    </div>
  )
}

function ClusteringBody({ data, method, k }: { data: ClusteringResponse; method: string; k: number }) {
  const { byId } = useCorpus()
  const r = data.methods[method]
  const titles = useMemo(() => Object.fromEntries(data.labels.map((l, i) => [l, byId.get(data.ids[i])?.title ?? ""])), [data, byId])
  const groups = useMemo(() => {
    const { leafGroup } = cutGroups(r, k)
    const out = new Map<number, number[]>()
    leafGroup.forEach((g, leaf) => out.set(g, [...(out.get(g) ?? []), data.ids[leaf]]))
    return [...out.entries()].sort((a, b) => a[0] - b[0])
  }, [r, k, data.ids])

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="gap-2 md:flex md:flex-row md:items-start md:justify-between">
          <div className="space-y-1.5">
            <CardTitle>
              Dendrograma — {r.label}
              {!r.required && (
                <Badge variant="outline" className="ml-2 align-middle">
                  adicional
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              {data.representation_label}; distancia {r.distance}. Pase el cursor por una hoja para ver el título.
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">CPCC {fmt(r.cophenetic_correlation)}</Badge>
            <Badge variant="secondary">silueta media {fmt(r.silhouette_mean)}</Badge>
            <Badge variant="secondary">
              mejor k = {r.best_k} ({fmt(r.best_silhouette)})
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <Dendrogram result={r} k={k} titles={titles} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <MetricsTable data={data} />
        <SilhouetteChart data={data} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Grupos al cortar en k = {k}</CardTitle>
            <CardDescription>Cruce con los metadatos: título y año de cada artículo del grupo.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {groups.map(([g, ids]) => (
              <div key={g} className="rounded-lg border p-3">
                <p className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <span className="size-2.5 rounded-full" style={{ background: SERIES[g % SERIES.length] }} />
                  Grupo {g + 1} · {ids.length} {ids.length === 1 ? "artículo" : "artículos"}
                </p>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {ids.map((id) => (
                    <li key={id}>
                      <span className="font-mono text-foreground">{byId.get(id)?.code}</span> {byId.get(id)?.title} ({byId.get(id)?.year})
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
        <MergeSteps r={r} labels={data.labels} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Fundamento matemático</CardTitle>
          <CardDescription>Implementado desde cero (sin scipy.cluster ni sklearn en la aplicación).</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm md:grid-cols-2">
          <div className="space-y-2">
            <p className="font-medium">Distancias</p>
            <Tex block>{String.raw`d_{\cos}(u,v)=1-\frac{u\cdot v}{\lVert u\rVert\lVert v\rVert},\qquad d_E(u,v)=\sqrt{2-2\cos(u,v)}\ \ (\lVert u\rVert=\lVert v\rVert=1)`}</Tex>
            <p className="font-medium">Actualización de Lance-Williams</p>
            <Tex block>{String.raw`d(h,i\cup j)=\alpha_i d(h,i)+\alpha_j d(h,j)+\beta d(i,j)+\gamma\,|d(h,i)-d(h,j)|`}</Tex>
            <p className="text-muted-foreground">
              Criterio actual: <span className="font-mono">{r.lance_williams}</span>. Complejidad O(n³) en tiempo y O(n²) en memoria; para n = 20 se evaluaron {r.pair_comparisons} pares.
            </p>
          </div>
          <div className="space-y-2">
            <p className="font-medium">Correlación cofenética</p>
            <Tex block>{String.raw`CPCC=\frac{\sum_{i<j}(d_{ij}-\bar d)(c_{ij}-\bar c)}{\sqrt{\sum_{i<j}(d_{ij}-\bar d)^2\sum_{i<j}(c_{ij}-\bar c)^2}}`}</Tex>
            <p className="font-medium">Coeficiente de silueta</p>
            <Tex block>{String.raw`s(i)=\frac{b(i)-a(i)}{\max\{a(i),b(i)\}},\qquad S=\frac{1}{n}\sum_i s(i)\in[-1,1]`}</Tex>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function MetricsTable({ data }: { data: ClusteringResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Evaluación interna</CardTitle>
        <CardDescription>
          Criterio de decisión: mayor silueta media en k ∈ [{data.k_range[0]}, {data.k_range[1]}] (desempate: CPCC).
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <Table data-testid="metrics-table">
          <TableHeader>
            <TableRow>
              <TableHead className="pl-6">Método</TableHead>
              <TableHead className="text-right">CPCC</TableHead>
              <TableHead className="text-right">Silueta media</TableHead>
              <TableHead className="text-right">Mejor k</TableHead>
              <TableHead className="pr-6 text-right">Silueta (k*)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="tabular">
            {data.ranking.map((m) => {
              const r = data.methods[m]
              return (
                <TableRow key={m}>
                  <TableCell className="pl-6">
                    <span className="inline-flex items-center gap-2">
                      <span className="size-2.5 rounded-sm" style={{ background: ALGORITHM_COLOR[m] }} />
                      {METHOD_LABEL[m]}
                      {m === data.best_required_method && (
                        <Badge className="gap-1">
                          <Trophy className="size-3" /> más coherente
                        </Badge>
                      )}
                      {!r.required && <Badge variant="outline">adicional</Badge>}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">{fmt(r.cophenetic_correlation)}</TableCell>
                  <TableCell className="text-right">{fmt(r.silhouette_mean)}</TableCell>
                  <TableCell className="text-right">{r.best_k}</TableCell>
                  <TableCell className="pr-6 text-right">{fmt(r.best_silhouette)}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        <div className="px-6 pt-4">
          <CpccChart data={data} />
        </div>
      </CardContent>
    </Card>
  )
}

function CpccChart({ data }: { data: ClusteringResponse }) {
  const rows = METHODS.map((m) => ({ method: METHOD_LABEL[m], key: m, value: data.methods[m].cophenetic_correlation }))
  const config = { value: { label: "CPCC" } } satisfies ChartConfig
  return (
    <ChartContainer config={config} className="aspect-auto h-40 w-full">
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 40 }}>
        <XAxis type="number" domain={[0, 1]} hide />
        <YAxis type="category" dataKey="method" width={70} tickLine={false} axisLine={false} fontSize={12} />
        <ChartTooltip cursor={false} content={<ChartTooltipContent hideIndicator />} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={16}>
          {rows.map((r) => (
            <Cell key={r.key} fill={ALGORITHM_COLOR[r.key]} />
          ))}
          <LabelList dataKey="value" position="right" formatter={(v: unknown) => Number(v).toFixed(3)} fontSize={11} className="fill-foreground" />
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}

function SilhouetteChart({ data }: { data: ClusteringResponse }) {
  const ks = Object.keys(data.methods.single.silhouette)
  const rows = ks.map((k) => ({ k, ...Object.fromEntries(METHODS.map((m) => [m, data.methods[m].silhouette[k]])) }))
  const config = Object.fromEntries(METHODS.map((m) => [m, { label: METHOD_LABEL[m], color: ALGORITHM_COLOR[m] }])) satisfies ChartConfig
  return (
    <Card>
      <CardHeader>
        <CardTitle>Silueta según el número de grupos</CardTitle>
        <CardDescription>Valores cercanos a 0 indican grupos poco separados: el corpus es temáticamente homogéneo.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Legend items={METHODS.map((m) => ({ key: m, label: METHOD_LABEL[m], color: ALGORITHM_COLOR[m] }))} />
        <ChartContainer config={config} className="aspect-auto h-72 w-full">
          <LineChart data={rows} margin={{ left: -8, right: 12 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="k" tickLine={false} axisLine={false} fontSize={11} label={{ value: "k", position: "insideBottomRight", offset: -4, fontSize: 11 }} />
            <YAxis tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v) => Number(v).toFixed(2)} />
            <ChartTooltip content={<ChartTooltipContent labelFormatter={(l) => `k = ${l}`} />} />
            {METHODS.map((m) => (
              <Line key={m} dataKey={m} stroke={`var(--color-${m})`} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} type="monotone" />
            ))}
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

function MergeSteps({ r, labels }: { r: MethodResult; labels: string[] }) {
  const n = labels.length
  const name = (id: number) => (id < n ? labels[id].split(" ")[0] : `C${id - n + 1}`)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Fusiones paso a paso</CardTitle>
        <CardDescription>Cada fila es una iteración del algoritmo (C<sub>t</sub> = clúster creado en el paso t).</CardDescription>
      </CardHeader>
      <CardContent className="max-h-96 overflow-y-auto px-0">
        <Table>
          <TableHeader className="sticky top-0 bg-card">
            <TableRow>
              <TableHead className="pl-6">t</TableHead>
              <TableHead>Fusión</TableHead>
              <TableHead className="text-right">Distancia</TableHead>
              <TableHead className="pr-6 text-right">Tamaño</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="tabular text-xs">
            {r.merges.map((m) => (
              <TableRow key={m.step}>
                <TableCell className="pl-6">{m.step}</TableCell>
                <TableCell className="font-mono">
                  {name(m.left)} ∪ {name(m.right)} → C{m.step}
                </TableCell>
                <TableCell className="text-right">{m.distance.toFixed(4)}</TableCell>
                <TableCell className="pr-6 text-right">{m.size}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
