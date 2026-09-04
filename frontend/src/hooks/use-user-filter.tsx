"use client"
import { createContext, useContext, useState, useCallback, type ReactNode } from "react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { useAuth } from "@/hooks/use-auth"
import type { Usuario } from "@/lib/types"

interface UserFilterContextType {
  selectedUser: string        // "todos" | string(user_id)
  setSelectedUser: (v: string) => void
  usuarios: Usuario[]
  selectedLabel: string       // "Todos" | "Nico" | "Daylyng"
}

const UserFilterContext = createContext<UserFilterContextType>({
  selectedUser: "self",
  setSelectedUser: () => {},
  usuarios: [],
  selectedLabel: "",
})

export function UserFilterProvider({ children }: { children: ReactNode }) {
  const { userId } = useAuth()
  const [selectedUser, setSelectedUser] = useState("self") // "self" = logueado por defecto

  const fetchUsuarios = useCallback(() => api.get<Usuario[]>("/api/usuarios"), [])
  const { data: usuarios } = usePolling(fetchUsuarios, 30000)

  // Resolver "self" al userId real. Si userId aún no cargó, mostrar todo temporalmente
  const effectiveUser = selectedUser === "self"
    ? (userId ? String(userId) : "todos")
    : selectedUser

  const selectedLabel = effectiveUser === "todos"
    ? "Hogar"
    : (usuarios ?? []).find(u => String(u.id) === effectiveUser)?.nombre ?? "Yo"

  return (
    <UserFilterContext.Provider value={{
      selectedUser: effectiveUser,
      setSelectedUser,
      usuarios: usuarios ?? [],
      selectedLabel,
    }}>
      {children}
    </UserFilterContext.Provider>
  )
}

export function useUserFilter() {
  return useContext(UserFilterContext)
}
