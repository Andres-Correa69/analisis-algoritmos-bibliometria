import { ExternalLink, FileText, Search } from "lucide-react"
import { useMemo, useState } from "react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import { ErrorAlert, Loading, PageHeader, StatTile } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useCorpus } from "@/lib/corpus-context"
import { authorsShort } from "@/lib/format"
import type { Article } from "@/lib/types"

const lengthConfig = { words: { label: "Palabras del abstract", color: "var(--series-1)" } } satisfies ChartConfig
const yearConfig = { count: { label: "Artículos", color: "var(--series-1)" } } satisfies ChartConfig

export default function HomePage() {
  const { articles, loading, error } = useCorpus()
  const [query, setQuery] = useState("")
  const [selected, setSelected] = useState<Article | null>(null)

  const stats = useMemo(() => {
    const authors = new Set(articles.flatMap((a) => a.authors))
    const words = articles.map((a) => a.abstract_words)
    const years = articles.map((a) => a.year ?? 0).filter(Boolean)
    const journals = new Set(articles.map((a) => a.journal))
    const perYear = new Map<number, number>()
    years.forEach((y) => perYear.set(y, (perYear.get(y) ?? 0) + 1))
    return {
      authors: authors.size,
      avgWords: words.length ? Math.round(words.reduce((s, x) => s + x, 0) / words.length) : 0,
      minYear: Math.min(...years),
      maxYear: Math.max(...years),
      journals: journals.size,
      perYear: [...perYear.entries()].sort((a, b) => a[0] - b[0]).map(([year, count]) => ({ year: String(year), count })),
    }
  }, [articles])

  const filtered = articles.filter((a) => {
    const q = query.trim().toLowerCase()
    if (!q) return true
    return `${a.code} ${a.title} ${a.authors.join(" ")} ${a.journal} ${a.keywords.join(" ")}`.toLowerCase().includes(q)
  })

  if (error) return <ErrorAlert error={error} />
  if (loading) return <Loading label="Cargando corpus…" />

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Corpus documental controlado"
        title="20 artículos sobre inteligencia artificial en educación"
        description="Título, autores, abstract, palabras clave, año, revista y DOI se extrajeron automáticamente de los PDF entregados por el docente (140/140 campos verificados contra una referencia manual)."
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Artículos" value={articles.length} hint="PDF procesados" />
        <StatTile label="Autores únicos" value={stats.authors} hint="extraídos de la primera página" />
        <StatTile label="Palabras por abstract" value={stats.avgWords} hint="promedio" />
        <StatTile label="Periodo" value={`${stats.minYear}–${stats.maxYear}`} hint={`${stats.journals} revistas`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Longitud de los abstracts</CardTitle>
            <CardDescription>Número de palabras de cada abstract (entrada de los tres requerimientos).</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={lengthConfig} className="aspect-auto h-64 w-full">
              <BarChart data={articles.map((a) => ({ code: a.code, words: a.abstract_words, title: a.short_title }))} margin={{ left: -12 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="code" tickLine={false} axisLine={false} fontSize={11} interval={0} angle={-45} textAnchor="end" height={44} />
                <YAxis tickLine={false} axisLine={false} fontSize={11} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent labelFormatter={(l) => `Artículo ${l}`} />} />
                <Bar dataKey="words" fill="var(--color-words)" radius={[4, 4, 0, 0]} maxBarSize={24} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Artículos por año</CardTitle>
            <CardDescription>Año de publicación extraído del encabezado del PDF.</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={yearConfig} className="aspect-auto h-64 w-full">
              <BarChart data={stats.perYear} margin={{ left: -20 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="year" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={11} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={[4, 4, 0, 0]} maxBarSize={24} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="gap-3 md:flex md:flex-row md:items-center md:justify-between">
          <div className="space-y-1.5">
            <CardTitle>Artículos del corpus</CardTitle>
            <CardDescription>Haga clic en un artículo para ver su abstract y metadatos.</CardDescription>
          </div>
          <div className="relative w-full md:w-72">
            <Search className="absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
            <Input placeholder="Filtrar por título, autor, revista…" className="pl-8" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Código</TableHead>
                <TableHead>Título</TableHead>
                <TableHead className="hidden md:table-cell">Autores</TableHead>
                <TableHead className="hidden lg:table-cell">Revista</TableHead>
                <TableHead className="text-right">Año</TableHead>
                <TableHead className="pr-6 text-right">Palabras</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((a) => (
                <TableRow key={a.id} className="cursor-pointer" onClick={() => setSelected(a)} data-testid={`row-${a.id}`}>
                  <TableCell className="pl-6 font-mono text-xs">{a.code}</TableCell>
                  <TableCell className="max-w-md whitespace-normal">{a.title}</TableCell>
                  <TableCell className="hidden max-w-56 whitespace-normal text-muted-foreground md:table-cell">{authorsShort(a.authors)}</TableCell>
                  <TableCell className="hidden max-w-56 whitespace-normal text-muted-foreground lg:table-cell">{a.journal}</TableCell>
                  <TableCell className="text-right tabular">{a.year}</TableCell>
                  <TableCell className="pr-6 text-right tabular">{a.abstract_words}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Sheet open={selected !== null} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          {selected && (
            <>
              <SheetHeader>
                <Badge variant="outline" className="w-fit font-mono">
                  {selected.code}
                </Badge>
                <SheetTitle className="text-lg leading-snug">{selected.title}</SheetTitle>
                <SheetDescription>
                  {selected.authors.join(", ")} · {selected.journal} ({selected.year})
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-4 px-4 pb-6 text-sm">
                <div>
                  <p className="mb-1 font-medium">Abstract</p>
                  <p className="leading-relaxed text-muted-foreground">{selected.abstract}</p>
                </div>
                {selected.keywords.length > 0 && (
                  <div>
                    <p className="mb-1.5 font-medium">Palabras clave</p>
                    <div className="flex flex-wrap gap-1.5">
                      {selected.keywords.map((k) => (
                        <Badge key={k} variant="secondary">
                          {k}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <FileText className="size-3.5" /> {selected.file}
                  </span>
                  {selected.doi && (
                    <a className="inline-flex items-center gap-1 underline" href={`https://doi.org/${selected.doi}`} target="_blank" rel="noreferrer">
                      <ExternalLink className="size-3.5" /> doi:{selected.doi}
                    </a>
                  )}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
