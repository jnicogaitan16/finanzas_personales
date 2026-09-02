import { useState, useMemo } from "react"

export type SortDirection = "asc" | "desc"

export interface SortState {
  key: string
  direction: SortDirection
}

export function useSort<T>(items: T[], defaultKey?: string) {
  const [sort, setSort] = useState<SortState | null>(
    defaultKey ? { key: defaultKey, direction: "desc" } : null,
  )

  function toggle(key: string) {
    setSort((prev) => {
      if (prev?.key === key) {
        return prev.direction === "desc"
          ? { key, direction: "asc" }
          : null // third click clears sort
      }
      return { key, direction: "desc" }
    })
  }

  const sorted = useMemo(() => {
    if (!sort) return items
    const { key, direction } = sort
    return [...items].sort((a, b) => {
      const va = (a as Record<string, unknown>)[key]
      const vb = (b as Record<string, unknown>)[key]

      // nulls last
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1

      let cmp = 0
      if (typeof va === "number" && typeof vb === "number") {
        cmp = va - vb
      } else {
        cmp = String(va).localeCompare(String(vb), "es", { numeric: true })
      }

      return direction === "asc" ? cmp : -cmp
    })
  }, [items, sort])

  return { sorted, sort, toggle }
}
