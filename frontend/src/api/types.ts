/**
 * TypeScript API contracts matching backend FastAPI Pydantic models.
 */

export type RelationshipType =
  | "CORROBORATES"
  | "CONTRADICTS"
  | "CONTEXTUAL_DIFFERENCE"
  | "RELATED"
  | "UNCERTAIN";

export interface HealthResponse {
  status: "ok" | "degraded" | string;
  database_connected: boolean;
  llm_provider: string;
  llm_model: string;
  fallback_enabled: boolean;
  primary_provider?: string | null;
  primary_model?: string | null;
  fallback_provider?: string | null;
  fallback_model?: string | null;
  embedding_provider: string;
  version: string;
  timestamp: string;
}

export interface DatasetResponse {
  id: string;
  name: string;
  description?: string | null;
  created_at?: string | null;
  document_count: number;
  fact_count: number;
  relationship_count: number;
}

export interface DocumentResponse {
  id: string;
  dataset_id: string;
  filename: string;
  page_count: number;
  file_size_bytes: number;
  storage_path: string;
  status: "ingested" | "processing" | "completed" | "failed" | string;
  created_at?: string | null;
}

export interface ProcessingRunItem {
  id: string;
  status: string;
  pages_processed: number;
  chunks_created: number;
  facts_extracted: number;
  facts_rejected: number;
  error_code?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface DocumentDetailResponse extends DocumentResponse {
  total_facts_extracted: number;
  total_chunks: number;
  extracted_page_numbers?: number[];
  extracted_pages_count?: number;
  processing_runs: ProcessingRunItem[];
}

export interface DocumentUploadResponse {
  document: DocumentResponse;
  pages_extracted: number;
  is_duplicate: boolean;
  message: string;
}

export interface ProcessingRequest {
  max_pages?: number | null;
  page_offset?: number;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface ProcessingResponse {
  document_id: string;
  status: string;
  chunks_created: number;
  facts_extracted: number;
  facts_rejected: number;
  message: string;
}

export interface EvidenceItem {
  id: string;
  quote: string;
  page_number: number;
  printed_page_number?: string | null;
  char_start?: number | null;
  char_end?: number | null;
  similarity_score?: number | null;
}

export interface FactWithEvidenceResponse {
  id: string;
  document_id: string;
  document_filename?: string | null;
  page_number?: number | null;
  printed_page_number?: string | null;
  entity: string;
  category: string;
  predicate: string;
  raw_value: string;
  normalized_value?: number | null;
  unit?: string | null;
  time_period?: string | null;
  scope?: string | null;
  status?: string | null;
  quote?: string | null;
  confidence_score?: number | null;
  evidence: EvidenceItem[];
  created_at?: string | null;
}

export interface FactsListResponse {
  total: number;
  limit: number;
  offset: number;
  facts: FactWithEvidenceResponse[];
}

export interface FactSummary {
  id: string;
  document_filename?: string | null;
  page_number?: number | null;
  entity: string;
  predicate: string;
  raw_value: string;
  normalized_value?: number | null;
  unit?: string | null;
  time_period?: string | null;
  scope?: string | null;
  status?: string | null;
  quote?: string | null;
}

export interface RelationshipWithDetailsResponse {
  id: string;
  fact_a_id: string;
  fact_b_id: string;
  relationship_type: RelationshipType;
  confidence: number;
  rationale: string;
  contextual_factors: Record<string, any>;
  evidence_a_quote?: string | null;
  evidence_b_quote?: string | null;
  fact_a: FactSummary;
  fact_b: FactSummary;
  created_at?: string | null;
}

export interface RelationshipsListResponse {
  total: number;
  relationships: RelationshipWithDetailsResponse[];
}

export interface CaseDemonstration {
  case_number: number;
  case_title: string;
  case_type: RelationshipType;
  description: string;
  fact_a: FactSummary;
  fact_b?: FactSummary | null;
  evidence_a?: string | null;
  evidence_b?: string | null;
  system_reasoning: string;
  contextual_factors: Record<string, any>;
}

export interface FourCasesResponse {
  title: string;
  dataset_name: string;
  cases: CaseDemonstration[];
}
