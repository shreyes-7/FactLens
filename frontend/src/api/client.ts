/**
 * FactLens API Client.
 * Connects directly to FastAPI backend without mock or fake data.
 */

import {
  HealthResponse,
  DatasetResponse,
  DocumentResponse,
  DocumentDetailResponse,
  DocumentUploadResponse,
  ProcessingRequest,
  ProcessingResponse,
  FactsListResponse,
  FactWithEvidenceResponse,
  RelationshipsListResponse,
  FourCasesResponse,
  RelationshipType,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // Non-JSON response
    }
    throw new ApiError(errorDetail, response.status);
  }

  return response.json();
}

export const api = {
  // 1. Health
  getHealth: (): Promise<HealthResponse> => request<HealthResponse>("/health"),

  // 2. Datasets
  getDatasets: (): Promise<DatasetResponse[]> => request<DatasetResponse[]>("/datasets"),
  getDataset: (id: string): Promise<DatasetResponse> => request<DatasetResponse>(`/datasets/${id}`),
  createDataset: (name: string, description?: string): Promise<DatasetResponse> =>
    request<DatasetResponse>("/datasets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    }),

  // 3. Documents
  getDocuments: (datasetId?: string): Promise<DocumentResponse[]> => {
    const query = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<DocumentResponse[]>(`/documents${query}`);
  },
  getDocumentDetail: (id: string): Promise<DocumentDetailResponse> =>
    request<DocumentDetailResponse>(`/documents/${id}`),

  uploadDocument: async (
    file: File,
    datasetId?: string,
    datasetName = "delhivery"
  ): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    if (datasetId) formData.append("dataset_id", datasetId);
    if (datasetName) formData.append("dataset_name", datasetName);

    return request<DocumentUploadResponse>("/documents/upload", {
      method: "POST",
      body: formData,
    });
  },

  processDocument: (
    id: string,
    options: ProcessingRequest = {},
    background = false
  ): Promise<ProcessingResponse> =>
    request<ProcessingResponse>(`/documents/${id}/process?background=${background}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    }),

  // 4. Facts
  getFacts: (params: {
    datasetId?: string;
    documentId?: string;
    category?: string;
    entity?: string;
    search?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<FactsListResponse> => {
    const sp = new URLSearchParams();
    if (params.datasetId) sp.set("dataset_id", params.datasetId);
    if (params.documentId) sp.set("document_id", params.documentId);
    if (params.category) sp.set("category", params.category);
    if (params.entity) sp.set("entity", params.entity);
    if (params.search) sp.set("search", params.search);
    if (params.limit !== undefined) sp.set("limit", String(params.limit));
    if (params.offset !== undefined) sp.set("offset", String(params.offset));

    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return request<FactsListResponse>(`/facts${qs}`);
  },

  getFactDetail: (id: string): Promise<FactWithEvidenceResponse> =>
    request<FactWithEvidenceResponse>(`/facts/${id}`),

  // 5. Relationships
  getRelationships: (params: {
    datasetId?: string;
    type?: RelationshipType;
    minConfidence?: number;
  } = {}): Promise<RelationshipsListResponse> => {
    const sp = new URLSearchParams();
    if (params.datasetId) sp.set("dataset_id", params.datasetId);
    if (params.type) sp.set("type", params.type);
    if (params.minConfidence) sp.set("min_confidence", String(params.minConfidence));

    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return request<RelationshipsListResponse>(`/relationships${qs}`);
  },

  triggerReasoning: (
    datasetId: string,
    topK = 5,
    minSimilarity = 0.65
  ): Promise<RelationshipsListResponse> =>
    request<RelationshipsListResponse>(
      `/relationships/reason?dataset_id=${encodeURIComponent(datasetId)}&top_k=${topK}&min_similarity=${minSimilarity}`,
      { method: "POST" }
    ),

  // 6. Core Assignment Cases
  getFourCases: (): Promise<FourCasesResponse> => request<FourCasesResponse>("/cases/four-cases"),
};
