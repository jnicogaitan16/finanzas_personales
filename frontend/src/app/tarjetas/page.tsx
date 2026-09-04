"use client"

import { useState, useCallback } from "react"
import { toast } from "sonner"
import { Plus, CreditCard, Pencil, Trash2 } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useAuth } from "@/hooks/use-auth"
import { useUserFilter } from "@/hooks/use-user-filter"
import { formatCOP } from "@/lib/format"
import type { TarjetaCredito, CompraCuotas, ProyeccionMes } from "@/lib/types"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface FormState {
  banco: string
  banco_otro: string
  ultimos_4: string
  fecha_corte: string
  fecha_pago: string
  tasa_ea: string
  cupo_total_cop: string
}

const emptyForm: FormState = {
  banco: "",
  banco_otro: "",
  ultimos_4: "",
  fecha_corte: "",
  fecha_pago: "",
  tasa_ea: "",
  cupo_total_cop: "",
}

const BANCOS = [
  "Bancolombia", "Davivienda", "BBVA", "Banco de Bogota", "Scotiabank Colpatria",
  "Banco de Occidente", "Banco Popular", "Banco Falabella", "Banco Pichincha",
  "Nu", "Rappi", "Lulo Bank", "Nequi", "Ualá", "Otro",
]

const CARD_GRADIENTS = [
  "from-violet-700 to-purple-900",
  "from-indigo-700 to-blue-900",
  "from-purple-700 to-fuchsia-900",
  "from-cyan-700 to-teal-900",
  "from-violet-800 to-indigo-900",
  "from-fuchsia-700 to-purple-900",
]

const inputClass = "w-full px-3 py-2.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 transition-all"

export default function TarjetasPage() {
  const { userId } = useAuth()
  const { selectedUser } = useUserFilter()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<TarjetaCredito | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)

  const isOwnView = selectedUser === "todos" || selectedUser === String(userId)

  const fetchTarjetas = useCallback(() => api.get<TarjetaCredito[]>("/api/tarjetas"), [])
  const { data: tarjetas, refetch: refetchTarjetas } = usePolling(fetchTarjetas, 5000)

  const fetchCuotas = useCallback(() => api.get<CompraCuotas[]>("/api/cuotas"), [])
  const { data: cuotas } = usePolling(fetchCuotas, 5000)

  const fetchProyeccion = useCallback(() => api.get<Record<string, ProyeccionMes>>("/api/proyeccion-cuotas?meses=6"), [])
  const { data: proyeccion } = usePolling(fetchProyeccion, 10000)

  // Filtrar por usuario seleccionado
  const tarjetasFiltradas = (tarjetas ?? []).filter(t => {
    if (selectedUser === "todos") return true
    return String(t.user_id) === selectedUser
  })

  function openCreate() {
    setEditing(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function openEdit(t: TarjetaCredito) {
    setEditing(t)
    const bancoEnLista = BANCOS.includes(t.banco)
    setForm({
      banco: bancoEnLista ? t.banco : "Otro",
      banco_otro: bancoEnLista ? "" : t.banco,
      ultimos_4: t.ultimos_4 || "",
      fecha_corte: String(t.fecha_corte),
      fecha_pago: String(t.fecha_pago),
      tasa_ea: t.tasa_ea != null ? String(t.tasa_ea) : "",
      cupo_total_cop: t.cupo_total_cop != null ? String(t.cupo_total_cop) : "",
    })
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const bancoFinal = form.banco === "Otro" ? form.banco_otro : form.banco
      const base = {
        user_id: userId,
        banco: bancoFinal,
        nombre: `${bancoFinal} ****${form.ultimos_4 || "0000"}`,
        ultimos_4: form.ultimos_4 || null,
        fecha_corte: Number(form.fecha_corte),
        fecha_pago: Number(form.fecha_pago),
        tasa_ea: form.tasa_ea ? Number(form.tasa_ea) : null,
        cupo_total_cop: form.cupo_total_cop ? Number(form.cupo_total_cop.replace(/[^0-9]/g, "")) : null,
      }
      if (editing) {
        await api.patch(`/api/tarjetas/${editing.id}`, base)
        toast.success("Tarjeta actualizada")
      } else {
        await api.post("/api/tarjetas", base)
        toast.success("Tarjeta creada")
      }
      setDialogOpen(false)
      refetchTarjetas()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Desactivar esta tarjeta?")) return
    try {
      await api.del(`/api/tarjetas/${id}`)
      toast.success("Tarjeta desactivada")
      refetchTarjetas()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    }
  }

  function getCuotasByTarjeta(tarjetaId: number) {
    return (cuotas ?? []).filter(c => c.tarjeta_id === tarjetaId && !c.liquidada)
  }

  function getTotalMensual(tarjetaId: number) {
    return getCuotasByTarjeta(tarjetaId).reduce((s, c) => s + c.valor_cuota_cop, 0)
  }

  function getDeudaTotal(tarjetaId: number) {
    return getCuotasByTarjeta(tarjetaId).reduce((s, c) => s + c.saldo_pendiente_cop, 0)
  }

  const MESES_CORTOS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
  const isOwn = (t: TarjetaCredito) => t.user_id === userId

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-100">Tarjetas</h1>
        {isOwnView && (
          <Button onClick={openCreate} size="sm" className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 shadow-lg shadow-violet-500/20">
            <Plus className="w-4 h-4 mr-1" /> Agregar
          </Button>
        )}
      </div>

      {tarjetasFiltradas.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <CreditCard className="w-14 h-14 mx-auto mb-4 opacity-20" />
          <p className="text-gray-300 font-medium">No hay tarjetas registradas</p>
          {isOwnView && (
            <>
              <p className="text-sm mt-1.5">Agrega tu primera tarjeta de credito</p>
              <div className="mt-6 mx-auto max-w-[260px] bg-violet-500/5 border border-violet-500/10 rounded-2xl px-4 py-3">
                <p className="text-xs text-violet-300/70 leading-relaxed">
                  🔒 Tu informacion esta segura. Solo la usamos para simular pagos y proyectar tu facturacion. No almacenamos datos bancarios reales.
                </p>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1 snap-x scrollbar-hide">
          {tarjetasFiltradas.map((t, i) => (
            <div
              key={t.id}
              className={`shrink-0 w-72 bg-gradient-to-br ${CARD_GRADIENTS[i % CARD_GRADIENTS.length]} rounded-2xl p-5 text-white cursor-pointer snap-start transition-transform hover:scale-[1.02]`}
              onClick={() => setExpanded(expanded === t.id ? null : t.id)}
            >
              <div className="flex items-center justify-between mb-6">
                <span className="text-sm font-medium opacity-80">{t.banco}</span>
                {isOwn(t) && (
                  <div className="flex gap-1">
                    <button onClick={(e) => { e.stopPropagation(); openEdit(t) }} className="p-1 rounded-lg hover:bg-white/20">
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(t.id) }} className="p-1 rounded-lg hover:bg-white/20">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 mb-4">
                <CreditCard className="w-6 h-6 opacity-60" />
                <span className="text-lg tracking-[0.2em] font-mono">•••• {t.ultimos_4 || "????"}</span>
              </div>
              <div className="flex justify-between text-xs opacity-70">
                <span>Corte: {t.fecha_corte}</span>
                <span>Pago: {t.fecha_pago}</span>
                {t.tasa_ea != null && <span>{t.tasa_ea}% EA</span>}
              </div>
              <div className="flex justify-between mt-4 pt-3 border-t border-white/20 text-xs">
                <div>
                  <p className="opacity-60">Cuota/mes</p>
                  <p className="font-bold text-sm">{formatCOP(getTotalMensual(t.id))}</p>
                </div>
                <div className="text-right">
                  <p className="opacity-60">Deuda total</p>
                  <p className="font-bold text-sm">{formatCOP(getDeudaTotal(t.id))}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {expanded && (
        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
          <h3 className="text-sm text-gray-400 uppercase tracking-wide mb-3">
            Compras activas — {tarjetasFiltradas.find(t => t.id === expanded)?.banco}
          </h3>
          {getCuotasByTarjeta(expanded).length === 0 ? (
            <p className="text-gray-500 text-sm">Sin compras activas</p>
          ) : (
            <div className="space-y-2">
              {getCuotasByTarjeta(expanded).map(c => (
                <div key={c.id} className="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-100">{c.establecimiento}</p>
                    <p className="text-xs text-gray-500">{c.fecha_compra}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-20 h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div className="h-full bg-violet-400 rounded-full" style={{ width: `${(c.cuotas_pagadas / c.num_cuotas) * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{c.cuotas_pagadas}/{c.num_cuotas}</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-200 tabular-nums shrink-0">{formatCOP(c.valor_cuota_cop)}/mes</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {proyeccion && Object.keys(proyeccion).length > 0 && (
        <div>
          <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-3">Proyeccion de cuotas</h3>
          <div className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden">
            {Object.entries(proyeccion).map(([mes, data], i) => {
              const [y, m] = mes.split("-").map(Number)
              const maxTotal = Math.max(...Object.values(proyeccion).map(d => d.total))
              const pct = maxTotal > 0 ? (data.total / maxTotal) * 100 : 0
              return (
                <div key={mes} className="px-4 py-3 border-b border-white/5 last:border-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm text-gray-200 font-medium">{MESES_CORTOS[m - 1]} {y}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">{data.compras.length} cuotas</span>
                      <span className="text-sm font-bold text-rose-400 tabular-nums">{formatCOP(data.total)}</span>
                    </div>
                  </div>
                  <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-violet-500 to-rose-400 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[380px]">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar tarjeta" : "Nueva tarjeta"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-2">
            {/* Banco */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Banco</label>
              <select
                value={form.banco}
                onChange={(e) => setForm(f => ({ ...f, banco: e.target.value, banco_otro: "" }))}
                required
                className={inputClass}
              >
                <option value="">Seleccionar banco</option>
                {BANCOS.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>

            {form.banco === "Otro" && (
              <div>
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Nombre del banco</label>
                <input
                  value={form.banco_otro}
                  onChange={(e) => setForm(f => ({ ...f, banco_otro: e.target.value }))}
                  required
                  placeholder="Nombre del banco"
                  className={inputClass}
                />
              </div>
            )}

            {/* Últimos 4 + Tasa EA */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Ultimos 4 digitos</label>
                <input
                  inputMode="numeric"
                  maxLength={4}
                  value={form.ultimos_4}
                  onChange={(e) => setForm(f => ({ ...f, ultimos_4: e.target.value.replace(/[^0-9]/g, "") }))}
                  placeholder="1234"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Tasa EA (%)</label>
                <input
                  inputMode="decimal"
                  value={form.tasa_ea}
                  onChange={(e) => setForm(f => ({ ...f, tasa_ea: e.target.value.replace(/[^0-9.]/g, "") }))}
                  placeholder="28.5"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Día corte + Día pago */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Dia de corte</label>
                <input
                  inputMode="numeric"
                  required
                  value={form.fecha_corte}
                  onChange={(e) => setForm(f => ({ ...f, fecha_corte: e.target.value.replace(/[^0-9]/g, "") }))}
                  placeholder="8"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Dia de pago</label>
                <input
                  inputMode="numeric"
                  required
                  value={form.fecha_pago}
                  onChange={(e) => setForm(f => ({ ...f, fecha_pago: e.target.value.replace(/[^0-9]/g, "") }))}
                  placeholder="25"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Cupo */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide block mb-1.5">Cupo total</label>
              <input
                inputMode="numeric"
                value={form.cupo_total_cop ? `$${Number(form.cupo_total_cop).toLocaleString("es-CO")}` : ""}
                onChange={(e) => setForm(f => ({ ...f, cupo_total_cop: e.target.value.replace(/[^0-9]/g, "") }))}
                placeholder="$5.000.000"
                className="w-full px-4 py-3 rounded-xl bg-[#0A0E1A] border border-white/10 text-lg font-bold text-gray-100 tabular-nums placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 transition-all"
              />
            </div>

            {/* Botones */}
            <div className="flex gap-3 pt-1">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="flex-1">
                Cancelar
              </Button>
              <Button type="submit" disabled={saving || !form.banco || !form.fecha_corte || !form.fecha_pago} className="flex-1 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 shadow-lg shadow-violet-500/20">
                {saving ? "Guardando..." : editing ? "Actualizar" : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
