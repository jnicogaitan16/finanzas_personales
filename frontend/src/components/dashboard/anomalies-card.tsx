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
  const catStats: Record<string, { total: number; count: number }> = {}
  for (const m of movimientos) {
    if (m.tipo !== "gasto" || !m.categoria) continue
    if (!catStats[m.categoria]) catStats[m.categoria] = { total: 0, count: 0 }
    catStats[m.categoria].total += m.monto_cop
    catStats[m.categoria].count += 1
  }

  const anomalies: Anomaly[] = []
  for (const m of movimientos) {
    if (m.tipo !== "gasto" || !m.categoria || !m.fecha_gasto?.startsWith(monthKey)) continue
    const stats = catStats[m.categoria]
    if (!stats || stats.count < 3) continue
    const avg = stats.total / stats.count
    const ratio = m.monto_cop / avg
    if (ratio >= 2) {
      anomalies.push({ movimiento: m, promedio: Math.round(avg), ratio })
    }
  }

  if (anomalies.length === 0) return null

  anomalies.sort((a, b) => b.ratio - a.ratio)
  const top = anomalies.slice(0, 5)

  return (
    <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-5">
      <div className="flex items-center gap-2 text-amber-400 text-xs uppercase tracking-wide mb-3">
        <AlertTriangle className="w-4 h-4" />
        Gastos inusuales este mes
      </div>
      <div className="space-y-2">
        {top.map((a) => (
          <div
            key={a.movimiento.id}
            className="flex items-center justify-between text-sm py-2 border-b border-white/5 last:border-0"
          >
            <div className="flex-1 min-w-0">
              <span className="font-medium text-gray-100">{a.movimiento.descripcion || a.movimiento.categoria}</span>
              <span className="text-gray-500 ml-2 text-xs">
                {a.movimiento.categoria} · {formatDate(a.movimiento.fecha_gasto)}
              </span>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-3">
              <span className="text-rose-400 font-semibold tabular-nums">
                {formatCOP(a.movimiento.monto_cop)}
              </span>
              <span className="text-[11px] text-amber-400 bg-amber-500/15 px-1.5 py-0.5 rounded-lg font-medium">
                {a.ratio.toFixed(1)}x
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
