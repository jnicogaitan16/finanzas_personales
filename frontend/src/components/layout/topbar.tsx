"use client"
import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { User, Settings, Tag, PieChart, Wallet, LogOut, ChevronLeft, ChevronDown, Users } from "lucide-react"
import { useAuth } from "@/hooks/use-auth"
import { useUserFilter } from "@/hooks/use-user-filter"

const menuItems = [
  { href: "/cuenta", label: "Mi cuenta", icon: Settings },
  { href: "/categorias", label: "Categorias", icon: Tag },
  { href: "/presupuestos", label: "Presupuestos", icon: PieChart },
  { href: "/gastos-fijos", label: "Gastos fijos", icon: Wallet },
]

export function Topbar() {
  const pathname = usePathname()
  const { user } = useAuth()
  const { selectedUser, setSelectedUser, usuarios, selectedLabel } = useUserFilter()
  const [menuOpen, setMenuOpen] = useState(false)
  const [filterOpen, setFilterOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const filterRef = useRef<HTMLDivElement>(null)
  const isHome = pathname === "/"
  const hasGroup = usuarios.length > 1

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) setFilterOpen(false)
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await fetch("/api/logout")
    window.location.href = "/login"
  }

  return (
    <header className="h-14 border-b border-white/5 bg-[#0D1122]/80 backdrop-blur-md flex items-center justify-between px-4 sticky top-0 z-30">
      {/* Left: back or logo */}
      <div className="flex items-center gap-1.5">
        {!isHome && (
          <Link href="/" className="p-1.5 -ml-1.5 rounded-xl hover:bg-white/5 text-gray-400">
            <ChevronLeft className="w-5 h-5" />
          </Link>
        )}
        <Link href="/" className="text-base font-bold text-gray-100">
          Finanzas <span className="text-violet-400">app</span>
        </Link>
      </div>

      {/* Center: user filter chip */}
      <div className="flex items-center gap-2">
        {hasGroup && (
          <div className="relative" ref={filterRef}>
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm text-gray-300 hover:bg-white/10 transition-colors"
            >
              <Users className="w-3.5 h-3.5 text-violet-400" />
              <span className="max-w-[80px] truncate">{selectedLabel}</span>
              <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
            </button>

            {filterOpen && (
              <div className="absolute right-0 top-10 w-44 bg-[#141832] border border-white/10 rounded-xl shadow-xl shadow-black/30 py-1 animate-fade-in z-50">
                {[
                  { value: "todos", label: "Hogar" },
                  ...usuarios.map(u => ({ value: String(u.id), label: u.nombre })),
                ].map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => { setSelectedUser(opt.value); setFilterOpen(false) }}
                    className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm transition-colors ${
                      selectedUser === opt.value
                        ? "text-violet-400 bg-violet-500/10"
                        : "text-gray-400 hover:text-gray-100 hover:bg-white/5"
                    }`}
                  >
                    {selectedUser === opt.value && (
                      <div className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                    )}
                    <span className={selectedUser === opt.value ? "" : "ml-3.5"}>{opt.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Right: avatar menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="w-9 h-9 rounded-full bg-violet-500/20 flex items-center justify-center text-violet-400 hover:bg-violet-500/30 transition-colors"
          >
            {user ? <span className="text-sm font-bold">{user.nombre[0]}</span> : <User className="w-4 h-4" />}
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-12 w-56 bg-[#141832] border border-white/10 rounded-2xl shadow-xl shadow-black/30 py-2 animate-fade-in z-50">
              {user && (
                <div className="px-4 py-2.5 border-b border-white/5">
                  <p className="text-sm font-medium text-gray-100">{user.nombre}</p>
                  <p className="text-xs text-gray-500">Conectado</p>
                </div>
              )}
              {menuItems.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                    pathname === href ? "text-violet-400 bg-violet-500/10" : "text-gray-400 hover:text-gray-100 hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              ))}
              <div className="border-t border-white/5 mt-1 pt-1">
                <button onClick={handleLogout} className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-400 hover:text-rose-400 hover:bg-rose-400/10 w-full transition-colors">
                  <LogOut className="w-4 h-4" />
                  Cerrar sesion
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
