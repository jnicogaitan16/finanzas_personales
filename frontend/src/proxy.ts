import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  if (pathname === "/login" || pathname.startsWith("/api/") || pathname.startsWith("/_next/")) {
    return NextResponse.next()
  }
  const session = request.cookies.get("finanzas_session")
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
