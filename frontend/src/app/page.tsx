"use client"
import { useCallback, useMemo, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { isInMonth } from "@/lib/format"
import type { Movimiento, Usuario } from "@/lib/types"
import { KpiCards } from "@/components/dashboard/kpi-cards"
import { CategoryBar } from "@/components/dashboard/category-bar"
import { DistributionDonut } from "@/components/dashboard/distribution-donut"
import { TrendLine } from "@/components/dashboard/trend-line"
import { RecentTable } from "@/components/dashboard/recent-table"

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

export default function DashboardPage() {
  const fetchMovimientos = useCallback(() => api.get<Movimiento[]>("/api/movimientos?limit=500"), [])
  const { data: movimientos, loading } = usePolling(fetchMovimientos, 5000)

  const fetchUsuarios = useCallback(() => api.get<Usuario[]>("/api/usuarios"), [])
  const { data: usuarios } = usePolling(fetchUsuarios, 30000)

  const [selectedUser, setSelectedUser] = useState("todos")
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const d = new Date()
    return { year: d.getFullYear(), month: d.getMonth() }
  })

  const monthKey = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`
  const monthLabel = `${MESES[selectedMonth.month]} ${selectedMonth.year}`

  function prevMonth() {
    setSelectedMonth(m => {
      if (m.month === 0) return { year: m.year - 1, month: 11 }
      return { ...m, month: m.month - 1 }
    })
  }
  function nextMonth() {
    setSelectedMonth(m => {
      if (m.month === 11) return { year: m.year + 1, month: 0 }
      return { ...m, month: m.month + 1 }
    })
  }

  const filtered = useMemo(() => {
    if (!movimientos) return []
    return movimientos.filter(m => {
      if (selectedUser !== "todos" && String(m.user_id) !== selectedUser) return false
      return true
    })
  }, [movimientos, selectedUser])

  const { gastoMes, ingresoMes, gastoMesAnterior, categoryData, trendData } = useMemo(() => {
    if (!filtered.length) return { gastoMes: 0, ingresoMes: 0, gastoMesAnterior: 0, categoryData: [], trendData: [] }

    let gastoMes = 0
    let ingresoMes = 0
    for (const m of filtered) {
      if (!isInMonth(m.fecha_gasto, monthKey)) continue
      if (m.tipo === "gasto") gastoMes += m.monto_cop
      else if (m.tipo === "ingreso") ingresoMes += m.monto_cop
    }

    const prevDate = new Date(selectedMonth.year, selectedMonth.month - 1, 1)
    const mesAnterior = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, "0")}`
    let gastoMesAnterior = 0
    for (const m of filtered) {
      if (isInMonth(m.fecha_gasto, mesAnterior) && m.tipo === "gasto") {
        gastoMesAnterior += m.monto_cop
      }
    }

    const catMap: Record<string, number> = {}
    for (const m of filtered) {
      if (m.tipo !== "gasto" || !isInMonth(m.fecha_gasto, monthKey)) continue
      const cat = m.categoria || "Otros"
      catMap[cat] = (catMap[cat] || 0) + m.monto_cop
    }
    const categoryData = Object.entries(catMap).map(([name, total]) => ({ name, total }))

    const mesesMap: Record<string, { gasto: number; ingreso: number }> = {}
    for (const m of filtered) {
      if (!m.fecha_gasto) continue
      const k = m.fecha_gasto.substring(0, 7)
      if (!mesesMap[k]) mesesMap[k] = { gasto: 0, ingreso: 0 }
      if (m.tipo === "gasto") mesesMap[k].gasto += m.monto_cop
      else if (m.tipo === "ingreso") mesesMap[k].ingreso += m.monto_cop
    }
    const trendData = Object.entries(mesesMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-6)
      .map(([mes, v]) => ({ mes: mes.substring(5), ...v }))

    return { gastoMes, ingresoMes, gastoMesAnterior, categoryData, trendData }
  }, [filtered, monthKey, selectedMonth.year, selectedMonth.month])

  if (loading && !movimientos) {
    return <p className="text-muted-foreground">Cargando datos...</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-3">
          {/* User filter */}
          <select
            value={selectedUser}
            onChange={(e) => setSelectedUser(e.target.value)}
            className="bg-card border border-border rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="todos">Todos</option>
            {(usuarios ?? []).map(u => (
              <option key={u.id} value={String(u.id)}>{u.nombre}</option>
            ))}
          </select>

          {/* Month selector */}
          <div className="flex items-center gap-1">
            <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium min-w-[100px] text-center">{monthLabel}</span>
            <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <KpiCards
        gastoMes={gastoMes}
        ingresoMes={ingresoMes}
        gastoMesAnterior={gastoMesAnterior}
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <CategoryBar data={categoryData} />
        </div>
        <div className="lg:col-span-2">
          <DistributionDonut data={categoryData} />
        </div>
      </div>

      <TrendLine data={trendData} />

      <RecentTable movimientos={filtered} />
    </div>
  )
}
