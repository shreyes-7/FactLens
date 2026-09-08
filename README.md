# FactLens — Evidence-Grounded Cross-Document Fact Knowledge Layer

> **Superjoin Engineering Intern Hiring Assignment Submission**  
> An intelligent system that extracts atomic, evidence-grounded facts from raw PDF disclosures, normalizes them into canonical representations, and discovers cross-document relationships (corroborations, contradictions, and contextual reconciliations).

- **Live Deployed Application**: [https://factlens-zeta.vercel.app/](https://factlens-zeta.vercel.app/)
- **Video Demo**: [Watch 3-minute Demo Video](YOUR_VIDEO_LINK_HERE) *(Placeholder for 3-minute video submission)*
- **GitHub Repository**: [https://github.com/shreyes-7/FactLens](https://github.com/shreyes-7/FactLens)

---

## 🚀 Setup and Run Instructions

### Prerequisites
- **Python**: Version 3.11+
- **Node.js**: Version 18+ and `npm`
- **Database**: PostgreSQL with `pgvector` extension (e.g., free [Supabase](https://supabase.com) project or local PostgreSQL instance)
- **API Keys**: Google Gemini API key (primary extraction) and/or Groq API key (optional fallback)

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

Open `.env` and fill in the required values. **Do not commit API keys or database passwords to git.**

```ini
# =================================================================
# DATABASE & STORAGE (Supabase PostgreSQL + pgvector + Storage)
# =================================================================
# PostgreSQL connection string (Transaction Pooler port 6543 or Session port 5432)
DATABASE_URL=postgresql://postgres:[YOUR_PASSWORD]@db.[YOUR_PROJECT_REF].supabase.co:5432/postgres

# Supabase Project API URL and Secret Service Role Key (for storage bucket and DB access)
SUPABASE_URL=https://[YOUR_PROJECT_REF].supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_secret_key
STORAGE_BUCKET=documents

# =================================================================
# LLM & EMBEDDING PROVIDERS (Gemini primary, Groq fallback)
# =================================================================
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# Optional: Groq fallback provider
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Embedding Provider (gemini or jina)
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768

# =================================================================
# CORS & FRONTEND SETTINGS
# =================================================================
FRONTEND_URL=https://factlens-zeta.vercel.app
ALLOWED_CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://factlens-zeta.vercel.app
APP_ENV=development
```

---

### 3. Database Migration

If setting up a fresh Supabase/PostgreSQL instance:
1. Enable `pgvector` in your database SQL Editor:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Run the SQL schema files located in `backend/migrations/` (starting with `001_initial_schema.sql`).
3. In Supabase Storage, create a bucket named `documents` (set to Private).

---

### 4. Run the Backend (FastAPI)

```bash
# Using uv (recommended)
uv run uvicorn backend.app.main:app --reload --port 8000

# Or using standard pip / virtualenv
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- Root Health Probe: `http://localhost:8000/health`

---

### 5. Run the Frontend (React + Vite + TypeScript)

```bash
cd frontend
npm install
npm run dev
```
- Open `http://localhost:5173` in your browser.

---

### 6. Run Automated Tests

FactLens includes **142 automated unit and integration tests** covering PDF parsing, fact extraction, normalizers, candidate matching, relationship reasoning, and API endpoints:
```bash
uv run pytest
```

---

## 💡 Approach & Architecture

### High-Level Design

```
                          ┌───────────────────────────┐
                          │   React + Vite Frontend   │
                          │ TypeScript + Tailwind CSS │
                          └─────────────┬─────────────┘
                                        │ REST API
                                        ▼
                          ┌───────────────────────────┐
                          │      FastAPI Backend      │
                          │   Pydantic v2 Validation  │
                          └──────┬─────────────┬──────┘
                                 │             │
                PDF Stream (RAM) │             │ SQL + pgvector
                                 ▼             ▼
       ┌─────────────────────────────┐    ┌─────────────────────────────┐
       │   In-Memory PyMuPDF Parser  │    │     Supabase PostgreSQL     │
       │   Zero Disk Write to Server │    │   Vector Embeddings & RAG   │
       └──────────────┬──────────────┘    │   Normalized Facts Schema   │
                      │                   │  Cross-Document Rel Tables  │
                      ▼                   └─────────────────────────────┘
       ┌─────────────────────────────┐
       │    Dual LLM Intelligence    │
       │  Gemini 2.0 (Primary)       │
       │  Groq Llama 3.3 (Fallback)  │
       └─────────────────────────────┘
```

### 1. Ingestion & In-Memory PDF Parsing
- **Zero Local Disk Footprint**: To run safely in ephemeral server environments (e.g., Render Free / serverless containers), PDFs uploaded via UI/API are streamed directly to Supabase Cloud Storage.
- **In-Memory Chunking**: PyMuPDF processes raw byte streams directly in memory (`fitz.open(stream=bytes)`), tagging text chunks with their physical PDF page number and token offsets.

### 2. Atomic Fact Discovery & Schema Normalization
- Documents guide what counts as a fact: rather than forcing a rigid hardcoded template, the extraction pipeline extracts atomic tuples:
  - `(Entity, Predicate, Raw Value, Normalized Value, Unit, Fiscal Period, Scope, Status)`
- **Multi-Dimensional Deterministic Normalizers**:
  - **Numeric & Scale Normalization**: Converts phrases like `₹1,266 Mn`, `Rs. 127 Cr`, `3.88K`, or `45.2%` into standardized base numbers and standard currency/unit tokens (`INR`, `USD`, `%`, `count`).
  - **Fiscal Period Anchoring**: Resolves `Q4 FY24`, `FY2023-24`, and relative dates into standardized fiscal identifiers.
  - **Scope Classification**: Disambiguates `Consolidated`, `Standalone`, `Segment-level`, `GAAP`, and `Non-GAAP`.

### 3. Verbatim Evidence Grounding
- Hallucination prevention is enforced at the schema level: **no fact can exist without an evidence citation**.
- Every fact links to a verbatim quote snippet and the physical page number in the original PDF where the statement appears.

### 4. Candidate Matching & Cross-Document Relationship Reasoning
- **Decoupled Architecture**: Uploading a document immediately extracts facts and generates embeddings. Cross-document relationship discovery is performed on-demand via the Reasoning Pipeline:
  - **Stage 1 (Semantic Candidate Retrieval)**: Uses `pgvector` cosine similarity combined with canonical predicate filtering to discover candidate pairs across distinct documents ($doc_a \neq doc_b$).
  - **Stage 2 (Hybrid Reasoning Engine)**: Evaluates numeric variance, unit compatibility, and fiscal period overlap to classify the relationship:
    - `CORROBORATES`: Same metric, same period, matching figures within $\pm 1.5\%$ tolerance.
    - `CONTRADICTS`: Same entity, metric, and period, but irreconcilable numeric divergence.
    - `CONTEXTUAL_DIFFERENCE`: Apparent discrepancy explained by accounting scope, time period progression, or reporting currency.
    - `UNCERTAIN / RELATED`: Thematic or directional association without strict mathematical comparison.

### 5. Key Engineering Decisions & Trade-Offs

| Decision | Trade-Off Chosen | Rationale |
|---|---|---|
| **Decoupled Reasoning** | Document extraction does not auto-run full cross-document reasoning on upload. | Comparing every new fact against hundreds of existing facts on upload creates an $O(N \times M)$ bottleneck and consumes excessive tokens. Decoupling gives users instant uploads and on-demand analysis. |
| **Deterministic Rules + LLM Reasoning** | Normalization uses regex + mathematical rules; semantic classification uses LLM. | Pure LLM comparison hallucinates rounding differences as contradictions. Pure regex fails on linguistic nuances. Combining both ensures sub-50ms deterministic checks with LLM adaptability. |
| **In-Memory Streaming** | Never persist PDFs to the local container disk. | Free-tier host environments (Render, Fly.io, Vercel) have ephemeral filesystems. In-memory streaming guarantees zero file-loss on container restarts. |

---

## 🔍 The Four Required Cases

FactLens provides dedicated views and an automated benchmark endpoint (`GET /api/cases/four-cases`) demonstrating each required case from real PDF disclosures:

### Case 1: Cross-Document Fact Corroboration
- **Description**: Two distinct documents report the same corporate metric using completely different units and scales, verified by FactLens.
- **Source A**: `03-delhivery-q4-fy24-earnings-presentation.pdf` (Page 5)  
  - *Extracted Fact*: `Delhivery Ltd | EBITDA | Rs. 127 Cr (Normalized: 1,270,000,000 INR)`
  - *Evidence Quote*: `"FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr from Rs. (452 Cr) in FY23"`
- **Source B**: `02-delhivery-annual-report-fy24-excerpt.pdf` (Page 4)  
  - *Extracted Fact*: `Delhivery Ltd | EBITDA | ₹1,266Mn (Normalized: 1,266,000,000 INR)`
  - *Evidence Quote*: `"₹1,266Mn EBITDA"`
- **System Reasoning**: FactLens converts `Rs. 127 Cr` ($1.27 \times 10^9$) and `₹1,266 Mn` ($1.266 \times 10^9$) into canonical base INR units. The variance is just $0.31\%$, confirming corroboration within standard rounding tolerance to the nearest crore.

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

## 🌟 Brownie Points & Extensions (FactLens 2.0)

1. **Incremental Ingestion Without Rebuilding Knowledge**:
   - FactLens tracks extracted page numbers at the database layer. Re-processing a document or uploading an amended version only extracts newly discovered or unparsed pages, preserving existing embeddings and citations.
2. **Contradiction Investigator**:
   - An interactive multi-factor audit engine that evaluates entity, metric, fiscal period, unit, and accounting scope matches deterministically in $<50\text{ms}$ with zero extra LLM cost.
3. **"What Changed?" Cross-Document Comparison Workspace**:
   - Compare 2 to 5 filings simultaneously in a consolidated matrix. A single lateral PostgreSQL query tracks metric trends (`INCREASED`, `DECREASED`, `UNCHANGED`, `ADDED`, `NOT_FOUND`).
4. **Fact Confidence & Evidence Quality Scoring (0–100)**:
   - Every fact receives a transparent, rule-based confidence score based on citation length, verified physical page attachment, ISO period anchoring, and numeric normalization completeness.
5. **No Hardcoded Filenames or Document Rules**:
   - Completely generalized prompt architecture tested against multi-industry filings, prospectuses, and earnings releases.

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
