"use client"

import { useState } from "react"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { formatCOP } from "@/lib/format"
import type { GastoFijo, Categoria, Usuario } from "@/lib/types"
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
  nombre: string
  monto_cop: string
  es_compartido: boolean
  porcentaje_compartido: string
  dia_esperado: string
}

const emptyForm: FormState = {
  user_id: "",
  categoria_id: "",
  nombre: "",
  monto_cop: "",
  es_compartido: false,
  porcentaje_compartido: "50",
  dia_esperado: "",
}

export default function GastosFijosPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<GastoFijo | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [filterUser, setFilterUser] = useState<string>("todos")
  const [saving, setSaving] = useState(false)

  const {
    data: gastosFijos,
    loading: loadingGF,
    refetch: refetchGF,
  } = usePolling<GastoFijo[]>(() => api.get("/api/gastos-fijos"), 5000)

  const { data: categorias } = usePolling<Categoria[]>(
    () => api.get("/api/categorias"),
    5000,
  )

  const { data: usuarios } = usePolling<Usuario[]>(
    () => api.get("/api/usuarios"),
    5000,
  )

  function openCreate() {
    setEditing(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function openEdit(g: GastoFijo) {
    setEditing(g)
    setForm({
      user_id: String(g.user_id),
      categoria_id: String(g.categoria_id),
      nombre: g.nombre,
      monto_cop: String(g.monto_cop),
      es_compartido: g.es_compartido,
      porcentaje_compartido: g.porcentaje_compartido != null ? String(g.porcentaje_compartido) : "50",
      dia_esperado: g.dia_esperado != null ? String(g.dia_esperado) : "",
    })
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const body = {
        user_id: Number(form.user_id),
        categoria_id: Number(form.categoria_id),
        nombre: form.nombre,
        monto_cop: Number(form.monto_cop),
        es_compartido: form.es_compartido,
        porcentaje_compartido: form.es_compartido ? Number(form.porcentaje_compartido) : null,
        dia_esperado: form.dia_esperado ? Number(form.dia_esperado) : null,
      }

      if (editing) {
        await api.patch(`/api/gastos-fijos/${editing.id}`, body)
        toast.success("Gasto fijo actualizado")
      } else {
        await api.post("/api/gastos-fijos", body)
        toast.success("Gasto fijo creado")
      }
      setDialogOpen(false)
      refetchGF()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al guardar")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar este gasto fijo?")) return
    try {
      await api.del(`/api/gastos-fijos/${id}`)
      toast.success("Gasto fijo eliminado")
      refetchGF()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al eliminar")
    }
  }

  async function handleToggleActivo(g: GastoFijo) {
    try {
      await api.patch(`/api/gastos-fijos/${g.id}`, { activo: !g.activo })
      toast.success(g.activo ? "Gasto fijo desactivado" : "Gasto fijo activado")
      refetchGF()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al actualizar")
    }
  }

  const filtered = (gastosFijos ?? []).filter((g) => {
    if (filterUser === "todos") return true
    return String(g.user_id) === filterUser
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Gastos Fijos</h1>
        <div className="flex items-center gap-3">
          <Select value={filterUser} onValueChange={(v) => setFilterUser(v ?? "todos")}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">Todos</SelectItem>
              {(usuarios ?? []).map((u) => (
                <SelectItem key={u.id} value={String(u.id)}>
                  {u.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={openCreate}>Nuevo gasto fijo</Button>
        </div>
      </div>

      {loadingGF && !gastosFijos && (
        <p className="text-muted-foreground">Cargando...</p>
      )}

      <div className="rounded-xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead>Categoria</TableHead>
                <TableHead className="text-right">Monto</TableHead>
                <TableHead className="text-center">Compartido</TableHead>
                <TableHead className="text-center">%</TableHead>
                <TableHead className="text-center">Dia</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((g) => (
                <TableRow key={g.id} className={!g.activo ? "opacity-50" : ""}>
                  <TableCell className="font-medium">{g.nombre}</TableCell>
                  <TableCell>{g.usuario ?? "—"}</TableCell>
                  <TableCell>{g.categoria ?? "—"}</TableCell>
                  <TableCell className="text-right tabular-nums font-medium text-rose-400">
                    {formatCOP(g.monto_cop)}
                  </TableCell>
                  <TableCell className="text-center">
                    {g.es_compartido ? (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-primary/20 text-primary">
                        Si
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-secondary text-muted-foreground">
                        No
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-center tabular-nums">
                    {g.porcentaje_compartido != null ? `${g.porcentaje_compartido}%` : "—"}
                  </TableCell>
                  <TableCell className="text-center tabular-nums">
                    {g.dia_esperado ?? "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => handleToggleActivo(g)}
                      >
                        {g.activo ? "Desactivar" : "Activar"}
                      </Button>
                      <Button variant="ghost" size="xs" onClick={() => openEdit(g)}>
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        className="text-rose-400"
                        onClick={() => handleDelete(g.id)}
                      >
                        Borrar
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!loadingGF && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    No hay gastos fijos
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
              {editing ? "Editar gasto fijo" : "Nuevo gasto fijo"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Usuario</label>
              <Select
                value={form.user_id}
                onValueChange={(v) => setForm((f) => ({ ...f, user_id: v ?? "" }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccionar usuario" />
                </SelectTrigger>
                <SelectContent>
                  {(usuarios ?? []).map((u) => (
                    <SelectItem key={u.id} value={String(u.id)}>
                      {u.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

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
              <label className="text-sm font-medium">Nombre</label>
              <Input
                required
                value={form.nombre}
                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                placeholder="Arriendo, Internet, etc."
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Monto</label>
              <Input
                type="number"
                required
                value={form.monto_cop}
                onChange={(e) => setForm((f) => ({ ...f, monto_cop: e.target.value }))}
                placeholder="0"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="es_compartido"
                checked={form.es_compartido}
                onChange={(e) => setForm((f) => ({ ...f, es_compartido: e.target.checked }))}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              <label htmlFor="es_compartido" className="text-sm font-medium">
                Compartido
              </label>
            </div>

            {form.es_compartido && (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Porcentaje compartido</label>
                <Input
                  type="number"
                  min="1"
                  max="100"
                  value={form.porcentaje_compartido}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, porcentaje_compartido: e.target.value }))
                  }
                  placeholder="50"
                />
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Dia del mes</label>
              <Input
                type="number"
                min="1"
                max="31"
                value={form.dia_esperado}
                onChange={(e) => setForm((f) => ({ ...f, dia_esperado: e.target.value }))}
                placeholder="1"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={saving || !form.user_id || !form.categoria_id || !form.nombre || !form.monto_cop}
              >
                {saving ? "Guardando..." : editing ? "Actualizar" : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
