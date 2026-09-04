"use client"

import { useCallback, useState } from "react"
import { ChevronLeft, ChevronRight, Users } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useAuth } from "@/hooks/use-auth"
import { useUserFilter } from "@/hooks/use-user-filter"
import { formatCOP } from "@/lib/format"
import type { BalanceCompartido } from "@/lib/types"

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

const FUENTE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  fijo: { bg: "bg-blue-400/15", text: "text-blue-400", label: "Fijo" },
  movimiento: { bg: "bg-violet-500/15", text: "text-violet-400", label: "Gasto" },
  cuota: { bg: "bg-cyan-400/15", text: "text-cyan-400", label: "Cuota" },
  deuda: { bg: "bg-rose-400/15", text: "text-rose-400", label: "Deuda" },
}

export default function CompartidoPage() {
  const { user } = useAuth()
  const { selectedUser, usuarios } = useUserFilter()
  const grupoLleno = usuarios.length >= 2

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

  const fetchBalance = useCallback(
    () => api.get<BalanceCompartido>(`/api/compartido?mes=${monthKey}`),
    [monthKey],
  )
  const { data: balance, loading } = usePolling<BalanceCompartido>(fetchBalance, 5000)

  if (!grupoLleno) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold text-gray-100">Compartido</h1>
        <div className="text-center py-16 text-gray-500">
          <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Necesitas al menos 2 miembros en tu grupo</p>
          <p className="text-sm mt-1">Invita a alguien desde Mi cuenta</p>
        </div>
      </div>
    )
  }

  const detalles = balance?.detalles ?? []
  const userNames = balance ? Object.values(balance.usuarios) : []
  const user1 = userNames[0] ?? "Usuario 1"
  const user2 = userNames[1] ?? "Usuario 2"

  const deudaDeUser2AUser1 = detalles.filter(d => d.debe === user2)
  const deudaDeUser1AUser2 = detalles.filter(d => d.debe === user1)
  const totalUser2 = deudaDeUser2AUser1.reduce((s, d) => s + d.mitad, 0)
  const totalUser1 = deudaDeUser1AUser2.reduce((s, d) => s + d.mitad, 0)

  const myName = user?.nombre
  const showSection1 = selectedUser === "todos" || myName === user1
  const showSection2 = selectedUser === "todos" || myName === user2

  function DeudaSection({ title, items, total }: { title: string; items: typeof detalles; total: number }) {
    return (
      <div>
        <h2 className="text-xs text-gray-400 uppercase tracking-wide mb-3">{title}</h2>
        {items.length === 0 ? (
          <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 text-center text-gray-500 text-sm">
            Sin gastos compartidos
          </div>
        ) : (
          <div className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden">
            {items.map((d, i) => {
              const style = FUENTE_STYLES[d.fuente] || { bg: "bg-white/10", text: "text-gray-400", label: d.fuente }
              return (
                <div key={i} className="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0">
                  <div className={`w-8 h-8 rounded-xl ${style.bg} flex items-center justify-center shrink-0`}>
                    <span className={`text-xs font-bold ${style.text}`}>{style.label[0]}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-100 truncate">{d.concepto}</p>
                    <p className="text-xs text-gray-500">{formatCOP(d.total)} · {style.label}</p>
                  </div>
                  <p className="text-sm font-semibold text-rose-400 tabular-nums shrink-0">
                    {formatCOP(d.mitad)}
                  </p>
                </div>
              )
            })}
            {/* Total */}
            <div className="flex items-center justify-between px-4 py-3 bg-white/[0.02] border-t border-white/10">
              <span className="text-sm font-medium text-gray-300">Total</span>
              <span className="text-base font-bold text-rose-400 tabular-nums">{formatCOP(total)}</span>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-100">Compartido</h1>
        <div className="flex items-center gap-1">
          <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-semibold text-gray-100 min-w-[100px] text-center">{monthLabel}</span>
          <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading && !balance && <p className="text-gray-400 text-sm">Cargando...</p>}

      {balance && (
        <>
          {/* Balance neto — solo en vista Hogar */}
          {selectedUser === "todos" && (
            <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-6 text-center">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Balance neto</p>
              <p className={`text-3xl font-bold tabular-nums ${balance.balance_neto !== 0 ? "text-rose-400" : "text-violet-400"}`}>
                {formatCOP(Math.abs(balance.balance_neto))}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                {balance.quien_debe || "Estan a mano"}
              </p>
            </div>
          )}

          {showSection1 && (
            <DeudaSection
              title={`Deuda de ${user2} a ${user1}`}
              items={deudaDeUser2AUser1}
              total={totalUser2}
            />
          )}

          {showSection2 && (
            <DeudaSection
              title={`Deuda de ${user1} a ${user2}`}
              items={deudaDeUser1AUser2}
              total={totalUser1}
            />
          )}
        </>
      )}
    </div>
  )
}
