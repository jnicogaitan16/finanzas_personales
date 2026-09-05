"use client"

import { useState } from "react"
import { toast } from "sonner"
import { api, ApiError } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import type { Usuario } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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

interface FormState {
  nombre: string
  email: string
}

const emptyForm: FormState = { nombre: "", email: "" }

export default function UsuariosPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Usuario | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)

  const {
    data: usuarios,
    loading,
    refetch,
  } = usePolling<Usuario[]>(() => api.get("/api/usuarios"), 5000)

  function openCreate() {
    setEditing(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function openEdit(u: Usuario) {
    setEditing(u)
    setForm({ nombre: u.nombre, email: u.email ?? "" })
    setDialogOpen(true)
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar este usuario?")) return
    try {
      await api.del(`/api/usuarios/${id}`)
      toast.success("Usuario eliminado")
      refetch()
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        toast.error("No se puede borrar: el usuario tiene movimientos asociados")
      } else {
        toast.error(e instanceof Error ? e.message : "Error al eliminar")
      }
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const body = {
        nombre: form.nombre,
        email: form.email || null,
      }
      if (editing) {
        await api.patch(`/api/usuarios/${editing.id}`, body)
        toast.success("Usuario actualizado")
      } else {
        await api.post("/api/usuarios", body)
        toast.success("Usuario creado")
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
        <h1 className="text-xl font-bold text-gray-100">Usuarios</h1>
        <Button onClick={openCreate}>Nuevo usuario</Button>
      </div>

      {loading && <p className="text-gray-400">Cargando...</p>}

      <div className="rounded-xl border border-white/5 bg-white/[0.03] overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(usuarios ?? []).map((u) => (
                <TableRow key={u.id}>
                  <TableCell>{u.id}</TableCell>
                  <TableCell className="font-medium">{u.nombre}</TableCell>
                  <TableCell className="text-gray-400">
                    {u.email || "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="xs" onClick={() => openEdit(u)}>
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        className="text-rose-400"
                        onClick={() => handleDelete(u.id)}
                      >
                        Borrar
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!loading && (usuarios ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-gray-400 py-8">
                    No hay usuarios
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
              {editing ? "Editar usuario" : "Nuevo usuario"}
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
                placeholder="Nombre del usuario"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Email</label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) =>
                  setForm((f) => ({ ...f, email: e.target.value }))
                }
                placeholder="usuario@ejemplo.com"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={saving || !form.nombre}
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
