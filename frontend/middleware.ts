import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // Auth-ready stub: currently passes through all requests.
  // When auth is implemented, add checks here:
  //
  // const session = await getSession(request);
  // if (!session && isProtectedRoute(request.nextUrl.pathname)) {
  //   return NextResponse.redirect(new URL("/login", request.url));
  // }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all routes except static files and API routes
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
