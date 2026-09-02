"use client"

import { useState } from "react"
import { toast } from "sonner"
import { api, ApiError } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import type { Categoria } from "@/lib/types"
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
  nombre: string
  tipo: string
}

const emptyForm: FormState = { nombre: "", tipo: "gasto" }

export default function CategoriasPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Categoria | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)

  const {
    data: categorias,
    loading,
    refetch,
  } = usePolling<Categoria[]>(() => api.get("/api/categorias"), 5000)

  function openCreate() {
    setEditing(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function openEdit(c: Categoria) {
    setEditing(c)
    setForm({ nombre: c.nombre, tipo: c.tipo })
    setDialogOpen(true)
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar esta categoria?")) return
    try {
      await api.del(`/api/categorias/${id}`)
      toast.success("Categoria eliminada")
      refetch()
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        toast.error("No se puede borrar: la categoria tiene movimientos asociados")
      } else {
        toast.error(e instanceof Error ? e.message : "Error al eliminar")
      }
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const body = { nombre: form.nombre, tipo: form.tipo }
      if (editing) {
        await api.patch(`/api/categorias/${editing.id}`, body)
        toast.success("Categoria actualizada")
      } else {
        await api.post("/api/categorias", body)
        toast.success("Categoria creada")
      }
      setDialogOpen(false)
      refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al guardar")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Categorias</h1>
        <Button onClick={openCreate}>Nueva categoria</Button>
      </div>

      {loading && <p className="text-muted-foreground">Cargando...</p>}

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(categorias ?? []).map((c) => (
                <TableRow key={c.id}>
                  <TableCell>{c.id}</TableCell>
                  <TableCell className="font-medium">{c.nombre}</TableCell>
                  <TableCell>
                    <Badge
                      className={
                        c.tipo === "ingreso"
                          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25"
                          : "bg-rose-500/15 text-rose-400 border-rose-500/25"
                      }
                      variant="outline"
                    >
                      {c.tipo}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="xs" onClick={() => openEdit(c)}>
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        className="text-rose-400"
                        onClick={() => handleDelete(c.id)}
                      >
                        Borrar
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!loading && (categorias ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    No hay categorias
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Editar categoria" : "Nueva categoria"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Nombre</label>
              <Input
                required
                value={form.nombre}
                onChange={(e) =>
                  setForm((f) => ({ ...f, nombre: e.target.value }))
                }
                placeholder="Nombre de la categoria"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Tipo</label>
              <Select
                value={form.tipo}
                onValueChange={(v) => setForm((f) => ({ ...f, tipo: v ?? "gasto" }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gasto">Gasto</SelectItem>
                  <SelectItem value="ingreso">Ingreso</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={saving || !form.nombre}>
                {saving ? "Guardando..." : editing ? "Actualizar" : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
