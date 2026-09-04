import { NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const form = new URLSearchParams()
  form.set("username", body.username)
  form.set("password", body.password)

  const res = await fetch(`${BACKEND}/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
    redirect: "manual",
  })

  const setCookie = res.headers.get("set-cookie")
  if ((res.status === 302 || res.status === 200) && setCookie) {
    const response = NextResponse.json({ status: "ok" })
    const match = setCookie.match(/finanzas_session=([^;]+)/)
    if (match) {
      response.cookies.set("finanzas_session", match[1], {
        httpOnly: true,
        sameSite: "strict",
        path: "/",
        maxAge: 86400,
      })
    }
    return response
  }
  return NextResponse.json({ error: "Usuario o contrasena incorrectos" }, { status: 401 })
}
