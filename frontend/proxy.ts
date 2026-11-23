import { NextResponse, type NextRequest } from "next/server";

/**
 * Forwards browser calls to /api/* on to the FastAPI backend, so the browser only ever talks to the
 * frontend's own site and the login cookies stay first-party.
 *
 * Active only when BACKEND_URL is set (production). Locally, without it, the browser calls the
 * backend directly through NEXT_PUBLIC_API_URL as before.
 *
 * Server-only settings (never exposed to the browser):
 *   BACKEND_URL          e.g. https://smartstudy-api.onrender.com
 *   PROXY_SHARED_SECRET  same value as the backend's PROXY_SHARED_SECRET
 */
export function proxy(request: NextRequest): NextResponse {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) return NextResponse.next();

  const headers = new Headers(request.headers);
  // Overwrite rather than append, so a browser cannot supply its own values for these.
  headers.set("x-proxy-secret", process.env.PROXY_SHARED_SECRET ?? "");
  headers.set("x-client-ip", clientIp(request));

  const target = new URL(request.nextUrl.pathname + request.nextUrl.search, backendUrl);
  return NextResponse.rewrite(target, { request: { headers } });
}

/** The visitor's address as reported by the hosting platform (Vercel sets x-forwarded-for itself). */
function clientIp(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return forwarded || request.headers.get("x-real-ip") || "unknown";
}

export const config = { matcher: "/api/:path*" };
