"""Self-check API end-to-end via TestClient bawaan FastAPI."""
import io

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_anonymize_endpoint_end_to_end():
    df = pd.DataFrame({
        "NIK": [f"{i:016d}" for i in range(1, 11)],
        "Nama Lengkap": [f"Orang {i}" for i in range(1, 11)],
        "Umur": [20, 20, 30, 30, 35, 35, 45, 45, 70, 70],
        "Pendapatan": [1.0e6, 1.1e6, 2.0e6, 2.1e6, 3.0e6, 3.1e6, 4.0e6, 4.1e6, 5.0e6, 5.1e6],
        "Kabupaten_Kota": ["A", "A", "B", "B", "C", "C", "D", "D", "E", "E"],
    })
    buf = io.StringIO()
    df.to_csv(buf, index=False)

    res = client.post(
        "/api/anonymize",
        files={"file": ("sensus.csv", buf.getvalue(), "text/csv")},
        data={"k": "2", "quasi_identifiers": "umur,pendapatan,kabupaten_kota"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["stats"]["columns_removed"] == ["NIK", "Nama Lengkap"]
    assert body["stats"]["rows_in"] == 10
    assert body["stats"]["rows_out"] == 10
    assert body["stats"]["rows_dropped"] == 0

    dl = client.get(body["download_url"])
    assert dl.status_code == 200
    assert "NIK" not in dl.text
    assert "Umur" in dl.text  # kolom non-PII tetap ada (sudah digeneralisasi)


def test_rejects_non_csv():
    res = client.post("/api/anonymize", files={"file": ("data.xlsx", b"x", "application/octet-stream")})
    assert res.status_code == 400


def test_rejects_small_k():
    res = client.post(
        "/api/anonymize",
        files={"file": ("a.csv", b"a,b\n1,2\n", "text/csv")},
        data={"k": "1"},
    )
    assert res.status_code == 422
