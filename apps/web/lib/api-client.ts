export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface HealthStatus {
  status: string;
  environment: string;
  version: string;
  database?: string;
}

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  user: User;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseListResponse {
  items: KnowledgeBase[];
  total: number;
}

// Health check
export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

// Auth API calls
export async function registerUser(email: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Registration failed with status: ${response.status}`);
  }
  return response.json();
}

export async function loginUser(email: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Login failed with status: ${response.status}`);
  }
  return response.json();
}

export async function fetchCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Authentication expired or invalid: ${response.status}`);
  }
  return response.json();
}

// Knowledge Base API calls (authenticated)
export async function fetchKnowledgeBases(token: string): Promise<KnowledgeBaseListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch knowledge bases: ${response.status}`);
  }
  return response.json();
}

export async function createKnowledgeBase(
  token: string,
  data: { name: string; description?: string },
): Promise<KnowledgeBase> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create knowledge base: ${response.status}`);
  }
  return response.json();
}

export async function deleteKnowledgeBase(token: string, id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`Failed to delete knowledge base: ${response.status}`);
  }
}

// Document API types and functions
export interface DocumentItem {
  id: string;
  knowledge_base_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: "uploaded" | "processing" | "ready" | "failed";
  error_summary?: string | null;
  ingestion_version: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
}

export async function uploadDocument(
  token: string,
  kbId: string,
  file: File,
  background: boolean = true,
): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/api/v1/knowledge-bases/${kbId}/documents/upload?background=${background}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status: ${response.status}`);
  }
  return response.json();
}

export async function reindexDocument(
  token: string,
  docId: string,
  background: boolean = true,
): Promise<DocumentItem> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/documents/${docId}/reindex?background=${background}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Reindex failed with status: ${response.status}`);
  }
  return response.json();
}

export async function fetchDocuments(
  token: string,
  kbId: string,
): Promise<DocumentListResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/knowledge-bases/${kbId}/documents`,
    {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.status}`);
  }
  return response.json();
}

export async function deleteDocument(token: string, docId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/${docId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`Failed to delete document: ${response.status}`);
  }
}

export interface ChunkItem {
  id: string;
  document_id: string;
  chunk_index: number;
  text_content: string;
  page_number?: number | null;
  chunk_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ChunkListResponse {
  items: ChunkItem[];
  total: number;
}

export async function fetchDocumentChunks(
  token: string,
  docId: string,
): Promise<ChunkListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/${docId}/chunks`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch chunks: ${response.status}`);
  }
  return response.json();
}

// Milestone 6: RAG Query Types & Client Calls
export interface CitationItem {
  document_id: string;
  document_title: string;
  page_number: number | null;
  chunk_id: string;
  excerpt: string;
}

export interface RetrievalDebugInfo {
  chunks_retrieved: number;
  top_distance: number | null;
  latency_ms: number;
}

export interface QueryResponse {
  answer: string;
  citations: CitationItem[];
  retrieval_debug: RetrievalDebugInfo;
}

export async function queryKnowledgeBase(
  token: string,
  kbId: string,
  question: string,
  topK: number = 4,
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${kbId}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      top_k: topK,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Query failed with status: ${response.status}`);
  }

  return response.json();
}

// Milestone 7: Conversation & Multi-Turn Chat Types & Calls
export interface MessageItem {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: CitationItem[] | null;
  model_metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  knowledge_base_id: string;
  owner_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  knowledge_base_id: string;
  owner_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: MessageItem[];
}

export interface ConversationListResponse {
  items: ConversationSummary[];
  total: number;
}

export interface ChatTurnResponse {
  user_message: MessageItem;
  assistant_message: MessageItem;
  standalone_query?: string | null;
  retrieval_debug: RetrievalDebugInfo;
}

export async function createConversation(
  token: string,
  kbId: string,
  title?: string,
): Promise<ConversationDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${kbId}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create conversation: ${response.status}`);
  }
  return response.json();
}

export async function listConversations(
  token: string,
  kbId: string,
): Promise<ConversationListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${kbId}/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to list conversations: ${response.status}`);
  }
  return response.json();
}

export async function getConversation(
  token: string,
  conversationId: string,
): Promise<ConversationDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to get conversation: ${response.status}`);
  }
  return response.json();
}

export async function updateConversationTitle(
  token: string,
  conversationId: string,
  title: string,
): Promise<ConversationSummary> {
  const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update conversation title: ${response.status}`);
  }
  return response.json();
}

export async function deleteConversation(
  token: string,
  conversationId: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`Failed to delete conversation: ${response.status}`);
  }
}

export async function sendChatMessage(
  token: string,
  conversationId: string,
  content: string,
  topK: number = 4,
): Promise<ChatTurnResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      content,
      top_k: topK,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to send message: ${response.status}`);
  }
  return response.json();
}

// Milestone 9: Evaluation & Metrics Types & Calls
export interface EvaluationSample {
  id: string;
  question: string;
  expected_answer: string;
  ground_truth_doc_filename?: string | null;
  ground_truth_page?: number | null;
  ground_truth_keywords: string[];
}

export interface SampleEvaluationResult {
  sample_id: string;
  question: string;
  generated_answer: string;
  retrieved_chunks_count: number;
  hit_at_k: boolean;
  reciprocal_rank: number;
  citation_accuracy: number;
  faithfulness_score: number;
  answer_relevance_score: number;
  latency_ms: number;
  citations: CitationItem[];
  retrieved_sources: string[];
}

export interface EvaluationSummaryMetrics {
  total_samples: number;
  hit_rate_at_k: number;
  mrr: number;
  mean_faithfulness: number;
  mean_answer_relevance: number;
  mean_citation_accuracy: number;
  mean_latency_ms: number;
}

export interface EvaluationReportResponse {
  knowledge_base_id: string;
  top_k: number;
  metrics: EvaluationSummaryMetrics;
  results: SampleEvaluationResult[];
  created_at: string;
}

export async function runEvaluationBenchmark(
  token: string,
  kbId: string,
  topK: number = 4,
  customSamples?: EvaluationSample[],
): Promise<EvaluationReportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${kbId}/eval`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      top_k: topK,
      custom_samples: customSamples,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Evaluation failed with status: ${response.status}`);
  }
  return response.json();
}



