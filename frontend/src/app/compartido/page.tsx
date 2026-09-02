"use client"

import { useCallback, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { formatCOP } from "@/lib/format"
import type { BalanceCompartido } from "@/lib/types"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

export default function CompartidoPage() {
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

  const fetchBalance = useCallback(
    () => api.get<BalanceCompartido>(`/api/compartido?mes=${monthKey}`),
    [monthKey],
  )

  const { data: balance, loading } = usePolling<BalanceCompartido>(fetchBalance, 5000)

  // Split detalles by "debe" direction
  const detalles = balance?.detalles ?? []

  // Get the two unique users
  const userNames = balance ? Object.values(balance.usuarios) : []
  const user1 = userNames[0] ?? "Usuario 1"
  const user2 = userNames[1] ?? "Usuario 2"

  // Group: items where user2 debe to user1, and vice versa
  const deudaDeUser2AUser1 = detalles.filter(d => d.debe === user2)
  const deudaDeUser1AUser2 = detalles.filter(d => d.debe === user1)

  const totalUser2 = deudaDeUser2AUser1.reduce((s, d) => s + d.mitad, 0)
  const totalUser1 = deudaDeUser1AUser2.reduce((s, d) => s + d.mitad, 0)

  function fuenteBadge(fuente: string) {
    switch (fuente) {
      case "fijo":
        return (
          <span className="px-2 py-0.5 rounded-full text-xs bg-blue-400/20 text-blue-400">
            Fijo
          </span>
        )
      case "movimiento":
        return (
          <span className="px-2 py-0.5 rounded-full text-xs bg-primary/20 text-primary">
            Movimiento
          </span>
        )
      case "deuda":
        return (
          <span className="px-2 py-0.5 rounded-full text-xs bg-rose-400/20 text-rose-400">
            Deuda
          </span>
        )
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-xs bg-secondary text-muted-foreground">
            {fuente}
          </span>
        )
    }
  }

  function renderTable(items: typeof detalles, total: number) {
    return (
      <div className="rounded-xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Concepto</TableHead>
                <TableHead className="text-right">Valor compra</TableHead>
                <TableHead className="text-right">Cuota mes</TableHead>
                <TableHead className="text-right">Mitad</TableHead>
                <TableHead>Fuente</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((d, i) => (
                <TableRow key={i}>
                  <TableCell>{d.concepto}</TableCell>
                  <TableCell className="text-right tabular-nums text-muted-foreground">
                    {d.valor_compra && d.valor_compra !== d.total ? formatCOP(d.valor_compra) : ""}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{formatCOP(d.total)}</TableCell>
                  <TableCell className="text-right tabular-nums font-medium text-rose-400">
                    {formatCOP(d.mitad)}
                  </TableCell>
                  <TableCell>{fuenteBadge(d.fuente)}</TableCell>
                </TableRow>
              ))}
              {items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-6">
                    Sin gastos compartidos
                  </TableCell>
                </TableRow>
              )}
              {items.length > 0 && (
                <TableRow className="border-t-2 border-border">
                  <TableCell className="font-semibold">Total</TableCell>
                  <TableCell />
                  <TableCell />
                  <TableCell className="text-right tabular-nums font-semibold text-rose-400">
                    {formatCOP(total)}
                  </TableCell>
                  <TableCell />
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Gastos Compartidos</h1>
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

      {loading && !balance && (
        <p className="text-muted-foreground">Cargando...</p>
      )}

      {balance && (
        <>
          {/* Balance card */}
          <div className="rounded-xl border border-border bg-card p-6 text-center space-y-2">
            <p className="text-sm text-muted-foreground">Balance neto</p>
            <p className={`text-3xl font-bold tabular-nums ${balance.balance_neto > 0 ? "text-rose-400" : "text-primary"}`}>
              {formatCOP(Math.abs(balance.balance_neto))}
            </p>
            <p className="text-sm text-muted-foreground">
              {balance.quien_debe
                ? `${balance.quien_debe} debe pagar`
                : "Estan a mano"}
            </p>
          </div>

          {/* Section: Deuda de User2 a User1 */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">
              Deuda de {user2} a {user1}
            </h2>
            {renderTable(deudaDeUser2AUser1, totalUser2)}
          </div>

          {/* Section: Deuda de User1 a User2 */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">
              Deuda de {user1} a {user2}
            </h2>
            {renderTable(deudaDeUser1AUser2, totalUser1)}
          </div>
        </>
      )}
    </div>
  )
}
