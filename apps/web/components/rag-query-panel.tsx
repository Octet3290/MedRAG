"use client";

import { useState } from "react";
import { CitationItem, queryKnowledgeBase, QueryResponse } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

interface RagQueryPanelProps {
  kbId: string;
  kbName: string;
  documentCount: number;
}

export function RagQueryPanel({ kbId, kbName, documentCount }: RagQueryPanelProps) {
  const { token } = useAuth();
  const [question, setQuestion] = useState("");
  const [querying, setQuerying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!question.trim() || !token || querying) return;

    try {
      setQuerying(true);
      setError(null);
      setSelectedCitation(null);
      const res = await queryKnowledgeBase(token, kbId, question.trim());
      setResult(res);
      if (res.citations.length > 0) {
        setSelectedCitation(res.citations[0]);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to execute grounded query");
      }
    } finally {
      setQuerying(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Query Input Card */}
      <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm">
        <div className="mb-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Grounded AI Assistant
            </h2>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              pgvector + LLM
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Questions are answered strictly using retrieved passages from{" "}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">{kbName}</span> with
            verified citations.
          </p>
        </div>

        {documentCount === 0 && (
          <div className="mb-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 text-xs">
            ⚠️ No documents uploaded yet. Go to the <strong>Documents</strong> tab to upload clinical
            guidelines or research papers before asking questions.
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. What is the recommended first-line therapy for type 2 diabetes?"
            className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-zinc-400 text-zinc-900 dark:text-zinc-100"
          />

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-zinc-400">
              Press <kbd className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 border text-[10px] font-mono">⌘/Ctrl + Enter</kbd> to submit
            </span>

            <button
              type="submit"
              disabled={querying || !question.trim() || documentCount === 0}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm flex items-center gap-2"
            >
              {querying ? (
                <>
                  <svg
                    className="animate-spin h-3.5 w-3.5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    />
                  </svg>
                  Retrieving & Generating...
                </>
              ) : (
                "Ask Question →"
              )}
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-3 p-3 text-xs rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}
      </div>

      {/* Answer & Citations View */}
      {result && (
        <div className="flex flex-col gap-6">
          {/* Main Answer Block */}
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100 dark:border-zinc-800">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Grounded Answer
              </span>
              <div className="flex items-center gap-2 text-[11px] text-zinc-500 font-mono">
                <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
                  {result.retrieval_debug.latency_ms} ms
                </span>
                <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
                  {result.retrieval_debug.chunks_retrieved} chunks retrieved
                </span>
                {result.retrieval_debug.top_distance !== null && (
                  <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
                    dist: {result.retrieval_debug.top_distance.toFixed(4)}
                  </span>
                )}
              </div>
            </div>

            <div className="text-sm leading-relaxed text-zinc-900 dark:text-zinc-100 whitespace-pre-wrap">
              {result.answer}
            </div>

            {/* Verified Citations List */}
            {result.citations.length > 0 ? (
              <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800 flex flex-col gap-2">
                <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Verified Citations ({result.citations.length}):
                </span>
                <div className="flex flex-wrap gap-2">
                  {result.citations.map((cit, idx) => {
                    const isSelected = selectedCitation?.chunk_id === cit.chunk_id;
                    return (
                      <button
                        key={idx}
                        onClick={() => setSelectedCitation(cit)}
                        className={`px-3 py-1.5 text-xs rounded-lg border font-mono transition-all text-left flex items-center gap-2 ${
                          isSelected
                            ? "bg-indigo-600 border-indigo-600 text-white shadow-sm"
                            : "bg-zinc-50 dark:bg-zinc-800/60 border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 hover:border-indigo-400"
                        }`}
                      >
                        <span className="font-semibold">
                          📄 {cit.document_title}
                        </span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            isSelected
                              ? "bg-indigo-700 text-indigo-100"
                              : "bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300"
                          }`}
                        >
                          Page {cit.page_number ?? "N/A"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 text-xs text-zinc-400 italic">
                No citations cited by the model for this answer.
              </div>
            )}
          </div>

          {/* Selected Citation Excerpt Drawer */}
          {selectedCitation && (
            <div className="p-5 rounded-xl border border-indigo-200 dark:border-indigo-900 bg-indigo-50/40 dark:bg-indigo-950/20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-indigo-800 dark:text-indigo-300 flex items-center gap-1.5">
                  🔍 Evidence Passage for Citation:{" "}
                  <span className="font-mono font-normal">
                    {selectedCitation.document_title} (Page {selectedCitation.page_number ?? "N/A"})
                  </span>
                </span>
                <span className="text-[10px] text-zinc-400 font-mono">
                  Chunk ID: {selectedCitation.chunk_id.slice(0, 8)}...
                </span>
              </div>
              <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed bg-white dark:bg-zinc-900 p-3 rounded-lg border border-indigo-100 dark:border-indigo-900 font-mono">
                {selectedCitation.excerpt}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
