"use client"
import { useCallback } from "react"
import { Heart, Check, X } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"

interface SaludFinanciera {
  score: number
  max_score: number
  nivel: string
  detalles: { criterio: string; cumple: boolean; detalle: string }[]
}

const NIVEL_COLORS: Record<string, string> = {
  excelente: "text-violet-400",
  bueno: "text-cyan-400",
  regular: "text-amber-400",
  critico: "text-rose-400",
}

const RING_COLORS: Record<string, string> = {
  excelente: "#8b5cf6",
  bueno: "#06b6d4",
  regular: "#fbbf24",
  critico: "#fb7185",
}

export function ScoreCard() {
  const fetchSalud = useCallback(() => api.get<SaludFinanciera>("/api/salud-financiera"), [])
  const { data } = usePolling(fetchSalud, 30000)

  if (!data) return null

  const pct = data.score / data.max_score
  const circumference = 2 * Math.PI * 40
  const strokeDashoffset = circumference * (1 - pct)
  const color = RING_COLORS[data.nivel] || RING_COLORS.regular

  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Heart className="w-4 h-4 text-gray-400" />
        <h3 className="text-xs text-gray-400 uppercase tracking-wide">Salud financiera</h3>
      </div>

      <div className="flex items-center gap-6">
        {/* Ring */}
        <div className="relative w-24 h-24 shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
            <circle
              cx="50" cy="50" r="40"
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-700"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-2xl font-bold ${NIVEL_COLORS[data.nivel]}`}>{data.score}</span>
            <span className="text-[10px] text-gray-500">/{data.max_score}</span>
          </div>
        </div>

        {/* Criteria */}
        <div className="flex-1 space-y-2">
          {data.detalles.map((d, i) => (
            <div key={i} className="flex items-start gap-2">
              {d.cumple ? (
                <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <X className="w-4 h-4 text-gray-500 shrink-0 mt-0.5" />
              )}
              <div className="min-w-0">
                <p className={`text-xs font-medium ${d.cumple ? "text-gray-200" : "text-gray-500"}`}>{d.criterio}</p>
                <p className="text-[11px] text-gray-500 truncate">{d.detalle}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
