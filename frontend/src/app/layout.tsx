import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Toaster } from "@/components/ui/sonner"
import { AppShell } from "@/components/layout/app-shell"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Finanzas App",
  description: "Dashboard de finanzas personales",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Finanzas",
  },
}

export const viewport: Viewport = {
  themeColor: "#34d399",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <head>
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body className={`${inter.className} bg-background text-foreground min-h-screen`}>
        <AppShell>
          {children}
        </AppShell>
        <Toaster />
      </body>
    </html>
  )
}
