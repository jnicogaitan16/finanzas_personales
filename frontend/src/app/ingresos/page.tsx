"use client"

import { useState, useCallback, useMemo } from "react"
import { toast } from "sonner"
import { Plus, Pencil, Trash2, Calendar, Repeat, ChevronLeft, ChevronRight, Gift } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useAuth } from "@/hooks/use-auth"
import { useUserFilter } from "@/hooks/use-user-filter"
import { formatCOP, isInMonth } from "@/lib/format"
import type { IngresoRecurrente, Movimiento, Categoria } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

// ── Form states ──

interface FijoFormState {
  nombre: string
  frecuencia: string
  monto_cop: string
  dia_pago_1: string
  dia_pago_2: string
}

const emptyFijoForm: FijoFormState = {
  nombre: "", frecuencia: "mensual",
  monto_cop: "", dia_pago_1: "", dia_pago_2: "",
}

interface IngresoFormState {
  monto_cop: string
  descripcion: string
  fecha: string
}

const emptyIngresoForm: IngresoFormState = {
  monto_cop: "", descripcion: "", fecha: "",
}

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

export default function IngresosPage() {
  // Fijo dialog
  const [fijoDialogOpen, setFijoDialogOpen] = useState(false)
  const [editingFijo, setEditingFijo] = useState<IngresoRecurrente | null>(null)
  const [fijoForm, setFijoForm] = useState<FijoFormState>(emptyFijoForm)
  const [savingFijo, setSavingFijo] = useState(false)

  // Ingreso puntual dialog
  const [ingresoDialogOpen, setIngresoDialogOpen] = useState(false)
  const [ingresoForm, setIngresoForm] = useState<IngresoFormState>(emptyIngresoForm)
  const [savingIngreso, setSavingIngreso] = useState(false)

  // Month selector
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

  const { userId } = useAuth()
  const { selectedUser } = useUserFilter()

  // Data
  const fetchIngresos = useCallback(() => api.get<IngresoRecurrente[]>("/api/ingresos"), [])
  const { data: ingresos, refetch: refetchIngresos } = usePolling(fetchIngresos, 5000)

  const fetchMovimientos = useCallback(() => api.get<Movimiento[]>("/api/movimientos?limit=500"), [])
  const { data: movimientos, refetch: refetchMov } = usePolling(fetchMovimientos, 5000)

  const fetchCategorias = useCallback(() => api.get<Categoria[]>("/api/categorias"), [])
  const { data: categorias } = usePolling(fetchCategorias, 30000)

  // Filtrar movimientos de ingreso del mes respetando filtro global
  const ingresosMes = useMemo(() => {
    if (!movimientos) return []
    return movimientos.filter(m => {
      if (!m.tipo || m.tipo !== "ingreso") return false
      if (!isInMonth(m.fecha_gasto, monthKey)) return false
      if (selectedUser !== "todos" && String(m.user_id) !== selectedUser) return false
      return true
    })
  }, [movimientos, monthKey, selectedUser])

  const totalMes = ingresosMes.reduce((s, m) => s + m.monto_cop, 0)

  // Ingresos fijos filtrados por usuario
  const ingresosFijos = (ingresos ?? []).filter(i => {
    if (i.tipo !== "fijo") return false
    if (selectedUser !== "todos" && String(i.user_id) !== selectedUser) return false
    return true
  })

  const totalFijoMensual = ingresosFijos.reduce((s, i) => {
    if (i.frecuencia === "quincenal") return s + i.monto_cop * 2
    if (i.frecuencia === "semanal") return s + i.monto_cop * 4
    if (i.frecuencia === "anual") return s + Math.round(i.monto_cop / 12)
    return s + i.monto_cop
  }, 0)

  // ── Fijo CRUD ──

  function openCreateFijo() {
    setEditingFijo(null)
    setFijoForm(emptyFijoForm)
    setFijoDialogOpen(true)
  }

  function openEditFijo(i: IngresoRecurrente) {
    setEditingFijo(i)
    setFijoForm({
      nombre: i.nombre,
      frecuencia: i.frecuencia,
      monto_cop: String(i.monto_cop),
      dia_pago_1: i.dia_pago_1 != null ? String(i.dia_pago_1) : "",
      dia_pago_2: i.dia_pago_2 != null ? String(i.dia_pago_2) : "",
    })
    setFijoDialogOpen(true)
  }

  async function handleSubmitFijo(e: React.FormEvent) {
    e.preventDefault()
    setSavingFijo(true)
    try {
      const base = {
        user_id: userId,
        nombre: fijoForm.nombre,
        tipo: "fijo",
        frecuencia: fijoForm.frecuencia,
        monto_cop: Number(fijoForm.monto_cop),
        dia_pago_1: fijoForm.dia_pago_1 ? Number(fijoForm.dia_pago_1) : null,
        dia_pago_2: fijoForm.dia_pago_2 ? Number(fijoForm.dia_pago_2) : null,
      }
      if (editingFijo) {
        await api.patch(`/api/ingresos/${editingFijo.id}`, base)
        toast.success("Ingreso fijo actualizado")
      } else {
        await api.post("/api/ingresos", base)
        toast.success("Ingreso fijo creado")
      }
      setFijoDialogOpen(false)
      refetchIngresos()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    } finally {
      setSavingFijo(false)
    }
  }

  async function handleDeleteFijo(id: number) {
    if (!confirm("¿Desactivar este ingreso fijo?")) return
    try {
      await api.del(`/api/ingresos/${id}`)
      toast.success("Ingreso fijo desactivado")
      refetchIngresos()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    }
  }

  // ── Ingreso puntual (variable/bono/extra) ──

  function openRegistrarIngreso() {
    setIngresoForm({
      ...emptyIngresoForm,
      fecha: `${monthKey}-15`,
    })
    setIngresoDialogOpen(true)
  }

  async function handleSubmitIngreso(e: React.FormEvent) {
    e.preventDefault()
    setSavingIngreso(true)
    try {
      const catIngreso = (categorias ?? []).find(c => c.tipo === "ingreso")
      await api.post("/api/movimientos", {
        user_id: userId,
        monto_cop: Number(ingresoForm.monto_cop),
        descripcion: ingresoForm.descripcion || "Ingreso",
        fecha_gasto: ingresoForm.fecha || null,
        categoria_id: catIngreso?.id ?? null,
      })
      toast.success("Ingreso registrado")
      setIngresoDialogOpen(false)
      refetchMov()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    } finally {
      setSavingIngreso(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <h1 className="text-2xl font-bold text-gray-100">Ingresos</h1>

      {/* Month selector + total */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-center gap-4 bg-white/5 rounded-xl py-2">
          <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-sm font-semibold text-gray-100 min-w-[120px] text-center">{monthLabel}</span>
          <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400">
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-4">
            <p className="text-[11px] text-gray-400 uppercase tracking-wide">Recibido en {MESES[selectedMonth.month]}</p>
            <p className="text-2xl font-bold text-emerald-400 tabular-nums mt-1">{formatCOP(totalMes)}</p>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl p-4">
            <p className="text-[11px] text-gray-400 uppercase tracking-wide">Fijo esperado / mes</p>
            <p className="text-2xl font-bold text-blue-400 tabular-nums mt-1">{formatCOP(totalFijoMensual)}</p>
          </div>
        </div>
      </div>

      {/* ── Sección: Ingresos fijos ── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm text-gray-400 uppercase tracking-wide">Ingresos fijos (automáticos)</h2>
          <Button onClick={openCreateFijo} size="xs" variant="ghost">
            <Plus className="w-4 h-4 mr-1" /> Agregar
          </Button>
        </div>

        {ingresosFijos.length === 0 ? (
          <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 text-center text-gray-500 text-sm">
            Sin ingresos fijos configurados. Agrega tu salario para que se registre automáticamente cada mes.
          </div>
        ) : (
          <div className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden">
            {ingresosFijos.map(i => (
              <div key={i.id} className="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/15 flex items-center justify-center shrink-0">
                  <Calendar className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-100">{i.nombre}</p>
                  <p className="text-xs text-gray-500">
                    {i.frecuencia}{i.dia_pago_1 ? ` · día ${i.dia_pago_1}` : ""}{i.dia_pago_2 ? ` y ${i.dia_pago_2}` : ""}
                    {i.usuario ? ` · ${i.usuario}` : ""}
                  </p>
                </div>
                <p className="text-sm font-bold text-emerald-400 tabular-nums shrink-0">{formatCOP(i.monto_cop)}</p>
                <div className="flex gap-0.5 shrink-0">
                  <button onClick={() => openEditFijo(i)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-500"><Pencil className="w-3.5 h-3.5" /></button>
                  <button onClick={() => handleDeleteFijo(i.id)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-500"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Sección: Historial del mes + registrar ── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm text-gray-400 uppercase tracking-wide">Ingresos de {monthLabel}</h2>
          <Button onClick={openRegistrarIngreso} size="xs" variant="ghost">
            <Plus className="w-4 h-4 mr-1" /> Registrar
          </Button>
        </div>

        {ingresosMes.length === 0 ? (
          <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 text-center text-gray-500 text-sm">
            Sin ingresos registrados en {monthLabel}
          </div>
        ) : (
          <div className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden">
            {ingresosMes.map(m => {
              const isAuto = m.marca_dedup?.startsWith("ingreso_fijo:")
              return (
                <div key={m.id} className="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${isAuto ? "bg-emerald-500/15" : "bg-amber-500/15"}`}>
                    {isAuto ? <Repeat className="w-4 h-4 text-emerald-400" /> : <Gift className="w-4 h-4 text-amber-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-100">
                      {m.descripcion || "Ingreso"}
                    </p>
                    <p className="text-xs text-gray-500">
                      {m.fecha_gasto}{isAuto ? " · Automático" : ""}{m.usuario ? ` · ${m.usuario}` : ""}
                    </p>
                  </div>
                  <p className="text-sm font-bold text-emerald-400 tabular-nums shrink-0">
                    +{formatCOP(m.monto_cop)}
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Dialog: Ingreso fijo ── */}
      <Dialog open={fijoDialogOpen} onOpenChange={setFijoDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingFijo ? "Editar ingreso fijo" : "Nuevo ingreso fijo"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmitFijo} className="grid gap-4 mt-2">
            <label className="text-sm">
              Nombre
              <Input value={fijoForm.nombre} onChange={e => setFijoForm(f => ({ ...f, nombre: e.target.value }))} placeholder="Salario, Arriendo recibido..." required className="mt-1" />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">
                Frecuencia
                <select value={fijoForm.frecuencia} onChange={e => setFijoForm(f => ({ ...f, frecuencia: e.target.value }))} className="w-full mt-1 px-3 py-2 rounded-lg border text-sm">
                  <option value="mensual">Mensual</option>
                  <option value="quincenal">Quincenal</option>
                </select>
              </label>
              <label className="text-sm">
                Monto (COP)
                <Input type="number" value={fijoForm.monto_cop} onChange={e => setFijoForm(f => ({ ...f, monto_cop: e.target.value }))} required className="mt-1" />
              </label>
            </div>
            {fijoForm.frecuencia === "quincenal" && fijoForm.monto_cop && (
              <p className="text-xs text-gray-500">Total mensual: {formatCOP(Number(fijoForm.monto_cop) * 2)}</p>
            )}
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">
                Día de pago{fijoForm.frecuencia === "quincenal" ? " (1ra)" : ""}
                <Input type="number" min={1} max={31} value={fijoForm.dia_pago_1} onChange={e => setFijoForm(f => ({ ...f, dia_pago_1: e.target.value }))} placeholder="30" className="mt-1" />
              </label>
              {fijoForm.frecuencia === "quincenal" && (
                <label className="text-sm">
                  Día de pago (2da)
                  <Input type="number" min={1} max={31} value={fijoForm.dia_pago_2} onChange={e => setFijoForm(f => ({ ...f, dia_pago_2: e.target.value }))} placeholder="15" className="mt-1" />
                </label>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-2">
              <Button type="button" variant="outline" onClick={() => setFijoDialogOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={savingFijo}>{savingFijo ? "Guardando..." : editingFijo ? "Actualizar" : "Crear"}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── Dialog: Registrar ingreso puntual ── */}
      <Dialog open={ingresoDialogOpen} onOpenChange={setIngresoDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Registrar ingreso</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmitIngreso} className="grid gap-4 mt-2">
            <label className="text-sm">
              Monto (COP)
              <Input type="number" value={ingresoForm.monto_cop} onChange={e => setIngresoForm(f => ({ ...f, monto_cop: e.target.value }))} required placeholder="1000000" className="mt-1" />
            </label>
            <label className="text-sm">
              Fecha
              <Input type="date" value={ingresoForm.fecha} onChange={e => setIngresoForm(f => ({ ...f, fecha: e.target.value }))} required className="mt-1" />
            </label>
            <label className="text-sm">
              Descripción / Observación
              <Input value={ingresoForm.descripcion} onChange={e => setIngresoForm(f => ({ ...f, descripcion: e.target.value }))} placeholder="Freelance, Bono, Prima, Venta..." className="mt-1" />
            </label>
            <div className="flex justify-end gap-2 mt-2">
              <Button type="button" variant="outline" onClick={() => setIngresoDialogOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={savingIngreso}>{savingIngreso ? "Guardando..." : "Registrar"}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
