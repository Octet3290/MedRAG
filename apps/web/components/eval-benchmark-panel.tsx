"use client";

import { useState } from "react";
import {
  EvaluationReportResponse,
  runEvaluationBenchmark,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

interface EvalBenchmarkPanelProps {
  kbId: string;
  kbName: string;
  documentCount: number;
}

export function EvalBenchmarkPanel({
  kbId,
  kbName,
  documentCount,
}: EvalBenchmarkPanelProps) {
  const { token } = useAuth();
  const [topK, setTopK] = useState<number>(4);
  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<EvaluationReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSampleId, setExpandedSampleId] = useState<string | null>(null);

  const handleRunBenchmark = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const res = await runEvaluationBenchmark(token, kbId, topK);
      setReport(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Benchmark evaluation failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const getMetricBadge = (score: number) => {
    if (score >= 0.8) {
      return (
        <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900">
          Excellent
        </span>
      );
    }
    if (score >= 0.5) {
      return (
        <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900">
          Acceptable
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900">
        Needs Review
      </span>
    );
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Banner / Explanation Header */}
      <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🧪</span>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              RAG Evaluation & Precision/Recall Benchmark
            </h3>
          </div>
          <p className="text-xs text-zinc-500 mt-1 max-w-2xl leading-relaxed">
            Quantitatively measure retrieval accuracy (Hit Rate @ K, MRR) and generation quality
            (Faithfulness, Relevance, Citation Accuracy) across {kbName}.
          </p>
        </div>

        {/* Top-K Selector & Action */}
        <div className="flex items-center gap-3 self-start md:self-auto">
          <div className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
            <label htmlFor="topk-select" className="font-medium">
              Top-K:
            </label>
            <select
              id="topk-select"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={loading}
              className="px-2 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 text-xs font-semibold text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value={3}>3 Chunks</option>
              <option value={4}>4 Chunks</option>
              <option value={5}>5 Chunks</option>
              <option value={8}>8 Chunks</option>
            </select>
          </div>

          <button
            onClick={handleRunBenchmark}
            disabled={loading || documentCount === 0}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50 disabled:pointer-events-none"
          >
            {loading ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Evaluating RAG Pipeline...</span>
              </>
            ) : (
              <>
                <span>▶</span>
                <span>Run Evaluation Benchmark</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-400">
          <strong>Evaluation Error:</strong> {error}
        </div>
      )}

      {documentCount === 0 && (
        <div className="p-8 text-center rounded-xl border border-dashed border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900">
          <div className="text-3xl mb-2">📄</div>
          <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            No Documents Indexed Yet
          </h4>
          <p className="text-xs text-zinc-500 mt-1">
            Please upload clinical documents in the Documents tab before executing benchmarks.
          </p>
        </div>
      )}

      {/* When Report is Generated */}
      {report && (
        <>
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Hit Rate @ K */}
            <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-medium text-zinc-500">Hit Rate @ {report.top_k}</span>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {(report.metrics.hit_rate_at_k * 100).toFixed(0)}%
                </div>
              </div>
              <div className="mt-3">{getMetricBadge(report.metrics.hit_rate_at_k)}</div>
            </div>

            {/* Mean Reciprocal Rank */}
            <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-medium text-zinc-500">MRR (Ranking Quality)</span>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {report.metrics.mrr.toFixed(3)}
                </div>
              </div>
              <div className="mt-3">{getMetricBadge(report.metrics.mrr)}</div>
            </div>

            {/* Faithfulness */}
            <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-medium text-zinc-500">Faithfulness (Grounded)</span>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {(report.metrics.mean_faithfulness * 100).toFixed(0)}%
                </div>
              </div>
              <div className="mt-3">{getMetricBadge(report.metrics.mean_faithfulness)}</div>
            </div>

            {/* Answer Relevance */}
            <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-medium text-zinc-500">Answer Relevance</span>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {(report.metrics.mean_answer_relevance * 100).toFixed(0)}%
                </div>
              </div>
              <div className="mt-3">{getMetricBadge(report.metrics.mean_answer_relevance)}</div>
            </div>

            {/* Citation Accuracy */}
            <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-medium text-zinc-500">Citation Accuracy</span>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {(report.metrics.mean_citation_accuracy * 100).toFixed(0)}%
                </div>
              </div>
              <div className="mt-3">{getMetricBadge(report.metrics.mean_citation_accuracy)}</div>
            </div>

            {/* Mean Latency */}
            <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-medium text-zinc-500">Avg Latency</span>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {report.metrics.mean_latency_ms.toFixed(0)} ms
                </div>
              </div>
              <div className="mt-3">
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 font-mono">
                  {report.metrics.total_samples} samples
                </span>
              </div>
            </div>
          </div>

          {/* Test Case Inspector */}
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Sample Evaluation Breakdown ({report.results.length} Test Queries)
              </h4>
              <span className="text-xs text-zinc-500">
                Ran at {new Date(report.created_at).toLocaleTimeString()}
              </span>
            </div>

            <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {report.results.map((res) => {
                const isExpanded = expandedSampleId === res.sample_id;
                return (
                  <div key={res.sample_id} className="py-4 first:pt-0 last:pb-0 flex flex-col gap-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex flex-col gap-1.5 flex-1">
                        <div className="flex items-center gap-2">
                          {res.hit_at_k ? (
                            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900">
                              ✓ HIT (Rank #{res.reciprocal_rank > 0 ? Math.round(1 / res.reciprocal_rank) : 1})
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900">
                              ✕ MISS
                            </span>
                          )}

                          <span className="text-xs font-mono text-zinc-400">
                            [{res.sample_id}]
                          </span>
                        </div>

                        <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                          {res.question}
                        </p>
                      </div>

                      {/* Pill Scores */}
                      <div className="flex items-center gap-2 text-[11px] font-mono shrink-0">
                        <span className="px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                          Faithful: {(res.faithfulness_score * 100).toFixed(0)}%
                        </span>
                        <span className="px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                          {res.latency_ms} ms
                        </span>
                        <button
                          onClick={() => setExpandedSampleId(isExpanded ? null : res.sample_id)}
                          className="px-2.5 py-1 text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                        >
                          {isExpanded ? "Hide Details ▲" : "Inspect ▼"}
                        </button>
                      </div>
                    </div>

                    {/* Expandable Details */}
                    {isExpanded && (
                      <div className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700/60 flex flex-col gap-3 text-xs">
                        <div>
                          <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                            Generated Response:
                          </span>
                          <p className="mt-1 text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap leading-relaxed">
                            {res.generated_answer}
                          </p>
                        </div>

                        {res.citations.length > 0 && (
                          <div>
                            <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                              Verified Citations ({res.citations.length}):
                            </span>
                            <div className="flex flex-wrap gap-2 mt-1">
                              {res.citations.map((c, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
                                >
                                  {c.document_title}:p{c.page_number || 1}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {res.retrieved_sources.length > 0 && (
                          <div>
                            <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                              Retrieved Sources (in top-{report.top_k}):
                            </span>
                            <div className="flex flex-wrap gap-1.5 mt-1">
                              {res.retrieved_sources.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-200/80 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300"
                                >
                                  #{idx + 1} {s}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
