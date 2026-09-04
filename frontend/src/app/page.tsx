"use client"
import { useCallback, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown, CreditCard, Users } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useUserFilter } from "@/hooks/use-user-filter"
import { isInMonth, formatCOP } from "@/lib/format"
import { getCategoryColor } from "@/lib/constants"
import type { Movimiento } from "@/lib/types"
import { AlertasCard } from "@/components/dashboard/alertas-card"
import { ScoreCard } from "@/components/dashboard/score-card"
import { CashflowCard } from "@/components/dashboard/cashflow-card"
import { DashboardSkeleton } from "@/components/ui/skeleton"

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

export default function DashboardPage() {
  const router = useRouter()
  const { selectedUser, usuarios } = useUserFilter()
  const grupoLleno = usuarios.length >= 2
  const fetchMovimientos = useCallback(() => api.get<Movimiento[]>("/api/movimientos?limit=500"), [])
  const { data: movimientos, loading } = usePolling(fetchMovimientos, 5000)

  const [selectedMonth, setSelectedMonth] = useState(() => {
    const d = new Date()
    return { year: d.getFullYear(), month: d.getMonth() }
  })

  const monthKey = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`
  const monthLabel = `${MESES[selectedMonth.month]} ${selectedMonth.year}`

  function prevMonth() {
    setSelectedMonth(m => m.month === 0 ? { year: m.year - 1, month: 11 } : { ...m, month: m.month - 1 })
  }
  function nextMonth() {
    setSelectedMonth(m => m.month === 11 ? { year: m.year + 1, month: 0 } : { ...m, month: m.month + 1 })
  }

  const filtered = useMemo(() => {
    if (!movimientos) return []
    return movimientos.filter(m => {
      if (selectedUser !== "todos" && String(m.user_id) !== selectedUser) return false
      return true
    })
  }, [movimientos, selectedUser])

  const { gastoMes, ingresoMes, categoryData } = useMemo(() => {
    if (!filtered.length) return { gastoMes: 0, ingresoMes: 0, categoryData: [] as { name: string; total: number }[] }

    let gastoMes = 0
    let ingresoMes = 0
    const catMap: Record<string, number> = {}
    for (const m of filtered) {
      if (!isInMonth(m.fecha_gasto, monthKey)) continue
      if (m.tipo === "gasto") {
        gastoMes += m.monto_cop
        const cat = m.categoria || "Otros"
        catMap[cat] = (catMap[cat] || 0) + m.monto_cop
      } else if (m.tipo === "ingreso") {
        ingresoMes += m.monto_cop
      }
    }
    const categoryData = Object.entries(catMap)
      .map(([name, total]) => ({ name, total }))
      .sort((a, b) => b.total - a.total)

    return { gastoMes, ingresoMes, categoryData }
  }, [filtered, monthKey])

  const recientes = filtered.filter(m => isInMonth(m.fecha_gasto, monthKey)).slice(0, 5)

  if (loading && !movimientos) return <DashboardSkeleton />

  const balance = ingresoMes - gastoMes
  const totalCat = categoryData.reduce((s, c) => s + c.total, 0)

  return (
    <div className="space-y-5 animate-fade-in">
      <h1 className="sr-only">Dashboard</h1>

      {/* Balance + filtros */}
      <div className="text-center">
        <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">Balance del mes</p>
        <p className={`text-4xl font-bold tabular-nums ${balance >= 0 ? "text-violet-400" : "text-rose-400"}`}>
          {formatCOP(balance)}
        </p>
      </div>

      {/* Selector de mes */}
      <div className="flex items-center justify-center gap-3 bg-white/5 rounded-xl py-2">
        <button onClick={prevMonth} className="p-1 rounded-lg hover:bg-white/10 text-gray-400">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="text-sm font-semibold text-gray-100 min-w-[100px] text-center">{monthLabel}</span>
        <button onClick={nextMonth} className="p-1 rounded-lg hover:bg-white/10 text-gray-400">
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* 4 módulos clickeables */}
      <div className="grid grid-cols-2 gap-3 stagger-children">
        <div
          onClick={() => router.push("/ingresos")}
          className="bg-gradient-to-br from-emerald-500/15 to-emerald-600/5 border border-white/5 rounded-2xl p-4 cursor-pointer active:scale-[0.97] transition-transform"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Ingresos</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-lg font-bold text-emerald-400 tabular-nums">{formatCOP(ingresoMes)}</p>
        </div>

        <div
          onClick={() => router.push("/movimientos")}
          className="bg-gradient-to-br from-rose-500/15 to-rose-600/5 border border-white/5 rounded-2xl p-4 cursor-pointer active:scale-[0.97] transition-transform"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Gastos</span>
            <TrendingDown className="w-4 h-4 text-rose-400" />
          </div>
          <p className="text-lg font-bold text-rose-400 tabular-nums">{formatCOP(gastoMes)}</p>
        </div>

        <div
          onClick={() => router.push("/tarjetas")}
          className="bg-gradient-to-br from-violet-500/15 to-violet-600/5 border border-white/5 rounded-2xl p-4 cursor-pointer active:scale-[0.97] transition-transform"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Tarjetas</span>
            <CreditCard className="w-4 h-4 text-violet-400" />
          </div>
          <p className="text-sm text-violet-400">Ver cuotas y TC</p>
        </div>

        {grupoLleno && (
          <div
            onClick={() => router.push("/compartido")}
            className="bg-gradient-to-br from-cyan-500/15 to-cyan-600/5 border border-white/5 rounded-2xl p-4 cursor-pointer active:scale-[0.97] transition-transform"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-xs uppercase tracking-wide">Compartido</span>
              <Users className="w-4 h-4 text-cyan-400" />
            </div>
            <p className="text-sm text-cyan-400">Balance hogar</p>
          </div>
        )}
      </div>

      {/* Alertas */}
      <AlertasCard />

      {/* ¿En qué gastas? — barras de categoría */}
      {categoryData.length > 0 && (
        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
          <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-4">En que gastas</h3>
          <div className="space-y-3">
            {categoryData.slice(0, 6).map(cat => {
              const pct = totalCat > 0 ? Math.round((cat.total / totalCat) * 100) : 0
              return (
                <div key={cat.name} className="flex items-center gap-3">
                  <span className="text-sm text-gray-300 w-24 truncate">{cat.name}</span>
                  <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: getCategoryColor(cat.name) }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 w-8 text-right tabular-nums">{pct}%</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Flujo de caja + Score lado a lado */}
      <div className="grid grid-cols-1 gap-4">
        <CashflowCard />
        <ScoreCard />
      </div>

      {/* Últimos movimientos */}
      {recientes.length > 0 && (
        <div className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between px-5 pt-4 pb-2">
            <h3 className="text-xs text-gray-400 uppercase tracking-wide">Ultimos movimientos</h3>
            <button onClick={() => router.push("/movimientos")} className="text-xs text-violet-400">Ver todos</button>
          </div>
          {recientes.map(m => (
            <div key={m.id} className="flex items-center gap-3 px-5 py-3 border-b border-white/5 last:border-0">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shrink-0"
                style={{
                  backgroundColor: getCategoryColor(m.categoria) + "20",
                  color: getCategoryColor(m.categoria),
                }}
              >
                {(m.categoria || "?")[0]}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-100 truncate">{m.descripcion || m.categoria || "Sin desc"}</p>
                <p className="text-xs text-gray-500">{m.fecha_gasto}</p>
              </div>
              <p className={`text-sm font-semibold tabular-nums shrink-0 ${m.tipo === "ingreso" ? "text-emerald-400" : "text-rose-400"}`}>
                {m.tipo === "ingreso" ? "+" : "-"}{formatCOP(m.monto_cop)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
