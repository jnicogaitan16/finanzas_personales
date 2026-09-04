"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  ArrowLeftRight,
  Users,
  CreditCard,
  PieChart,
  Tag,
  LogOut,
  X,
  Wallet,
  Settings,
} from "lucide-react"

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/movimientos", label: "Movimientos", icon: ArrowLeftRight },
  { href: "/compartido", label: "Compartido", icon: Users },
  { href: "/tarjetas", label: "Tarjetas", icon: CreditCard },
  { href: "/presupuestos", label: "Presupuestos", icon: PieChart },
  { href: "/gastos-fijos", label: "Gastos fijos", icon: Wallet },
  { href: "/categorias", label: "Categorias", icon: Tag },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const pathname = usePathname()

  const handleLogout = async () => {
    await fetch("/api/logout")
    window.location.href = "/login"
  }

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed top-0 left-0 bottom-0 z-50 w-72
          bg-[hsl(228,14%,10%)] border-r border-white/10
          flex flex-col
          transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto lg:w-60
          ${open ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Header */}
        <div className="h-16 flex items-center justify-between px-6 shrink-0">
          <Link href="/" className="text-lg font-bold text-gray-100" onClick={onClose}>
            Finanzas <span className="text-emerald-400">app</span>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 rounded-lg hover:bg-white/10 text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl text-[15px] font-medium transition-all
                  ${active
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "text-gray-400 hover:text-gray-100 hover:bg-white/5"
                  }
                `}
              >
                <Icon className={`w-5 h-5 shrink-0 ${active ? "text-emerald-400" : ""}`} />
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Account + Logout */}
        <div className="px-3 pb-5 pt-3 border-t border-white/10 space-y-0.5">
          <Link
            href="/cuenta"
            onClick={onClose}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-[15px] font-medium transition-all ${
              pathname === "/cuenta"
                ? "bg-emerald-500/15 text-emerald-400"
                : "text-gray-400 hover:text-gray-100 hover:bg-white/5"
            }`}
          >
            <Settings className="w-5 h-5 shrink-0" />
            Mi cuenta
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-[15px] font-medium text-gray-400 hover:text-rose-400 hover:bg-rose-400/10 w-full transition-colors"
          >
            <LogOut className="w-5 h-5 shrink-0" />
            Salir
          </button>
        </div>
      </aside>
    </>
  )
}
