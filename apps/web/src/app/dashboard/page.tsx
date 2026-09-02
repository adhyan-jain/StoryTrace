"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { listProjects, ApiError } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { DropZone } from "@/components/Upload/DropZone";

const SEVERITY_DOT: Record<ProjectSummary["severity"], string> = {
  critical: "var(--severity-critical)",
  warning: "var(--severity-warning)",
  resolved: "var(--severity-resolved)",
};

export default function DashboardPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    listProjects()
      .then(setProjects)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load projects."));
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  return (
    <div className="min-h-screen bg-[var(--bg-base)] px-8 py-10">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">My Documents</h1>
            <p className="text-[var(--text-secondary)] text-sm mt-1">{user.email}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowUpload((v) => !v)}
              className="px-4 py-2 rounded-md text-sm font-medium text-white bg-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
            >
              {showUpload ? "Cancel" : "New project"}
            </button>
            <button
              onClick={logout}
              className="px-4 py-2 rounded-md text-sm font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            >
              Log out
            </button>
          </div>
        </div>

        {showUpload && (
          <div className="mb-8 flex justify-center">
            <DropZone />
          </div>
        )}

        {error && <p className="text-sm text-[var(--severity-critical)] mb-4">{error}</p>}

        {projects === null && !error && <p className="text-[var(--text-secondary)] text-sm">Loading...</p>}

        {projects?.length === 0 && (
          <p className="text-[var(--text-secondary)] text-sm">
            No projects yet. Upload a screenplay or novel to get started.
          </p>
        )}

        <div className="flex flex-col gap-2">
          {projects?.map((p) => (
            <Link
              key={p.project_id}
              href={`/projects/${p.project_id}`}
              className="flex items-center justify-between rounded-lg border border-[var(--bg-border)] bg-[var(--bg-surface)] px-4 py-3 hover:border-[var(--accent-blue)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: SEVERITY_DOT[p.severity] }}
                />
                <div>
                  <p className="text-[var(--text-primary)] text-sm font-medium">{p.title}</p>
                  <p className="text-[var(--text-muted)] text-xs">
                    v{p.latest_version_number} &middot; {p.version_count} version{p.version_count === 1 ? "" : "s"}
                  </p>
                </div>
              </div>
              <span className="text-[var(--text-muted)] text-xs">{new Date(p.created_at).toLocaleDateString()}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
