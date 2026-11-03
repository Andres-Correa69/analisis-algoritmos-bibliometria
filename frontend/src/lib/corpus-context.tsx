import { createContext, useContext, type ReactNode } from "react"

import { api } from "./api"
import type { Article, Meta } from "./types"
import { useAsync } from "./use-async"

interface CorpusState {
  articles: Article[]
  byId: Map<number, Article>
  meta?: Meta
  loading: boolean
  error?: Error
}

const CorpusContext = createContext<CorpusState>({ articles: [], byId: new Map(), loading: true })

export function CorpusProvider({ children }: { children: ReactNode }) {
  const { data, loading, error } = useAsync(() => api.corpus(), [])
  const { data: meta } = useAsync(() => api.meta(), [])
  const articles = data?.articles ?? []
  const value: CorpusState = { articles, byId: new Map(articles.map((a) => [a.id, a])), meta, loading, error }
  return <CorpusContext.Provider value={value}>{children}</CorpusContext.Provider>
}

export const useCorpus = () => useContext(CorpusContext)
