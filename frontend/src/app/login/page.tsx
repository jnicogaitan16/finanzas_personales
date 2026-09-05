"use client"
import { useState, useEffect, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"

interface AuthConfig {
  registro_abierto: boolean
  google_enabled: boolean
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const codigoUrl = searchParams.get("codigo")
  const oauthError = searchParams.get("error") === "oauth"
  const oauthMsg = searchParams.get("msg")

  const [mode, setMode] = useState<"login" | "register">(codigoUrl ? "register" : "login")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState("")
  const [config, setConfig] = useState<AuthConfig | null>(null)

  useEffect(() => {
    fetch("/api/auth-config")
      .then(r => r.json())
      .then(setConfig)
      .catch(() => setConfig({ registro_abierto: false, google_enabled: false }))
  }, [])

  const canRegister = config?.registro_abierto || !!codigoUrl

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
      const codigo = (fd.get("codigo_invitacion") as string) || codigoUrl || ""
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
      {oauthError && !error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm px-4 py-3 rounded-xl mb-4">
          {oauthMsg || "Error al iniciar sesion con Google"}
        </div>
      )}
      {success && <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm px-4 py-3 rounded-xl mb-4">{success}</div>}

      {/* Google OAuth button */}
      {mode === "login" && config?.google_enabled && (
        <div className="mb-5">
          <a
            href="/api/oauth/google"
            className="w-full py-3.5 rounded-xl bg-white text-gray-800 font-medium text-base hover:bg-gray-100 active:scale-[0.98] transition-all flex items-center justify-center gap-3 shadow-lg"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Continuar con Google
          </a>

          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-xs text-gray-500 uppercase">o</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>
        </div>
      )}

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
          {canRegister && (
            <p className="text-center text-sm text-gray-500">
              ¿No tienes cuenta?{" "}
              <button type="button" onClick={() => { setMode("register"); setError(""); setSuccess("") }} className="text-violet-400 font-medium">Registrate</button>
            </p>
          )}
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
          {!codigoUrl && (
            <div>
              <label className="text-sm font-medium text-gray-400 block mb-1.5">Codigo de invitacion</label>
              <input name="codigo_invitacion" required className={`${inputClass} tracking-widest`} placeholder="ABC12XYZ" />
              <p className="text-xs text-gray-600 mt-1.5">Necesitas un codigo de invitacion para crear tu cuenta</p>
            </div>
          )}
          {codigoUrl && <input type="hidden" name="codigo_invitacion" value={codigoUrl} />}
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
  )
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col justify-end sm:justify-center px-6 pb-12 sm:pb-0 bg-[#0A0E1A]">
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  )
}
