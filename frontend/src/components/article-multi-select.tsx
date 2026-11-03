import { Check, ChevronsUpDown, X } from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { authorsShort } from "@/lib/format"
import type { Article } from "@/lib/types"
import { cn } from "@/lib/utils"

interface Props {
  articles: Article[]
  value: number[]
  onChange: (ids: number[]) => void
  max?: number
}

export function ArticleMultiSelect({ articles, value, onChange, max = 20 }: Props) {
  const [open, setOpen] = useState(false)
  const toggle = (id: number) => {
    if (value.includes(id)) onChange(value.filter((v) => v !== id))
    else if (value.length < max) onChange([...value, id].sort((a, b) => a - b))
  }
  const byId = new Map(articles.map((a) => [a.id, a]))

  return (
    <div className="space-y-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" role="combobox" aria-expanded={open} className="w-full justify-between" data-testid="article-select">
            <span className="truncate text-left font-normal">
              {value.length === 0 ? "Seleccione dos o más artículos…" : `${value.length} artículos seleccionados`}
            </span>
            <ChevronsUpDown className="size-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[min(92vw,640px)] p-0" align="start">
          <Command>
            <CommandInput placeholder="Buscar por título, autor o código…" />
            <CommandList className="max-h-80">
              <CommandEmpty>Sin resultados.</CommandEmpty>
              <CommandGroup>
                {articles.map((a) => {
                  const selected = value.includes(a.id)
                  return (
                    <CommandItem
                      key={a.id}
                      value={`${a.code} ${a.title} ${a.authors.join(" ")}`}
                      onSelect={() => toggle(a.id)}
                      data-testid={`option-${a.id}`}
                    >
                      <Check className={cn("size-4 shrink-0", selected ? "opacity-100" : "opacity-0")} />
                      <span className="w-9 shrink-0 font-mono text-xs text-muted-foreground">{a.code}</span>
                      <span className="flex min-w-0 flex-col">
                        <span className="truncate text-sm">{a.title}</span>
                        <span className="truncate text-xs text-muted-foreground">
                          {authorsShort(a.authors)} · {a.year}
                        </span>
                      </span>
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((id) => {
            const a = byId.get(id)
            return (
              <Badge key={id} variant="secondary" className="gap-1 pr-1">
                <span className="font-mono">{a?.code}</span>
                <span className="max-w-48 truncate font-normal">{a?.short_title}</span>
                <button
                  type="button"
                  aria-label={`Quitar ${a?.code}`}
                  className="rounded-sm p-0.5 hover:bg-background/70"
                  onClick={() => toggle(id)}
                >
                  <X className="size-3" />
                </button>
              </Badge>
            )
          })}
        </div>
      )}
    </div>
  )
}
