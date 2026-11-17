"use client";

import { useState } from "react";
import { AuthModal } from "@/components/auth-modal";
import { HealthBadge } from "@/components/health-badge";
import { KnowledgeBaseManager } from "@/components/knowledge-base-manager";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, logout } = useAuth();
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/70 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm tracking-wider shadow-sm">
              MR
            </div>
            <div>
              <span className="font-semibold text-base tracking-tight">MedRAG</span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-mono">
                v0.7.0-milestone7
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <HealthBadge />

            {user ? (
              <div className="flex items-center gap-3 pl-3 border-l border-zinc-200 dark:border-zinc-800">
                <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                  {user.email}
                </span>
                <button
                  onClick={logout}
                  className="px-3 py-1 text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 rounded-md border border-zinc-200 dark:border-zinc-800 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsAuthOpen(true)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm"
              >
                Sign In / Register
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col gap-10">
        {/* Hero Section */}
        <div className="flex flex-col gap-3 max-w-2xl">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Production AI Knowledge Assistant
          </h1>
          <p className="text-base text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Upload documents, index structured chunks in PostgreSQL with pgvector, and ask
            evidence-grounded questions with verifiable citations and source page numbers.
          </p>
        </div>

        {/* Milestone Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: API & Security */}
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider mb-2">
                FastAPI & Auth
              </div>
              <h2 className="text-lg font-semibold mb-1">JWT & IDOR Protection</h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                Bcrypt password derivation, signed JWT Bearer tokens, and strict resource-level
                ownership checks on every API route.
              </p>
            </div>
            <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
              <span>Security</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400">Authenticated</span>
            </div>
          </div>

          {/* Card 2: Database */}
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-2">
                Vector Storage
              </div>
              <h2 className="text-lg font-semibold mb-1">Neon + pgvector 0.8.6</h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                Relational multi-tenant tables with foreign key cascades and vector similarity
                indexes.
              </p>
            </div>
            <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
              <span>Neon Cloud</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400">Live</span>
            </div>
          </div>

          {/* Card 3: RAG Engine */}
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider mb-2">
                Ingestion & RAG
              </div>
              <h2 className="text-lg font-semibold mb-1">Grounded RAG Pipeline</h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                Document file upload (PDF/TXT), chunking with overlap, vector embeddings, and
                evidence citation validation.
              </p>
            </div>
            <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
              <span>Milestones 4-6</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400">Live & Verified</span>
            </div>
          </div>
        </div>

        {/* Live Knowledge Base Manager Section */}
        <section>
          <div className="mb-4">
            <h2 className="text-xl font-bold tracking-tight">Your Knowledge Bases</h2>
            <p className="text-xs text-zinc-500">
              Manage your private document collections isolated by user account.
            </p>
          </div>
          <KnowledgeBaseManager onOpenAuth={() => setIsAuthOpen(true)} />
        </section>
      </main>

      {/* Auth Modal */}
      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />

      {/* Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 py-6 text-center text-xs text-zinc-500">
        MedRAG Engineering Project • Built for Production & Technical Rigor
      </footer>
    </div>
  );
}
