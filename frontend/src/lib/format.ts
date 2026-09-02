export function formatCOP(n: number): string {
  return "$" + n.toLocaleString("es-CO")
}

export function formatDate(iso: string | null): string {
  if (!iso) return ""
  return iso.split("T")[0]
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return ""
  return iso.replace("T", " ").substring(0, 19)
}

export function currentMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
}

export function isInMonth(dateStr: string | null, month: string): boolean {
  if (!dateStr) return false
  return dateStr.startsWith(month)
}
