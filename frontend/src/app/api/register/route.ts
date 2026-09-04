import { NextRequest, NextResponse } from "next/server"
const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"
export async function POST(request: NextRequest) {
  const body = await request.json()
  const res = await fetch(`${BACKEND}/admin/api/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return NextResponse.json(await res.json(), { status: res.status })
}
