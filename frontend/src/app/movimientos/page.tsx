"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/hooks/use-auth"
import { useUserFilter } from "@/hooks/use-user-filter"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { formatCOP, formatDate } from "@/lib/format"
import { getCategoryColor } from "@/lib/constants"
import type { Movimiento, Categoria, Usuario, TarjetaCredito } from "@/lib/types"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface FormState {
  user_id: string
  categoria_id: string
  monto_cop: string
  descripcion: string
  fecha_gasto: string
  medio_pago: string
  es_compartido: boolean
  num_cuotas: string
  tarjeta_id: string
}

const emptyForm: FormState = {
  user_id: "",
  categoria_id: "",
  monto_cop: "",
  descripcion: "",
  fecha_gasto: "",
  medio_pago: "cuenta_ahorros",
  es_compartido: false,
  num_cuotas: "1",
  tarjeta_id: "",
}

const MEDIOS_PAGO = [
  { value: "cuenta_ahorros", label: "Cuenta ahorros" },
  { value: "tarjeta_credito", label: "Tarjeta credito" },
  { value: "nequi", label: "Nequi" },
  { value: "daviplata", label: "Daviplata" },
  { value: "efectivo", label: "Efectivo" },
]

function medioPagoLabel(value: string | null | undefined): string {
  return MEDIOS_PAGO.find((m) => m.value === value)?.label ?? value ?? "—"
}

export default function MovimientosPage() {
  const { userId } = useAuth()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Movimiento | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const { selectedUser: filterUser, usuarios } = useUserFilter()
  const grupoLleno = usuarios.length >= 2
  const [saving, setSaving] = useState(false)

  // Open dialog when navigated with ?new=1 (FAB button)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get("new") === "1") {
      setEditing(null)
      setForm(emptyForm)
      setDialogOpen(true)
      window.history.replaceState(null, "", "/movimientos")
    }
  }, [])

  const {
    data: movimientos,
    loading: loadingMov,
    refetch: refetchMov,
  } = usePolling<Movimiento[]>(() => api.get("/api/movimientos?limit=200"), 5000)

  const { data: categorias, refetch: refetchCat } = usePolling<Categoria[]>(
    () => api.get("/api/categorias"),
    5000,
  )

  const { data: usuariosList, refetch: refetchUsr } = usePolling<Usuario[]>(
    () => api.get("/api/usuarios"),
    5000,
  )

  const { data: tarjetas } = usePolling<TarjetaCredito[]>(
    () => api.get("/api/tarjetas"),
    10000,
  )

  function refetch() {
    refetchMov()
    refetchCat()
    refetchUsr()
  }

  function openCreate() {
    setEditing(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function openEdit(m: Movimiento) {
    setEditing(m)
    setForm({
      user_id: String(m.user_id),
      categoria_id: m.categoria_id != null ? String(m.categoria_id) : "",
      monto_cop: String(m.monto_cop),
      descripcion: m.descripcion ?? "",
      fecha_gasto: m.fecha_gasto ? formatDate(m.fecha_gasto) : "",
      medio_pago: m.medio_pago ?? "cuenta_ahorros",
      es_compartido: m.es_compartido ?? false,
      num_cuotas: "1",
      tarjeta_id: "",
    })
    setDialogOpen(true)
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar este movimiento?")) return
    try {
      await api.del(`/api/movimientos/${id}`)
      toast.success("Movimiento eliminado")
      refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al eliminar")
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const base = {
        user_id: editing ? editing.user_id : userId,
        categoria_id: form.categoria_id ? Number(form.categoria_id) : null,
        monto_cop: Number(form.monto_cop),
        descripcion: form.descripcion || null,
        fecha_gasto: form.fecha_gasto || null,
        medio_pago: form.medio_pago || null,
        es_compartido: form.es_compartido,
        porcentaje_compartido: form.es_compartido ? 50 : null,
      }
      const numCuotas = parseInt(form.num_cuotas) || 1
      if (editing) {
        await api.patch(`/api/movimientos/${editing.id}`, {
          ...base,
          limpiar_categoria: !form.categoria_id,
        })
        // Si edita un movimiento TC con cuotas vinculadas, actualizar la cuota
        if (editing.compra_cuotas_id && form.medio_pago === "tarjeta_credito") {
          try {
            await api.patch(`/api/cuotas/${editing.compra_cuotas_id}`, {
              establecimiento: form.descripcion || "Compra TC",
              valor_total_cop: Number(form.monto_cop),
              num_cuotas: numCuotas,
            })
          } catch { /* silencioso */ }
        }
        toast.success("Movimiento actualizado")
      } else {
        const res = await api.post<{ id?: number }>("/api/movimientos", base)
        // Si es TC, registrar en tabla de cuotas y vincular
        if (form.medio_pago === "tarjeta_credito") {
          try {
            const cuotaRes = await api.post<{ id?: number }>("/api/cuotas", {
              user_id: userId,
              fecha_compra: form.fecha_gasto || new Date().toISOString().split("T")[0],
              establecimiento: form.descripcion || "Compra TC",
              valor_total_cop: Number(form.monto_cop),
              num_cuotas: numCuotas,
              tarjeta_id: form.tarjeta_id ? Number(form.tarjeta_id) : null,
              es_compartido: form.es_compartido,
              movimiento_id: res?.id,
            })
            toast.success(numCuotas > 1 ? `Movimiento + ${numCuotas} cuotas` : "Movimiento TC registrado")
          } catch {
            toast.success("Movimiento creado")
          }
        } else {
          toast.success("Movimiento creado")
        }
      }
      setDialogOpen(false)
      refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al guardar")
    } finally {
      setSaving(false)
    }
  }

  const filtered = (movimientos ?? []).filter((m) => {
    if (filterUser === "todos") return true
    return String(m.user_id) === filterUser
  })

  const sorted = [...filtered].sort((a, b) => {
    const da = a.fecha_gasto || ""
    const db2 = b.fecha_gasto || ""
    return db2.localeCompare(da)
  })

  const [expandedId, setExpandedId] = useState<number | null>(null)

  // Colores únicos por usuario para diferenciar iniciales iguales
  const USER_COLORS = ["#8b5cf6", "#06b6d4", "#f472b6", "#fbbf24", "#34d399", "#fb923c"]
  const userColorMap = Object.fromEntries(
    (usuarios.length > 0 ? usuarios : []).map((u, i) => [u.id, USER_COLORS[i % USER_COLORS.length]])
  )

  return (
    <div className="space-y-5 animate-fade-in">
      <h1 className="text-xl font-bold text-gray-100">Gastos</h1>

      {loadingMov && !movimientos && <p className="text-gray-400 text-sm">Cargando...</p>}

      {sorted.length === 0 && !loadingMov && (
        <div className="text-center py-12 text-gray-500">
          <p>Sin movimientos</p>
        </div>
      )}

      <div className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden">
        {sorted.map((m) => {
          const isExpanded = expandedId === m.id
          const isOwn = m.user_id === userId
          return (
            <div key={m.id} className="border-b border-white/5 last:border-0">
              {/* Row principal — tap para expandir */}
              <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer active:bg-white/[0.02]"
                onClick={() => setExpandedId(isExpanded ? null : m.id)}
              >
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
                  style={{
                    backgroundColor: (userColorMap[m.user_id] || "#8b5cf6") + "20",
                    color: userColorMap[m.user_id] || "#8b5cf6",
                  }}
                >
                  {(m.usuario || "?")[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-100 truncate">{m.descripcion || m.categoria || "Sin desc"}</p>
                  <p className="text-xs text-gray-500">{formatDate(m.fecha_gasto)}{m.es_compartido ? " · 50%" : ""}</p>
                </div>
                <p className={`text-sm font-semibold tabular-nums shrink-0 ${m.tipo === "ingreso" ? "text-emerald-400" : "text-rose-400"}`}>
                  {m.tipo === "ingreso" ? "+" : "-"}{formatCOP(m.monto_cop)}
                </p>
              </div>

              {/* Detalle expandido */}
              {isExpanded && (
                <div className="px-4 pb-3 space-y-2 animate-fade-in">
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-white/[0.03] rounded-xl px-3 py-2">
                      <span className="text-gray-500">Categoria</span>
                      <p className="text-gray-200 mt-0.5">{m.categoria || "—"}</p>
                    </div>
                    <div className="bg-white/[0.03] rounded-xl px-3 py-2">
                      <span className="text-gray-500">Medio</span>
                      <p className="text-gray-200 mt-0.5">{medioPagoLabel(m.medio_pago)}</p>
                    </div>
                    {m.usuario && (
                      <div className="bg-white/[0.03] rounded-xl px-3 py-2">
                        <span className="text-gray-500">Usuario</span>
                        <p className="text-gray-200 mt-0.5">{m.usuario}</p>
                      </div>
                    )}
                    {m.es_compartido && (
                      <div className="bg-white/[0.03] rounded-xl px-3 py-2">
                        <span className="text-gray-500">Compartido</span>
                        <p className="text-cyan-400 mt-0.5">50%</p>
                      </div>
                    )}
                  </div>
                  {isOwn && (
                    <div className="flex gap-2 pt-1">
                      <button
                        onClick={() => openEdit(m)}
                        className="flex-1 py-2 rounded-xl bg-violet-500/10 text-violet-400 text-sm font-medium hover:bg-violet-500/20 transition-colors"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(m.id)}
                        className="flex-1 py-2 rounded-xl bg-rose-500/10 text-rose-400 text-sm font-medium hover:bg-rose-500/20 transition-colors"
                      >
                        Eliminar
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[380px]">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Editar movimiento" : "Nuevo movimiento"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-2">
            {/* Monto — prominente con formato COP */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Monto</label>
              <input
                inputMode="numeric"
                required
                value={form.monto_cop ? `$${Number(form.monto_cop).toLocaleString("es-CO")}` : ""}
                onChange={(e) => {
                  const raw = e.target.value.replace(/[^0-9]/g, "")
                  setForm((f) => ({ ...f, monto_cop: raw }))
                }}
                placeholder="$0"
                className="w-full px-4 py-3 rounded-xl bg-[#0A0E1A] border border-white/10 text-2xl font-bold text-gray-100 tabular-nums placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500 transition-all"
              />
            </div>

            {/* Categoría + Fecha en grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="min-w-0">
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Categoria</label>
                <select
                  value={form.categoria_id}
                  onChange={(e) => setForm((f) => ({ ...f, categoria_id: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                >
                  <option value="">Sin categoria</option>
                  {(categorias ?? []).map((c) => (
                    <option key={c.id} value={String(c.id)}>{c.nombre}</option>
                  ))}
                </select>
              </div>
              <div className="min-w-0">
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Fecha</label>
                <input
                  type="date"
                  value={form.fecha_gasto}
                  onChange={(e) => setForm((f) => ({ ...f, fecha_gasto: e.target.value }))}
                  className="w-full min-w-0 max-w-full px-2 py-2.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50 [color-scheme:dark] overflow-hidden box-border appearance-none"
                />
              </div>
            </div>

            {/* Descripción */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Descripcion</label>
              <input
                value={form.descripcion}
                onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))}
                placeholder="Uber, Mercado, Netflix..."
                className="w-full px-3 py-2.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              />
            </div>

            {/* Medio de pago + Compartido */}
            <div className="grid grid-cols-2 gap-3 items-end">
              <div>
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Medio de pago</label>
                <select
                  value={form.medio_pago}
                  onChange={(e) => setForm((f) => ({ ...f, medio_pago: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                >
                  {MEDIOS_PAGO.map((mp) => (
                    <option key={mp.value} value={mp.value}>{mp.label}</option>
                  ))}
                </select>
              </div>
              {grupoLleno && (
                <button
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, es_compartido: !f.es_compartido }))}
                  className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-white/10 bg-[#0A0E1A] cursor-pointer transition-all hover:border-violet-500/30"
                >
                  <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                    form.es_compartido ? "border-violet-500 bg-violet-500" : "border-gray-500"
                  }`}>
                    {form.es_compartido && (
                      <div className="w-2 h-2 rounded-full bg-white" />
                    )}
                  </div>
                  <span className="text-sm text-gray-300">Compartido</span>
                </button>
              )}
            </div>

            {/* Cuotas TC */}
            {form.medio_pago === "tarjeta_credito" && (
              <>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Tarjeta</label>
                  <select
                    value={form.tarjeta_id}
                    onChange={(e) => setForm((f) => ({ ...f, tarjeta_id: e.target.value }))}
                    className="w-full px-3 py-2.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  >
                    <option value="">Seleccionar tarjeta</option>
                    {(tarjetas ?? []).filter(t => t.user_id === userId).map(t => (
                      <option key={t.id} value={String(t.id)}>{t.banco} ****{t.ultimos_4 || "????"}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Numero de cuotas</label>
                  <input
                    inputMode="numeric"
                    value={form.num_cuotas}
                    onChange={(e) => setForm((f) => ({ ...f, num_cuotas: e.target.value.replace(/[^0-9]/g, "") }))}
                    placeholder="1"
                    className="w-full px-3 py-2.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                  {parseInt(form.num_cuotas) > 1 && form.monto_cop && (
                    <p className="text-xs text-violet-400 mt-1.5">
                      {parseInt(form.num_cuotas)} cuotas de {formatCOP(Math.round(Number(form.monto_cop) / parseInt(form.num_cuotas)))} /mes
                    </p>
                  )}
                </div>
              </>
            )}

            {/* Botones */}
            <div className="flex gap-3 pt-1">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="flex-1">
                Cancelar
              </Button>
              <Button type="submit" disabled={saving || !form.monto_cop} className="flex-1 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 shadow-lg shadow-violet-500/20">
                {saving ? "Guardando..." : editing ? "Actualizar" : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
