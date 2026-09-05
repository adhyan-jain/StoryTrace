"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";
import { FileText, Pencil, Trash2, Check, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { listProjects, renameProject, deleteProject, ApiError } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { DropZone } from "@/components/Upload/DropZone";
import { ListSkeleton } from "@/components/ui/Skeleton";

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
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  function refresh() {
    listProjects()
      .then(setProjects)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load projects."));
  }

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, router]);

  function startRename(p: ProjectSummary) {
    setRenamingId(p.project_id);
    setRenameValue(p.title);
    setTimeout(() => renameInputRef.current?.select(), 0);
  }

  async function commitRename(projectId: string) {
    const title = renameValue.trim();
    setRenamingId(null);
    const previous = projects;
    if (!title || !previous) return;
    setProjects(previous.map((p) => (p.project_id === projectId ? { ...p, title } : p)));
    try {
      await renameProject(projectId, title);
    } catch (err) {
      setProjects(previous);
      setError(err instanceof ApiError ? err.message : "Could not rename project.");
    }
  }

  async function handleDelete(p: ProjectSummary) {
    if (!confirm(`Delete "${p.title}"? This removes all of its versions and findings permanently.`)) return;
    setDeletingId(p.project_id);
    const previous = projects;
    setProjects((cur) => cur?.filter((x) => x.project_id !== p.project_id) ?? cur);
    try {
      await deleteProject(p.project_id);
    } catch (err) {
      setProjects(previous ?? null);
      setError(err instanceof ApiError ? err.message : "Could not delete project.");
    } finally {
      setDeletingId(null);
    }
  }

  if (authLoading || !user) return null;

  return (
    <div className="min-h-screen bg-[var(--bg-base)] px-4 py-8 sm:px-8 sm:py-10">
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">My Documents</h1>
            <p className="text-[var(--text-secondary)] text-sm mt-1 break-all">{user.email}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowUpload((v) => !v)}
              className="flex-1 sm:flex-none px-4 py-2 rounded-md text-sm font-medium text-white bg-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
            >
              {showUpload ? "Cancel" : "New project"}
            </button>
            <button
              onClick={logout}
              className="flex-1 sm:flex-none px-4 py-2 rounded-md text-sm font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
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

        {projects === null && !error && <ListSkeleton rows={3} />}

        {projects?.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-[var(--bg-border)] px-6 py-16 text-center">
            <FileText className="w-8 h-8 text-[var(--text-muted)]" strokeWidth={1.5} />
            <p className="text-[var(--text-primary)] text-sm font-medium">No projects yet</p>
            <p className="text-[var(--text-secondary)] text-sm max-w-xs">
              Upload a screenplay or novel to run its first continuity check.
            </p>
            {!showUpload && (
              <button
                onClick={() => setShowUpload(true)}
                className="mt-1 px-4 py-2 rounded-md text-sm font-medium text-white bg-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
              >
                New project
              </button>
            )}
          </div>
        )}

        <div className="flex flex-col gap-2">
          {projects?.map((p) => {
            const isRenaming = renamingId === p.project_id;
            const isDeleting = deletingId === p.project_id;
            return (
              <div
                key={p.project_id}
                className={clsx(
                  "flex items-center justify-between gap-3 rounded-lg border border-[var(--bg-border)] bg-[var(--bg-surface)] px-4 py-3 transition-colors",
                  !isRenaming && "hover:border-[var(--accent-blue)]",
                  isDeleting && "opacity-50 pointer-events-none",
                )}
              >
                <Link
                  href={isRenaming ? "#" : `/projects/${p.project_id}`}
                  onClick={(e) => isRenaming && e.preventDefault()}
                  className="flex items-center gap-3 min-w-0 flex-1"
                >
                  <span
                    title={`${p.severity === "critical" ? "Verified conflicts found" : p.severity === "warning" ? "Unresolved / uncertain conflicts" : "No open conflicts"}`}
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: SEVERITY_DOT[p.severity] }}
                  />
                  <div className="min-w-0 flex-1">
                    {isRenaming ? (
                      <input
                        ref={renameInputRef}
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onClick={(e) => e.preventDefault()}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") commitRename(p.project_id);
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        className="w-full max-w-xs bg-[var(--bg-base)] border border-[var(--accent-blue)] rounded px-2 py-0.5 text-sm text-[var(--text-primary)] outline-none"
                      />
                    ) : (
                      <p className="text-[var(--text-primary)] text-sm font-medium truncate">{p.title}</p>
                    )}
                    <p className="text-[var(--text-muted)] text-xs">
                      v{p.latest_version_number} &middot; {p.version_count} version{p.version_count === 1 ? "" : "s"}
                    </p>
                  </div>
                </Link>
                <span className="text-[var(--text-muted)] text-xs shrink-0 hidden sm:block">
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
                <div className="flex items-center gap-1 shrink-0">
                  {isRenaming ? (
                    <>
                      <button
                        onClick={() => commitRename(p.project_id)}
                        title="Save"
                        className="p-1.5 rounded text-[var(--severity-resolved)] hover:bg-[var(--bg-base)] cursor-pointer"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setRenamingId(null)}
                        title="Cancel"
                        className="p-1.5 rounded text-[var(--text-secondary)] hover:bg-[var(--bg-base)] cursor-pointer"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => startRename(p)}
                        title="Rename project"
                        className="p-1.5 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-base)] cursor-pointer"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(p)}
                        title="Delete project"
                        className="p-1.5 rounded text-[var(--text-secondary)] hover:text-[var(--severity-critical)] hover:bg-[var(--bg-base)] cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
