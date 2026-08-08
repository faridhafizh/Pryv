"""Deteksi PII pada kolom teks bebas via NLP lokal (Ollama).

Struktur sudah siap: pipeline memanggil detect_free_text_pii() hanya saat
MPG_OLLAMA_ENABLED=true (lihat app/main.py). Fungsi ini fungsional terhadap
/ollama /api/generate dan memakai format JSON untuk output yang terstruktur.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.config import get_settings

# ponytail: chunking/batching per nilai & pemangkasan teks; upgrade saat
# volume kolom teks bebas benar-benar besar.


@dataclass
class PiiSpan:
    start: int
    end: int
    entity: str  # PER | LOC | EMAIL | PHONE | NIK | OTHER
    text: str


PROMPT = """Tandai entitas PII (nama orang, lokasi, email, telepon, NIK) pada teks di bawah.
Balas HANYA JSON array, tanpa teks lain:
[{"start": int, "end": int, "entity": "PER|LOC|EMAIL|PHONE|NIK|OTHER", "text": str}]
Jika tidak ada entitas, balas [].

Teks: {text}"""


async def detect_free_text_pii(text_columns: dict[str, list[str]]) -> dict[str, list[PiiSpan]]:
    """Deteksi entitas PII per kolom teks bebas. Kembalikan dict kosong jika off."""
    s = get_settings()
    if not s.ollama_enabled:
        return {col: [] for col in text_columns}

    async with httpx.AsyncClient(base_url=s.ollama_url, timeout=300) as client:
        results: dict[str, list[PiiSpan]] = {}
        for col, values in text_columns.items():
            spans: list[PiiSpan] = []
            for text in values:
                resp = await client.post("/api/generate", json={
                    "model": s.ollama_model,
                    "prompt": PROMPT.format(text=str(text)[:4000]),
                    "stream": False,
                    "format": "json",
                })
                resp.raise_for_status()
                try:
                    items = json.loads(resp.json()["response"])
                except (json.JSONDecodeError, KeyError):
                    items = []
                for item in items:
                    spans.append(PiiSpan(
                        start=int(item.get("start", 0)),
                        end=int(item.get("end", 0)),
                        entity=str(item.get("entity", "OTHER")),
                        text=str(item.get("text", "")),
                    ))
            results[col] = spans
        return results
