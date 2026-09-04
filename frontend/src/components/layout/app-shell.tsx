"use client"
import { usePathname } from "next/navigation"
import { Topbar } from "./topbar"
import { Fab } from "./fab"
import { UserFilterProvider } from "@/hooks/use-user-filter"

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  if (pathname === "/login") {
    return <>{children}</>
  }

  return (
    <UserFilterProvider>
      <div className="min-h-screen flex flex-col bg-[#0A0E1A] text-gray-100">
        <Topbar />
        <main className="flex-1 px-4 py-5 max-w-lg w-full mx-auto">
          {children}
        </main>
        <Fab />
      </div>
    </UserFilterProvider>
  )
}
