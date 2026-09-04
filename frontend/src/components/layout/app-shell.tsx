"use client"
import { usePathname } from "next/navigation"
import { useState } from "react"
import { Sidebar } from "./sidebar"
import { Topbar } from "./topbar"
import { Fab } from "./fab"

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Login page: no shell
  if (pathname === "/login") {
    return <>{children}</>
  }

  return (
    <div className="min-h-screen flex bg-[hsl(228,14%,7%)] text-gray-100">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 px-4 py-6 lg:px-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>

      <Fab />
    </div>
  )
}
