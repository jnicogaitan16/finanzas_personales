"use client"
import { Plus } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"

export function Fab() {
  const pathname = usePathname()
  const router = useRouter()

  if (pathname === "/login") return null

  return (
    <button
      onClick={() => router.push("/movimientos?new=1")}
      className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-600 text-white shadow-lg shadow-violet-500/25 flex items-center justify-center hover:scale-105 active:scale-90 transition-all duration-200 lg:hidden animate-fade-in-up"
      aria-label="Agregar gasto"
    >
      <Plus className="w-6 h-6" strokeWidth={2.5} />
    </button>
  )
}
