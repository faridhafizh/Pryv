"""Self-check mesin anonimisasi. Jalankan: python -m pytest -q"""
import pandas as pd

from app.services.anonymizer import AnonymizeConfig, anonymize, detect_pii_columns


def _sample() -> pd.DataFrame:
    """10 baris, 5 grup quasi-id masing-masing 2 baris.

    Income dipilih strictly increasing dan berpasangan agar pasangan
    jatuh di kuintil yang sama (boundary kuintil di rank 2/3, 4/5, 6/7, 8/9).
    """
    return pd.DataFrame({
        "NIK": [f"{i:016d}" for i in range(1, 11)],
        "Nama Lengkap": [f"Orang {i}" for i in range(1, 11)],
        "Email": [f"o{i}@mail.com" for i in range(1, 11)],
        "Umur": [20, 20, 30, 30, 35, 35, 45, 45, 70, 70],
        "Pendapatan": [1.0e6, 1.1e6, 2.0e6, 2.1e6, 3.0e6, 3.1e6, 4.0e6, 4.1e6, 5.0e6, 5.1e6],
        "Kabupaten_Kota": ["A", "A", "B", "B", "C", "C", "D", "D", "E", "E"],
    })


def test_pipeline_suppresses_generalizes_and_enforces_k():
    df = _sample()
    out, stats = anonymize(df, AnonymizeConfig(
        k=2, quasi_identifiers=["umur", "pendapatan", "kabupaten_kota"]))

    # Suppression: semua kolom PII hilang
    assert "NIK" not in out.columns
    assert "Nama Lengkap" not in out.columns
    assert "Email" not in out.columns
    assert stats.columns_removed == ["NIK", "Nama Lengkap", "Email"]

    # Generalization: umur -> rentang, pendapatan -> kuintil (5 level utuh)
    assert set(out["Umur"].unique()) <= {"0-14", "15-24", "25-59", "60+"}
    assert set(out["Pendapatan"].unique()) == {"Q1", "Q2", "Q3", "Q4", "Q5"}

    # K-Anonymity: setiap grup quasi-id >= k, tidak ada baris terbuang
    sizes = out.groupby(["Umur", "Pendapatan", "Kabupaten_Kota"], observed=True).size()
    assert (sizes >= 2).all()
    assert stats.rows_dropped == 0
    assert stats.rows_out == stats.rows_in == 10
    assert stats.groups_below_k == 0


def test_k_anonymity_drops_small_groups():
    df = _sample()
    out, stats = anonymize(df, AnonymizeConfig(
        k=5, quasi_identifiers=["umur", "pendapatan", "kabupaten_kota"]))
    # Semua grup hanya berisi 2 baris < k=5 -> seluruh data di-suppress.
    assert stats.rows_dropped == 10
    assert stats.rows_out == 0
    assert stats.groups_below_k == 5


def test_detect_pii_by_content():
    df = pd.DataFrame({"nik": ["1234567890123456"] * 6, "bebas": ["x"] * 6})
    assert detect_pii_columns(df) == ["nik"]


def test_case_insensitive_column_lookup():
    df = pd.DataFrame({"UMUR": [30, 30], "Pendapatan": [5e6, 5e6]})
    out, _ = anonymize(df, AnonymizeConfig(
        k=1, quasi_identifiers=["umur", "pendapatan"], pii_columns=[]))
    assert out["UMUR"].tolist() == ["25-59", "25-59"]
    assert out["Pendapatan"].str.startswith("Q").all()
