"use client"
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"
import { TableHead } from "@/components/ui/table"
import type { SortState } from "@/hooks/use-sort"

interface SortableHeadProps {
  label: string
  sortKey: string
  sort: SortState | null
  onToggle: (key: string) => void
  className?: string
}

export function SortableHead({ label, sortKey, sort, onToggle, className = "" }: SortableHeadProps) {
  const active = sort?.key === sortKey
  const Icon = active
    ? sort.direction === "asc" ? ArrowUp : ArrowDown
    : ArrowUpDown

  return (
    <TableHead
      className={`cursor-pointer select-none hover:text-foreground transition-colors ${className}`}
      onClick={() => onToggle(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <Icon className={`w-3 h-3 ${active ? "text-primary" : "text-muted-foreground/50"}`} />
      </span>
    </TableHead>
  )
}
