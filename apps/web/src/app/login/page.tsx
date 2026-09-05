"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-[var(--bg-base)]">
      <div className="hidden md:flex md:w-[42%] bg-[var(--text-primary)] relative flex-col justify-between p-10 lg:p-14 overflow-hidden">
        <span className="ghost-index absolute -bottom-16 -left-10 text-[22rem] select-none" style={{ color: "var(--bg-elevated)", opacity: 0.08 }} aria-hidden="true">
          02
        </span>
        <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.2em] uppercase text-[var(--bg-elevated)] relative">
          Case File / Re-entry
        </p>
        <h2 className="font-[family-name:var(--font-heading)] uppercase text-6xl lg:text-7xl leading-[0.86] text-[var(--bg-elevated)] relative">
          Every
          <br />
          Gap
          <br />
          Found.
        </h2>
        <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-wide text-[var(--bg-surface)] relative max-w-xs">
          StoryTrace cross-examines a manuscript against itself, unit by unit, and keeps the receipts.
        </p>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <h1 className="font-[family-name:var(--font-heading)] uppercase text-2xl text-[var(--text-primary)] mb-8 md:hidden">
            StoryTrace
          </h1>
          <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.2em] uppercase text-[var(--text-secondary)] mb-1">
            Reopen a Case
          </p>
          <h1 className="font-[family-name:var(--font-heading)] uppercase text-3xl text-[var(--text-primary)] mb-8 hidden md:block">
            Log In
          </h1>

          <form onSubmit={handleSubmit} className="flex flex-col gap-1">
            <div className="flex flex-col gap-1.5 py-2.5 border-b-2 border-[var(--bg-border)] focus-within:border-[var(--accent-blue)]">
              <label className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.14em] text-[var(--text-secondary)]" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-transparent text-[15px] text-[var(--text-primary)] outline-none"
              />
            </div>
            <div className="flex flex-col gap-1.5 py-2.5 border-b-2 border-[var(--bg-border)] focus-within:border-[var(--accent-blue)]">
              <label className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.14em] text-[var(--text-secondary)]" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-transparent text-[15px] text-[var(--text-primary)] outline-none"
              />
            </div>

            {error && (
              <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--severity-critical)] mt-3 border border-[var(--severity-critical)] px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="stamp !text-sm justify-center mt-6 bg-[var(--accent-blue)] px-3 py-3.5 text-[var(--accent-blue-contrast)] border-[var(--accent-blue)] disabled:opacity-50 cursor-pointer"
            >
              {submitting ? "Entering…" : "Enter →"}
            </button>
          </form>

          <p className="mt-6 font-[family-name:var(--font-mono)] text-xs tracking-wide text-[var(--text-secondary)]">
            NO ACCOUNT?{" "}
            <Link href="/signup" className="text-[var(--text-primary)] underline underline-offset-2">
              SIGN UP
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
