"use client"
import { AlertTriangle } from "lucide-react"
import { formatCOP, formatDate } from "@/lib/format"
import type { Movimiento } from "@/lib/types"

interface AnomaliesProps {
  movimientos: Movimiento[]
  monthKey: string
}

interface Anomaly {
  movimiento: Movimiento
  promedio: number
  ratio: number
}

export function AnomaliesCard({ movimientos, monthKey }: AnomaliesProps) {
  // Calculate average per category from all historical data
  const catStats: Record<string, { total: number; count: number }> = {}
  for (const m of movimientos) {
    if (m.tipo !== "gasto" || !m.categoria) continue
    if (!catStats[m.categoria]) catStats[m.categoria] = { total: 0, count: 0 }
    catStats[m.categoria].total += m.monto_cop
    catStats[m.categoria].count += 1
  }

  // Find anomalies: current month expenses that are 2x+ the category average
  const anomalies: Anomaly[] = []
  for (const m of movimientos) {
    if (m.tipo !== "gasto" || !m.categoria || !m.fecha_gasto?.startsWith(monthKey)) continue
    const stats = catStats[m.categoria]
    if (!stats || stats.count < 3) continue // need at least 3 data points
    const avg = stats.total / stats.count
    const ratio = m.monto_cop / avg
    if (ratio >= 2) {
      anomalies.push({ movimiento: m, promedio: Math.round(avg), ratio })
    }
  }

  if (anomalies.length === 0) return null

  // Sort by ratio descending, show top 5
  anomalies.sort((a, b) => b.ratio - a.ratio)
  const top = anomalies.slice(0, 5)

  return (
    <div className="bg-card border border-amber-500/30 rounded-xl p-5">
      <div className="flex items-center gap-2 text-amber-500 text-sm mb-3">
        <AlertTriangle className="w-4 h-4" />
        Gastos inusuales este mes
      </div>
      <div className="space-y-2">
        {top.map((a) => (
          <div
            key={a.movimiento.id}
            className="flex items-center justify-between text-sm py-1.5 border-b border-border last:border-0"
          >
            <div className="flex-1 min-w-0">
              <span className="font-medium">{a.movimiento.descripcion || a.movimiento.categoria}</span>
              <span className="text-muted-foreground ml-2 text-xs">
                {a.movimiento.categoria} · {formatDate(a.movimiento.fecha_gasto)}
              </span>
            </div>
            <div className="flex items-center gap-3 shrink-0 ml-3">
              <span className="text-rose-400 font-medium tabular-nums">
                {formatCOP(a.movimiento.monto_cop)}
              </span>
              <span className="text-xs text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">
                {a.ratio.toFixed(1)}x prom
              </span>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Gastos que superan 2x el promedio historico de su categoria
      </p>
    </div>
  )
}
