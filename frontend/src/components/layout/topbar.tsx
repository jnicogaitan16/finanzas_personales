"use client"
import { Menu } from "lucide-react"

interface TopbarProps {
  onMenuClick: () => void
}

export function Topbar({ onMenuClick }: TopbarProps) {
  return (
    <header className="h-14 border-b border-white/10 bg-[hsl(228,14%,9%)] flex items-center px-4 lg:px-6 sticky top-0 z-30">
      <button
        onClick={onMenuClick}
        className="lg:hidden p-2 -ml-2 rounded-xl hover:bg-white/10 text-gray-400 mr-3"
      >
        <Menu className="w-5 h-5" />
      </button>
      <div className="lg:hidden text-base font-bold text-gray-100">
        Finanzas <span className="text-emerald-400">app</span>
      </div>
    </header>
  )
}
