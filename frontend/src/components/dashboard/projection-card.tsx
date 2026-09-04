"use client"
import { Target } from "lucide-react"
import { formatCOP } from "@/lib/format"

interface ProjectionProps {
  gastoMes: number
  ingresoMes: number
  selectedMonth: { year: number; month: number }
}

export function ProjectionCard({ gastoMes, ingresoMes, selectedMonth }: ProjectionProps) {
  const now = new Date()
  const isCurrentMonth =
    selectedMonth.year === now.getFullYear() && selectedMonth.month === now.getMonth()

  if (!isCurrentMonth || (gastoMes === 0 && ingresoMes === 0)) {
    return null
  }

  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(selectedMonth.year, selectedMonth.month + 1, 0).getDate()
  const ratio = daysInMonth / dayOfMonth

  const gastoProyectado = Math.round(gastoMes * ratio)
  const ingresoProyectado = Math.round(ingresoMes * ratio)
  const balanceProyectado = ingresoProyectado - gastoProyectado

  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
      <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide mb-4">
        <Target className="w-4 h-4" />
        Proyeccion al cierre ({dayOfMonth}/{daysInMonth} dias)
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-rose-500/10 rounded-xl p-3 text-center">
          <p className="text-[11px] text-gray-400 mb-1">Gasto</p>
          <p className="text-base font-bold tabular-nums text-rose-400">{formatCOP(gastoProyectado)}</p>
        </div>
        <div className="bg-emerald-500/10 rounded-xl p-3 text-center">
          <p className="text-[11px] text-gray-400 mb-1">Ingreso</p>
          <p className="text-base font-bold tabular-nums text-emerald-400">{formatCOP(ingresoProyectado)}</p>
        </div>
        <div className={`${balanceProyectado >= 0 ? "bg-blue-500/10" : "bg-rose-500/10"} rounded-xl p-3 text-center`}>
          <p className="text-[11px] text-gray-400 mb-1">Balance</p>
          <p className={`text-base font-bold tabular-nums ${balanceProyectado >= 0 ? "text-blue-400" : "text-rose-400"}`}>
            {formatCOP(balanceProyectado)}
          </p>
        </div>
      </div>
    </div>
  )
}
