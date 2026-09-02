"use client"

import { useState } from "react"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { formatCOP, formatDate } from "@/lib/format"
import type { Movimiento, Categoria, Usuario } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface FormState {
  user_id: string
  categoria_id: string
  monto_cop: string
  descripcion: string
  fecha_gasto: string
  mensaje_original: string
  medio_pago: string
  es_compartido: boolean
  num_cuotas: string
}

const emptyForm: FormState = {
  user_id: "",
  categoria_id: "",
  monto_cop: "",
  descripcion: "",
  fecha_gasto: "",
  mensaje_original: "",
  medio_pago: "cuenta_ahorros",
  es_compartido: false,
  num_cuotas: "1",
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
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Movimiento | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [filterUser, setFilterUser] = useState<string>("todos")
  const [saving, setSaving] = useState(false)

  const {
    data: movimientos,
    loading: loadingMov,
    refetch: refetchMov,
  } = usePolling<Movimiento[]>(() => api.get("/api/movimientos?limit=200"), 5000)

  const { data: categorias, refetch: refetchCat } = usePolling<Categoria[]>(
    () => api.get("/api/categorias"),
    5000,
  )

  const { data: usuarios, refetch: refetchUsr } = usePolling<Usuario[]>(
    () => api.get("/api/usuarios"),
    5000,
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
      mensaje_original: m.mensaje_original ?? "",
      medio_pago: m.medio_pago ?? "cuenta_ahorros",
      es_compartido: m.es_compartido ?? false,
      num_cuotas: "1",
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
        user_id: Number(form.user_id),
        categoria_id: form.categoria_id ? Number(form.categoria_id) : null,
        monto_cop: Number(form.monto_cop),
        descripcion: form.descripcion || null,
        fecha_gasto: form.fecha_gasto || null,
        mensaje_original: form.mensaje_original || null,
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
              user_id: Number(form.user_id),
              fecha_compra: form.fecha_gasto || new Date().toISOString().split("T")[0],
              establecimiento: form.descripcion || "Compra TC",
              valor_total_cop: Number(form.monto_cop),
              num_cuotas: numCuotas,
              tarjeta: "TC",
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
    return m.usuario?.toLowerCase() === filterUser.toLowerCase()
  })

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
        <h1 className="text-2xl font-bold">Movimientos</h1>
        <div className="flex items-center gap-3">
          <Select value={filterUser} onValueChange={(v) => setFilterUser(v ?? "todos")}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">Todos</SelectItem>
              {(usuarios ?? []).map((u) => (
                <SelectItem key={u.id} value={u.nombre.toLowerCase()}>
                  {u.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={openCreate}>Nuevo movimiento</Button>
        </div>
      </div>

      {loadingMov && <p className="text-muted-foreground">Cargando...</p>}

      <div className="rounded-xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead>Categoria</TableHead>
                <TableHead className="text-right">Monto</TableHead>
                <TableHead>Descripcion</TableHead>
                <TableHead>Medio</TableHead>
                <TableHead>Comp.</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((m) => (
                <TableRow key={m.id}>
                  <TableCell className="text-sm">{formatDate(m.fecha_gasto)}</TableCell>
                  <TableCell className="text-sm">{m.usuario ?? "—"}</TableCell>
                  <TableCell>
                    {m.categoria ? (
                      <span className="text-sm">{m.categoria}</span>
                    ) : "—"}
                  </TableCell>
                  <TableCell
                    className={`tabular-nums font-medium text-right text-sm ${
                      m.tipo === "ingreso" ? "text-primary" : "text-rose-400"
                    }`}
                  >
                    {m.tipo === "ingreso" ? "+" : "-"}
                    {formatCOP(m.monto_cop)}
                  </TableCell>
                  <TableCell className="max-w-[180px] truncate text-sm">
                    {m.descripcion ?? "—"}
                  </TableCell>
                  <TableCell>
                    {m.medio_pago ? (
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        m.medio_pago === "tarjeta_credito"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-gray-100 text-gray-600"
                      }`}>
                        {m.medio_pago === "tarjeta_credito" ? "TC" : medioPagoLabel(m.medio_pago)}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {m.es_compartido && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">50%</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button className="text-xs text-gray-500 hover:text-gray-800" onClick={() => openEdit(m)}>
                        Editar
                      </button>
                      <button className="text-xs text-rose-400 hover:text-rose-600" onClick={() => handleDelete(m.id)}>
                        Borrar
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!loadingMov && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    No hay movimientos
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Editar movimiento" : "Nuevo movimiento"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-2">
            <div className="flex gap-3">
              <div className="flex-1 flex flex-col gap-1.5">
                <label className="text-sm font-medium">Usuario</label>
                <select
                  value={form.user_id}
                  onChange={(e) => setForm((f) => ({ ...f, user_id: e.target.value }))}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm"
                  required
                >
                  <option value="">Seleccionar</option>
                  {(usuarios ?? []).map((u) => (
                    <option key={u.id} value={String(u.id)}>{u.nombre}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1 flex flex-col gap-1.5">
                <label className="text-sm font-medium">Categoria</label>
                <select
                  value={form.categoria_id}
                  onChange={(e) => setForm((f) => ({ ...f, categoria_id: e.target.value }))}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm"
                >
                  <option value="">Sin categoria</option>
                  {(categorias ?? []).map((c) => (
                    <option key={c.id} value={String(c.id)}>{c.nombre}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="flex-1 flex flex-col gap-1.5">
                <label className="text-sm font-medium">Monto</label>
                <Input
                  type="number"
                  required
                  value={form.monto_cop}
                  onChange={(e) => setForm((f) => ({ ...f, monto_cop: e.target.value }))}
                  placeholder="0"
                />
              </div>
              <div className="flex-1 flex flex-col gap-1.5">
                <label className="text-sm font-medium">Fecha</label>
                <Input
                  type="date"
                  value={form.fecha_gasto}
                  onChange={(e) => setForm((f) => ({ ...f, fecha_gasto: e.target.value }))}
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Descripcion</label>
              <Input
                value={form.descripcion}
                onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))}
                placeholder="Descripcion"
              />
            </div>

            <div className="flex gap-3">
              <div className="flex-1 flex flex-col gap-1.5">
                <label className="text-sm font-medium">Medio de pago</label>
                <select
                  value={form.medio_pago}
                  onChange={(e) => setForm((f) => ({ ...f, medio_pago: e.target.value }))}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm"
                >
                  {MEDIOS_PAGO.map((mp) => (
                    <option key={mp.value} value={mp.value}>{mp.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end pb-1 gap-2">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.es_compartido}
                    onChange={(e) => setForm((f) => ({ ...f, es_compartido: e.target.checked }))}
                    className="w-4 h-4 rounded"
                  />
                  Compartido
                </label>
              </div>
            </div>

            {form.medio_pago === "tarjeta_credito" && (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Numero de cuotas</label>
                <Input
                  type="number"
                  min="1"
                  value={form.num_cuotas}
                  onChange={(e) => setForm((f) => ({ ...f, num_cuotas: e.target.value }))}
                  placeholder="1"
                />
                {parseInt(form.num_cuotas) > 1 && (
                  <p className="text-xs text-amber-600">
                    Se registrara en Cuotas: {parseInt(form.num_cuotas)} cuotas de {formatCOP(Math.round(Number(form.monto_cop) / parseInt(form.num_cuotas)))}
                  </p>
                )}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={saving || !form.user_id || !form.monto_cop}>
                {saving ? "Guardando..." : editing ? "Actualizar" : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
