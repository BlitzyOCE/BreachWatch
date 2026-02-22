import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const code = searchParams.get("code");
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") ?? "signup";
  const redirectTo = searchParams.get("redirectTo") ?? "/";

  const supabase = await createServerClient();

  // PKCE flow (Google OAuth) — exchange code for session
  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(new URL(redirectTo, origin));
    }
    const url = new URL("/login", origin);
    url.searchParams.set("error", error.message);
    return NextResponse.redirect(url);
  }

  // Token hash flow (email confirmation, password reset)
  if (token_hash) {
    const { error } = await supabase.auth.verifyOtp({
      token_hash,
      type: type as "signup" | "email" | "recovery" | "invite",
    });
    if (!error) {
      if (type === "recovery") {
        return NextResponse.redirect(new URL("/reset-password", origin));
      }
      return NextResponse.redirect(new URL(redirectTo, origin));
    }
    const url = new URL("/login", origin);
    url.searchParams.set("error", error.message);
    return NextResponse.redirect(url);
  }

  return NextResponse.redirect(new URL("/login?error=no_code_or_token", origin));
}
