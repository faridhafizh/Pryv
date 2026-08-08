"use client";

import { useRef, useState, type DragEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

type JobStats = {
  rows_in: number;
  rows_out: number;
  rows_dropped: number;
  data_loss_pct: number;
  columns_removed: string[];
  columns_kept: string[];
  k: number;
  quasi_identifiers: string[];
};

type Status = "idle" | "loading" | "success" | "error";

const inputCls =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";

export default function UploadForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [k, setK] = useState(5);
  const [qid, setQid] = useState("umur,pendapatan,kabupaten_kota,jenis_kelamin");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<JobStats | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  function pickFile(f: File | undefined) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setError("Hanya file CSV yang didukung.");
      return;
    }
    setFile(f);
    setError(null);
    setStatus("idle");
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    pickFile(e.dataTransfer.files[0]);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Pilih file CSV terlebih dahulu.");
      return;
    }
    setStatus("loading");
    setError(null);

    const body = new FormData();
    body.append("file", file);
    body.append("k", String(k));
    body.append("quasi_identifiers", qid);

    try {
      // Proxy Next.js (/api/upload) yang memeriksa sesi Supabase,
      // lalu meneruskan multipart ke FastAPI.
      const res = await fetch("/api/upload", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Gagal memproses (HTTP ${res.status}).`);

      setStats(data.stats);
      setDownloadUrl(data.download_url);

      // Catat job ke Supabase. RLS memastikan baris hanya terlihat pemiliknya.
      const supabase = createClient();
      await supabase.from("anonymization_jobs").insert({
        original_filename: file.name,
        rows_in: data.stats.rows_in,
        rows_out: data.stats.rows_out,
        rows_dropped: data.stats.rows_dropped,
        k: data.stats.k,
        quasi_identifiers: data.stats.quasi_identifiers,
      });

      setStatus("success");
      router.refresh();
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Terjadi kesalahan tak terduga.");
    }
  }

  function reset() {
    setFile(null);
    setStats(null);
    setDownloadUrl(null);
    setError(null);
    setStatus("idle");
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      {/* Drop zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className="cursor-pointer rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center transition hover:border-blue-400"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
        <p className="text-sm font-medium text-slate-700">
          {file ? file.name : "Tarik file CSV ke sini, atau klik untuk memilih"}
        </p>
        {file && (
          <p className="mt-1 text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">K (K-Anonymity)</span>
          <input
            type="number"
            min={2}
            max={100}
            value={k}
            onChange={(e) => setK(Number(e.target.value))}
            className={inputCls}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">
            Quasi-identifier (pisahkan koma)
          </span>
          <input
            type="text"
            value={qid}
            onChange={(e) => setQid(e.target.value)}
            className={inputCls}
          />
        </label>
      </div>

      <button
        type="submit"
        disabled={status === "loading"}
        className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {status === "loading" ? "Memproses dataset…" : "Anonimkan Dataset"}
      </button>

      {status === "loading" && (
        <p className="text-center text-sm text-slate-500">
          Memproses… file besar bisa memakan waktu beberapa saat.
        </p>
      )}

      {status === "error" && error && (
        <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}

      {status === "success" && stats && (
        <div className="space-y-4 rounded-lg bg-green-50 p-4 text-sm text-green-800">
          <p className="font-semibold">Dataset berhasil dianonimkan.</p>
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <div>
              <dt className="text-green-600">Baris masuk</dt>
              <dd className="font-semibold">{stats.rows_in}</dd>
            </div>
            <div>
              <dt className="text-green-600">Baris keluar</dt>
              <dd className="font-semibold">{stats.rows_out}</dd>
            </div>
            <div>
              <dt className="text-green-600">Data hilang</dt>
              <dd className="font-semibold">{stats.data_loss_pct}%</dd>
            </div>
            <div>
              <dt className="text-green-600">Kolom dihapus</dt>
              <dd className="font-semibold">{stats.columns_removed.join(", ") || "—"}</dd>
            </div>
            <div>
              <dt className="text-green-600">K</dt>
              <dd className="font-semibold">{stats.k}</dd>
            </div>
            <div>
              <dt className="text-green-600">Quasi-id</dt>
              <dd className="font-semibold">{stats.quasi_identifiers.join(", ") || "—"}</dd>
            </div>
          </dl>
          {downloadUrl && (
            <a
              href={downloadUrl}
              className="inline-block rounded-lg bg-green-700 px-4 py-2 font-semibold text-white transition hover:bg-green-800"
            >
              Unduh CSV teranonim
            </a>
          )}
          <button type="button" onClick={reset} className="ml-2 text-sm underline">
            Upload dataset lain
          </button>
        </div>
      )}
    </form>
  );
}
