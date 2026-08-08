import UploadForm from "@/components/UploadForm";

export default function UploadPage() {
  return (
    <main className="min-h-screen px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <header className="mb-6">
          <a href="/dashboard" className="text-sm text-blue-600 hover:underline">
            ← Dashboard
          </a>
          <h1 className="mt-2 text-2xl font-semibold">Anonimisasi Dataset</h1>
          <p className="mt-1 text-sm text-slate-500">
            Kolom PII (NIK, nama, email, dll.) akan dihapus otomatis. Umur digeneralisasi
            menjadi rentang dan Pendapatan menjadi kuintil, lalu K-Anonymity dijamin
            pada kelompok quasi-identifier.
          </p>
        </header>
        <UploadForm />
      </div>
    </main>
  );
}
