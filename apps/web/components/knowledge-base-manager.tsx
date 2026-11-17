"use client";

import { useEffect, useState } from "react";
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  fetchKnowledgeBases,
  KnowledgeBase,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { DocumentManager } from "@/components/document-manager";

interface KnowledgeBaseManagerProps {
  onOpenAuth: () => void;
}

export function KnowledgeBaseManager({ onOpenAuth }: KnowledgeBaseManagerProps) {
  const { user, token } = useAuth();
  const [items, setItems] = useState<KnowledgeBase[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Selected KB for document management
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);

  // Form states
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");

  const loadData = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetchKnowledgeBases(token);
      setItems(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to load knowledge bases");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadData();
    } else {
      setItems([]);
      setTotal(0);
      setSelectedKb(null);
    }
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !token) return;

    try {
      setSubmitting(true);
      setError(null);
      await createKnowledgeBase(token, {
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setName("");
      setDescription("");
      await loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to create knowledge base");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this knowledge base?") || !token) return;

    try {
      setError(null);
      await deleteKnowledgeBase(token, id);
      if (selectedKb?.id === id) {
        setSelectedKb(null);
      }
      await loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to delete knowledge base");
      }
    }
  };

  if (!user || !token) {
    return (
      <div className="p-8 rounded-xl border border-dashed border-zinc-300 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50 text-center flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 flex items-center justify-center font-bold text-lg">
          🔒
        </div>
        <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          Authentication Required
        </h3>
        <p className="text-xs text-zinc-500 max-w-sm">
          Knowledge bases and indexed documents are private to each user. Sign in to your account
          to view or create knowledge bases.
        </p>
        <button
          onClick={onOpenAuth}
          className="mt-2 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm"
        >
          Sign In / Create Account
        </button>
      </div>
    );
  }

  // If a Knowledge Base is selected, show its DocumentManager view
  if (selectedKb) {
    return (
      <DocumentManager
        kbId={selectedKb.id}
        kbName={selectedKb.name}
        onBack={() => setSelectedKb(null)}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Creation Form */}
      <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
          Create Knowledge Base
        </h2>
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="kb-name"
              className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1"
            >
              Knowledge Base Name *
            </label>
            <input
              id="kb-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Clinical Pharmacology Reports"
              className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label
              htmlFor="kb-desc"
              className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1"
            >
              Description (Optional)
            </label>
            <textarea
              id="kb-desc"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief summary of document topics or research scope..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            {error && (
              <span className="text-xs text-rose-600 dark:text-rose-400">{error}</span>
            )}
            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="ml-auto px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              {submitting ? "Creating..." : "Create Knowledge Base"}
            </button>
          </div>
        </form>
      </div>

      {/* List of Knowledge Bases */}
      <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Your Knowledge Bases
            </h2>
            <p className="text-xs text-zinc-500">
              Scoped to {user.email} (Total: {total})
            </p>
          </div>
          <button
            onClick={loadData}
            className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 underline font-medium"
          >
            Refresh List
          </button>
        </div>

        {loading ? (
          <div className="py-8 text-center text-xs text-zinc-500 animate-pulse">
            Loading your knowledge bases from Neon database...
          </div>
        ) : items.length === 0 ? (
          <div className="py-8 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-lg">
            <p className="text-xs text-zinc-500">
              No knowledge bases created yet. Use the form above to add your first knowledge base!
            </p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {items.map((item) => (
              <div
                key={item.id}
                className="py-4 flex items-start justify-between gap-4 first:pt-0 last:pb-0"
              >
                <div className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {item.name}
                  </span>
                  {item.description && (
                    <span className="text-xs text-zinc-500 dark:text-zinc-400">
                      {item.description}
                    </span>
                  )}
                  <span className="text-[10px] text-zinc-400 font-mono mt-1">
                    ID: {item.id} • Created: {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedKb(item)}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950/40 dark:text-indigo-300 dark:hover:bg-indigo-900/50 transition-colors"
                  >
                    Manage Documents →
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
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
    </div>
  );
}
