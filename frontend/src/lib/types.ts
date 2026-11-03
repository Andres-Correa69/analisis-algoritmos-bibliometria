// Tipos de las respuestas de la API (bibliometria/api/main.py)

export interface Article {
  id: number
  code: string
  file: string
  title: string
  short_title: string
  authors: string[]
  year: number | null
  journal: string | null
  doi: string | null
  keywords: string[]
  abstract: string
  abstract_words: number
  abstract_chars: number
}

export interface AlgorithmInfo {
  key: string
  label: string
  family?: string
  technique?: string
  formula?: string
  complexity?: string
}

export interface Meta {
  title: string
  version: string
  authors: string[]
  course: string
  corpus_size: number
  similarity_algorithms: AlgorithmInfo[]
  clustering_representations: Record<string, string>
  string_matching_algorithms: (AlgorithmInfo & Record<string, string>)[]
  search_fields: Record<string, string>
  report_available: boolean
}

export interface ArticleSummary {
  id: number
  code: string
  title: string
  short_title: string
  authors: string[]
  year: number | null
  abstract?: string
}

export interface CompareResponse {
  articles: ArticleSummary[]
  algorithms: AlgorithmInfo[]
  granularity: "words" | "chars"
  pairs: { a: number; b: number; scores: Record<string, { value: number; ms: number }> }[]
  matrices: Record<string, number[][]>
  timings_ms: Record<string, number>
}

export interface EditOp {
  op: "match" | "substitute" | "delete" | "insert"
  a: string | null
  b: string | null
  i: number
  j: number
}

export interface TfidfTerm {
  term: string
  word: string
  tf_a: number
  tf_b: number
  df: number
  idf: number
  w_a: number
  w_b: number
  product: number
}

export interface VectorExplain {
  model: string
  dim: number
  head_a: number[]
  head_b: number[]
  dot: number
  norm_a: number
  norm_b: number
  cosine: number
  angle_deg: number
  euclidean: number
  euclidean_normalized: number
}

export interface PreprocessingSummary {
  tokens: number
  filtered: number
  stems: number
  unique_stems: number
  sample_tokens: string[]
  sample_filtered: string[]
  sample_stems: string[]
}

export interface ExplainResponse {
  a: ArticleSummary
  b: ArticleSummary
  preprocessing: { a: PreprocessingSummary; b: PreprocessingSummary }
  levenshtein: {
    window_a: string[]
    window_b: string[]
    matrix: number[][]
    path: [number, number][]
    operations: EditOp[]
    window_distance: number
    distance: number
    len_a: number
    len_b: number
    similarity: number
    chars: { distance: number; len_a: number; len_b: number; similarity: number }
  }
  needleman_wunsch: {
    params: { match: number; mismatch: number; gap: number }
    window_a: string[]
    window_b: string[]
    matrix: number[][]
    window_alignment: [string | null, string | null][]
    window_score: number
    score: number
    matches: number
    mismatches: number
    gaps: number
    length: number
    similarity: number
    alignment: [string | null, string | null][]
  }
  jaccard: {
    size_a: number
    size_b: number
    intersection: string[]
    only_a: string[]
    only_b: string[]
    union_size: number
    similarity: number
    display: Record<string, string>
  }
  tfidf: {
    n_docs: number
    idf_formula: string
    terms: TfidfTerm[]
    shared_terms: number
    dot_raw: number
    norm_a: number
    norm_b: number
    cosine: number
    angle_deg: number
  }
  glove?: VectorExplain & {
    used_a: number
    used_b: number
    oov_a: string[]
    oov_b: string[]
    sample_words_a: string[]
    sample_vectors_a: number[][]
  }
  sbert?: VectorExplain & { tokens_a: number; tokens_b: number; max_seq_length: number }
  summary: (AlgorithmInfo & { value: number })[]
}

export interface MatrixResponse {
  algorithm: string
  ids: number[]
  codes: string[]
  matrix: number[][]
  seconds: number
}

export interface DendroLink {
  id: number
  left: number
  right: number
  height: number
  size: number
  icoord: number[]
  dcoord: number[]
  group: number | null
}

export interface ClusterGroup {
  group: number
  size: number
  articles: { id: number; code: string; title: string; year: number | null }[]
}

export interface MethodResult {
  method: string
  label: string
  formula: string
  lance_williams: string
  required: boolean
  distance: string
  merges: { step: number; left: number; right: number; distance: number; size: number; members: number[] }[]
  linkage: number[][]
  cophenetic_correlation: number
  silhouette: Record<string, number>
  silhouette_mean: number
  best_k: number
  best_silhouette: number
  clusters: ClusterGroup[]
  display_k: number
  display_clusters: ClusterGroup[]
  dendrogram: {
    n: number
    order: number[]
    labels: string[]
    leaf_groups: number[]
    links: DendroLink[]
    threshold: number | null
    k: number | null
    max_height: number
  }
  pair_comparisons: number
}

export interface ClusteringResponse {
  representation: string
  representation_label: string
  n: number
  ids: number[]
  labels: string[]
  k_range: [number, number]
  methods: Record<string, MethodResult>
  ranking: string[]
  best_required_method: string
  best_method: string
  distance_matrix: number[][]
}

export interface SearchTotals {
  occurrences: number
  comparisons: number
  alignments: number
  preprocessing_ns: number
  search_ns: number
  total_ns: number
  spurious_hits: number
  documents: number
}

export interface SearchResult {
  id: number
  code: string
  title: string
  authors: string[]
  year: number | null
  field: string
  field_label: string
  count: number
  occurrences: { position: number; before: string; match: string; after: string }[]
}

export interface SearchResponse {
  pattern: string
  case_sensitive: boolean
  fields: string[]
  algorithms: (AlgorithmInfo & Record<string, string>)[]
  rabin_karp: { base: number; modulus: number }
  totals: Record<string, SearchTotals>
  results: SearchResult[]
  total_occurrences: number
  documents_with_matches: number
  scanned_chars: number
  consistent: boolean
}

export type TraceEvent =
  | { type: "compare"; i: number; j: number; alignment: number; match: boolean }
  | {
      type: "shift"
      from_alignment: number
      to_alignment: number
      reason?: string
      rule?: string
      bad_char?: string
      mismatch_j?: number
      bc_shift?: number | null
      gs_shift?: number | null
    }
  | { type: "found"; position: number }
  | { type: "spurious"; position: number }
  | {
      type: "window"
      alignment: number
      window_hash: number
      pattern_hash: number
      hash_match: boolean
      verified: boolean | null
      out_char: string | null
      in_char: string | null
      next_hash: number | null
    }

export interface TraceResponse {
  algorithm: string
  pattern: string
  text: string
  text_length: number
  positions: number[]
  occurrences: number
  comparisons: number
  alignments: number
  preprocessing_ns: number
  search_ns: number
  total_ns: number
  extra: Record<string, number>
  tables: {
    pi?: number[]
    pi_steps?: { q: number; char: string; k_before: number; fallbacks: number[]; pi: number }[]
    bad_character?: Record<string, number>
    good_suffix?: number[]
    border_positions?: number[]
    h?: number
    pattern_hash?: number
    pattern_hash_steps?: { index: number; char: string; code: number; hash: number }[]
  }
  trace: TraceEvent[]
  trace_truncated: boolean
  info: Record<string, string>
}

export interface BenchMeasure {
  preprocessing_us: number
  search_us: number
  total_us: number
  comparisons: number
  spurious_hits: number
  occurrences: number
}

export type BenchRow = { m: number; n: number } & Record<string, BenchMeasure | number | string | string[]>

export interface BenchmarkResponse {
  meta: Record<string, string | number | boolean>
  pattern_length: BenchRow[]
  text_length: (BenchRow & { factor: number; pattern: string })[]
  worst_case: (BenchRow & { case: string })[]
  rabin_karp_collisions: {
    modulus: number
    hash_hits: number
    spurious_hits: number
    occurrences: number
    comparisons: number
    search_us: number
  }[]
}
