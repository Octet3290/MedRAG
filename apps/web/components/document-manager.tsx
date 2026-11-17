"use client";

import { useEffect, useRef, useState } from "react";
import {
  ChunkItem,
  deleteDocument,
  DocumentItem,
  fetchDocumentChunks,
  fetchDocuments,
  reindexDocument,
  uploadDocument,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { RagQueryPanel } from "@/components/rag-query-panel";
import { ChatInterface } from "@/components/chat-interface";
import { EvalBenchmarkPanel } from "@/components/eval-benchmark-panel";

interface DocumentManagerProps {
  kbId: string;
  kbName: string;
  onBack: () => void;
}

export function DocumentManager({ kbId, kbName, onBack }: DocumentManagerProps) {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<"documents" | "query" | "chat" | "eval">("documents");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [reindexingId, setReindexingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Chunk inspection state
  const [selectedDocForChunks, setSelectedDocForChunks] = useState<DocumentItem | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [loadingChunks, setLoadingChunks] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocuments = async (silent: boolean = false) => {
    if (!token) return;
    try {
      if (!silent) setLoading(true);
      setError(null);
      const res = await fetchDocuments(token, kbId);
      setDocuments(res.items);
    } catch (err: unknown) {
      if (!silent) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load documents");
        }
      }
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [kbId, token]);

  // Milestone 8: Polling effect for in-flight ingestion background jobs
  useEffect(() => {
    const hasPending = documents.some(
      (doc) => doc.status === "processing" || doc.status === "uploaded"
    );
    if (!hasPending || !token) return;

    const intervalId = setInterval(() => {
      loadDocuments(true);
    }, 2500);

    return () => clearInterval(intervalId);
  }, [documents, token, kbId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    if (file.size > 10 * 1024 * 1024) {
      setError("File exceeds 10 MB limit. Please select a smaller document.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    try {
      setUploading(true);
      setError(null);
      // Upload with background=true: returns immediately with status='processing'
      const newDoc = await uploadDocument(token, kbId, file, true);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setDocuments((prev) => [newDoc, ...prev]);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Upload failed");
      }
    } finally {
      setUploading(false);
    }
  };

  const handleReindex = async (docId: string) => {
    if (!token) return;
    try {
      setReindexingId(docId);
      setError(null);
      const updated = await reindexDocument(token, docId, true);
      setDocuments((prev) =>
        prev.map((d) => (d.id === docId ? updated : d))
      );
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Reindex failed");
      }
    } finally {
      setReindexingId(null);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document?") || !token) return;

    try {
      setError(null);
      await deleteDocument(token, docId);
      if (selectedDocForChunks?.id === docId) {
        setSelectedDocForChunks(null);
      }
      await loadDocuments();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to delete document");
      }
    }
  };

  const handleInspectChunks = async (doc: DocumentItem) => {
    if (!token) return;
    setSelectedDocForChunks(doc);
    setLoadingChunks(true);
    try {
      const res = await fetchDocumentChunks(token, doc.id);
      setChunks(res.items);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setLoadingChunks(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Navigation header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-zinc-200 dark:border-zinc-800 gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="text-xs px-2.5 py-1 rounded bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors font-medium"
          >
            ← Back to Knowledge Bases
          </button>
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            {kbName}
          </h2>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab("documents")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === "documents"
                ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            }`}
          >
            📄 Documents ({documents.length})
          </button>
          <button
            onClick={() => setActiveTab("query")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === "query"
                ? "bg-white dark:bg-zinc-900 text-indigo-600 dark:text-indigo-400 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            }`}
          >
            <span>⚡ Quick Query</span>
          </button>
          <button
            onClick={() => setActiveTab("chat")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === "chat"
                ? "bg-white dark:bg-zinc-900 text-indigo-600 dark:text-indigo-400 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            }`}
          >
            <span>💬 Chat Assistant</span>
            {documents.length > 0 && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("eval")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === "eval"
                ? "bg-white dark:bg-zinc-900 text-indigo-600 dark:text-indigo-400 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            }`}
          >
            <span>🧪 Evaluation & Metrics</span>
          </button>
        </div>
      </div>

      {activeTab === "eval" ? (
        <EvalBenchmarkPanel kbId={kbId} kbName={kbName} documentCount={documents.length} />
      ) : activeTab === "chat" ? (
        <ChatInterface kbId={kbId} kbName={kbName} documentCount={documents.length} />
      ) : activeTab === "query" ? (
        <RagQueryPanel kbId={kbId} kbName={kbName} documentCount={documents.length} />
      ) : (
        <>
          {/* Upload Zone */}
      <div className="p-6 rounded-xl border border-dashed border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 flex flex-col items-center justify-center gap-3 text-center">
        <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 flex items-center justify-center font-bold text-lg">
          📄
        </div>
        <div>
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Upload Document (PDF or TXT)
          </h3>
          <p className="text-xs text-zinc-500 mt-1">
            Automatic text chunking (500 tokens) • Overlap preserved • Indexed in pgvector
          </p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          onChange={handleFileUpload}
          disabled={uploading}
          className="hidden"
          id="doc-upload-input"
        />

        <label
          htmlFor="doc-upload-input"
          className={`cursor-pointer px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm ${
            uploading ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          {uploading ? "Extracting & Embedding..." : "Select Document to Upload"}
        </label>

        {error && (
          <div className="p-3 w-full max-w-md rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-400">
            {error}
          </div>
        )}
      </div>

      {/* Document List */}
      <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
          Indexed Documents ({documents.length})
        </h3>

        {loading ? (
          <div className="py-8 text-center text-xs text-zinc-500 animate-pulse">
            Loading documents...
          </div>
        ) : documents.length === 0 ? (
          <div className="py-8 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-lg">
            <p className="text-xs text-zinc-500">
              No documents in this knowledge base yet. Upload a PDF or TXT file above!
            </p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="py-4 flex items-center justify-between gap-4 first:pt-0 last:pb-0"
              >
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                      {doc.original_filename}
                    </span>
                    {doc.status === "ready" && (
                      <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900 flex items-center gap-1">
                        <span>✓</span>
                        <span>Ready & Indexed</span>
                      </span>
                    )}
                    {doc.status === "failed" && (
                      <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900 flex items-center gap-1">
                        <span>⚠</span>
                        <span>Ingestion Failed</span>
                      </span>
                    )}
                    {(doc.status === "uploaded" || doc.status === "processing") && (
                      <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900 flex items-center gap-1.5 animate-pulse">
                        <svg className="w-2.5 h-2.5 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                        </svg>
                        <span>Extracting & Indexing...</span>
                      </span>
                    )}
                  </div>

                  <div className="text-[11px] text-zinc-500 flex items-center gap-3">
                    <span>{doc.mime_type}</span>
                    <span>•</span>
                    <span>{formatFileSize(doc.file_size_bytes)}</span>
                    <span>•</span>
                    <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>

                  {doc.error_summary && (
                    <div className="p-2 rounded bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 text-[11px] text-rose-700 dark:text-rose-400 font-mono mt-1">
                      <strong>Worker Error:</strong> {doc.error_summary}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {doc.status === "ready" && (
                    <>
                      <button
                        onClick={() => handleInspectChunks(doc)}
                        className="px-2.5 py-1 text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 rounded border border-indigo-200 dark:border-indigo-800 transition-colors font-medium"
                      >
                        View Chunks
                      </button>
                      <button
                        onClick={() => handleReindex(doc.id)}
                        disabled={reindexingId === doc.id}
                        className="px-2.5 py-1 text-xs text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded border border-zinc-200 dark:border-zinc-700 transition-colors font-medium disabled:opacity-50"
                      >
                        {reindexingId === doc.id ? "Reindexing..." : "Reindex"}
                      </button>
                    </>
                  )}
                  {doc.status === "failed" && (
                    <button
                      onClick={() => handleReindex(doc.id)}
                      disabled={reindexingId === doc.id}
                      className="px-2.5 py-1 text-xs text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30 rounded border border-amber-300 dark:border-amber-800 transition-colors font-medium disabled:opacity-50"
                    >
                      {reindexingId === doc.id ? "Retrying..." : "Retry Ingestion"}
                    </button>
                  )}
                  {(doc.status === "uploaded" || doc.status === "processing") && (
                    <span className="px-2.5 py-1 text-xs text-amber-600 dark:text-amber-400 font-medium animate-pulse">
                      In Queue...
                    </span>
                  )}
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="px-2.5 py-1 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded border border-rose-200 dark:border-rose-900 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chunks Inspection Drawer/Modal */}
      {selectedDocForChunks && (
        <div className="p-6 rounded-xl border border-indigo-200 dark:border-indigo-900 bg-indigo-50/20 dark:bg-indigo-950/20">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Vector Chunks for: {selectedDocForChunks.original_filename}
              </h4>
              <p className="text-xs text-zinc-500">
                Total chunks in pgvector: {chunks.length}
              </p>
            </div>
            <button
              onClick={() => setSelectedDocForChunks(null)}
              className="text-xs text-zinc-500 hover:text-zinc-800 dark:text-zinc-400"
            >
              Close Chunks Panel ✕
            </button>
          </div>

          {loadingChunks ? (
            <div className="py-6 text-center text-xs text-zinc-500 animate-pulse">
              Loading vector chunks...
            </div>
          ) : chunks.length === 0 ? (
            <p className="text-xs text-zinc-500">No chunks found for this document.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {chunks.map((c) => (
                <div
                  key={c.id}
                  className="p-4 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono border-b border-zinc-100 dark:border-zinc-800 pb-1">
                    <span>Chunk #{c.chunk_index}</span>
                    {c.page_number && <span>Page {c.page_number}</span>}
                  </div>
                  <p className="text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed line-clamp-6">
                    {c.text_content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
        </>
      )}
    </div>
  );
}
