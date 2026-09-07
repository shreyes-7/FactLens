-- Migration 007: Add embedding column to facts table for pgvector candidate retrieval
-- Matches configured Jina AI embedding dimension (1024)

alter table public.facts
add column if not exists embedding vector(1024);

-- Comment explaining the column usage
comment on column public.facts.embedding is '1024-dimensional semantic embedding for candidate fact retrieval (jina-embeddings-v3)';

-- Index on facts(dataset_id) for rapid scoped retrieval
create index if not exists idx_facts_dataset_id on public.facts(dataset_id);
create index if not exists idx_facts_document_id on public.facts(document_id);
