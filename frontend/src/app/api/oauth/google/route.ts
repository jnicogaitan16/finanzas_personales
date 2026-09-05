import { NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000"

function getOrigin(request: NextRequest): string {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000"
  const proto = request.headers.get("x-forwarded-proto") || "http"
  return `${proto}://${host}`
}

export async function GET(request: NextRequest) {
  const res = await fetch(`${BACKEND}/admin/api/oauth/google/url`)
  if (!res.ok) {
    return NextResponse.redirect(new URL("/login?error=oauth", getOrigin(request)))
  }
  const data = await res.json()
  return NextResponse.redirect(data.url)
}
