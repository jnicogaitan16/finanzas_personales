import { NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const cookie = request.headers.get("cookie") || ""
  const body = await request.json()
  const res = await fetch(`${BACKEND}/admin/api/usuarios/${id}`, {
    method: "PATCH",
    headers: { cookie, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (res.status === 401) return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  return NextResponse.json(await res.json(), { status: res.status })
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const cookie = request.headers.get("cookie") || ""
  const res = await fetch(`${BACKEND}/admin/api/usuarios/${id}`, {
    method: "DELETE",
    headers: { cookie },
  })
  if (res.status === 401) return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  return NextResponse.json(await res.json(), { status: res.status })
}
