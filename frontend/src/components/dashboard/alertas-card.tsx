"use client"
import { useCallback } from "react"
import { AlertTriangle, Bell, CreditCard, AlertCircle } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"

interface Alerta {
  tipo: string
  nivel: string
  titulo: string
  detalle: string
}

const ICONS: Record<string, typeof Bell> = {
  presupuesto: AlertTriangle,
  pago_tarjeta: CreditCard,
  deuda_vencida: AlertCircle,
}

const COLORS: Record<string, { bg: string; border: string; text: string }> = {
  critico: { bg: "bg-rose-500/10", border: "border-rose-500/30", text: "text-rose-400" },
  advertencia: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400" },
  info: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" },
}

export function AlertasCard() {
  const fetchAlertas = useCallback(() => api.get<Alerta[]>("/api/alertas"), [])
  const { data: alertas } = usePolling(fetchAlertas, 30000)

  if (!alertas || alertas.length === 0) return null

  return (
    <div className="space-y-2">
      {alertas.map((a, idx) => {
        const Icon = ICONS[a.tipo] || Bell
        const colors = COLORS[a.nivel] || COLORS.info
        return (
          <div key={idx} className={`${colors.bg} border ${colors.border} rounded-2xl px-4 py-3 flex items-start gap-3`}>
            <Icon className={`w-5 h-5 ${colors.text} shrink-0 mt-0.5`} />
            <div className="min-w-0">
              <p className={`text-sm font-medium ${colors.text}`}>{a.titulo}</p>
              <p className="text-xs text-gray-400 mt-0.5">{a.detalle}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
