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
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 text-muted-foreground text-sm mb-4">
        <Target className="w-4 h-4" />
        Proyeccion al cierre del mes ({dayOfMonth}/{daysInMonth} dias)
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Gasto proyectado</p>
          <p className="text-lg font-bold tabular-nums text-rose-400">{formatCOP(gastoProyectado)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Ingreso proyectado</p>
          <p className="text-lg font-bold tabular-nums text-primary">{formatCOP(ingresoProyectado)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Balance proyectado</p>
          <p className={`text-lg font-bold tabular-nums ${balanceProyectado >= 0 ? "text-primary" : "text-rose-400"}`}>
            {formatCOP(balanceProyectado)}
          </p>
        </div>
      </div>
    </div>
  )
}
