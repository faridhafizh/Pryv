"""Mesin anonimisasi (Pandas): suppression, generalization, K-Anonymity.

Alur pipeline:
  1. Suppression    : hapus kolom PII (daftar default + deteksi otomatis).
  2. Generalization : Umur -> rentang tahun, Pendapatan -> kuintil.
  3. K-Anonymity    : grup berdasarkan quasi-identifier; baris pada grup
                      beranggotakan < k ikut di-suppress (drop).

Semua pencarian kolom case-insensitive ("UMUR"/"umur" sama saja) karena
dataset BPS sering memakai header campuran.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Umur -> rentang. Rentang bisa disesuaikan tanpa mengubah kode lain.
AGE_BINS = [0, 14, 24, 59, 120]
AGE_LABELS = ["0-14", "15-24", "25-59", "60+"]

# Pola nama kolom PII (regex, case-insensitive).
PII_NAME_PATTERNS = [
    r"^nik$", r"^no_?ktp$", r"^nama", r"^email", r"^e-?mail",
    r"^no_?hp", r"^telepon", r"^telp", r"^alamat", r"^ip_?address", r"^npwp",
]

NIK_RE = re.compile(r"^\d{16}$")                 # NIK = 16 digit
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def _find_column(df: pd.DataFrame, name: str) -> str | None:
    """Temukan nama kolom asli dari nama yang di-normalisasi (case-insensitive)."""
    lookup = {_norm(c): c for c in df.columns}
    return lookup.get(_norm(name))


def detect_pii_columns(df: pd.DataFrame, extra_names: list[str] | None = None) -> list[str]:
    """Deteksi kolom PII: (a) cocok pola nama, (b) isi berupa NIK/email.

    Content check membuat kolom bernama bebas (mis. 'c1') tetap tertangkap
    selama isinya jelas PII — cukup untuk MVP, bukan pengganti NLP penuh.
    """
    names = {_norm(c) for c in (extra_names or [])}
    hits: list[str] = []
    for col in df.columns:
        norm = _norm(col)
        if names and norm in names:
            hits.append(col)
            continue
        if any(re.search(p, norm) for p in PII_NAME_PATTERNS):
            hits.append(col)
            continue
        sample = df[col].dropna().astype(str).head(1000)
        if len(sample) < 5:
            continue
        if sample.str.fullmatch(NIK_RE).mean() > 0.9 or sample.str.match(EMAIL_RE).mean() > 0.9:
            hits.append(col)
    return hits


def suppress_columns(df: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Hapus kolom PII. Kolom yang tidak ada di df dilewati tanpa error."""
    present = [c for c in columns if c in df.columns]
    return df.drop(columns=present), present


def generalize_age(series: pd.Series, bins: list[int] = AGE_BINS, labels: list[str] = AGE_LABELS) -> pd.Series:
    """Umur -> rentang tahun. Nilai di luar bins / kosong menjadi 'Lainnya'."""
    num = pd.to_numeric(series, errors="coerce")
    out = pd.cut(num, bins=bins, labels=labels, right=True)
    return out.astype(str).replace("nan", "Lainnya")


def generalize_income(series: pd.Series) -> pd.Series:
    """Pendapatan -> kuintil Q1..Q5.

    pd.qcut gagal saat nilai duplikat menghasilkan bin tidak unik, jadi
    pakai rank berbasis posisi: dijamin selalu menghasilkan 5 kelompok.
    """
    num = pd.to_numeric(series, errors="coerce")
    valid = num.notna()
    out = pd.Series(np.nan, index=series.index, dtype="object")
    if valid.any():
        ranks = num[valid].rank(method="first")
        q = ((ranks - 1) * 5 // ranks.max()).clip(0, 4) + 1
        out[valid] = "Q" + q.astype(int).astype(str)
    return out.fillna("Lainnya").astype(str)


def enforce_k_anonymity(df: pd.DataFrame, quasi_identifiers: list[str], k: int) -> tuple[pd.DataFrame, int]:
    """Drop baris pada grup quasi-identifier yang beranggotakan < k.

    Returns: (df bersih, jumlah baris di-suppress).
    # ponytail: global recoding (menaikkan level generalisasi) bisa menggantikan
    # dropping baris bila data loss jadi masalah; upgrade saat itu dibutuhkan.
    """
    if not quasi_identifiers or k <= 1:
        return df, 0
    sizes = df.groupby(quasi_identifiers, observed=True).size()
    small_groups = set(sizes[sizes < k].index)
    mask = df.set_index(quasi_identifiers).index.isin(small_groups)
    return df[~mask].copy(), int(mask.sum())


@dataclass
class AnonymizeConfig:
    k: int = 5
    quasi_identifiers: list[str] = field(default_factory=list)
    pii_columns: list[str] = field(default_factory=list)  # tambahan manual
    age_column: str = "umur"
    income_column: str = "pendapatan"
    generalize_age: bool = True
    generalize_income: bool = True


@dataclass
class AnonymizeStats:
    rows_in: int
    rows_out: int
    rows_dropped: int
    columns_removed: list[str]
    columns_kept: list[str]
    quasi_identifiers: list[str]
    k: int
    groups_below_k: int


def anonymize(df: pd.DataFrame, cfg: AnonymizeConfig) -> tuple[pd.DataFrame, AnonymizeStats]:
    """Pipeline lengkap: suppression -> generalization -> K-Anonymity."""
    df = df.copy()
    rows_in = len(df)

    # 1. Suppression
    df_clean, removed_cols = suppress_columns(df, detect_pii_columns(df, cfg.pii_columns))

    # 2. Generalization (nama kolom dicari case-insensitive)
    if cfg.generalize_age:
        age_col = _find_column(df_clean, cfg.age_column)
        if age_col:
            df_clean[age_col] = generalize_age(df_clean[age_col])
    if cfg.generalize_income:
        income_col = _find_column(df_clean, cfg.income_column)
        if income_col:
            df_clean[income_col] = generalize_income(df_clean[income_col])

    # 3. K-Anonymity
    qid_actual: list[str] = []
    for q in cfg.quasi_identifiers:
        found = _find_column(df_clean, q)
        if found and found not in qid_actual:
            qid_actual.append(found)
    out, dropped = enforce_k_anonymity(df_clean, qid_actual, cfg.k)

    stats = AnonymizeStats(
        rows_in=rows_in,
        rows_out=len(out),
        rows_dropped=dropped,
        columns_removed=removed_cols,
        columns_kept=list(out.columns),
        quasi_identifiers=qid_actual,
        k=cfg.k,
        groups_below_k=(
            int(df_clean.groupby(qid_actual, observed=True).size().lt(cfg.k).sum())
            if qid_actual and cfg.k > 1 else 0
        ),
    )
    return out, stats
