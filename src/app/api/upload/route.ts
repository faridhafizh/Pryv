import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

export const runtime = "nodejs";
// Vercel: perpanjang batas waktu fungsi untuk file besar.
export const maxDuration = 300;

/**
 * Proxy upload ke FastAPI. Sesi Supabase diperiksa DI SINI (authorization),
 * lalu multipart diteruskan apa adanya. Backend tidak perlu memegang kunci
 * Supabase dan tidak perlu diekspos publik.
 */
export async function POST(request: Request) {
  const supabase = createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json(
      { detail: "Sesi berakhir. Silakan masuk kembali." },
      { status: 401 },
    );
  }

  const backend = process.env.MPG_BACKEND_URL ?? "http://localhost:8000";
  const upstream = await fetch(`${backend}/api/anonymize`, {
    method: "POST",
    body: await request.formData(),
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
