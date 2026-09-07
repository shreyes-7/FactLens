# Database Schema

The PostgreSQL schema is defined exclusively through the ordered SQL migrations in `database/migrations/`.

`datasets` isolate independent knowledge layers. Their documents retain page-level source material in `document_pages`, which is chunked in `chunks`. Extracted claims are held in generic `facts` rows, with one or more exact source records in `evidence`. `fact_relationships` preserves both facts and records the reason they were connected; it never overwrites disagreement. `processing_runs` captures the state and counts for each document-processing attempt.

The `chunks.embedding` column uses `vector(384)`, matching the configured local embedding model. pgvector is strictly for candidate retrieval; final fact relationships require structured comparison and evidence.
