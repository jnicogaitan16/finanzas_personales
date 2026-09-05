"use client"

import { useState, useMemo } from "react"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useUserFilter } from "@/hooks/use-user-filter"
import { useAuth } from "@/hooks/use-auth"
import { useSort } from "@/hooks/use-sort"
import { formatCOP, formatDate } from "@/lib/format"
import type { CompraCuotas } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SortableHead } from "@/components/ui/sortable-head"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

/* ------------------------------------------------------------------ */
/*  Form state for create / edit dialog                                */
/* ------------------------------------------------------------------ */

interface FormState {
  fecha_compra: string
  establecimiento: string
  descripcion: string
  valor_total_cop: string
  num_cuotas: string
  cuotas_pagadas: string
  valor_cuota: string
  valor_intereses: string
  tasa_ea: string
  numero_transaccion: string
  compartida: boolean
}

const emptyForm: FormState = {
  fecha_compra: "",
  establecimiento: "",
  descripcion: "",
  valor_total_cop: "",
  num_cuotas: "",
  cuotas_pagadas: "0",
  valor_cuota: "",
  valor_intereses: "0",
  tasa_ea: "",
  numero_transaccion: "",
  compartida: false,
}

/* ------------------------------------------------------------------ */
/*  Progress bar component                                            */
/* ------------------------------------------------------------------ */

function ProgressBar({ pagadas, total }: { pagadas: number; total: number }) {
  const pct = total > 0 ? Math.round((pagadas / total) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-zinc-200 dark:bg-zinc-700 overflow-hidden">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-gray-400">
        {pagadas}/{total}
      </span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main page                                                         */
/* ------------------------------------------------------------------ */

export default function CuotasPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const { selectedUser: filterUser } = useUserFilter()
  const { userId } = useAuth()
  const [saving, setSaving] = useState(false)

  const {
    data: cuotas,
    loading: loadingCuotas,
    refetch: refetchCuotas,
  } = usePolling<CompraCuotas[]>(() => api.get("/api/cuotas"), 5000)

  /* ---- Filtered list ---- */
  const filtered = useMemo(
    () =>
      (cuotas ?? []).filter((c) => {
        if (filterUser === "todos") return true
        return String(c.user_id) === filterUser
      }),
    [cuotas, filterUser],
  )

  const { sorted, sort, toggle } = useSort(filtered, "fecha_compra"
  )

  /* ---- Summary metrics (active only) ---- */
  const activas = useMemo(() => filtered.filter((c) => !c.liquidada), [filtered])
  const cuotaMensualTotal = useMemo(
    () => activas.reduce((s, c) => s + c.valor_cuota_cop, 0),
    [activas],
  )
  const deudaTotal = useMemo(
    () => activas.reduce((s, c) => s + c.saldo_pendiente_cop, 0),
    [activas],
  )
  const comprasActivas = activas.length

  /* ---- Auto-calculate valor_cuota when valor_total or num_cuotas changes ---- */
  function updateForm(patch: Partial<FormState>) {
    setForm((prev) => {
      const next = { ...prev, ...patch }

      // Auto-calculate valor_cuota when total or num_cuotas change
      if ("valor_total_cop" in patch || "num_cuotas" in patch) {
        const total = Number(next.valor_total_cop) || 0
        const n = Number(next.num_cuotas) || 0
        if (total > 0 && n > 0) {
          next.valor_cuota = String(Math.round(total / n))
        }
      }

      // Auto-recalculate saldo_pendiente is done on display / submit
      return next
    })
  }

  /* ---- Computed saldo from form ---- */
  function computeSaldo(f: FormState): number {
    const cuota = Number(f.valor_cuota) || 0
    const total = Number(f.num_cuotas) || 0
    const pagadas = Number(f.cuotas_pagadas) || 0
    const restantes = Math.max(total - pagadas, 0)
    return cuota * restantes
  }

  /* ---- Open create dialog ---- */
  function openCreate() {
    setEditingId(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  /* ---- Open edit dialog ---- */
  function openEdit(c: CompraCuotas) {
    setEditingId(c.id)
    setForm({
      fecha_compra: c.fecha_compra ? c.fecha_compra.split("T")[0] : "",
      establecimiento: c.establecimiento,
      descripcion: c.descripcion ?? "",
      valor_total_cop: String(c.valor_total_cop),
      num_cuotas: String(c.num_cuotas),
      cuotas_pagadas: String(c.cuotas_pagadas),
      valor_cuota: String(c.valor_cuota_cop),
      valor_intereses: String(c.valor_intereses_cop),
      tasa_ea: c.tasa_ea != null ? String(c.tasa_ea) : "",
      numero_transaccion: c.numero_transaccion ?? "",
      compartida: c.es_compartido ?? false,
    })
    setDialogOpen(true)
  }

  /* ---- Submit create or edit ---- */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)

    const body: Record<string, unknown> = {
      user_id: userId,
      fecha_compra: form.fecha_compra || null,
      establecimiento: form.establecimiento,
      descripcion: form.descripcion || null,
      valor_total_cop: Number(form.valor_total_cop),
      num_cuotas: Number(form.num_cuotas),
      cuotas_pagadas: Number(form.cuotas_pagadas),
      valor_cuota_cop: Number(form.valor_cuota) || null,
      valor_intereses_cop: Number(form.valor_intereses) || 0,
      tasa_ea: form.tasa_ea ? Number(form.tasa_ea) : null,
      numero_transaccion: form.numero_transaccion || null,
      es_compartido: form.compartida,
    }

    try {
      if (editingId) {
        await api.patch(`/api/cuotas/${editingId}`, body)
        toast.success("Compra actualizada")
      } else {
        await api.post("/api/cuotas", body)
        toast.success("Compra en cuotas creada")
      }
      setDialogOpen(false)
      refetchCuotas()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al guardar")
    } finally {
      setSaving(false)
    }
  }

  /* ---- Delete ---- */
  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar esta compra en cuotas?")) return
    try {
      await api.del(`/api/cuotas/${id}`)
      toast.success("Compra eliminada")
      refetchCuotas()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al eliminar")
    }
  }

  /* ================================================================ */
  /*  RENDER                                                          */
  /* ================================================================ */

  return (
    <div className="space-y-6">
      {/* ---- Header row ---- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Compras en cuotas</h1>
        <div className="flex items-center gap-3">
          {(filterUser === "todos" || filterUser === String(userId)) && (
            <Button onClick={openCreate}>Nueva compra</Button>
          )}
        </div>
      </div>

      {/* ---- Summary cards ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-5 space-y-1">
          <p className="text-sm text-gray-400">Cuota mensual total</p>
          <p className="text-2xl font-semibold tabular-nums text-rose-500">
            {formatCOP(cuotaMensualTotal)}
          </p>
        </div>
        <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-5 space-y-1">
          <p className="text-sm text-gray-400">Deuda total</p>
          <p className="text-2xl font-semibold tabular-nums text-rose-500">
            {formatCOP(deudaTotal)}
          </p>
        </div>
        <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-5 space-y-1">
          <p className="text-sm text-gray-400">Compras activas</p>
          <p className="text-2xl font-semibold tabular-nums">
            {comprasActivas}
          </p>
        </div>
      </div>

      {/* ---- Loading ---- */}
      {loadingCuotas && !cuotas && (
        <p className="text-gray-400">Cargando...</p>
      )}

      {/* ---- Table ---- */}
      <div className="rounded-2xl border border-white/5 overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHead label="Fecha" sortKey="fecha_compra" sort={sort} onToggle={toggle} />
                <SortableHead label="Establecimiento" sortKey="establecimiento" sort={sort} onToggle={toggle} />
                <SortableHead label="Valor total" sortKey="valor_total_cop" sort={sort} onToggle={toggle} className="text-right" />
                <SortableHead label="Cuotas" sortKey="cuotas_pagadas" sort={sort} onToggle={toggle} className="text-center" />
                <SortableHead label="Valor cuota" sortKey="valor_cuota_cop" sort={sort} onToggle={toggle} className="text-right" />
                <SortableHead label="Intereses" sortKey="valor_intereses_cop" sort={sort} onToggle={toggle} className="text-right" />
                <SortableHead label="Saldo pendiente" sortKey="saldo_pendiente_cop" sort={sort} onToggle={toggle} className="text-right" />
                <SortableHead label="Tarjeta" sortKey="tarjeta" sort={sort} onToggle={toggle} />
                <SortableHead label="Tasa %EA" sortKey="tasa_ea" sort={sort} onToggle={toggle} className="text-right" />
                <TableHead className="text-center">Comp.</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((c) => (
                <TableRow
                  key={c.id}
                  className={c.liquidada ? "opacity-40" : ""}
                >
                  <TableCell className="whitespace-nowrap text-sm">
                    {formatDate(c.fecha_compra)}
                  </TableCell>
                  <TableCell className="font-medium">
                    {c.establecimiento}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCOP(c.valor_total_cop)}
                  </TableCell>
                  <TableCell className="text-center">
                    <ProgressBar
                      pagadas={c.cuotas_pagadas}
                      total={c.num_cuotas}
                    />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCOP(c.valor_cuota_cop)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-gray-400">
                    {formatCOP(c.valor_intereses_cop)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium text-rose-500">
                    {formatCOP(c.saldo_pendiente_cop)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {c.tarjeta ?? "---"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-gray-400">
                    {c.tasa_ea != null ? `${c.tasa_ea}%` : "---"}
                  </TableCell>
                  <TableCell className="text-center">
                    {c.es_compartido ? (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">50%</span>
                    ) : "---"}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    {c.user_id === userId && (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          className="text-xs font-medium text-blue-500 hover:text-blue-700 transition-colors"
                          onClick={() => openEdit(c)}
                        >
                          Editar
                        </button>
                        <button
                          className="text-xs font-medium text-rose-400 hover:text-rose-600 transition-colors"
                          onClick={() => handleDelete(c.id)}
                        >
                          Eliminar
                        </button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {!loadingCuotas && filtered.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={11}
                    className="text-center text-gray-400 py-10"
                  >
                    No hay compras en cuotas
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* ================================================================ */}
      {/*  Create / Edit Dialog                                            */}
      {/* ================================================================ */}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg bg-white dark:bg-zinc-900">
          <DialogHeader>
            <DialogTitle>
              {editingId ? "Editar compra en cuotas" : "Nueva compra en cuotas"}
            </DialogTitle>
          </DialogHeader>

          <form
            onSubmit={handleSubmit}
            className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 mt-2"
          >
            {/* Establecimiento */}
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label className="text-sm font-medium">Establecimiento</label>
              <Input
                required
                value={form.establecimiento}
                onChange={(e) =>
                  updateForm({ establecimiento: e.target.value })
                }
                placeholder="Nombre del comercio"
              />
            </div>

            {/* Fecha compra */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Fecha compra</label>
              <Input
                type="date"
                value={form.fecha_compra}
                onChange={(e) =>
                  updateForm({ fecha_compra: e.target.value })
                }
              />
            </div>

            {/* Valor total */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Valor total</label>
              <Input
                type="number"
                required
                value={form.valor_total_cop}
                onChange={(e) =>
                  updateForm({ valor_total_cop: e.target.value })
                }
                placeholder="0"
              />
            </div>

            {/* Num cuotas total */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">No. cuotas total</label>
              <Input
                type="number"
                required
                min={1}
                value={form.num_cuotas}
                onChange={(e) =>
                  updateForm({ num_cuotas: e.target.value })
                }
                placeholder="12"
              />
            </div>

            {/* Cuotas pagadas */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Cuotas pagadas</label>
              <Input
                type="number"
                min={0}
                max={Number(form.num_cuotas) || 999}
                value={form.cuotas_pagadas}
                onChange={(e) =>
                  updateForm({ cuotas_pagadas: e.target.value })
                }
                placeholder="0"
              />
              {form.num_cuotas && form.cuotas_pagadas && (
                <p className="text-xs text-gray-400">
                  Saldo estimado:{" "}
                  <span className="font-medium text-rose-500">
                    {formatCOP(computeSaldo(form))}
                  </span>
                </p>
              )}
            </div>

            {/* Valor cuota */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Valor cuota</label>
              <Input
                type="number"
                value={form.valor_cuota}
                onChange={(e) =>
                  setForm((f) => ({ ...f, valor_cuota: e.target.value }))
                }
                placeholder="Auto-calculado"
              />
            </div>

            {/* Valor intereses */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Valor intereses</label>
              <Input
                type="number"
                value={form.valor_intereses}
                onChange={(e) =>
                  updateForm({ valor_intereses: e.target.value })
                }
                placeholder="0"
              />
            </div>

            {/* Tasa EA */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Tasa EA %</label>
              <Input
                type="number"
                step="0.01"
                value={form.tasa_ea}
                onChange={(e) =>
                  updateForm({ tasa_ea: e.target.value })
                }
                placeholder="28.77"
              />
            </div>

            {/* No. transaccion */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">No. transaccion</label>
              <Input
                value={form.numero_transaccion}
                onChange={(e) =>
                  updateForm({ numero_transaccion: e.target.value })
                }
                placeholder="Opcional"
              />
            </div>

            {/* Compartida */}
            <div className="flex items-center gap-2 sm:col-span-2 pt-1">
              <input
                id="compartida"
                type="checkbox"
                checked={form.compartida}
                onChange={(e) =>
                  updateForm({ compartida: e.target.checked })
                }
                className="h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="compartida" className="text-sm font-medium">
                Compartida
              </label>
            </div>

            {/* Descripcion */}
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label className="text-sm font-medium">Descripcion</label>
              <Input
                value={form.descripcion}
                onChange={(e) =>
                  updateForm({ descripcion: e.target.value })
                }
                placeholder="Nota opcional"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-3 sm:col-span-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={
                  saving ||
                  !form.establecimiento ||
                  !form.valor_total_cop ||
                  !form.num_cuotas
                }
              >
                {saving
                  ? "Guardando..."
                  : editingId
                    ? "Guardar cambios"
                    : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
