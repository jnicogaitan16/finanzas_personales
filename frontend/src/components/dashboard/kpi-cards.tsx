"use client"
import { useRouter } from "next/navigation"
import { TrendingDown, TrendingUp, Wallet, BarChart3 } from "lucide-react"
import { formatCOP } from "@/lib/format"

interface KpiProps {
  gastoMes: number
  ingresoMes: number
  gastoMesAnterior: number
}

export function KpiCards({ gastoMes, ingresoMes, gastoMesAnterior }: KpiProps) {
  const router = useRouter()
  const balance = ingresoMes - gastoMes
  const cambio = gastoMesAnterior > 0
    ? Math.round(((gastoMes / gastoMesAnterior) - 1) * 100)
    : 0

  const cards = [
    {
      label: "Ingresos",
      value: formatCOP(ingresoMes),
      icon: TrendingUp,
      gradient: "from-emerald-500/20 to-emerald-600/5",
      iconBg: "bg-emerald-500/20",
      iconColor: "text-emerald-400",
      valueColor: "text-emerald-400",
      href: "/ingresos",
    },
    {
      label: "Gastos",
      value: formatCOP(gastoMes),
      icon: TrendingDown,
      gradient: "from-rose-500/20 to-rose-600/5",
      iconBg: "bg-rose-500/20",
      iconColor: "text-rose-400",
      valueColor: "text-rose-400",
      href: "/movimientos",
    },
    {
      label: "Balance",
      value: formatCOP(balance),
      icon: Wallet,
      gradient: balance >= 0 ? "from-violet-500/20 to-violet-600/5" : "from-rose-500/20 to-rose-600/5",
      iconBg: balance >= 0 ? "bg-violet-500/20" : "bg-rose-500/20",
      iconColor: balance >= 0 ? "text-violet-400" : "text-rose-400",
      valueColor: balance >= 0 ? "text-violet-400" : "text-rose-400",
    },
    {
      label: "vs Mes anterior",
      value: `${cambio > 0 ? "+" : ""}${cambio}%`,
      icon: BarChart3,
      gradient: cambio <= 0 ? "from-cyan-500/20 to-cyan-600/5" : "from-amber-500/20 to-amber-600/5",
      iconBg: cambio <= 0 ? "bg-cyan-500/20" : "bg-amber-500/20",
      iconColor: cambio <= 0 ? "text-cyan-400" : "text-amber-400",
      valueColor: cambio <= 0 ? "text-cyan-400" : "text-amber-400",
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 stagger-children">
      {cards.map((card) => (
        <div
          key={card.label}
          onClick={card.href ? () => router.push(card.href) : undefined}
          className={`bg-gradient-to-br ${card.gradient} border border-white/5 rounded-2xl p-4 backdrop-blur-sm ${card.href ? "cursor-pointer active:scale-[0.97] transition-transform" : ""}`}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-400 text-xs font-medium uppercase tracking-wide">{card.label}</span>
            <div className={`w-8 h-8 rounded-xl ${card.iconBg} flex items-center justify-center`}>
              <card.icon className={`w-4 h-4 ${card.iconColor}`} />
            </div>
          </div>
          <div className={`text-xl font-bold tabular-nums ${card.valueColor}`}>{card.value}</div>
        </div>
      ))}
    </div>
  )
}
