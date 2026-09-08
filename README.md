# FactLens — Evidence-Grounded Cross-Document Fact Knowledge Layer

> A deterministic, evidence-grounded Fact Knowledge Layer that extracts atomic, verifiable facts from complex corporate PDF disclosures, normalizes them into canonical representations, and discovers cross-document relationships (corroborations, contradictions, and contextual reconciliations).

- **Live Deployed Application**: [https://factlens-zeta.vercel.app/](https://factlens-zeta.vercel.app/)
- **Video Demo**: [Watch 3-minute Demo Video](YOUR_VIDEO_LINK_HERE) *(Placeholder for demo video)*
- **GitHub Repository**: [https://github.com/shreyes-7/FactLens](https://github.com/shreyes-7/FactLens)

---

## 🚀 Setup and Run Instructions

### Prerequisites
- **Python**: Version 3.11+
- **Node.js**: Version 18+ and `npm`
- **Database**: PostgreSQL with `pgvector` extension (e.g., [Supabase](https://supabase.com) project or local PostgreSQL)
- **API Keys**: Google Gemini API key (primary extraction) and/or Groq API key (optional fallback), Jina AI API key (1024-dim embeddings)

---

### 1. Clone the Repository
```bash
git clone https://github.com/shreyes-7/FactLens.git
cd FactLens
```

---

### 2. Configure Environment Variables (`.env`)

Copy the example environment file:
```bash
cp .env.example .env
```

Open `.env` and configure the required settings:

```ini
# =================================================================
# APPLICATION
# =================================================================
APP_NAME=FactLens
APP_ENV=development
DEBUG=true

# =================================================================
# DATABASE & STORAGE (Supabase PostgreSQL + pgvector + Storage)
# =================================================================
# PostgreSQL connection string (Transaction Pooler port 6543 or Session port 5432)
DATABASE_URL=postgresql://postgres:[YOUR_PASSWORD]@db.[YOUR_PROJECT_REF].supabase.co:5432/postgres

# Supabase Project API URL and Secret Service Role Key
SUPABASE_URL=https://[YOUR_PROJECT_REF].supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_secret_key
SUPABASE_STORAGE_BUCKET=documents

# =================================================================
# AI PROVIDERS (Primary: Gemini 3.5 Flash-Lite | Fallback: Groq)
# =================================================================
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-3.5-flash-lite
LLM_FALLBACK_ENABLED=true

# Groq High-Speed Standby Fallback Provider
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
FACT_EXTRACTION_BATCH_SIZE=4

# =================================================================
# EMBEDDINGS (Jina AI v3: 1024-dimensional vectors)
# =================================================================
EMBEDDING_PROVIDER=jina
EMBEDDING_MODEL=jina-embeddings-v3
EMBEDDING_DIMENSION=1024
JINA_API_KEY=your_jina_api_key_here

# =================================================================
# OBSERVABILITY & PROCESSING DEFAULTS
# =================================================================
LOGFIRE_TOKEN=your_optional_pydantic_logfire_token
MAX_FILE_SIZE_MB=50
CHUNK_SIZE=1200
CHUNK_OVERLAP=150
TOP_K_CANDIDATES=10

# =================================================================
# CORS & FRONTEND DEPLOYMENT SETTINGS
# =================================================================
FRONTEND_URL=https://factlens-zeta.vercel.app
ALLOWED_CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://factlens-zeta.vercel.app
VITE_API_BASE_URL=http://localhost:8000
```

---

### 3. Database Migration

1. In your Supabase / PostgreSQL SQL Editor, enable `pgvector`:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Execute the migration files located in `backend/migrations/` (starting with `001_initial_schema.sql`).
3. In Supabase Storage, create a private bucket named `documents`.

---

### 4. Run Backend (FastAPI)

```bash
# Using uv (recommended)
uv run uvicorn backend.app.main:app --reload --port 8000

# Or standard virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Swagger Interactive Docs: `http://localhost:8000/docs`
- Cloud Health Check Probe: `http://localhost:8000/health`

---

### 5. Run Frontend (React + Vite + TypeScript)

```bash
cd frontend
npm install
npm run dev
```
- Web Application: `http://localhost:5173`

---

### 6. Run Automated Tests

FactLens includes **142 automated unit and integration tests** verifying PDF ingestion, normalization algorithms, candidate matching, relationship classification, and security middlewares:
```bash
uv run pytest
```

---

## 🏛️ System Architecture & High-Level Design (HLD)

FactLens is architected with strict decoupling between **in-memory document ingestion**, **atomic fact normalization**, **pgvector semantic indexing**, and **hybrid cross-document reasoning**.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENT LAYER (React 18 + Vite)                                 │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌────────────────┐ ┌───────────────────┐  │
│  │   Overview    │ │  Document Hub │ │ Fact Explorer │ │ Cross-Doc Rel  │ │ "What Changed?"   │  │
│  │ Dashboard KPIs│ │ Upload & Parse│ │Evidence Drawer│ │Reconciliations │ │ Comparison Matrix │  │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬────────┘ └─────────┬─────────┘  │
└──────────┼─────────────────┼─────────────────┼─────────────────┼────────────────────┼────────────┘
           │                 │                 │                 │                    │
           └─────────────────┴────────┬────────┴─────────────────┴────────────────────┘
                                      │ HTTPS / REST API
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               API GATEWAY & MIDDLEWARE (FastAPI)                                 │
│  ┌─────────────────────────┐ ┌───────────────────────────┐ ┌──────────────────────────────────┐  │
│  │ RateLimitingMiddleware  │ │ SecurityHeadersMiddleware │ │ Dynamic CORS & Problem Details   │  │
│  └─────────────────────────┘ └───────────────────────────┘ └──────────────────────────────────┘  │
└─────────────────────────────────────┬────────────────────────────────────────────────────────────┘
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           │                                                     │
           ▼                                                     ▼
┌─────────────────────────────────────┐       ┌────────────────────────────────────────────────────┐
│      INGESTION & PARSING ENGINE     │       │            AI & INTELLIGENCE ORCHESTRATION         │
│  ┌───────────────────────────────┐  │       │  ┌──────────────────────────────────────────────┐  │
│  │  In-Memory PyMuPDF Streaming  │  │       │  │ Primary LLM: Google Gemini                   │  │
│  │  (Zero container disk writes) │  │       │  │ (gemini-3.5-flash-lite)                      │  │
│  └──────────────┬────────────────┘  │       │  └──────────────────────┬───────────────────────┘  │
│                 ▼                   │       │                         │ Automatic Failover       │
│  ┌───────────────────────────────┐  │       │  ┌──────────────────────▼───────────────────────┐  │
│  │  Page-Aware Text Chunking     │  │       │  │ Standby LLM: Groq Llama 3.3 / GPT-OSS 20B    │  │
│  │  (1200 chars, 150 overlap)    │  │       │  │ (openai/gpt-oss-20b)                         │  │
│  └──────────────┬────────────────┘  │       │  └──────────────────────────────────────────────┘  │
└─────────────────┼───────────────────┘       │                         ▲                          │
                  │                           │                         │ Structured Prompts       │
                  ▼                           │  ┌──────────────────────┴───────────────────────┐  │
┌─────────────────────────────────────┐       │  │ Deterministic Schema Normalizer              │  │
│     VECTOR & STORAGE LAYER          │       │  │ • Numeric & Currency Scaling (Cr, Mn, K, %) │  │
│  ┌───────────────────────────────┐  │       │  │ • ISO Fiscal Periods (Q4 FY24, FY23)         │  │
│  │ Jina Embeddings v3            │  │       │  │ • Scope & Accounting Standards (GAAP/Non-G)  │  │
│  │ (1024-dim dense vectors)      │  │       │  └──────────────────────────────────────────────┘  │
│  └──────────────┬────────────────┘  │       │                         ▲                          │
│                 ▼                   │       │                         │ Candidate Pairs          │
│  ┌───────────────────────────────┐  │       │  ┌──────────────────────┴───────────────────────┐  │
│  │ Supabase pgvector             │  │◄──────┼──┤ pgvector Semantic Retrieval Engine           │  │
│  │ (Cosine similarity indexing)  │  │       │  │ (Filters doc_a != doc_b, top-k candidates)   │  │
│  └──────────────┬────────────────┘  │       │  └──────────────────────────────────────────────┘  │
│                 ▼                   │       │                                                    │
│  ┌───────────────────────────────┐  │       │  ┌──────────────────────────────────────────────┐  │
│  │ Relational PostgreSQL Tables  │  │       │  │ Contradiction Investigator                   │  │
│  │ • datasets, documents, facts  │  │       │  │ (9-factor sub-50ms deterministic audit)      │  │
│  │ • evidence (verbatim quotes)  │  │       │  └──────────────────────────────────────────────┘  │
│  │ • fact_relationships         │  │       │  ┌──────────────────────────────────────────────┐  │
│  │ • Supabase Storage (PDFs)     │  │       │  │ "What Changed?" Analytical Matrix Engine     │  │
│  └───────────────────────────────┘  │       │  │ (Sub-30ms SQL joins, 2-5 filings comparison) │  │
└─────────────────────────────────────┘       └────────────────────────────────────────────────────┘
```

---

## 🌟 What Makes FactLens Unique (Stand-Out Capabilities)

FactLens is built to solve the real-world failure modes of naive RAG and generic LLM summaries:

### 1. 🔍 Deterministic Contradiction Investigator (Sub-50ms, Zero Extra LLM Cost)
When two corporate filings cite different numbers for a metric, naive LLMs hallucinate a generic "they contradict". FactLens executes an instant 9-factor deterministic audit:
- Evaluates `entity_match`, `predicate_match`, `period_match`, `currency_match`, `unit_match`, `scope_match`, `same_document`, `same_page`, and exact `variance_percent`.
- Categorizes outcomes into `TRUE_CONTRADICTION`, `CONTEXTUAL_DIFFERENCE`, `TEMPORAL_DIFFERENCE`, `UNIT_DIFFERENCE`, or `CORROBORATED`.
- Slide-over drawer exposes verbatim side-by-side excerpts and exact mathematical variance without calling an LLM.

### 2. 📊 "What Changed?" — Multi-Filing Analytical Matrix
Designed for equity research analysts and auditors comparing **2 to 5 documents simultaneously**:
- Select 2 to 5 filings (e.g., Q1, Q2, Q3 10-Q and Annual 10-K) to generate a unified financial timeline matrix across shared canonical metrics.
- Automatically computes directional movement: `INCREASED` (📈), `DECREASED` (📉), `UNCHANGED` (➖), `ADDED` (➕), `NOT_FOUND` (❓), and `CONTEXT_CHANGED` (🔄).
- Powered by a single lateral SQL query joining normalized facts and lateral citations in `<30ms`.

### 3. 🛡️ Fact Confidence & Evidence Quality Scoring (0–100 Points)
Every extracted fact receives an explainable confidence score computed from transparent evidentiary signals:
- `+25 pts`: Verbatim evidence quote length $\ge 20$ characters.
- `+15 pts`: Strong evidence citation length $\ge 50$ characters.
- `+15 pts`: Verified physical page number anchored to source PDF.
- `+15 pts`: Explicit ISO fiscal date or reporting period anchored.
- `+15 pts`: Standardized unit of measurement (USD, INR, %, shares, etc.).
- `+10 pts`: Explicit contextual scope defined (Consolidated, Non-GAAP, Segment).
- `+5 pts`: Numeric normalization successfully resolved without ambiguity.
- `-20 pts`: Missing citation / ungrounded assertion.

### 4. ⚡ Decoupled 2-Stage Ingestion & Reasoning Architecture
- Ingesting a PDF ($O(1)$) takes seconds: text is parsed, chunked, embedded, and facts are extracted immediately.
- Cross-document relationship reasoning ($O(N \times M)$) is decoupled into an on-demand background pipeline, preventing token burn and UI freezing on uploads.

### 5. 🔄 Incremental Extraction (Never Reprocess Old Pages)
- Tracks extracted page numbers at the database layer.
- Re-processing an amended filing only parses newly added or unextracted pages, conserving LLM quotas and database storage.

### 6. 🛡️ Dual-Model Zero-Downtime Resilience
- Primary extraction and reasoning powered by Google Gemini (`gemini-3.5-flash-lite`).
- Automatic transparent fallback to Groq (`openai/gpt-oss-20b`) upon rate limits or 429/503 errors.

### 7. 💾 100% In-Memory Stream Processing (Container-Safe)
- Zero permanent or temporary PDF files written to local container disk (`/tmp` or working dir).
- Streams bytes directly to Supabase Storage and parses via PyMuPDF in-memory (`fitz.open(stream=bytes)`), making it safe for ephemeral platforms like Render Free and Vercel.

---

## 📡 Core API Endpoints

FactLens exposes clean, RESTful endpoints adhering to OpenAPI 3.0 standards:

| Method | Endpoint | Description | Primary Use Case |
|---|---|---|---|
| `GET` | `/health` | Root lightweight health probe | Container health check for Render & cloud balancers |
| `GET` | `/api/health` | Deep diagnostic system health check | Inspects database connection, active LLM model, and vector provider |
| `GET` | `/api/datasets` | List all datasets with aggregates | Retrieves datasets with real-time fact and relationship counters |
| `POST` | `/api/documents/upload` | Ingest PDF document | Streams uploaded PDF to Supabase Storage and registers document metadata |
| `POST` | `/api/documents/{id}/process` | Trigger document processing | Runs page-aware chunking, vector embedding, and atomic fact extraction |
| `GET` | `/api/facts` | Query & filter normalized facts | Filter facts by dataset, document, entity, category, or search term |
| `GET` | `/api/facts/{id}` | Retrieve single fact details | Fetches fact attributes, verbatim evidence quote, and physical PDF page |
| `GET` | `/api/facts/{id}/confidence` | Fact confidence score breakdown | Returns explainable 0–100 point scorecard and quality factors |
| `GET` | `/api/relationships` | Query fact relationships | Filter comparisons by cross-doc, same-doc, type, and confidence |
| `POST` | `/api/relationships/reason` | Trigger cross-document reasoning | Executes pgvector candidate search and LLM relationship classification |
| `GET` | `/api/relationships/{id}/investigate` | Run Contradiction Investigator | Deterministic 9-factor audit resolving contradictions vs contextual diffs |
| `POST` | `/api/comparisons` | "What Changed?" Analytical Matrix | Generates multi-filing financial comparison timeline across 2 to 5 PDFs |
| `GET` | `/api/cases/four-cases` | Four evaluation benchmark cases | Structured demonstration of the four core evaluation cases |

---

## 🔍 The Four Required Cases

FactLens provides dedicated views and an automated benchmark endpoint (`GET /api/cases/four-cases`) demonstrating each required case from real corporate disclosures:

### Case 1: Cross-Document Fact Corroboration
- **Description**: Two distinct corporate filings report the same metric using different units and scale representations, reconciled and verified by FactLens.
- **Source A**: `03-delhivery-q4-fy24-earnings-presentation.pdf` (Page 5)  
  - *Extracted Fact*: `Delhivery Ltd | EBITDA | Rs. 127 Cr (Normalized: 1,270,000,000 INR)`
  - *Evidence Quote*: `"FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr from Rs. (452 Cr) in FY23"`
- **Source B**: `02-delhivery-annual-report-fy24-excerpt.pdf` (Page 4)  
  - *Extracted Fact*: `Delhivery Ltd | EBITDA | ₹1,266Mn (Normalized: 1,266,000,000 INR)`
  - *Evidence Quote*: `"₹1,266Mn EBITDA"`
- **System Reasoning**: FactLens converts `Rs. 127 Cr` ($1.27 \times 10^9$) and `₹1,266 Mn` ($1.266 \times 10^9$) into canonical base INR units. The variance is just $0.31\%$, mathematically confirming corroboration within standard rounding tolerance to the nearest crore.

---

### Case 2: Genuine or Unreconciled Contradiction
- **Description**: Conflicting values reported for the same metric over the exact same reporting timeframe without reconciling scope or accounting context.
- **Source A**: `03-delhivery-q4-fy24-earnings-presentation.pdf` (Page 5)  
  - *Extracted Fact*: `PAT loss reduction amount | Rs. 759 Cr | FY24`
  - *Evidence Quote*: `"PAT loss reduced by Rs. 759 Cr from Rs. (1,008 Cr) in FY23"`
- **Source B**: `03-delhivery-q4-fy24-earnings-presentation.pdf` (Page 5)  
  - *Extracted Fact*: `FY24 EBITDA increase amount | Rs. 578 Cr | FY24`
  - *Evidence Quote*: `"FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr from Rs. (452 Cr) in FY23"`
- **System Reasoning**: Both statements assert full-year operating performance improvements for FY24. The reported delta of $23.8\%$ represents an unreconciled numerical conflict unless detailed sub-line item bridges are provided.

---

### Case 3: Apparent Contradiction Reconciled by Context
- **Description**: Two values appear in direct conflict at first glance, but the discrepancy is fully resolved once temporal context is isolated.
- **Source A**: `02-delhivery-annual-report-fy24-excerpt.pdf` (Page 4)  
  - *Extracted Fact*: `Delhivery Ltd | EBITDA | ₹1,266Mn | FY24`
  - *Evidence Quote*: `"₹1,266Mn EBITDA"`
- **Source B**: `03-delhivery-q4-fy24-earnings-presentation.pdf` (Page 5)  
  - *Extracted Fact*: `Delhivery Ltd | EBITDA | Rs. (452 Cr) | FY23`
  - *Evidence Quote*: `"from Rs. (452 Cr) in FY23"`
- **System Reasoning**: An uncontextualized search engine might flag $+₹1,266\text{ Mn}$ and $-₹452\text{ Cr}$ as a direct contradiction. FactLens extracts the temporal dimensions (`FY24` vs `FY23`), classifying the pair as a valid `CONTEXTUAL_DIFFERENCE` representing YoY business turnaround rather than a data conflict.

---

### Case 4: Extraction or Reasoning Failure Handled Gracefully
- **Description**: Handling ambiguous, qualitative, or unquantified textual claims without fabricating facts or relationships.
- **Source A**: `02-delhivery-annual-report-fy24-excerpt.pdf` (Page 4)  
  - *Extracted Fact*: `Express Parcel | Volume growth | "steady growth across service lines" (Normalized: None)`
  - *Evidence Quote*: `"Our steady growth across service lines, coupled with inherent operating leverage in our business"`
- **Source B**: `02-delhivery-annual-report-fy24-excerpt.pdf` (Page 4)  
  - *Extracted Fact*: `Express Parcel | Shipment Volume | 740Mn parcels | FY24`
  - *Evidence Quote*: `"740Mn Express parcels shipped"`
- **System Handling**: Fact A contains no numeric baseline or fiscal period definition. Rather than hallucinating a corroboration or guessing a growth percentage, FactLens assigns Fact A a `LOW` confidence score and flags the candidate relationship as `UNCERTAIN`, explaining the exact missing contextual signals.

---

## ⚠️ Limitations & Next Steps

### What Does Not Work Yet
- **Scanned Image OCR**: FactLens currently utilizes PyMuPDF vector text layer extraction. Scanned image-only PDFs with no embedded text require an upstream OCR engine (e.g., Tesseract or Google Cloud Vision).
- **Deeply Nested Multi-Page Tables**: Complex financial tables spanning 3+ consecutive pages without repeated table headers can occasionally fragment related row headers.
- **Candidate Pair Scaling on Very Large Corpora**: For datasets exceeding 10,000+ facts, brute-force candidate matching needs hierarchical clustering or k-means partitioning before pairwise comparison.

### What We Would Build Next
- **Asynchronous Task Queue (Celery / Redis)**: Move large batch extractions (50+ PDFs) to dedicated worker queues with live WebSocket progress feeds.
- **Visual Bounding-Box Overlay**: Render the physical PDF page directly in the browser with highlight boxes over the exact coordinates of the cited text quote.
- **Entity Knowledge Graph Visualization**: Interactive node-link graph mapping corporate subsidiaries, directors, and cross-filing metric flows.

---

## 📋 Additional Notes

- **Production Deployment**: Frontend is live on **Vercel** (`https://factlens-zeta.vercel.app/`), connected to a free **Render** FastAPI backend and **Supabase** (PostgreSQL + `pgvector` + Cloud Storage).
- **Security & Privacy**: Zero API keys, passwords, or confidential tokens are committed to this repository. All environment keys are dynamically injected via environment variables.

---

## 👥 Author
- **Developer**: Shreyes Jaiswal
- **Email**: [shreyesjaiswal7@gmail.com](mailto:shreyesjaiswal7@gmail.com)
- **GitHub**: [https://github.com/shreyes-7](https://github.com/shreyes-7)
- **Repository**: [https://github.com/shreyes-7/FactLens](https://github.com/shreyes-7/FactLens)
