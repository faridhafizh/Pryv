import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

export const runtime = "nodejs";
export const maxDuration = 300;

/** Proxy unduhan hasil anonimisasi. File hanya untuk pegawai yang login. */
export async function GET(_req: Request, { params }: { params: { jobId: string } }) {
  const supabase = createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ detail: "Sesi berakhir. Silakan masuk kembali." }, { status: 401 });
  }

  const backend = process.env.MPG_BACKEND_URL ?? "http://localhost:8000";
  const upstream = await fetch(`${backend}/api/anonymize/${params.jobId}/download`);

  if (!upstream.ok) {
    return NextResponse.json(
      { detail: "File tidak ditemukan atau sudah kedaluwarsa." },
      { status: upstream.status },
    );
  }

  return new NextResponse(upstream.body, {
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition":
        upstream.headers.get("content-disposition") ??
        `attachment; filename="anonymized_${params.jobId}.csv"`,
    },
  });
}
