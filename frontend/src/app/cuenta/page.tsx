"use client"

import { useState, useCallback } from "react"
import { toast } from "sonner"
import { User, Users, Key, Copy, Link, Shield } from "lucide-react"
import { api } from "@/lib/api-client"
import { usePolling } from "@/hooks/use-polling"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface MeData {
  id: number
  nombre: string
  grupo: { id: number; nombre: string } | null
  miembros: { id: number; nombre: string }[]
  codigo_invitacion_activo: string | null
  max_miembros: number
}

export default function CuentaPage() {
  const fetchMe = useCallback(() => api.get<MeData>("/api/me"), [])
  const { data: me, refetch } = usePolling(fetchMe, 5000)

  // Password
  const [passActual, setPassActual] = useState("")
  const [passNueva, setPassNueva] = useState("")
  const [passConfirm, setPassConfirm] = useState("")
  const [savingPass, setSavingPass] = useState(false)

  // Grupo
  const [codigoUnirse, setCodigoUnirse] = useState("")
  const [generando, setGenerando] = useState(false)
  const [uniendose, setUniendose] = useState(false)

  async function handleCambiarPassword(e: React.FormEvent) {
    e.preventDefault()
    if (passNueva !== passConfirm) {
      toast.error("Las contrasenas no coinciden")
      return
    }
    setSavingPass(true)
    try {
      await api.post("/api/cambiar-password", {
        password_actual: passActual,
        password_nueva: passNueva,
      })
      toast.success("Contrasena actualizada")
      setPassActual("")
      setPassNueva("")
      setPassConfirm("")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    } finally {
      setSavingPass(false)
    }
  }

  async function handleGenerarCodigo() {
    setGenerando(true)
    try {
      const res = await api.post<{ codigo: string }>("/api/grupo", {})
      try {
        const ta = document.createElement("textarea")
        ta.value = res.codigo
        ta.style.position = "fixed"
        ta.style.opacity = "0"
        document.body.appendChild(ta)
        ta.select()
        document.execCommand("copy")
        document.body.removeChild(ta)
        toast.success(`Codigo copiado: ${res.codigo}`)
      } catch {
        toast.success(`Codigo: ${res.codigo}`)
      }
      refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    } finally {
      setGenerando(false)
    }
  }

  function handleCopiarCodigo() {
    const texto = me?.codigo_invitacion_activo
    if (!texto) return
    // Fallback para HTTP (no seguro) donde navigator.clipboard no funciona
    try {
      const ta = document.createElement("textarea")
      ta.value = texto
      ta.style.position = "fixed"
      ta.style.opacity = "0"
      document.body.appendChild(ta)
      ta.select()
      document.execCommand("copy")
      document.body.removeChild(ta)
      toast.success("Codigo copiado")
    } catch {
      // Si falla, al menos mostrar el código
      toast.info(`Codigo: ${texto}`)
    }
  }

  async function handleUnirse(e: React.FormEvent) {
    e.preventDefault()
    setUniendose(true)
    try {
      await api.post("/api/grupo/unirse", { codigo_invitacion: codigoUnirse })
      toast.success("Te uniste al grupo familiar")
      setCodigoUnirse("")
      refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error")
    } finally {
      setUniendose(false)
    }
  }

  if (!me) return null

  const grupoLleno = (me.miembros?.length ?? 0) >= me.max_miembros
  const estaSolo = (me.miembros?.length ?? 0) <= 1

  return (
    <div className="space-y-6 animate-fade-in max-w-lg">
      <h1 className="text-2xl font-bold text-gray-100">Mi cuenta</h1>

      {/* ── Perfil ── */}
      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 flex items-center justify-center">
            <User className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-100">{me.nombre}</p>
            <p className="text-xs text-gray-500">ID: {me.id}</p>
          </div>
        </div>
      </div>

      {/* ── Grupo familiar ── */}
      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-4 h-4 text-gray-400" />
          <h2 className="text-sm text-gray-400 uppercase tracking-wide">Grupo familiar</h2>
        </div>

        {me.grupo && (
          <div className="mb-4">
            <p className="text-sm font-medium text-gray-200 mb-2">{me.grupo.nombre}</p>
            <div className="space-y-1.5">
              {me.miembros.map(m => (
                <div key={m.id} className="flex items-center gap-2 text-sm">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center text-xs font-bold text-emerald-400">
                    {m.nombre[0]}
                  </div>
                  <span className={`${m.id === me.id ? "text-gray-100" : "text-gray-400"}`}>
                    {m.nombre} {m.id === me.id && "(tu)"}
                  </span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">{me.miembros.length}/{me.max_miembros} miembros</p>
          </div>
        )}

        {/* Generar código de invitación */}
        {me.grupo && !grupoLleno && (
          <div className="border-t border-white/5 pt-4">
            <p className="text-xs text-gray-400 mb-2">Invita a alguien a tu hogar</p>
            {me.codigo_invitacion_activo ? (
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-white/5 rounded-xl px-4 py-3 font-mono text-lg tracking-[0.3em] text-emerald-400 text-center">
                  {me.codigo_invitacion_activo}
                </div>
                <Button onClick={handleCopiarCodigo} size="icon" variant="ghost">
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            ) : (
              <Button onClick={handleGenerarCodigo} disabled={generando} variant="outline" className="w-full">
                <Link className="w-4 h-4 mr-2" />
                {generando ? "Generando..." : "Generar codigo de invitacion"}
              </Button>
            )}
            <p className="text-[11px] text-gray-500 mt-2">El codigo expira en 24 horas y es de un solo uso</p>
          </div>
        )}

        {grupoLleno && (
          <p className="text-xs text-amber-400 bg-amber-500/10 rounded-xl px-3 py-2">
            Grupo completo ({me.max_miembros}/{me.max_miembros} miembros)
          </p>
        )}

        {/* Unirse a grupo (si está solo) */}
        {estaSolo && (
          <div className="border-t border-white/5 pt-4 mt-4">
            <p className="text-xs text-gray-400 mb-2">¿Tienes un codigo de invitacion?</p>
            <form onSubmit={handleUnirse} className="flex gap-2">
              <Input
                value={codigoUnirse}
                onChange={e => setCodigoUnirse(e.target.value)}
                placeholder="ABC12XYZ"
                className="tracking-widest text-center"
                required
              />
              <Button type="submit" disabled={uniendose} size="sm">
                {uniendose ? "..." : "Unirse"}
              </Button>
            </form>
          </div>
        )}
      </div>

      {/* ── Cambiar contraseña ── */}
      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-gray-400" />
          <h2 className="text-sm text-gray-400 uppercase tracking-wide">Seguridad</h2>
        </div>

        <form onSubmit={handleCambiarPassword} className="space-y-3">
          <label className="text-sm text-gray-300 block">
            Contrasena actual
            <Input type="password" value={passActual} onChange={e => setPassActual(e.target.value)} required className="mt-1" />
          </label>
          <label className="text-sm text-gray-300 block">
            Nueva contrasena
            <Input type="password" value={passNueva} onChange={e => setPassNueva(e.target.value)} required minLength={4} className="mt-1" />
          </label>
          <label className="text-sm text-gray-300 block">
            Confirmar nueva contrasena
            <Input type="password" value={passConfirm} onChange={e => setPassConfirm(e.target.value)} required minLength={4} className="mt-1" />
          </label>
          <Button type="submit" disabled={savingPass} variant="outline" className="w-full">
            <Key className="w-4 h-4 mr-2" />
            {savingPass ? "Guardando..." : "Cambiar contrasena"}
          </Button>
        </form>
      </div>
    </div>
  )
}
