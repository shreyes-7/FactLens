-- FactLens stores source material and derived representations separately so that
-- every fact and relationship remains explainable and traceable to its evidence.

create table datasets (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (name)
);

create table documents (
    id uuid primary key default gen_random_uuid(),
    dataset_id uuid not null references datasets(id) on delete cascade,
    filename text not null,
    title text,
    publisher text,
    document_type text,
    publication_date date,
    file_hash text,
    storage_path text not null,
    page_count integer check (page_count is null or page_count > 0),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (dataset_id, file_hash)
);

create table document_pages (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    pdf_page_number integer not null check (pdf_page_number > 0),
    printed_page_number text,
    text text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (document_id, pdf_page_number)
);

create table chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    page_id uuid not null references document_pages(id) on delete cascade,
    chunk_index integer not null check (chunk_index >= 0),
    text text not null,
    start_offset integer check (start_offset is null or start_offset >= 0),
    end_offset integer check (end_offset is null or end_offset >= 0),
    embedding vector(384),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (end_offset is null or start_offset is null or end_offset >= start_offset),
    unique (page_id, chunk_index)
);

create table facts (
    id uuid primary key default gen_random_uuid(),
    dataset_id uuid not null references datasets(id) on delete cascade,
    document_id uuid not null references documents(id) on delete cascade,
    subject text not null,
    predicate text not null,
    raw_claim text not null,
    value_text text,
    raw_value_text text,
    value_numeric double precision,
    value_boolean boolean,
    unit text,
    normalized_unit text,
    fact_type text not null check (fact_type in ('NUMERICAL', 'SEMANTIC', 'DERIVED')),
    period_text text,
    period_start date,
    period_end date,
    scope text,
    geography text,
    segment text,
    status text,
    attribution text,
    qualifiers jsonb not null default '{}'::jsonb,
    confidence numeric(4,3) not null check (confidence >= 0 and confidence <= 1),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (period_end is null or period_start is null or period_end >= period_start),
    check (value_text is not null or value_numeric is not null or value_boolean is not null)
);

create table evidence (
    id uuid primary key default gen_random_uuid(),
    fact_id uuid not null references facts(id) on delete cascade,
    document_id uuid not null references documents(id) on delete cascade,
    page_id uuid not null references document_pages(id) on delete restrict,
    chunk_id uuid references chunks(id) on delete set null,
    quote text not null,
    start_offset integer check (start_offset is null or start_offset >= 0),
    end_offset integer check (end_offset is null or end_offset >= 0),
    extraction_method text,
    extraction_confidence numeric(4,3) check (extraction_confidence is null or (extraction_confidence >= 0 and extraction_confidence <= 1)),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (end_offset is null or start_offset is null or end_offset >= start_offset)
);

create table processing_runs (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    status text not null check (status in ('QUEUED', 'PROCESSING', 'COMPLETED', 'PARTIAL', 'FAILED')),
    started_at timestamptz,
    completed_at timestamptz,
    pages_processed integer not null default 0 check (pages_processed >= 0),
    chunks_created integer not null default 0 check (chunks_created >= 0),
    facts_extracted integer not null default 0 check (facts_extracted >= 0),
    facts_rejected integer not null default 0 check (facts_rejected >= 0),
    relationships_found integer not null default 0 check (relationships_found >= 0),
    model text,
    prompt_version text,
    error_code text,
    error_message text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (completed_at is null or started_at is null or completed_at >= started_at)
);

create table fact_relationships (
    id uuid primary key default gen_random_uuid(),
    fact_a_id uuid not null references facts(id) on delete cascade,
    fact_b_id uuid not null references facts(id) on delete cascade,
    relationship_type text not null check (relationship_type in ('CORROBORATES', 'CONTRADICTS', 'CONTEXTUAL_DIFFERENCE', 'RELATED', 'UNCERTAIN')),
    confidence numeric(4,3) not null check (confidence >= 0 and confidence <= 1),
    reason text not null,
    contextual_factors jsonb not null default '{}'::jsonb,
    reasoning_method text,
    model text,
    prompt_version text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (fact_a_id < fact_b_id),
    unique (fact_a_id, fact_b_id)
);

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger datasets_set_updated_at
before update on datasets
for each row execute function set_updated_at();

create trigger documents_set_updated_at
before update on documents
for each row execute function set_updated_at();

create trigger facts_set_updated_at
before update on facts
for each row execute function set_updated_at();

create trigger fact_relationships_set_updated_at
before update on fact_relationships
for each row execute function set_updated_at();
