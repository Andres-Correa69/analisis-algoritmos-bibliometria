import { Bar, BarChart, CartesianGrid, Cell, LabelList, XAxis, YAxis } from "recharts"

import { DpMatrix } from "@/components/dp-matrix"
import { Mono, Tex } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fmt } from "@/lib/format"
import { ALGORITHM_COLOR } from "@/lib/palette"
import type { ExplainResponse, VectorExplain } from "@/lib/types"
import { cn } from "@/lib/utils"

const summaryConfig = { value: { label: "Similitud" } } satisfies ChartConfig

function Section({ n, title, description, children }: { n: number; title: string; description?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="flex size-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">{n}</span>
          {title}
        </CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  )
}

function Result({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular">{value}</p>
    </div>
  )
}

export function SimilarityExplain({ data }: { data: ExplainResponse }) {
  const { a, b } = data
  const lev = data.levenshtein
  const nw = data.needleman_wunsch
  const jac = data.jaccard
  const tf = data.tfidf
  const shared = tf.terms.filter((t) => t.tf_a > 0 && t.tf_b > 0)

  return (
    <div className="space-y-4" data-testid="explain-view">
      <Card>
        <CardHeader>
          <CardTitle>Caso de estudio: {a.code} vs {b.code}</CardTitle>
          <CardDescription>
            <strong>{a.code}</strong> {a.title} · <strong>{b.code}</strong> {b.title}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={summaryConfig} className="aspect-auto h-56 w-full">
            <BarChart data={data.summary.map((s) => ({ ...s, value: s.value }))} layout="vertical" margin={{ left: 24, right: 48 }}>
              <CartesianGrid horizontal={false} />
              <XAxis type="number" domain={[0, 1]} tickLine={false} axisLine={false} fontSize={11} />
              <YAxis type="category" dataKey="label" width={150} tickLine={false} axisLine={false} fontSize={12} />
              <ChartTooltip cursor={false} content={<ChartTooltipContent hideIndicator />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22}>
                {data.summary.map((s) => (
                  <Cell key={s.key} fill={ALGORITHM_COLOR[s.key]} />
                ))}
                <LabelList dataKey="value" position="right" formatter={(v: unknown) => Number(v).toFixed(3)} className="fill-foreground" fontSize={11} />
              </Bar>
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Section n={0} title="Preprocesamiento" description="Normalización → tokenización → eliminación de stopwords y números → stemming de Porter.">
        <div className="grid gap-4 md:grid-cols-2">
          {(["a", "b"] as const).map((k) => {
            const p = data.preprocessing[k]
            return (
              <div key={k} className="space-y-2 text-sm">
                <p className="font-medium">
                  {data[k].code}: {p.tokens} tokens → {p.filtered} sin stopwords → {p.unique_stems} raíces distintas
                </p>
                <p className="text-xs text-muted-foreground">Primeras raíces (secuencia usada por los algoritmos clásicos):</p>
                <div className="flex flex-wrap gap-1">
                  {p.sample_stems.map((s, i) => (
                    <Mono key={i}>{s}</Mono>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </Section>

      <Section n={1} title="Levenshtein (programación dinámica)" description="Número mínimo de inserciones, eliminaciones y sustituciones para transformar A en B.">
        <Tex block>{String.raw`D[i][j]=\min\begin{cases}D[i-1][j]+1 & \text{(eliminación)}\\ D[i][j-1]+1 & \text{(inserción)}\\ D[i-1][j-1]+[a_i\neq b_j] & \text{(sustitución)}\end{cases}\qquad sim=1-\frac{d(A,B)}{\max(|A|,|B|)}`}</Tex>
        <DpMatrix
          rows={lev.window_a}
          cols={lev.window_b}
          matrix={lev.matrix}
          path={lev.path}
          caption={`Ventana de las primeras ${lev.window_a.length} raíces de cada abstract: d = ${lev.window_distance}. La ruta resaltada es una secuencia óptima de operaciones.`}
        />
        <div className="flex flex-wrap gap-1 text-xs">
          {lev.operations.map((op, i) => (
            <Badge key={i} variant={op.op === "match" ? "secondary" : "outline"} className={cn(op.op !== "match" && "border-dashed")}>
              {op.op === "match" && `= ${op.a}`}
              {op.op === "substitute" && `${op.a} → ${op.b}`}
              {op.op === "delete" && `− ${op.a}`}
              {op.op === "insert" && `+ ${op.b}`}
            </Badge>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Result label="d(A,B) por palabras" value={lev.distance} />
          <Result label="|A|, |B| (raíces)" value={`${lev.len_a}, ${lev.len_b}`} />
          <Result label="Similitud (palabras)" value={fmt(lev.similarity, 4)} />
          <Result label="Similitud (caracteres)" value={fmt(lev.chars.similarity, 4)} />
        </div>
      </Section>

      <Section n={2} title="Needleman-Wunsch (alineamiento global)" description={`Puntuación: coincidencia ${nw.params.match}, discrepancia ${nw.params.mismatch}, hueco ${nw.params.gap}.`}>
        <Tex block>{String.raw`F[i][j]=\max\{F[i-1][j-1]+s(a_i,b_j),\;F[i-1][j]+g,\;F[i][j-1]+g\}\qquad sim=\frac{\#\text{coincidencias}}{\text{longitud del alineamiento}}`}</Tex>
        <DpMatrix rows={nw.window_a} cols={nw.window_b} matrix={nw.matrix} caption={`Matriz F de la ventana: puntuación F[n][m] = ${nw.window_score}.`} />
        <div className="overflow-x-auto rounded-lg border p-2">
          <div className="flex w-max gap-0.5 font-mono text-[11px]">
            {nw.alignment.slice(0, 60).map(([x, y], i) => {
              const kind = x === null || y === null ? "gap" : x === y ? "match" : "mismatch"
              return (
                <div
                  key={i}
                  className={cn(
                    "flex min-w-14 flex-col items-center rounded px-1 py-0.5",
                    kind === "match" && "bg-[var(--match-bg)] text-[var(--match-fg)]",
                    kind === "mismatch" && "bg-muted",
                    kind === "gap" && "bg-[var(--miss-bg)]/60 text-[var(--miss-fg)]",
                  )}
                >
                  <span>{x ?? "—"}</span>
                  <span>{y ?? "—"}</span>
                </div>
              )
            })}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Primeras 60 columnas del alineamiento global óptimo (verde: coincidencia, rojo: hueco).</p>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Result label="Puntuación F[n][m]" value={nw.score} />
          <Result label="Coincidencias" value={nw.matches} />
          <Result label="Discrepancias" value={nw.mismatches} />
          <Result label="Huecos" value={nw.gaps} />
          <Result label="Identidad" value={fmt(nw.similarity, 4)} />
        </div>
      </Section>

      <Section n={3} title="Coeficiente de Jaccard" description="Proporción de raíces compartidas sobre el total de raíces distintas.">
        <Tex block>{`J(A,B)=\\frac{|A\\cap B|}{|A\\cup B|}=\\frac{${jac.intersection.length}}{${jac.size_a}+${jac.size_b}-${jac.intersection.length}}=\\frac{${jac.intersection.length}}{${jac.union_size}}=${jac.similarity.toFixed(4)}`}</Tex>
        <div className="flex flex-wrap gap-1">
          {jac.intersection.map((t) => (
            <Badge key={t} variant="secondary" title={jac.display[t]}>
              {t}
            </Badge>
          ))}
        </div>
      </Section>

      <Section n={4} title="Coseno sobre TF-IDF" description={`IDF calculado sobre los ${tf.n_docs} abstracts del corpus: ${tf.idf_formula}.`}>
        <Tex block>{String.raw`w(t,d)=tf(t,d)\cdot\left(\ln\frac{1+N}{1+df(t)}+1\right)\qquad \cos\theta=\frac{\vec w_A\cdot\vec w_B}{\lVert\vec w_A\rVert\,\lVert\vec w_B\rVert}`}</Tex>
        <div className="max-h-80 overflow-auto rounded-lg border">
          <Table>
            <TableHeader className="sticky top-0 bg-background">
              <TableRow>
                <TableHead>Término (raíz)</TableHead>
                <TableHead className="text-right">tf A</TableHead>
                <TableHead className="text-right">tf B</TableHead>
                <TableHead className="text-right">df</TableHead>
                <TableHead className="text-right">idf</TableHead>
                <TableHead className="text-right">ŵ A</TableHead>
                <TableHead className="text-right">ŵ B</TableHead>
                <TableHead className="text-right">ŵA·ŵB</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="tabular">
              {shared.map((t) => (
                <TableRow key={t.term}>
                  <TableCell className="font-mono text-xs">
                    {t.term} <span className="text-muted-foreground">({t.word})</span>
                  </TableCell>
                  <TableCell className="text-right">{t.tf_a}</TableCell>
                  <TableCell className="text-right">{t.tf_b}</TableCell>
                  <TableCell className="text-right">{t.df}</TableCell>
                  <TableCell className="text-right">{fmt(t.idf, 3)}</TableCell>
                  <TableCell className="text-right">{fmt(t.w_a, 4)}</TableCell>
                  <TableCell className="text-right">{fmt(t.w_b, 4)}</TableCell>
                  <TableCell className="text-right font-medium">{fmt(t.product, 4)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-muted-foreground">
          Sólo los {tf.shared_terms} términos compartidos aportan al producto punto; ŵ son los pesos ya normalizados con la norma L2.
        </p>
        <Tex block>{`\\cos\\theta=\\frac{${tf.dot_raw.toFixed(3)}}{${tf.norm_a.toFixed(3)}\\times ${tf.norm_b.toFixed(3)}}=${tf.cosine.toFixed(4)}\\quad\\Rightarrow\\quad \\theta=${tf.angle_deg.toFixed(2)}^\\circ`}</Tex>
      </Section>

      {data.glove && (
        <Section n={5} title="Modelo de IA 1 — GloVe (promedio de embeddings de palabras)" description={`${data.glove.model}: ${data.glove.dim} dimensiones, preentrenado sobre Wikipedia + Gigaword.`}>
          <Tex block>{String.raw`\vec e(d)=\frac{1}{|W_d|}\sum_{w\in W_d}\vec v_w\qquad \cos\theta=\frac{\vec e_A\cdot\vec e_B}{\lVert\vec e_A\rVert\,\lVert\vec e_B\rVert}`}</Tex>
          <p className="text-sm text-muted-foreground">
            Palabras con vector: A = {data.glove.used_a}, B = {data.glove.used_b}. Fuera de vocabulario:{" "}
            {[...new Set([...data.glove.oov_a, ...data.glove.oov_b])].map((w) => (
              <Mono key={w} className="mr-1">
                {w}
              </Mono>
            ))}
          </p>
          <VectorBlock v={data.glove} />
        </Section>
      )}

      {data.sbert && (
        <Section n={6} title="Modelo de IA 2 — Sentence-BERT" description={`${data.sbert.model}: transformer de 6 capas, ${data.sbert.dim} dimensiones, mean pooling y normalización L2.`}>
          <p className="text-sm text-muted-foreground">
            Tokens WordPiece: A = {data.sbert.tokens_a}, B = {data.sbert.tokens_b} (límite configurado {data.sbert.max_seq_length}, sin truncamiento).
          </p>
          <VectorBlock v={data.sbert} />
        </Section>
      )}
    </div>
  )
}

function VectorBlock({ v }: { v: VectorExplain }) {
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-max text-xs tabular">
          <tbody>
            {(["head_a", "head_b"] as const).map((k) => (
              <tr key={k} className="border-b last:border-0">
                <th className="px-3 py-1.5 text-left font-medium">{k === "head_a" ? "e(A)" : "e(B)"}</th>
                {v[k].map((x, i) => (
                  <td key={i} className="px-2 py-1.5 text-right">
                    {x.toFixed(4)}
                  </td>
                ))}
                <td className="px-3 py-1.5 text-muted-foreground">… ({v.dim} dims)</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Tex block>{`\\cos\\theta=\\frac{${v.dot.toFixed(4)}}{${v.norm_a.toFixed(4)}\\times ${v.norm_b.toFixed(4)}}=${v.cosine.toFixed(4)}\\;(\\theta=${v.angle_deg.toFixed(2)}^\\circ)\\qquad d_E=${v.euclidean.toFixed(4)}`}</Tex>
    </div>
  )
}
