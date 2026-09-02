"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, ArrowLeftRight, Tag, Users, LogOut, Menu, X, CreditCard, PieChart } from "lucide-react"
import { useState, useEffect, useRef } from "react"

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/movimientos", label: "Movimientos", icon: ArrowLeftRight },
  { href: "/compartido", label: "Compartido", icon: Users },
  { href: "/cuotas", label: "Cuotas", icon: CreditCard },
  { href: "/presupuestos", label: "Presupuestos", icon: PieChart },
  { href: "/categorias", label: "Categorias", icon: Tag },
]

export function Header() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [visible, setVisible] = useState(true)
  const lastScroll = useRef(0)

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY
      setVisible(y < 50 || y < lastScroll.current)
      lastScroll.current = y
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  const handleLogout = async () => {
    await fetch("/api/logout")
    window.location.href = "/login"
  }

  return (
    <header className={`border-b border-border bg-card/95 backdrop-blur-sm fixed top-0 left-0 right-0 z-50 transition-transform duration-300 ${visible ? "translate-y-0" : "-translate-y-full"}`}>
      <div className="max-w-7xl mx-auto px-4 h-12 flex items-center justify-between">
        <Link href="/" className="text-base font-bold shrink-0">
          Finanzas <span className="text-primary">app</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-0.5">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm transition-colors ${
                pathname === href
                  ? "bg-primary text-primary-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </Link>
          ))}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm text-muted-foreground hover:text-destructive hover:bg-secondary ml-1"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </nav>

        {/* Mobile hamburger */}
        <button className="md:hidden p-1.5 -mr-1.5" onClick={() => setOpen(!open)}>
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <nav className="md:hidden border-t border-border bg-card px-4 pb-3 pt-1">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm ${
                pathname === href
                  ? "bg-primary text-primary-foreground font-medium"
                  : "text-muted-foreground"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:text-destructive w-full"
          >
            <LogOut className="w-4 h-4" />
            Salir
          </button>
        </nav>
      )}
    </header>
  )
}
