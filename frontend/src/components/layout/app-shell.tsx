import { BookOpenText, GitCompareArrows, Info, LayoutDashboard, Menu, Network, TextSearch } from "lucide-react"
import { useState } from "react"
import { NavLink, Outlet } from "react-router-dom"

import { ThemeToggle } from "@/components/theme-toggle"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { useCorpus } from "@/lib/corpus-context"
import { cn } from "@/lib/utils"

const NAV = [
  { to: "/", label: "Corpus", hint: "20 artículos", icon: LayoutDashboard, end: true },
  { to: "/similitud", label: "Similitud textual", hint: "Requerimiento 1", icon: GitCompareArrows },
  { to: "/clustering", label: "Agrupamiento", hint: "Requerimiento 2", icon: Network },
  { to: "/patrones", label: "Búsqueda de patrones", hint: "Requerimiento 3", icon: TextSearch },
  { to: "/acerca", label: "Arquitectura y despliegue", hint: "Requerimiento 4", icon: Info },
]

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )
          }
        >
          <item.icon className="size-4 shrink-0" />
          <span className="flex flex-col leading-tight">
            <span className="font-medium">{item.label}</span>
            <span className="text-[11px] opacity-70">{item.hint}</span>
          </span>
        </NavLink>
      ))}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <BookOpenText className="size-5" />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold">Bibliometría</p>
        <p className="text-xs text-muted-foreground">Análisis de Algoritmos</p>
      </div>
    </div>
  )
}

export function AppShell() {
  const [open, setOpen] = useState(false)
  const { meta } = useCorpus()
  return (
    <div className="min-h-svh bg-muted/30">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col gap-6 border-r bg-background p-4 lg:flex">
        <Brand />
        <NavItems />
        <div className="mt-auto rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
          Universidad del Quindío · Ingeniería de Sistemas y Computación · 2026-2
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-background/85 px-4 backdrop-blur md:px-6">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Abrir menú">
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-4">
              <SheetTitle className="sr-only">Navegación</SheetTitle>
              <div className="flex flex-col gap-6 pt-2">
                <Brand />
                <NavItems onNavigate={() => setOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>
          <p className="truncate text-sm font-medium">Análisis de algoritmos en el contexto de la bibliometría</p>
          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" size="sm" asChild>
              <a href="/docs" target="_blank" rel="noreferrer">
                API
              </a>
            </Button>
            {meta?.report_available && (
              <Button variant="ghost" size="sm" asChild>
                <a href="/informe.pdf" target="_blank" rel="noreferrer">
                  Informe PDF
                </a>
              </Button>
            )}
            <ThemeToggle />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
