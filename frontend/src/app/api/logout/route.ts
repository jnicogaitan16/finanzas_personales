import { NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  const cookie = request.headers.get("cookie") || ""
  await fetch(`${BACKEND}/admin/logout`, { headers: { cookie }, redirect: "manual" }).catch(() => {})
  const response = NextResponse.json({ status: "ok" })
  response.cookies.delete("finanzas_session")
  return response
}
