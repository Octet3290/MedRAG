"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Authentication failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex border-b border-zinc-200 dark:border-zinc-800">
          <button
            type="button"
            onClick={() => {
              setMode("login");
              setError(null);
            }}
            className={`flex-1 py-3 text-sm font-semibold transition-colors ${
              mode === "login"
                ? "border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-zinc-50/50 dark:bg-zinc-800/30"
                : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("register");
              setError(null);
            }}
            className={`flex-1 py-3 text-sm font-semibold transition-colors ${
              mode === "register"
                ? "border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-zinc-50/50 dark:bg-zinc-800/30"
                : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-400">
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="auth-email"
              className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1"
            >
              Email Address
            </label>
            <input
              id="auth-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. researcher@hospital.org"
              className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label
              htmlFor="auth-pass"
              className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1"
            >
              Password {mode === "register" && "(Min. 8 characters)"}
            </label>
            <input
              id="auth-pass"
              type="password"
              required
              minLength={mode === "register" ? 8 : 1}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={onClose}
              className="text-xs text-zinc-500 hover:text-zinc-800 dark:text-zinc-400"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !email.trim() || !password.trim()}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              {submitting
                ? "Processing..."
                : mode === "login"
                ? "Sign In"
                : "Register Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
