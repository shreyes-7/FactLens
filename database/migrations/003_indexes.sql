create index documents_dataset_id_idx on documents(dataset_id);
create index document_pages_document_id_idx on document_pages(document_id);
create index chunks_document_id_idx on chunks(document_id);
create index chunks_page_id_idx on chunks(page_id);
create index facts_dataset_id_idx on facts(dataset_id);
create index facts_document_id_idx on facts(document_id);
create index facts_subject_predicate_idx on facts(dataset_id, subject, predicate);
create index evidence_fact_id_idx on evidence(fact_id);
create index evidence_document_page_idx on evidence(document_id, page_id);
create index processing_runs_document_id_idx on processing_runs(document_id, created_at desc);
create index fact_relationships_fact_a_id_idx on fact_relationships(fact_a_id);
create index fact_relationships_fact_b_id_idx on fact_relationships(fact_b_id);

-- The starter dataset is small enough for exact pgvector scans. Add an HNSW
-- index only when measured query volume or latency justifies its maintenance cost.
