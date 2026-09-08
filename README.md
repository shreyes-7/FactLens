# FactLens — Evidence-Grounded Cross-Document Fact Knowledge Layer

> **FactLens 2.0** transforms raw PDF corporate disclosures, earnings reports, and financial filings into a deterministic, verifiable, and evidence-grounded knowledge layer.

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-142%20Passing-brightgreen.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)]()
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791.svg)]()

---

## 🌟 Key Capabilities & FactLens 2.0 Features

FactLens goes beyond basic RAG or LLM question answering by extracting atomic, normalized facts from complex PDF documents, grounding every fact in verbatim source quotes and page numbers, and analyzing relationships across documents.

### 1. 🔍 Contradiction Investigator (New in FactLens 2.0)
When two corporate filings present different figures for what appears to be the same metric (e.g., Q3 revenue or operating income), an LLM hallucinating a generic "they contradict" answer is dangerous. The **Contradiction Investigator** performs an instant, deterministic, multi-factor audit:
- **Exhaustive Multi-Factor Verification**: Evaluates `entity_match`, `predicate_match`, `period_match`, `currency_match`, `unit_match`, `scope_match`, `same_document`, `same_page`, and exact `variance_percent`.
- **Intelligent Classification & Verdicts**:
  - `TRUE_CONTRADICTION`: Same entity, same reporting period, same accounting scope, but irreconcilable numeric variance (>1.5%).
  - `CONTEXTUAL_DIFFERENCE`: Figures differ because one is GAAP and one is Non-GAAP, or one represents a specific business segment while the other is Consolidated.
  - `TEMPORAL_DIFFERENCE`: Figures differ because they measure different fiscal periods (e.g., Q3 2023 vs Q3 2024 progression).
  - `UNIT_DIFFERENCE`: Figures appear different due to scale reporting (e.g., thousands vs millions) or currency denomination.
  - `CORROBORATED`: Numerical figures match within ±1.5% tolerance.
- **Explainable Checklist & Evidence Drawer**: Slide-over drawer provides side-by-side excerpts with verbatim source quotes, page coordinates, and clear actionable explanations.
- **Zero Additional LLM Overhead**: Evaluated deterministically in `<50ms` using structured entity-relation rules.

---

### 2. 📊 "What Changed?" — Cross-Document Analytical Workspace (New in FactLens 2.0)
A specialized analytical workspace for financial analysts, auditors, and researchers comparing 2 to 5 corporate filings simultaneously:
- **Multi-Document Comparison Matrix**: Select 2 to 5 filings (e.g., 10-Q Q1, Q2, Q3, and 10-K) to generate a unified financial timeline matrix across all shared canonical metrics.
- **Automated Trend & Change Classification**:
  - `INCREASED` (📈): Metric grew by `+X%`.
  - `DECREASED` (📉): Metric decreased by `-X%`.
  - `UNCHANGED` (➖): Metric remained stable (within ±1.5%).
  - `ADDED` (➕): New metric or disclosure introduced in later filing.
  - `NOT_FOUND` (❓): Metric present in earlier filing but omitted or unreported in later filing.
  - `CONTEXT_CHANGED` (🔄): Metric value changed due to restatement, scope adjustment, or accounting standard update.
- **Executive Summary KPI Cards**: Instant breakdown of total tracked metrics, growth counts, declines, and new line items.
- **Evidence Drill-down**: Click any metric row to inspect verbatim quotes, page numbers, and dates across all participating documents.
- **Instant Query Performance**: Sub-30ms execution powered by single SQL aggregation joining normalized facts and lateral citations in PostgreSQL.

---

### 3. 🛡️ Fact Confidence & Evidence Quality Scoring (New in FactLens 2.0)
Every extracted fact is assigned an explainable **Confidence Score (0–100)** and confidence level (`HIGH`, `MEDIUM`, `LOW`) computed from deterministic evidence signals:
- **Transparent Signal Breakdown**:
  - `+25 pts`: Verbatim evidence quote length ≥ 20 characters.
  - `+15 pts`: Strong evidence citation with quote length ≥ 50 characters.
  - `+15 pts`: Verified physical page number attached to source text.
  - `+15 pts`: Explicit ISO fiscal date or reporting period anchored.
  - `+15 pts`: Standardized unit of measurement (USD, EUR, %, shares, etc.).
  - `+10 pts`: Explicit contextual scope defined (Consolidated, Non-GAAP, Segment).
  - `+5 pts`: Numeric normalization successfully parsed without ambiguity.
  - `-20 pts`: Missing evidence citation / ungrounded assertion.
  - `-15 pts`: Missing or unassigned page number.
  - `-10 pts`: Short or ambiguous evidence snippet (<20 characters).
- **Integrated UI Verification**: Color-coded badges and confidence breakdown drawer integrated across the Fact Explorer, Evidence Inspector, and Relationship Views.

---

### 4. 🗂️ Core Architecture & Foundation
- **PDF Ingestion & Page Breakdown**: PyMuPDF extraction preserving page numbers and chunk boundaries.
- **Incremental Extraction**: Only processes unextracted pages; avoids wasteful reprocessing of existing pages.
- **Dual LLM Pipeline**: Primary extraction via Google Gemini with automatic, seamless fallback to Groq (Llama 3.3 70B).
- **Hybrid Search & Candidate Matching**: pgvector semantic embedding retrieval + canonical metadata filtering to discover cross-document relationships.
- **Isolated Cross-Doc vs Same-Doc Comparisons**: Clean 3-way toggle segregating cross-document comparisons (`doc_a != doc_b`) and intra-document page checks without leakage.
- **Real-Time Extraction Status**: Immediate optimistic state updates, spinning loader indicators on rows and buttons, automatic polling every 2s, and live dashboard counter synchronization.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, PyMuPDF, psycopg3 |
| **Database & Search** | Supabase PostgreSQL, pgvector (embeddings & semantic search) |
| **LLM & Embeddings** | Google Gemini (primary), Groq / Llama 3.3 (fallback), Jina Embeddings v3 |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons, Radix UI Primitives |
| **Testing** | Pytest (142 automated test suites) |

---

## 🌐 Production Deployment Guide (Vercel + Render + Supabase)

FactLens is engineered for cost-effective, enterprise-grade production deployment using **100% free-tier** services:
- **Frontend**: [Vercel Free Tier](https://vercel.com) (React 18 + Vite + TypeScript + Tailwind CSS)
- **Backend**: [Render Free Web Service](https://render.com) (FastAPI + Python 3.11 + Uvicorn)
- **Database & Storage**: [Supabase Free Tier](https://supabase.com) (Managed PostgreSQL + pgvector + Cloud Storage)
- **LLM Engine**: Google Gemini API (Primary) with Groq Llama 3.3 (Fallback)

```
                       ┌─────────────────────────────────────────┐
                       │              Vercel (SPA)               │
                       │     React + Vite + TypeScript + CSS     │
                       └────────────────────┬────────────────────┘
                                            │
                                            │ HTTPS /api/*
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │         Render Free Web Service         │
                       │        FastAPI + Python + Uvicorn       │
                       └──────┬──────────────────┬───────────────┘
                              │                  │
                SQL / pgvector│                  │ REST API (Direct stream)
                              ▼                  ▼
       ┌─────────────────────────────┐    ┌─────────────────────────────┐
       │     Supabase PostgreSQL     │    │   Supabase Cloud Storage    │
       │    Normalized Fact Tables   │    │  Private 'documents' Bucket │
       │  pgvector Semantic Indices  │    │  In-memory PDF parsing via  │
       │   Lateral Evidence Joins    │    │      PyMuPDF streams        │
       └─────────────────────────────┘    └─────────────────────────────┘
```

---

### 1. Database & Cloud Storage Setup (Supabase)

1. **Create Supabase Project**:
   - Go to [Supabase Dashboard](https://supabase.com/dashboard) and create a new project.
   - Note down your **Database Connection String** (`URI` mode with pooling or direct port 5432).
   - Note down your **Project URL** (`https://<project-ref>.supabase.co`) and **Service Role Key** (`service_role` secret key from Settings > API).

2. **Enable pgvector & Apply Schema**:
   - In Supabase SQL Editor, run:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Execute the schema migration files located in `backend/migrations/` (starting with `001_initial_schema.sql` and any subsequent feature migrations) to create tables for datasets, documents, facts, evidence chunks, relationships, and vector search functions.

3. **Configure Storage Bucket**:
   - Navigate to **Storage** > **New Bucket**.
   - Bucket Name: `documents`
   - Privacy: **Private** (recommended; documents are accessed via server-signed URLs and service role credentials).

---

### 2. Backend Deployment (Render Free Web Service)

1. **Create Web Service**:
   - Log into [Render Dashboard](https://dashboard.render.com).
   - Click **New +** > **Web Service**.
   - Connect your GitHub repository: `https://github.com/shreyes-7/FactLens`.

2. **Configure Service Settings**:
   - **Name**: `factlens-backend` (or your preferred name)
   - **Region**: Choose the region closest to your Supabase project (e.g., Frankfurt, Oregon, Singapore).
   - **Branch**: `main`
   - **Root Directory**: Leave blank (uses repository root `.`).
   - **Runtime**: `Python 3` (3.11+)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**:
     ```bash
     uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: `Free` (0.1 CPU, 512 MB RAM)

3. **Configure Health Check**:
   - In **Advanced Settings**, set **Health Check Path** to `/health`.
   - Render will periodically ping `GET /health` to monitor container health and trigger fast zero-downtime rollouts.

4. **Add Environment Variables on Render**:

| Variable Name | Required | Default / Value | Description |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | `postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres` | Supabase PostgreSQL connection string |
| `SUPABASE_URL` | **Yes** | `https://[project-ref].supabase.co` | Supabase Project API URL |
| `SUPABASE_SERVICE_KEY` | **Yes** | `eyJh...` | Supabase Service Role Secret Key (for private bucket & DB access) |
| `STORAGE_BUCKET` | No | `documents` | Supabase Storage bucket for PDF documents |
| `GEMINI_API_KEY` | **Yes** | `AIza...` | Google Gemini API Key (primary extraction and embeddings) |
| `GROQ_API_KEY` | No | `gsk_...` | Groq API Key (high-speed fallback provider) |
| `FRONTEND_URL` | **Yes** | `https://factlens.vercel.app` | Deployed Vercel URL for strict CORS validation |
| `ALLOWED_CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Additional origins (comma-separated or JSON list) |
| `APP_ENV` | No | `production` | Deployment environment flag |
| `LOGFIRE_TOKEN` | No | *(Optional)* | Pydantic Logfire token for observability |

> **Note on Render Free Tier Cold Starts**:
> Render's free tier spins down web instances after 15 minutes of inactivity. When a request arrives, the instance spins up automatically, taking **~45 to 60 seconds** on the first request. The FactLens frontend client includes built-in detection that alerts the user with helpful status guidance during cold starts.

> **Note on Ephemeral Filesystem**:
> Render free instances have an ephemeral local disk. FactLens is architected with **zero disk persistence requirements**: all uploaded PDFs are streamed directly into Supabase Storage and parsed in-memory using PyMuPDF streams (`fitz.open(stream=file_bytes)`). No data is ever lost on container restart.

---

### 3. Frontend Deployment (Vercel Free Tier)

1. **Import Project**:
   - Log into [Vercel Dashboard](https://vercel.com) and click **Add New...** > **Project**.
   - Select your `FactLens` GitHub repository.

2. **Configure Build Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and set to `frontend`.
   - **Build Command**: `npm run build` (or leave default Vite command).
   - **Output Directory**: `dist` (default).
   - **Install Command**: `npm install` (default).

3. **Configure Environment Variables on Vercel**:

| Variable Name | Required | Example Value | Description |
|---|---|---|---|
| `VITE_API_URL` | **Yes** | `https://factlens-backend.onrender.com` | Base URL of your deployed Render backend |

4. **Deploy**:
   - Click **Deploy**. Vercel will build and deploy your React SPA in <60 seconds.
   - Once deployed, copy your production Vercel URL (e.g., `https://factlens.vercel.app`) and ensure it matches the `FRONTEND_URL` set in Render's environment variables.

---

### 4. 📋 36-Point Pre-Deployment Verification Checklist

#### Architecture & Configuration
- [ ] 1. Single unified repository with clean separation: `backend/` (FastAPI) and `frontend/` (Vite).
- [ ] 2. Zero hardcoded secrets, database credentials, or API keys in git history or tracked code.
- [ ] 3. `.env.example` mirrors all backend and frontend configuration keys without values.
- [ ] 4. Dynamic `$PORT` handling on backend: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] 5. Root lightweight health check endpoint `GET /health` responding with HTTP 200 `{"status": "ok"}`.
- [ ] 6. Detailed system health check endpoint `GET /api/health` checking DB connectivity and LLM provider readiness.
- [ ] 7. CORS origins properly configured with dynamic `FRONTEND_URL` and `ALLOWED_CORS_ORIGINS`.
- [ ] 8. Comma-separated string parsing for `ALLOWED_CORS_ORIGINS` to support Render environment input.
- [ ] 9. Rate limiting middleware active with configurable per-minute thresholds.
- [ ] 10. Security headers middleware active (X-Content-Type-Options, X-Frame-Options, HSTS).

#### Storage & Ephemeral Container Hardening
- [ ] 11. PDF upload pipeline writes directly to Supabase Storage private bucket (`documents`).
- [ ] 12. No permanent files written to local container disk (`/tmp` or working dir).
- [ ] 13. PyMuPDF parsing executes from in-memory byte streams (`fitz.open(stream=bytes)`).
- [ ] 14. Signed URLs generated dynamically for document downloads with configurable expiration.
- [ ] 15. Graceful handling of missing or deleted storage objects.

#### Database & Vector Retrieval
- [ ] 16. Supabase PostgreSQL instance active with `vector` extension enabled.
- [ ] 17. Connection pooling supported (supports both transaction pooler port 6543 and session port 5432).
- [ ] 18. Normalized fact schema with explicit foreign keys, composite indexes, and lateral evidence joins.
- [ ] 19. pgvector cosine similarity search queries executing with IVFFlat or HNSW indexes.
- [ ] 20. Sub-30ms analytical queries for "What Changed?" comparison matrix.

#### Extraction & AI Providers
- [ ] 21. Gemini API primary provider active with valid credentials.
- [ ] 22. Groq Llama 3.3 fallback provider tested and functional upon primary exhaustion.
- [ ] 23. Incremental fact extraction prevents re-extracting previously processed document pages.
- [ ] 24. Deterministic entity, date, number, unit, and scope normalizers active.
- [ ] 25. Verbatim evidence grounding validated with exact physical page coordinates.

#### FactLens 2.0 Intelligence Features
- [ ] 26. Contradiction Investigator performs deterministic 9-factor verification without extra LLM cost.
- [ ] 27. Cross-Document Comparison Matrix correctly handles 2 to 5 simultaneous document comparisons.
- [ ] 28. Evidence Quality & Fact Confidence scoring (0–100) computed with transparent signal breakdown.
- [ ] 29. Isolated cross-document comparison view (`doc_a != doc_b`) strictly segregated from same-doc checks.
- [ ] 30. Real-time extraction status polling with immediate optimistic UI updates and counter sync.

#### Frontend & Build Integrity
- [ ] 31. `frontend/vercel.json` contains SPA rewrite rules (`/(.*)` -> `/index.html`) to prevent 404s on refresh.
- [ ] 32. `VITE_API_URL` and `VITE_API_BASE_URL` properly resolved with trailing-slash and `/api` auto-formatting.
- [ ] 33. Axios/Fetch interceptors handle Render cold-start HTTP 502/504 errors with informative user messaging.
- [ ] 34. Frontend TypeScript build compiles with zero errors (`tsc && vite build`).
- [ ] 35. Responsive layout tested across desktop, tablet, and mobile breakpoints.
- [ ] 36. 100% automated test suite passing (142 of 142 Pytest unit and integration tests).

---

### 5. 🔧 Troubleshooting & FAQ

#### Q: The frontend shows "Request failed with status 502/504" on first visit.
> **Answer**: This is normal for Render's free tier. Render spins down services after 15 minutes of inactivity. When the first request arrives, it takes ~45 to 60 seconds to launch the container. The FactLens frontend displays a helpful retry message. Once awake, subsequent requests respond in milliseconds.

#### Q: CORS error: `Access to fetch at '...' from origin '...' has been blocked by CORS policy`.
> **Answer**: Make sure `FRONTEND_URL` on Render matches your exact Vercel URL (including `https://`, without a trailing slash, e.g., `https://factlens.vercel.app`). Also verify that `ALLOWED_CORS_ORIGINS` includes any staging or preview domains if applicable.

#### Q: Refreshing a page on Vercel returns a 404 error.
> **Answer**: Ensure `frontend/vercel.json` is committed and contains the rewrite rule routing `/(.*)` to `/index.html`. This allows React Router to manage client-side routes.

#### Q: Render build fails during `pip install`.
> **Answer**: Ensure Render's Python version is set to 3.11. All dependencies in `requirements.txt` are pinned and verified compatible with Python 3.11+.

---

## 👥 Author
- **Developer**: Shreyes Jaiswal
- **Email**: [shreyesjaiswal7@gmail.com](mailto:shreyesjaiswal7@gmail.com)
- **Repository**: [https://github.com/shreyes-7/FactLens](https://github.com/shreyes-7/FactLens)

