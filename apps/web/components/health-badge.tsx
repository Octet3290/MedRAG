"use client";

import { useEffect, useState } from "react";
import { fetchHealth, HealthStatus } from "@/lib/api-client";

export function HealthBadge() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const checkHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to connect to API backend");
      }
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  if (loading) {
    return (
      <span className="inline-flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-full bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        Checking API Health...
      </span>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3">
        <span className="inline-flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-full bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          Backend Offline ({error})
        </span>
        <button
          onClick={checkHealth}
          className="text-xs text-zinc-500 hover:text-zinc-800 underline dark:text-zinc-400"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="inline-flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        API Online (v{health?.version} • {health?.environment})
      </span>
      <button
        onClick={checkHealth}
        className="text-xs text-zinc-500 hover:text-zinc-800 underline dark:text-zinc-400"
      >
        Refresh
      </button>
    </div>
  );
}
