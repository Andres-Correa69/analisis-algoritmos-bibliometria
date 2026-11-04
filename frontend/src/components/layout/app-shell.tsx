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

/**
 * Franja institucional bajo el encabezado: verde UQ, verde profundo y ámbar.
 * Bajo el menú lateral va sólo el verde, para que con la del encabezado se lea como una sola franja.
 */
function BrandStripe({ solid = false }: { solid?: boolean }) {
  if (solid) return <div className="h-[3px] bg-primary" aria-hidden />
  return (
    <div className="flex h-[3px]" aria-hidden>
      <span className="flex-[5] bg-primary" />
      <span className="flex-[2] bg-[#08590c]" />
      <span className="flex-1 bg-brand-amber" />
    </div>
  )
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5">
      <p className="px-3 pb-2 font-mono text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">Módulos</p>
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "relative flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors",
              "before:absolute before:inset-y-1 before:left-0 before:w-[3px] before:rounded-r-sm",
              isActive
                ? "bg-accent text-accent-foreground before:bg-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground before:bg-transparent",
            )
          }
        >
          <item.icon className="size-4 shrink-0" />
          <span className="flex flex-col leading-tight">
            <span className="font-medium">{item.label}</span>
            <span className="text-[11px] opacity-75">{item.hint}</span>
          </span>
        </NavLink>
      ))}
    </nav>
  )
}

function Brand({ inverted = false }: { inverted?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={cn(
          "flex size-8 items-center justify-center rounded-sm",
          inverted ? "bg-white/12 text-white ring-1 ring-white/25" : "bg-primary text-primary-foreground",
        )}
      >
        <BookOpenText className="size-4.5" />
      </div>
      <div className="leading-tight">
        <p className={cn("text-sm font-semibold", inverted && "text-white")}>Bibliometría</p>
        <p className={cn("text-[11px]", inverted ? "text-white/70" : "text-muted-foreground")}>Análisis de Algoritmos</p>
      </div>
    </div>
  )
}

const headerButton = "text-white/85 hover:bg-white/10 hover:text-white dark:hover:bg-white/10"

export function AppShell() {
  const [open, setOpen] = useState(false)
  const { meta } = useCorpus()
  return (
    <div className="min-h-svh bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r bg-sidebar lg:flex">
        <div className="flex h-14 shrink-0 items-center bg-brand-deep px-4">
          <Brand inverted />
        </div>
        <BrandStripe solid />
        <div className="flex flex-1 flex-col p-3 pt-5">
          <NavItems />
          <div className="mt-auto border-t px-3 pt-3 text-[11px] leading-relaxed text-muted-foreground">
            Universidad del Quindío
            <br />
            Ingeniería de Sistemas y Computación · 2026-2
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <div className="sticky top-0 z-20">
          <header className="flex h-14 items-center gap-3 bg-brand-deep px-4 text-white md:px-6">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className={cn("lg:hidden", headerButton)} aria-label="Abrir menú">
                  <Menu className="size-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-72 gap-0 p-0 [&>button]:text-white [&>button:hover]:bg-white/10 [&>button:hover]:text-white">
                <SheetTitle className="sr-only">Navegación</SheetTitle>
                <div className="flex h-14 items-center bg-brand-deep px-4">
                  <Brand inverted />
                </div>
                <BrandStripe />
                <div className="p-3 pt-5">
                  <NavItems onNavigate={() => setOpen(false)} />
                </div>
              </SheetContent>
            </Sheet>
            <p className="truncate text-sm font-medium tracking-tight">Análisis de algoritmos en el contexto de la bibliometría</p>
            <div className="ml-auto flex items-center gap-1">
              <Button variant="ghost" size="sm" className={headerButton} asChild>
                <a href="/docs" target="_blank" rel="noreferrer">
                  API
                </a>
              </Button>
              {meta?.report_available && (
                <Button variant="ghost" size="sm" className={headerButton} asChild>
                  <a href="/informe.pdf" target="_blank" rel="noreferrer">
                    Informe PDF
                  </a>
                </Button>
              )}
              <ThemeToggle className={headerButton} />
            </div>
          </header>
          <BrandStripe />
        </div>
        <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
