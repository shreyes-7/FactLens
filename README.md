# FactLens — Evidence-Grounded Cross-Document Fact Knowledge Layer

> **FactLens 2.0** transforms raw PDF corporate disclosures, earnings reports, and financial filings into a deterministic, verifiable, and evidence-grounded knowledge layer.

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-140%20Passing-brightgreen.svg)]()
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
| **Testing** | Pytest (140 automated test suites) |

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase / PostgreSQL instance with `pgvector` extension

### 1. Clone & Configure Environment
```bash
git clone https://github.com/shreyes-7/FactLens.git
cd FactLens
cp .env.example .env
```
Ensure `.env` contains:
- `DATABASE_URL` (PostgreSQL connection string)
- `GEMINI_API_KEY` (Google Gemini API key)
- `GROQ_API_KEY` (Optional Groq fallback API key)

### 2. Run Backend
```bash
# Using uv (recommended)
uv run uvicorn backend.app.main:app --reload --port 8000
```
Backend API will be accessible at: `http://localhost:8000` (Docs: `http://localhost:8000/docs`).

### 3. Run Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend UI will be accessible at: `http://localhost:5173`.

### 4. Run Automated Tests
```bash
uv run pytest
```
All **140 tests** covering extraction, normalization, reasoning, confidence scoring, contradiction investigation, and document comparison should pass.

---

## 👥 Author
- **Developer**: Shreyes Jaiswal
- **Email**: [shreyesjaiswal7@gmail.com](mailto:shreyesjaiswal7@gmail.com)
- **Repository**: [https://github.com/shreyes-7/FactLens](https://github.com/shreyes-7/FactLens)
