import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Toaster } from "@/components/ui/sonner"
import { HeaderWrapper } from "@/components/layout/header-wrapper"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Finanzas Personales",
  description: "Dashboard de finanzas personales",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <body className={`${inter.className} bg-background text-foreground min-h-screen`}>
        <HeaderWrapper />
        <main className="max-w-7xl mx-auto px-4 pt-16 pb-6">
          {children}
        </main>
        <Toaster />
      </body>
    </html>
  )
}
