"use client"

import { useCallback, useState } from "react"
import { toast } from "sonner"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useUserFilter } from "@/hooks/use-user-filter"
import { useAuth } from "@/hooks/use-auth"
import { formatCOP } from "@/lib/format"
import type { Presupuesto, PresupuestoResumen, Categoria } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

interface FormState {
  categoria_id: string
  monto_limite_cop: string
  mes_vigente: string
}

const emptyForm: FormState = {
  categoria_id: "",
  monto_limite_cop: "",
  mes_vigente: "",
}

export default function PresupuestosPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)

  const [selectedMonth, setSelectedMonth] = useState(() => {
    const d = new Date()
    return { year: d.getFullYear(), month: d.getMonth() }
  })
  const { selectedUser: filterUser } = useUserFilter()
  const { userId } = useAuth()

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

  const {
    data: presupuestos,
    refetch: refetchPres,
  } = usePolling<Presupuesto[]>(() => api.get("/api/presupuestos"), 5000)

  const { data: categorias } = usePolling<Categoria[]>(
    () => api.get("/api/categorias"),
    5000,
  )

  // Determine which user_id to use for resumen
  const resumenUserId = filterUser !== "todos" ? filterUser : null

  const fetchResumen = useCallback(
    () =>
      resumenUserId
        ? api.get<PresupuestoResumen[]>(
            `/api/presupuestos/resumen?user_id=${resumenUserId}&mes=${monthKey}`,
          )
        : api.get<PresupuestoResumen[]>(
            `/api/presupuestos/resumen?mes=${monthKey}`,
          ),
    [resumenUserId, monthKey],
  )

  const { data: resumen, loading: loadingResumen } = usePolling<PresupuestoResumen[]>(
    fetchResumen,
    5000,
  )

  function openCreate() {
    setForm({ ...emptyForm, mes_vigente: monthKey })
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post("/api/presupuestos", {
        user_id: userId,
        categoria_id: Number(form.categoria_id),
        monto_limite_cop: Number(form.monto_limite_cop),
        mes_vigente: form.mes_vigente,
      })
      toast.success("Presupuesto creado")
      setDialogOpen(false)
      refetchPres()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al crear")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar este presupuesto?")) return
    try {
      await api.del(`/api/presupuestos/${id}`)
      toast.success("Presupuesto eliminado")
      refetchPres()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al eliminar")
    }
  }

  // Filter presupuestos for the current month for the delete list
  const presFiltered = (presupuestos ?? []).filter(p => {
    if (p.mes_vigente !== monthKey) return false
    if (filterUser !== "todos" && String(p.user_id) !== filterUser) return false
    return true
  })

  // Build a map of presupuesto id by categoria_id for delete buttons
  const presByCat: Record<number, Presupuesto> = {}
  for (const p of presFiltered) {
    presByCat[p.categoria_id] = p
  }

  function progressColor(pct: number) {
    if (pct > 100) return "bg-rose-400"
    if (pct >= 80) return "bg-yellow-400"
    return "bg-violet-500"
  }

  function progressTextColor(pct: number) {
    if (pct > 100) return "text-rose-400"
    if (pct >= 80) return "text-yellow-500"
    return "text-violet-400"
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-bold text-gray-100">Presupuestos</h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium min-w-[100px] text-center">{monthLabel}</span>
            <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {(filterUser === "todos" || filterUser === String(userId)) && (
            <Button onClick={openCreate}>Nuevo presupuesto</Button>
          )}
        </div>
      </div>

      {loadingResumen && !resumen && (
        <p className="text-gray-400">Cargando...</p>
      )}

      {resumen && resumen.length === 0 && (
        <p className="text-gray-400 text-center py-12">
          No hay presupuestos configurados para {monthLabel}
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {(resumen ?? []).map((r) => {
          const pct = Math.round(r.porcentaje)
          const barWidth = Math.min(pct, 100)
          const pres = presByCat[r.categoria_id]

          return (
            <div
              key={r.categoria_id}
              className="rounded-xl border border-white/5 bg-white/[0.03] p-5 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium">{r.categoria}</h3>
                {pres && pres.user_id === userId && (
                  <Button
                    variant="ghost"
                    size="xs"
                    className="text-rose-400"
                    onClick={() => handleDelete(pres.id)}
                  >
                    Borrar
                  </Button>
                )}
              </div>

              <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${progressColor(pct)}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>

              <div className="flex items-baseline justify-between text-sm">
                <span className="text-gray-400">
                  <span className={`font-medium tabular-nums ${progressTextColor(pct)}`}>
                    {formatCOP(r.gastado)}
                  </span>
                  {" / "}
                  <span className="tabular-nums">{formatCOP(r.limite)}</span>
                </span>
                <span className={`font-semibold tabular-nums ${progressTextColor(pct)}`}>
                  {pct}%
                </span>
              </div>

              <p className="text-xs text-gray-400">
                Restante: <span className="tabular-nums">{formatCOP(r.restante)}</span>
              </p>
            </div>
          )
        })}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Nuevo presupuesto</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Categoria</label>
              <Select
                value={form.categoria_id}
                onValueChange={(v) => setForm((f) => ({ ...f, categoria_id: v ?? "" }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccionar categoria" />
                </SelectTrigger>
                <SelectContent>
                  {(categorias ?? [])
                    .filter((c) => c.tipo === "gasto")
                    .map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.nombre}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Monto limite</label>
              <Input
                type="number"
                required
                value={form.monto_limite_cop}
                onChange={(e) => setForm((f) => ({ ...f, monto_limite_cop: e.target.value }))}
                placeholder="0"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Mes (YYYY-MM)</label>
              <Input
                required
                value={form.mes_vigente}
                onChange={(e) => setForm((f) => ({ ...f, mes_vigente: e.target.value }))}
                placeholder="2026-09"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={saving || !form.categoria_id || !form.monto_limite_cop}
              >
                {saving ? "Guardando..." : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
