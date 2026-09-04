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
        body: JSON.stringify({
          username: fd.get("username"),
          password: fd.get("password"),
        }),
      })
      if (res.ok) {
        router.push("/")
        router.refresh()
      } else {
        setError("Usuario o contrasena incorrectos")
      }
    } catch {
      setError("Error de conexion")
    } finally {
      setLoading(false)
    }
  }

  async function onRegister(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError("")
    setSuccess("")
    const fd = new FormData(e.currentTarget)
    const password = fd.get("password") as string
    const confirm = fd.get("confirm") as string

    if (password !== confirm) {
      setError("Las contrasenas no coinciden")
      setLoading(false)
      return
    }

    try {
      const body: Record<string, string> = {
        nombre: fd.get("nombre") as string,
        password,
      }
      const codigo = fd.get("codigo_invitacion") as string
      if (codigo) body.codigo_invitacion = codigo

      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (res.ok) {
        setSuccess("Cuenta creada. Ahora inicia sesion.")
        setMode("login")
      } else {
        setError(data.detail || "Error al registrar")
      }
    } catch {
      setError("Error de conexion")
    } finally {
      setLoading(false)
    }
  }

  const inputClass = "w-full px-4 py-3 rounded-xl border border-gray-300 bg-white text-gray-900 text-base placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 transition-colors"

  return (
    <div className="min-h-screen flex flex-col justify-end sm:justify-center px-6 pb-12 sm:pb-0 bg-white">
      <div className="w-full max-w-sm mx-auto">
        {/* Logo */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Finanzas <span className="text-emerald-500">app</span>
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {mode === "login" ? "Ingresa tus credenciales" : "Crea tu cuenta"}
          </p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl mb-4">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-emerald-50 text-emerald-600 text-sm px-4 py-3 rounded-xl mb-4">
            {success}
          </div>
        )}

        {mode === "login" ? (
          <form onSubmit={onLogin} className="flex flex-col gap-5">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">Usuario</label>
              <input name="username" required autoFocus autoComplete="username" className={inputClass} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">Contrasena</label>
              <input name="password" type="password" required autoComplete="current-password" className={inputClass} />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-gray-900 text-white font-medium text-base hover:bg-gray-800 active:scale-[0.98] transition-all disabled:opacity-50 mt-2"
            >
              {loading ? "Entrando..." : "Entrar"}
            </button>
            <p className="text-center text-sm text-gray-500">
              ¿No tienes cuenta?{" "}
              <button type="button" onClick={() => { setMode("register"); setError(""); setSuccess("") }} className="text-emerald-600 font-medium">
                Registrate
              </button>
            </p>
          </form>
        ) : (
          <form onSubmit={onRegister} className="flex flex-col gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">Nombre</label>
              <input name="nombre" required autoFocus className={inputClass} placeholder="Tu nombre" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">Contrasena</label>
              <input name="password" type="password" required minLength={4} autoComplete="new-password" className={inputClass} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">Confirmar contrasena</label>
              <input name="confirm" type="password" required minLength={4} autoComplete="new-password" className={inputClass} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">
                Codigo de invitacion <span className="text-gray-400 font-normal">(opcional)</span>
              </label>
              <input name="codigo_invitacion" className={`${inputClass} tracking-widest`} placeholder="ABC12XYZ" />
              <p className="text-xs text-gray-400 mt-1.5">Si alguien te invito a su hogar, ingresa el codigo aqui</p>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-gray-900 text-white font-medium text-base hover:bg-gray-800 active:scale-[0.98] transition-all disabled:opacity-50 mt-1"
            >
              {loading ? "Creando cuenta..." : "Crear cuenta"}
            </button>
            <p className="text-center text-sm text-gray-500">
              ¿Ya tienes cuenta?{" "}
              <button type="button" onClick={() => { setMode("login"); setError(""); setSuccess("") }} className="text-emerald-600 font-medium">
                Inicia sesion
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
