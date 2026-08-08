<p align="center">
  <img src="assets/logo.jpg" alt="Microdata Privacy Guard Logo" width="300" />
</p>

<h1 align="center">Microdata Privacy Guard</h1>

<p align="center">
  <strong>SaaS Anonymization Platform for Official Census Datasets (BPS)</strong>
</p>

<p align="center">
  <em>Ensuring K-Anonymity & Dynamic PII Protection Prior to Public Release</em>
</p>

<p align="center">
  <a href="https://nextjs.org/"><img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi" alt="FastAPI"></a>
  <a href="https://supabase.com/"><img src="https://img.shields.io/badge/Supabase-Auth%20%26%20DB-3ECF8E?logo=supabase" alt="Supabase"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python" alt="Python"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
</p>

---

## 📌 Overview

**Microdata Privacy Guard (MPG)** is a secure, automated data privacy solution tailored for microdata census datasets managed by **Badan Pusat Statistik (BPS)**. It empowers data engineers and researchers to sanitize raw datasets by applying **Suppression**, **Generalization**, and **K-Anonymity** constraints before public dissemination.

It features a modern decoupled web architecture built for scale, complete with flexible UI-driven parameters and local LLM/NLP capability for unstructured free-text inspection.

---

## 🏗️ Architecture & Stack

```
+---------------------------------------------------------+
|                  Frontend (Next.js 14)                  |
|             Deploy: Vercel / Auth: Supabase              |
+----------------------------+------------------------------+
                             |
                    JWT Proxy / HTTP API
                             |
                             v
+---------------------------------------------------------+
|                   Backend (FastAPI)                     |
|              Deploy: Render / Railway / VPS               |
+----------------------------+------------------------------+
                             |
              +--------------+---------------+
              |                              |
              v                              v
   +-----------------------+      +-----------------------+
   |     Pandas Engine      |      |    Ollama NLP Engine   |
   |  (Suppression/K-Anon)  |      |   (Optional Local PII) |
   +-----------------------+      +-----------------------+
```

| Domain | Technology Stack | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS | High-performance user portal deployed to Vercel. |
| **Backend** | FastAPI, Pandas, Pytest | High-speed Python pipeline handling state-free dataset mutations. |
| **Auth & DB** | Supabase (PostgreSQL + RLS + GoTrue Auth) | Enterprise-grade access control with Row-Level Security (RLS). |
| **Local NLP** | Ollama (Llama 3.2 model) | Localized unstructured text processing without data leakage. |

---

## ⚙️ Core Pipeline Capabilities

The core anonymization engine operates sequentially via `backend/app/services/anonymizer.py`:

```
[ Raw File ]
     │
     ▼
SUPPRESSION ────────► Strips explicit PII (NIK, Phone, Name, Email, NPWP)
     │                and applies regex auto-detection (16-digit sequences, '@').
     ▼
GENERALIZATION ─────► Recodes continuous variables into buckets:
     │                • Age (Umur)       -> Ranges: [0-14, 15-24, 25-59, 60+]
     │                • Income (Pendapatan) -> Rank-based Quintiles Q1..Q5
     ▼
K-ANONYMITY ────────► Groups quasi-identifiers; drops rows with group size < k.
     │                Calculates and outputs exact data loss statistics.
     ▼
[ Sanitized Output ]
```

> **Note:** Column matching is strictly **case-insensitive** (e.g., `"UMUR"` equals `"umur"`). Target $k$-value and custom Quasi-Identifiers can be dynamically configured per upload request.

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- **Node.js**: `v18.x` or higher
- **Python**: `3.12+`
- **Supabase Account**: (Free tier suffices)

### 1. Backend Setup

```bash
# Navigate to backend workspace
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run developmental API server
uvicorn app.main:app --reload --port 8000

# Execute unit tests (optional)
python -m pytest -q
```

Backend runs locally at: `http://localhost:8000`

### 2. Frontend Setup

```bash
# Navigate to frontend workspace
cd frontend

# Copy environment template
cp .env.local.example .env.local

# Configure .env.local with your Supabase credentials:
# NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
# NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Install dependencies and launch dev server
npm install
npm run dev
```

Frontend application opens at: `http://localhost:3000`

### 3. Database Initialization (Supabase)

1. Create a new project at [supabase.com](https://supabase.com).
2. Navigate to **Authentication → Providers → Email/Password** and enable it.
3. Manually create an initial operator account via **Authentication → Users → Add user**.
4. Run the SQL schema script inside the Supabase SQL Editor:

```sql
-- Executes migrations/0001_init.sql
```

This initializes the `anonymization_jobs` table and enforces Row Level Security (RLS) so users only query their own jobs.

---

## 🧠 Unstructured Text NLP (Optional)

The backend provides built-in PII extraction capability for unstructured text fields using a local Ollama integration (`backend/app/services/pii_detector.py`).

To activate local NLP PII Detection:

1. Install Ollama and pull the target model:

   ```bash
   ollama pull llama3.2
   ```

2. Enable the feature flag in `backend/.env`:

   ```env
   MPG_OLLAMA_ENABLED=true
   ```

Extracted entities (`PER`, `LOC`, `EMAIL`, `PHONE`, `NIK`) will automatically be calculated and attached under `stats.pii_in_free_text` in the API output.

---

## 🚢 Deployment Guide

### Frontend Deployment (Vercel)

1. Import the repository to Vercel.
2. Configure environment variables identical to `.env.local`.
3. Make sure API handler constraints permit extended runtime operations:

   ```ts
   export const maxDuration = 300; // 5-minute limit for long dataset processing
   ```

### Backend Deployment (Docker Container)

Set `MPG_ALLOWED_ORIGINS` to your Vercel deployment domain. You can containerize the production server using the lightweight single-stage Dockerfile:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ⚠️ Known Limitations & Roadmap

- **Stateless Workspace**: Processing generates outputs into temp storage without an active TTL auto-purge mechanism (requires scheduled CRON cleanup).
- **Auth Boundary**: JWT verification currently relies on the Next.js API proxy. Direct JWKS-level verification in FastAPI is recommended if exposing the backend publicly.
- **Anonymization Strategy**: Current K-Anonymity enforces strict row-suppression. Global recoding is planned for datasets where data-loss thresholds are critical.

---

## 📜 License

Distributed under the MIT License. See [LICENSE](./LICENSE) for more information.
