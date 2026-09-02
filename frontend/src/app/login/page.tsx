"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError("")
    const fd = new FormData(e.currentTarget)
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: fd.get("username"),
          password: fd.get("password"),
          totp_code: fd.get("totp_code") || undefined,
        }),
      })
      if (res.ok) {
        router.push("/")
        router.refresh()
      } else {
        setError("Usuario, contrasena o codigo 2FA incorrectos")
      }
    } catch {
      setError("Error de conexion")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="bg-card rounded-2xl p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold mb-1">
          Finanzas <span className="text-primary">app</span>
        </h1>
        <p className="text-muted-foreground text-sm mb-6">Ingresa tus credenciales</p>
        {error && <p className="text-destructive text-sm mb-4">{error}</p>}
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <label className="text-sm text-muted-foreground">
            Usuario
            <Input name="username" required autoFocus className="mt-1" />
          </label>
          <label className="text-sm text-muted-foreground">
            Contrasena
            <Input name="password" type="password" required className="mt-1" />
          </label>
          <label className="text-sm text-muted-foreground">
            Codigo 2FA
            <Input name="totp_code" inputMode="numeric" maxLength={6} placeholder="000000" className="mt-1" />
            <span className="text-xs text-muted-foreground">Abre tu app de autenticacion</span>
          </label>
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Entrando..." : "Entrar"}
          </Button>
        </form>
      </div>
    </div>
  )
}
