import { NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  const cookie = request.headers.get("cookie") || ""
  const search = request.nextUrl.search
  const res = await fetch(`${BACKEND}/admin/api/proyeccion-cuotas${search}`, {
    headers: { cookie },
  })
  if (res.status === 401) return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  return NextResponse.json(await res.json(), { status: res.status })
}
