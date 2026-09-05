import { NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET() {
  const res = await fetch(`${BACKEND}/admin/api/auth-config`)
  return NextResponse.json(await res.json(), { status: res.status })
}
