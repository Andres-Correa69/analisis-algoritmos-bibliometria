import type {
  Article,
  BenchmarkResponse,
  ClusteringResponse,
  CompareResponse,
  ExplainResponse,
  MatrixResponse,
  Meta,
  SearchResponse,
  TraceResponse,
} from "./types"

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!res.ok) {
    let message = `Error ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === "string") message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ")
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, message)
  }
  return (await res.json()) as T
}

const post = <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) })

export const api = {
  meta: () => request<Meta>("/api/meta"),
  corpus: () => request<{ count: number; articles: Article[] }>("/api/corpus"),
  compare: (ids: number[], granularity: "words" | "chars" = "words") =>
    post<CompareResponse>("/api/similarity/compare", { ids, granularity }),
  explain: (a: number, b: number, window = 10) =>
    request<ExplainResponse>(`/api/similarity/explain?a=${a}&b=${b}&window=${window}`),
  matrix: (algorithm: string) => request<MatrixResponse>(`/api/similarity/matrix?algorithm=${algorithm}`),
  clustering: (representation: string, displayK = 4) =>
    request<ClusteringResponse>(`/api/clustering?representation=${representation}&display_k=${displayK}`),
  search: (body: {
    pattern: string
    fields: string[]
    case_sensitive: boolean
    algorithms?: string[]
    modulus?: number
  }) => post<SearchResponse>("/api/search", body),
  trace: (body: {
    pattern: string
    algorithm: string
    text?: string
    article_id?: number
    case_sensitive?: boolean
    modulus?: number
    base?: number
  }) => post<TraceResponse>("/api/search/trace", body),
  benchmark: () => request<BenchmarkResponse>("/api/search/benchmark"),
}
