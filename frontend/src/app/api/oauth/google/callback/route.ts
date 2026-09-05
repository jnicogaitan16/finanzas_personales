import { NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

function getOrigin(request: NextRequest): string {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000"
  const proto = request.headers.get("x-forwarded-proto") || "http"
  return `${proto}://${host}`
}

export async function GET(request: NextRequest) {
  const origin = getOrigin(request)
  const code = request.nextUrl.searchParams.get("code")
  const error = request.nextUrl.searchParams.get("error")

  // Google may return an error instead of a code
  if (error) {
    const loginUrl = new URL("/login", origin)
    loginUrl.searchParams.set("error", "oauth")
    loginUrl.searchParams.set("msg", `Google: ${error}`)
    return NextResponse.redirect(loginUrl)
  }

  if (!code) {
    return NextResponse.redirect(new URL("/login?error=oauth&msg=No+se+recibio+codigo", origin))
  }

  // Exchange code via backend
  try {
    const res = await fetch(`${BACKEND}/admin/api/oauth/google/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    })

    if (!res.ok) {
      let msg = "Error al autenticar"
      try {
        const data = await res.json()
        if (data.detail) msg = data.detail
      } catch { /* ignore */ }
      const loginUrl = new URL("/login", origin)
      loginUrl.searchParams.set("error", "oauth")
      loginUrl.searchParams.set("msg", msg)
      return NextResponse.redirect(loginUrl)
    }

    const data = await res.json()

    const response = NextResponse.redirect(new URL("/", origin))
    response.cookies.set("finanzas_session", data.token, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 86400,
    })
    return response
  } catch (e) {
    const loginUrl = new URL("/login", origin)
    loginUrl.searchParams.set("error", "oauth")
    loginUrl.searchParams.set("msg", `Fetch error: ${e instanceof Error ? e.message : String(e)}`)
    return NextResponse.redirect(loginUrl)
  }
}
