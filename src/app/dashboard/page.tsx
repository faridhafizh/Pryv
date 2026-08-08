import Link from "next/link";
import { redirect } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase/server";

export default async function DashboardPage() {
  const supabase = createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // RLS: hanya job milik user ini yang kembali.
  const { data: jobs } = await supabase
    .from("anonymization_jobs")
    .select("id, original_filename, rows_in, rows_out, rows_dropped, k, created_at")
    .order("created_at", { ascending: false })
    .limit(10);

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-slate-500">{user.email}</p>
        </div>
        <form action="/auth/signout" method="post">
          <button className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50">
            Keluar
          </button>
        </form>
      </header>

      <Link
        href="/upload"
        className="inline-block rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
      >
        Upload dataset baru
      </Link>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold">Riwayat anonimisasi</h2>
        {jobs && jobs.length > 0 ? (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">File</th>
                  <th className="px-4 py-3">Baris masuk</th>
                  <th className="px-4 py-3">Baris keluar</th>
                  <th className="px-4 py-3">K</th>
                  <th className="px-4 py-3">Waktu</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td className="px-4 py-3">{j.original_filename}</td>
                    <td className="px-4 py-3">{j.rows_in}</td>
                    <td className="px-4 py-3">{j.rows_out}</td>
                    <td className="px-4 py-3">{j.k}</td>
                    <td className="px-4 py-3 text-slate-500">
                      {new Date(j.created_at).toLocaleString("id-ID")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            Belum ada riwayat. Upload dataset pertama Anda.
          </p>
        )}
      </section>
    </main>
  );
}
