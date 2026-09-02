import { NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  const cookie = request.headers.get("cookie") || ""
  const search = request.nextUrl.search
  const res = await fetch(`${BACKEND}/admin/api/usuarios${search}`, {
    headers: { cookie },
  })
  if (res.status === 401) return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  return NextResponse.json(await res.json(), { status: res.status })
}

export async function POST(request: NextRequest) {
  const cookie = request.headers.get("cookie") || ""
  const body = await request.json()
  const res = await fetch(`${BACKEND}/admin/api/usuarios`, {
    method: "POST",
    headers: { cookie, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (res.status === 401) return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  return NextResponse.json(await res.json(), { status: res.status })
}
