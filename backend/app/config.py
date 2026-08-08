"""Konfigurasi backend. Semua nilai bisa dioverride lewat env dengan prefix MPG_.

Contoh .env: lihat backend/.env.example
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MPG_", extra="ignore")

    app_name: str = "Microdata Privacy Guard API"
    max_upload_mb: int = 2048

    # Default parameter anonimisasi (bisa dioverride per-request).
    default_k: int = 5
    default_quasi_identifiers: list[str] = ["umur", "pendapatan", "kabupaten_kota", "jenis_kelamin"]

    # Kolom PII yang selalu di-suppress. Deteksi otomatis (pola nama + isi NIK/email)
    # menangkap kolom lain yang tidak tercantum di sini.
    pii_columns: list[str] = [
        "nik", "no_ktp", "nama", "nama_lengkap", "email", "no_hp",
        "telepon", "telp", "alamat", "ip_address", "npwp",
    ]

    # Origin frontend yang diizinkan (format JSON array di .env).
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "https://microdata-privacy-guard.vercel.app",
    ]

    # --- NLP lokal (Ollama) untuk deteksi PII teks bebas ---
    ollama_enabled: bool = False
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
