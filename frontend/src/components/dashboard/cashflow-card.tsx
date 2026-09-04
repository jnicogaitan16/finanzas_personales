"use client"
import { useCallback } from "react"
import { ArrowDownLeft, ArrowUpRight, CreditCard, ShoppingBag, Wallet } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { formatCOP } from "@/lib/format"

interface FlujoCaja {
  ingresos_esperados: number
  gastos_fijos: number
  cuotas_tarjetas: number
  gasto_flexible_promedio: number
  disponible_estimado: number
}

export function CashflowCard() {
  const fetchFlujo = useCallback(() => api.get<FlujoCaja>("/api/flujo-caja"), [])
  const { data } = usePolling(fetchFlujo, 15000)

  if (!data || (data.ingresos_esperados === 0 && data.gastos_fijos === 0)) return null

  const items = [
    { label: "Ingresos esperados", value: data.ingresos_esperados, icon: ArrowDownLeft, color: "text-emerald-400", sign: "+" },
    { label: "Gastos fijos", value: data.gastos_fijos, icon: ArrowUpRight, color: "text-rose-400", sign: "-" },
    { label: "Cuotas tarjetas", value: data.cuotas_tarjetas, icon: CreditCard, color: "text-rose-400", sign: "-" },
    { label: "Gasto flexible (prom)", value: data.gasto_flexible_promedio, icon: ShoppingBag, color: "text-amber-400", sign: "-" },
  ]

  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Wallet className="w-4 h-4 text-gray-400" />
        <h3 className="text-xs text-gray-400 uppercase tracking-wide">Flujo de caja mensual</h3>
      </div>

      <div className="space-y-2.5">
        {items.map(item => (
          <div key={item.label} className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <item.icon className={`w-4 h-4 ${item.color}`} />
              <span className="text-sm text-gray-300">{item.label}</span>
            </div>
            <span className={`text-sm font-semibold tabular-nums ${item.color}`}>
              {item.sign}{formatCOP(item.value)}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
        <span className="text-sm font-medium text-gray-300">Disponible estimado</span>
        <span className={`text-lg font-bold tabular-nums ${data.disponible_estimado >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
          {formatCOP(data.disponible_estimado)}
        </span>
      </div>
    </div>
  )
}
