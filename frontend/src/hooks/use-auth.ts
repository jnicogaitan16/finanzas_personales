"use client"
import { useCallback } from "react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"

interface MeData {
  id: number
  nombre: string
  grupo: { id: number; nombre: string } | null
  miembros: { id: number; nombre: string }[]
  codigo_invitacion_activo: string | null
  max_miembros: number
}

export function useAuth() {
  const fetchMe = useCallback(() => api.get<MeData>("/api/me"), [])
  const { data } = usePolling(fetchMe, 30000)
  return {
    user: data ? { id: data.id, nombre: data.nombre } : null,
    userId: data?.id ?? null,
    grupo: data?.grupo ?? null,
    miembros: data?.miembros ?? [],
  }
}
