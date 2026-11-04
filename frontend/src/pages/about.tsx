import { ArrowDown, ArrowRight, Download, FileCode2, Server, TerminalSquare } from "lucide-react"

import { Mono, PageHeader } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useCorpus } from "@/lib/corpus-context"

const TEAM = ["Mariana Muñoz Rodriguez", "Andres Felipe Correa Valencia", "Ivan Alexander Cardona", "Milton Cesar Gomez Roso"]

function Box({ title, items, tone = "default" }: { title: string; items: string[]; tone?: "default" | "accent" }) {
  return (
    <div className={`rounded-lg border p-3 text-sm ${tone === "accent" ? "border-primary/40 bg-accent/40" : "bg-background"}`}>
      <p className="font-medium">{title}</p>
      <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  )
}

export default function AboutPage() {
  const { meta } = useCorpus()
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Requerimiento 4"
        title="Arquitectura, despliegue y documentación"
        description="Aplicación modular en Python (núcleo algorítmico + API REST) con una interfaz web en React. Todos los algoritmos solicitados están implementados explícitamente con estructuras básicas del lenguaje."
        actions={
          meta?.report_available ? (
            <Button asChild>
              <a href="/informe.pdf" target="_blank" rel="noreferrer">
                <Download className="size-4" /> Informe final (PDF)
              </a>
            </Button>
          ) : undefined
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Arquitectura por capas</CardTitle>
          <CardDescription>Flujo de datos desde los PDF hasta la interfaz.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid items-center gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
            <Box title="Fuente" items={["20 artículos en PDF", "data/raw/articulos/"]} />
            <ArrowRight className="mx-auto hidden size-4 text-muted-foreground md:block" />
            <Box title="Extracción" items={["PyMuPDF (líneas + posiciones)", "Heurísticas propias: título, autores,", "abstract, keywords, año, DOI"]} tone="accent" />
            <ArrowRight className="mx-auto hidden size-4 text-muted-foreground md:block" />
            <Box title="Corpus procesado" items={["data/processed/corpus.json", "embeddings GloVe/SBERT precalculados"]} />
          </div>
          <ArrowDown className="mx-auto size-4 text-muted-foreground" />
          <Box title="Preprocesamiento compartido" items={["Normalización → tokenización → stopwords → stemmer de Porter (propio)"]} tone="accent" />
          <ArrowDown className="mx-auto size-4 text-muted-foreground" />
          <div className="grid gap-3 md:grid-cols-3">
            <Box title="R1 · similarity/" items={["Levenshtein, Needleman-Wunsch", "Jaccard, Coseno TF-IDF", "GloVe y Sentence-BERT + coseno"]} tone="accent" />
            <Box title="R2 · clustering/" items={["Aglomerativo + Lance-Williams", "single, complete, average (+ ward)", "CPCC, silueta, dendrogramas"]} tone="accent" />
            <Box title="R3 · string_matching/" items={["KMP, Boyer-Moore, Rabin-Karp", "trazas paso a paso", "benchmark empírico"]} tone="accent" />
          </div>
          <ArrowDown className="mx-auto size-4 text-muted-foreground" />
          <div className="grid gap-3 md:grid-cols-3">
            <Box title="API REST (FastAPI)" items={["/api/corpus, /api/similarity/*", "/api/clustering, /api/search/*", "OpenAPI en /docs"]} />
            <Box title="Interfaz web" items={["React + TypeScript + Vite", "shadcn/ui + Tailwind CSS", "Recharts, KaTeX, SVG propio"]} />
            <Box title="Consola" items={["python main.py", "genera PNG/CSV en outputs/"]} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TerminalSquare className="size-4" /> Ejecución local
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">Python 3.11+ y Node 20+:</p>
            <pre className="overflow-x-auto rounded-lg bg-muted p-3 text-xs">{`python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py           # menú por consola
cd frontend && npm install && npm run build
uvicorn bibliometria.api.main:app`}</pre>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="size-4" /> Despliegue (Docker)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">Una sola imagen sirve la API y la interfaz compilada. En el servidor de OVHcloud, Caddy publica la app en el dominio del equipo con HTTPS automático:</p>
            <pre className="overflow-x-auto rounded-lg bg-muted p-3 text-xs">{`cp .env.example .env   # DOMAIN=...
docker compose --profile produccion up -d --build`}</pre>
            <p className="text-muted-foreground">
              Localmente basta con <Mono>docker compose up -d --build</Mono> (puerto 8000).
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileCode2 className="size-4" /> Pruebas automatizadas
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              <Mono>pytest</Mono>: unitarias, de propiedades (Hypothesis), de oráculo contra SciPy, scikit-learn, NLTK y RapidFuzz, de integración de la API y de flujo completo.
            </p>
            <p>
              <Mono>npx playwright test</Mono>: pruebas de extremo a extremo de la interfaz.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Equipo</CardTitle>
            <CardDescription>Análisis de Algoritmos · Profesor Sergio Augusto Cardona Torres</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {TEAM.map((t) => (
              <Badge key={t} variant="secondary" className="text-sm font-normal">
                {t}
              </Badge>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Uso de inteligencia artificial generativa</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>Los modelos de IA que forman parte de la solución (GloVe y Sentence-BERT) sólo generan vectores; la similitud se calcula con código propio.</p>
            <p>El uso de herramientas de IA generativa durante el proyecto se declara en el informe técnico.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
