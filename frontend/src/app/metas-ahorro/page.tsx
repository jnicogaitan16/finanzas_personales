"use client"

import { useCallback, useState } from "react"
import { toast } from "sonner"
import { Target, Plus, Trash2, Pencil } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useAuth } from "@/hooks/use-auth"
import { formatCOP } from "@/lib/format"
import type { MetaAhorro } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface FormState {
  nombre: string
  monto_objetivo_cop: string
  monto_actual_cop: string
  fecha_limite: string
}

const emptyForm: FormState = {
  nombre: "",
  monto_objetivo_cop: "",
  monto_actual_cop: "0",
  fecha_limite: "",
}

function progressColor(pct: number) {
  if (pct >= 100) return "bg-emerald-400"
  if (pct >= 60) return "bg-violet-500"
  if (pct >= 30) return "bg-amber-400"
  return "bg-gray-500"
}

function progressRingColor(pct: number) {
  if (pct >= 100) return "#34d399"
  if (pct >= 60) return "#8b5cf6"
  if (pct >= 30) return "#fbbf24"
  return "#6b7280"
}

export default function MetasAhorroPage() {
  const { userId } = useAuth()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)

  const fetchMetas = useCallback(() => api.get<MetaAhorro[]>("/api/metas-ahorro"), [])
  const { data: metas, refetch } = usePolling(fetchMetas, 5000)

  function openCreate() {
    setEditId(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function openEdit(meta: MetaAhorro) {
    setEditId(meta.id)
    setForm({
      nombre: meta.nombre,
      monto_objetivo_cop: String(meta.monto_objetivo_cop),
      monto_actual_cop: String(meta.monto_actual_cop),
      fecha_limite: meta.fecha_limite || "",
    })
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editId) {
        await api.patch(`/api/metas-ahorro/${editId}`, {
          nombre: form.nombre,
          monto_objetivo_cop: Number(form.monto_objetivo_cop),
          monto_actual_cop: Number(form.monto_actual_cop),
          fecha_limite: form.fecha_limite || null,
        })
        toast.success("Meta actualizada")
      } else {
        await api.post("/api/metas-ahorro", {
          user_id: userId,
          nombre: form.nombre,
          monto_objetivo_cop: Number(form.monto_objetivo_cop),
          monto_actual_cop: Number(form.monto_actual_cop),
          fecha_limite: form.fecha_limite || null,
        })
        toast.success("Meta creada")
      }
      setDialogOpen(false)
      refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al guardar")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("¿Eliminar esta meta?")) return
    try {
      await api.del(`/api/metas-ahorro/${id}`)
      toast.success("Meta eliminada")
      refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al eliminar")
    }
  }

  const activas = (metas ?? []).filter(m => m.activa)
  const completadas = (metas ?? []).filter(m => m.progreso >= 100)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-100">Metas de ahorro</h1>
        <Button onClick={openCreate} size="sm">
          <Plus className="w-4 h-4 mr-1" /> Nueva meta
        </Button>
      </div>

      {activas.length === 0 && (
        <div className="text-center py-16 space-y-3">
          <Target className="w-12 h-12 text-gray-600 mx-auto" />
          <p className="text-gray-400">No tienes metas de ahorro activas</p>
          <p className="text-sm text-gray-500">
            Crea una meta para empezar a ahorrar con objetivo
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {activas.map(meta => {
          const circumference = 2 * Math.PI * 36
          const offset = circumference * (1 - Math.min(meta.progreso, 100) / 100)
          const ringColor = progressRingColor(meta.progreso)

          return (
            <div
              key={meta.id}
              className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 space-y-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-gray-100">{meta.nombre}</h3>
                  {meta.fecha_limite && (
                    <p className="text-xs text-gray-500 mt-0.5">Meta: {meta.fecha_limite}</p>
                  )}
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => openEdit(meta)}
                    className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500 hover:text-gray-300"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(meta.id)}
                    className="p-1.5 rounded-lg hover:bg-rose-500/10 text-gray-500 hover:text-rose-400"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-5">
                {/* Progress ring */}
                <div className="relative w-20 h-20 shrink-0">
                  <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                    <circle cx="50" cy="50" r="36" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
                    <circle
                      cx="50" cy="50" r="36"
                      fill="none"
                      stroke={ringColor}
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray={circumference}
                      strokeDashoffset={offset}
                      className="transition-all duration-700"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold" style={{ color: ringColor }}>
                      {meta.progreso}%
                    </span>
                  </div>
                </div>

                <div className="flex-1 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Ahorrado</span>
                    <span className="text-gray-200 font-medium tabular-nums">{formatCOP(meta.monto_actual_cop)}</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${progressColor(meta.progreso)}`}
                      style={{ width: `${Math.min(meta.progreso, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Objetivo</span>
                    <span className="text-gray-200 font-medium tabular-nums">{formatCOP(meta.monto_objetivo_cop)}</span>
                  </div>
                </div>
              </div>

              {meta.progreso < 100 && meta.monto_objetivo_cop > meta.monto_actual_cop && (
                <p className="text-xs text-gray-500">
                  Faltan {formatCOP(meta.monto_objetivo_cop - meta.monto_actual_cop)} para completar
                </p>
              )}
              {meta.progreso >= 100 && (
                <p className="text-xs text-emerald-400 font-medium">Meta completada</p>
              )}
            </div>
          )
        })}
      </div>

      {completadas.length > 0 && (
        <div className="text-center">
          <p className="text-sm text-gray-500">
            {completadas.length} meta{completadas.length > 1 ? "s" : ""} completada{completadas.length > 1 ? "s" : ""}
          </p>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editId ? "Editar meta" : "Nueva meta de ahorro"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Nombre</label>
              <Input
                required
                value={form.nombre}
                onChange={(e) => setForm(f => ({ ...f, nombre: e.target.value }))}
                placeholder="Ej: Viaje a Cartagena"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Monto objetivo (COP)</label>
              <Input
                type="number"
                required
                value={form.monto_objetivo_cop}
                onChange={(e) => setForm(f => ({ ...f, monto_objetivo_cop: e.target.value }))}
                placeholder="2000000"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Monto actual (COP)</label>
              <Input
                type="number"
                value={form.monto_actual_cop}
                onChange={(e) => setForm(f => ({ ...f, monto_actual_cop: e.target.value }))}
                placeholder="0"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Fecha limite (opcional)</label>
              <Input
                type="date"
                value={form.fecha_limite}
                onChange={(e) => setForm(f => ({ ...f, fecha_limite: e.target.value }))}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={saving || !form.nombre || !form.monto_objetivo_cop}
              >
                {saving ? "Guardando..." : editId ? "Guardar" : "Crear"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
