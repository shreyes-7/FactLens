-- FactLens migration: Update vector dimensions from 384 to 1024
-- to support Jina AI hosted embeddings (jina-embeddings-v3).

alter table public.chunks alter column embedding type vector(1024);
