"""Microdata Privacy Guard — Data Processing Engine (FastAPI).

Endpoints:
  GET  /health                              healthcheck
  POST /api/anonymize                       upload CSV -> statistik anonimisasi
  GET  /api/anonymize/{job_id}/download     unduh hasil (CSV teranonim)

Alur: file disimpan sementara di disk (per-chunk, tidak dimuat penuh ke
memori), diproses Pandas di threadpool, hasil disimpan per-job. Backend
stateless tanpa DB — riwayat job dicatat di frontend (Supabase + RLS).
# ponytail: hasil job di /tmp tidak pernah dibersihkan & verifikasi JWT
# Supabase ada di sisi proxy Next.js, bukan di sini. Tambahkan TTL sweep
# + verifikasi JWT (jwks) saat backend diekspos publik tanpa proxy.
"""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import anyio
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import get_settings
from app.services.anonymizer import AnonymizeConfig, anonymize
from app.services.pii_detector import detect_free_text_pii

app = FastAPI(title="Microdata Privacy Guard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_DIR = Path(tempfile.gettempdir()) / "mpg_jobs"
JOBS_DIR.mkdir(exist_ok=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": get_settings().app_name}


@app.post("/api/anonymize")
async def anonymize_endpoint(
    file: UploadFile = File(...),
    k: int = Form(get_settings().default_k),
    quasi_identifiers: str = Form(",".join(get_settings().default_quasi_identifiers)),
    extra_pii_columns: str = Form(""),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Hanya file CSV yang didukung.")
    if not 2 <= k <= 100:
        raise HTTPException(422, "k harus antara 2 dan 100.")

    job_id = uuid.uuid4().hex
    src = JOBS_DIR / f"{job_id}.csv"
    dst = JOBS_DIR / f"{job_id}_anonymized.csv"

    # Simpan ke disk per-chunk: file besar tidak boleh dimuat utuh ke memori.
    size = 0
    with src.open("wb") as fh:
        while chunk := await file.read(1 << 20):  # 1 MB per chunk
            size += len(chunk)
            if size > get_settings().max_upload_mb * 1024 * 1024:
                src.unlink(missing_ok=True)
                raise HTTPException(413, f"File melebihi {get_settings().max_upload_mb} MB.")
            fh.write(chunk)

    try:
        # Pandas jalan di threadpool agar event loop tidak terblokir.
        df = await anyio.to_thread.run_sync(pd.read_csv, src)
    except Exception as exc:
        src.unlink(missing_ok=True)
        raise HTTPException(422, f"Gagal membaca CSV: {exc}") from exc

    qid = [q.strip().lower() for q in quasi_identifiers.split(",") if q.strip()]
    extra = [c.strip().lower() for c in extra_pii_columns.split(",") if c.strip()]

    out_df, stats = await anyio.to_thread.run_sync(
        anonymize, df, AnonymizeConfig(k=k, quasi_identifiers=qid, pii_columns=extra)
    )
    await anyio.to_thread.run_sync(lambda: out_df.to_csv(dst, index=False))
    src.unlink(missing_ok=True)  # file asli dibuang setelah diproses

    # Hook NLP (Ollama): hanya aktif saat MPG_OLLAMA_ENABLED=true.
    # Menandai entitas PII pada kolom teks bebas yang lolos pipeline.
    pii_in_free_text: dict[str, int] = {}
    if get_settings().ollama_enabled:
        free_text = {
            col: out_df[col].dropna().astype(str).head(50).tolist()
            for col in out_df.columns if out_df[col].dtype == object
        }
        if free_text:
            found = await detect_free_text_pii(free_text)
            pii_in_free_text = {col: len(spans) for col, spans in found.items()}

    return {
        "job_id": job_id,
        "download_url": f"/api/anonymize/{job_id}/download",
        "stats": {
            "rows_in": stats.rows_in,
            "rows_out": stats.rows_out,
            "rows_dropped": stats.rows_dropped,
            "data_loss_pct": round(stats.rows_dropped / stats.rows_in * 100, 2) if stats.rows_in else 0.0,
            "columns_removed": stats.columns_removed,
            "columns_kept": stats.columns_kept,
            "k": stats.k,
            "quasi_identifiers": stats.quasi_identifiers,
            "groups_below_k": stats.groups_below_k,
            "pii_in_free_text": pii_in_free_text,
        },
    }


@app.get("/api/anonymize/{job_id}/download")
def download(job_id: str) -> FileResponse:
    dst = JOBS_DIR / f"{job_id}_anonymized.csv"
    if not dst.exists():
        raise HTTPException(404, "Hasil sudah kedaluwarsa atau tidak ada.")
    return FileResponse(dst, media_type="text/csv", filename=f"anonymized_{job_id}.csv")
