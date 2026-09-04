"use client"

import { useState, useCallback } from "react"
import { toast } from "sonner"
import { Plus, CreditCard, Pencil, Trash2, ChevronRight } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { formatCOP } from "@/lib/format"
import type { TarjetaCredito, CompraCuotas, Usuario, ProyeccionMes } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface FormState {
  user_id: string
  banco: string
  nombre: string
  ultimos_4: string
  fecha_corte: string
  fecha_pago: string
  tasa_ea: string
  cupo_total_cop: string
}

const emptyForm: FormState = {
  user_id: "",
  banco: "",
  nombre: "",
  ultimos_4: "",
  fecha_corte: "",
  fecha_pago: "",
  tasa_ea: "",
  cupo_total_cop: "",
}

const BANCOS = ["Bancolombia", "Davivienda", "BBVA", "Scotiabank", "Nu", "Rappi", "Otro"]

const CARD_GRADIENTS = [
  "from-violet-600 to-indigo-700",
  "from-emerald-600 to-teal-700",
  "from-rose-600 to-pink-700",
  "from-amber-600 to-orange-700",
  "from-cyan-600 to-blue-700",
  "from-fuchsia-600 to-purple-700",
]

export default function TarjetasPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<TarjetaCredito | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)

  const fetchTarjetas = useCallback(() => api.get<TarjetaCredito[]>("/api/tarjetas"), [])
  const { data: tarjetas, refetch: refetchTarjetas } = usePolling(fetchTarjetas, 5000)

  const fetchCuotas = useCallback(() => api.get<CompraCuotas[]>("/api/cuotas"), [])
  const { data: cuotas } = usePolling(fetchCuotas, 5000)

  const fetchUsuarios = useCallback(() => api.get<Usuario[]>("/api/usuarios"), [])
  const { data: usuarios } = usePolling(fetchUsuarios, 30000)

  const fetchProyeccion = useCallback(() => api.get<Record<string, ProyeccionMes>>("/api/proyeccion-cuotas?meses=6"), [])
  const { data: proyeccion } = usePolling(fetchProyeccion, 10000)

  function openCreate() {
    setEditing(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function openEdit(t: TarjetaCredito) {
    setEditing(t)
    setForm({
      user_id: String(t.user_id),
      banco: t.banco,
      nombre: t.nombre,
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
      const base = {
        user_id: Number(form.user_id),
        banco: form.banco,
        nombre: form.nombre,
        ultimos_4: form.ultimos_4 || null,
        fecha_corte: Number(form.fecha_corte),
        fecha_pago: Number(form.fecha_pago),
        tasa_ea: form.tasa_ea ? Number(form.tasa_ea) : null,
        cupo_total_cop: form.cupo_total_cop ? Number(form.cupo_total_cop) : null,
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Tarjetas</h1>
        <Button onClick={openCreate} size="sm">
          <Plus className="w-4 h-4 mr-1" /> Agregar
        </Button>
      </div>

      {/* Cards carousel */}
      {(tarjetas ?? []).length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No tienes tarjetas registradas</p>
          <p className="text-sm mt-1">Agrega tu primera tarjeta de credito</p>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
          {(tarjetas ?? []).map((t, i) => (
            <div
              key={t.id}
              className={`shrink-0 w-72 bg-gradient-to-br ${CARD_GRADIENTS[i % CARD_GRADIENTS.length]} rounded-2xl p-5 text-white cursor-pointer snap-start transition-transform hover:scale-[1.02]`}
              onClick={() => setExpanded(expanded === t.id ? null : t.id)}
            >
              <div className="flex items-center justify-between mb-6">
                <span className="text-sm font-medium opacity-80">{t.banco}</span>
                <div className="flex gap-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); openEdit(t) }}
                    className="p-1 rounded-lg hover:bg-white/20"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(t.id) }}
                    className="p-1 rounded-lg hover:bg-white/20"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-2 mb-4">
                <CreditCard className="w-6 h-6 opacity-60" />
                <span className="text-lg tracking-[0.2em] font-mono">
                  •••• {t.ultimos_4 || "????"}
                </span>
              </div>
              <p className="text-sm font-medium mb-1">{t.nombre}</p>
              <div className="flex justify-between text-xs opacity-70 mt-3">
                <span>Corte: {t.fecha_corte}</span>
                <span>Pago: {t.fecha_pago}</span>
                {t.tasa_ea != null && <span>{t.tasa_ea}% EA</span>}
              </div>
              {/* Summary below card */}
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

      {/* Expanded: compras activas de la tarjeta seleccionada */}
      {expanded && (
        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
          <h3 className="text-sm text-gray-400 uppercase tracking-wide mb-3">
            Compras activas — {(tarjetas ?? []).find(t => t.id === expanded)?.nombre}
          </h3>
          {getCuotasByTarjeta(expanded).length === 0 ? (
            <p className="text-gray-500 text-sm">Sin compras activas en esta tarjeta</p>
          ) : (
            <div className="space-y-2">
              {getCuotasByTarjeta(expanded).map(c => (
                <div key={c.id} className="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-100">{c.establecimiento}</p>
                    <p className="text-xs text-gray-500">{c.fecha_compra}</p>
                  </div>
                  {/* Progress */}
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-20 h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-400 rounded-full"
                        style={{ width: `${(c.cuotas_pagadas / c.num_cuotas) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">
                      {c.cuotas_pagadas}/{c.num_cuotas}
                    </span>
                  </div>
                  <span className="text-sm font-semibold text-gray-200 tabular-nums shrink-0">
                    {formatCOP(c.valor_cuota_cop)}/mes
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Proyeccion 6 meses */}
      {proyeccion && Object.keys(proyeccion).length > 0 && (
        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
          <h3 className="text-sm text-gray-400 uppercase tracking-wide mb-4">
            Proyeccion de cuotas
          </h3>
          <div className="space-y-2">
            {Object.entries(proyeccion).map(([mes, data]) => {
              const [y, m] = mes.split("-").map(Number)
              const label = `${MESES_CORTOS[m - 1]} ${y}`
              return (
                <div key={mes} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                  <span className="text-sm text-gray-300 font-medium">{label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">{data.compras.length} compras</span>
                    <span className="text-sm font-bold text-rose-400 tabular-nums">
                      {formatCOP(data.total)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Dialog crear/editar tarjeta */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar tarjeta" : "Nueva tarjeta"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="grid gap-4 mt-2">
            <label className="text-sm">
              Usuario
              <select
                value={form.user_id}
                onChange={(e) => setForm(f => ({ ...f, user_id: e.target.value }))}
                required
                className="w-full mt-1 px-3 py-2 rounded-lg border text-sm"
              >
                <option value="">Seleccionar</option>
                {(usuarios ?? []).map(u => (
                  <option key={u.id} value={String(u.id)}>{u.nombre}</option>
                ))}
              </select>
            </label>

            <label className="text-sm">
              Banco
              <select
                value={form.banco}
                onChange={(e) => setForm(f => ({ ...f, banco: e.target.value }))}
                required
                className="w-full mt-1 px-3 py-2 rounded-lg border text-sm"
              >
                <option value="">Seleccionar</option>
                {BANCOS.map(b => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </label>

            <label className="text-sm">
              Nombre de la tarjeta
              <Input
                value={form.nombre}
                onChange={(e) => setForm(f => ({ ...f, nombre: e.target.value }))}
                placeholder="Visa Gold, Mastercard Black..."
                required
                className="mt-1"
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">
                Ultimos 4 digitos
                <Input
                  value={form.ultimos_4}
                  onChange={(e) => setForm(f => ({ ...f, ultimos_4: e.target.value }))}
                  maxLength={4}
                  placeholder="1234"
                  className="mt-1"
                />
              </label>
              <label className="text-sm">
                Tasa EA (%)
                <Input
                  type="number"
                  step="0.1"
                  value={form.tasa_ea}
                  onChange={(e) => setForm(f => ({ ...f, tasa_ea: e.target.value }))}
                  placeholder="28.5"
                  className="mt-1"
                />
              </label>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">
                Dia de corte
                <Input
                  type="number"
                  min={1}
                  max={31}
                  value={form.fecha_corte}
                  onChange={(e) => setForm(f => ({ ...f, fecha_corte: e.target.value }))}
                  required
                  placeholder="8"
                  className="mt-1"
                />
              </label>
              <label className="text-sm">
                Dia de pago
                <Input
                  type="number"
                  min={1}
                  max={31}
                  value={form.fecha_pago}
                  onChange={(e) => setForm(f => ({ ...f, fecha_pago: e.target.value }))}
                  required
                  placeholder="25"
                  className="mt-1"
                />
              </label>
            </div>

            <label className="text-sm">
              Cupo total (COP)
              <Input
                type="number"
                value={form.cupo_total_cop}
                onChange={(e) => setForm(f => ({ ...f, cupo_total_cop: e.target.value }))}
                placeholder="5000000"
                className="mt-1"
              />
            </label>

            <div className="flex justify-end gap-2 mt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Guardando..." : editing ? "Actualizar" : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
