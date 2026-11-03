import { lazy, Suspense } from "react"
import { Route, Routes } from "react-router-dom"

import { Loading } from "./components/common"
import { AppShell } from "./components/layout/app-shell"
import { Toaster } from "./components/ui/sonner"
import HomePage from "./pages/home"

const SimilarityPage = lazy(() => import("./pages/similarity"))
const ClusteringPage = lazy(() => import("./pages/clustering"))
const SearchPage = lazy(() => import("./pages/search"))
const AboutPage = lazy(() => import("./pages/about"))

export default function App() {
  return (
    <>
      <Suspense fallback={<Loading label="Cargando…" />}>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<HomePage />} />
            <Route path="similitud" element={<SimilarityPage />} />
            <Route path="clustering" element={<ClusteringPage />} />
            <Route path="patrones" element={<SearchPage />} />
            <Route path="acerca" element={<AboutPage />} />
            <Route path="*" element={<HomePage />} />
          </Route>
        </Routes>
      </Suspense>
      <Toaster richColors position="top-right" />
    </>
  )
}
