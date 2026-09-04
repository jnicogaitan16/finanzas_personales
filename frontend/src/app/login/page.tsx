"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"

export default function LoginPage() {
  const router = useRouter()
  const [mode, setMode] = useState<"login" | "register">("login")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState("")

  async function onLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError("")
    const fd = new FormData(e.currentTarget)
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: fd.get("username"), password: fd.get("password") }),
      })
      if (res.ok) { router.push("/"); router.refresh() }
      else setError("Usuario o contrasena incorrectos")
    } catch { setError("Error de conexion") }
    finally { setLoading(false) }
  }

  async function onRegister(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError("")
    setSuccess("")
    const fd = new FormData(e.currentTarget)
    const password = fd.get("password") as string
    if (password !== fd.get("confirm")) { setError("Las contrasenas no coinciden"); setLoading(false); return }
    try {
      const body: Record<string, string> = { nombre: fd.get("nombre") as string, password }
      const codigo = fd.get("codigo_invitacion") as string
      if (codigo) body.codigo_invitacion = codigo
      const res = await fetch("/api/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      const data = await res.json()
      if (res.ok) { setSuccess("Cuenta creada. Ahora inicia sesion."); setMode("login") }
      else setError(data.detail || "Error al registrar")
    } catch { setError("Error de conexion") }
    finally { setLoading(false) }
  }

  const inputClass = "w-full px-4 py-3.5 rounded-xl bg-[#0A0E1A] border border-white/10 text-gray-100 text-base placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500 transition-all"

  return (
    <div className="min-h-screen flex flex-col justify-end sm:justify-center px-6 pb-12 sm:pb-0 bg-[#0A0E1A]">
      <div className="w-full max-w-sm mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100">
            Finanzas <span className="text-violet-400">app</span>
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {mode === "login" ? "Ingresa tus credenciales" : "Crea tu cuenta"}
          </p>
        </div>

        {error && <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm px-4 py-3 rounded-xl mb-4">{error}</div>}
        {success && <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm px-4 py-3 rounded-xl mb-4">{success}</div>}

        {mode === "login" ? (
          <form onSubmit={onLogin} className="flex flex-col gap-5">
            <div>
              <label className="text-sm font-medium text-gray-400 block mb-1.5">Usuario</label>
              <input name="username" required autoFocus autoComplete="username" className={inputClass} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-400 block mb-1.5">Contrasena</label>
              <input name="password" type="password" required autoComplete="current-password" className={inputClass} />
            </div>
            <button type="submit" disabled={loading} className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium text-base hover:from-violet-500 hover:to-purple-500 active:scale-[0.98] transition-all disabled:opacity-50 mt-2 shadow-lg shadow-violet-500/20">
              {loading ? "Entrando..." : "Entrar"}
            </button>
            <p className="text-center text-sm text-gray-500">
              ¿No tienes cuenta?{" "}
              <button type="button" onClick={() => { setMode("register"); setError(""); setSuccess("") }} className="text-violet-400 font-medium">Registrate</button>
            </p>
          </form>
        ) : (
          <form onSubmit={onRegister} className="flex flex-col gap-4">
            <div>
              <label className="text-sm font-medium text-gray-400 block mb-1.5">Nombre</label>
              <input name="nombre" required autoFocus className={inputClass} placeholder="Tu nombre" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-400 block mb-1.5">Contrasena</label>
              <input name="password" type="password" required minLength={4} autoComplete="new-password" className={inputClass} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-400 block mb-1.5">Confirmar contrasena</label>
              <input name="confirm" type="password" required minLength={4} autoComplete="new-password" className={inputClass} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-400 block mb-1.5">Codigo de invitacion <span className="text-gray-600 font-normal">(opcional)</span></label>
              <input name="codigo_invitacion" className={`${inputClass} tracking-widest`} placeholder="ABC12XYZ" />
              <p className="text-xs text-gray-600 mt-1.5">Si alguien te invito a su hogar, ingresa el codigo aqui</p>
            </div>
            <button type="submit" disabled={loading} className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium text-base hover:from-violet-500 hover:to-purple-500 active:scale-[0.98] transition-all disabled:opacity-50 mt-1 shadow-lg shadow-violet-500/20">
              {loading ? "Creando cuenta..." : "Crear cuenta"}
            </button>
            <p className="text-center text-sm text-gray-500">
              ¿Ya tienes cuenta?{" "}
              <button type="button" onClick={() => { setMode("login"); setError(""); setSuccess("") }} className="text-violet-400 font-medium">Inicia sesion</button>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
