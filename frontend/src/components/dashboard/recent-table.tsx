"use client"
import { formatCOP, formatDate } from "@/lib/format"
import { getCategoryColor } from "@/lib/constants"
import type { Movimiento } from "@/lib/types"

interface Props {
  movimientos: Movimiento[]
}

export function RecentTable({ movimientos }: Props) {
  const recientes = movimientos.slice(0, 10)

  if (!recientes.length) {
    return null
  }

  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden">
      <h3 className="text-xs text-gray-400 uppercase tracking-wide px-5 pt-5 pb-3">
        Ultimos movimientos
      </h3>
      <div className="space-y-0">
        {recientes.map((m) => (
          <div
            key={m.id}
            className="flex items-center gap-3 px-5 py-3 border-b border-white/5 last:border-0"
          >
            {/* Category dot */}
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold"
              style={{
                backgroundColor: getCategoryColor(m.categoria) + "20",
                color: getCategoryColor(m.categoria),
              }}
            >
              {(m.categoria || "?")[0]}
            </div>
            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-100 truncate">
                {m.descripcion || m.categoria || "Sin descripcion"}
              </p>
              <p className="text-xs text-gray-500">{m.categoria} · {formatDate(m.fecha_gasto)}</p>
            </div>
            {/* Amount */}
            <p className={`text-sm font-semibold tabular-nums shrink-0 ${
              m.tipo === "ingreso" ? "text-emerald-400" : "text-rose-400"
            }`}>
              {m.tipo === "ingreso" ? "+" : "-"}{formatCOP(m.monto_cop)}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
