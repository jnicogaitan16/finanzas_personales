"use client"
import { TrendingDown, TrendingUp, Wallet, BarChart3 } from "lucide-react"
import { formatCOP } from "@/lib/format"

interface KpiProps {
  gastoMes: number
  ingresoMes: number
  gastoMesAnterior: number
}

export function KpiCards({ gastoMes, ingresoMes, gastoMesAnterior }: KpiProps) {
  const balance = ingresoMes - gastoMes
  const cambio = gastoMesAnterior > 0
    ? Math.round(((gastoMes / gastoMesAnterior) - 1) * 100)
    : 0

  const cards = [
    {
      label: "Gasto del mes",
      value: formatCOP(gastoMes),
      icon: TrendingDown,
      color: "text-rose-400",
    },
    {
      label: "Ingreso del mes",
      value: formatCOP(ingresoMes),
      icon: TrendingUp,
      color: "text-primary",
    },
    {
      label: "Balance",
      value: formatCOP(balance),
      icon: Wallet,
      color: balance >= 0 ? "text-primary" : "text-rose-400",
    },
    {
      label: "vs mes anterior",
      value: `${cambio > 0 ? "+" : ""}${cambio}%`,
      icon: BarChart3,
      color: cambio <= 0 ? "text-primary" : "text-rose-400",
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-card border border-border rounded-xl p-4"
        >
          <div className="flex items-center gap-2 text-muted-foreground text-sm mb-2">
            <card.icon className="w-4 h-4" />
            {card.label}
          </div>
          <div className={`text-xl font-bold tabular-nums ${card.color}`}>
            {card.value}
          </div>
        </div>
      ))}
    </div>
  )
}
