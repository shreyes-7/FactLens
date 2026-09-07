# Database Schema

The PostgreSQL schema is defined exclusively through the ordered SQL migrations in `database/migrations/`.

`datasets` isolate independent knowledge layers. Their documents retain page-level source material in `document_pages`, which is chunked in `chunks`. Extracted claims are held in generic `facts` rows, with one or more exact source records in `evidence`. `fact_relationships` preserves both facts and records the reason they were connected; it never overwrites disagreement. `processing_runs` captures the state and counts for each document-processing attempt.

The `chunks.embedding` column uses `vector(1024)`, matching the configured Jina AI embedding model (`jina-embeddings-v3`). pgvector is strictly for candidate retrieval; final fact relationships require structured comparison and evidence.

Facts preserve raw values alongside normalized representations (`facts.normalized_value_numeric`, `facts.normalized_unit`, `facts.period_start`, `facts.period_end`) allowing mathematical comparison across heterogeneous reporting scales (e.g. Crore, Lakh, Million). In addition, `facts.embedding` holds a 1024-dimensional vector (`vector(1024)`) computed via Jina AI for candidate fact pairing and semantic retrieval.

