"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";
import { Pencil, Trash2, Check, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { listProjects, renameProject, deleteProject, ApiError } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { DropZone } from "@/components/Upload/DropZone";
import { ListSkeleton } from "@/components/ui/Skeleton";

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

  const openCount = projects?.filter((p) => p.severity !== "resolved").length ?? 0;

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <div className="grain-surface border-b-2 border-[var(--bg-border)] relative overflow-hidden">
        <div className="max-w-6xl mx-auto px-5 py-10 sm:px-10 sm:py-14 relative">
          <span
            className="ghost-index absolute -top-6 right-4 sm:right-10 text-[9rem] sm:text-[13rem] select-none"
            aria-hidden="true"
          >
            {String(projects?.length ?? 0).padStart(2, "0")}
          </span>

          <div className="flex items-baseline justify-between gap-4 mb-8 relative">
            <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.2em] uppercase text-[var(--accent-blue)]">
              StoryTrace &mdash; Case Log
            </p>
            <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-wide text-[var(--text-secondary)] break-all text-right hidden sm:block">
              {user.email}
            </p>
          </div>

          <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between relative">
            <h1 className="font-[family-name:var(--font-heading)] uppercase text-[13vw] leading-[0.82] sm:text-[5.5rem] tracking-[-0.01em] text-[var(--text-primary)] max-w-2xl">
              Open
              <br />
              Files
            </h1>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => setShowUpload((v) => !v)}
                className="stamp !text-[13px] px-5 py-2.5 text-[var(--accent-blue-contrast)] bg-[var(--accent-blue)] border-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
              >
                {showUpload ? "Cancel" : "+ New Document"}
              </button>
              <button
                onClick={logout}
                className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide px-4 py-2.5 text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
              >
                Log out
              </button>
            </div>
          </div>

          <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-wide text-[var(--text-secondary)] mt-6 border-t border-[var(--rule-hair)] pt-3">
            {projects === null ? "Loading docket…" : `${projects.length} document${projects.length === 1 ? "" : "s"} on file · ${openCount} awaiting review`}
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-5 py-10 sm:px-10">

        {showUpload && (
          <div className="mb-10 flex justify-center">
            <DropZone />
          </div>
        )}

        {error && (
          <p className="font-[family-name:var(--font-mono)] text-sm text-[var(--severity-critical)] mb-4 border border-[var(--severity-critical)] px-3 py-2 inline-block">
            {error}
          </p>
        )}

        {projects === null && !error && <ListSkeleton rows={3} />}

        {projects?.length === 0 && (
          <div className="flex flex-col items-center gap-3 border-2 border-dashed border-[var(--bg-border)] px-6 py-20 text-center">
            <p className="font-[family-name:var(--font-heading)] uppercase text-2xl text-[var(--text-primary)]">
              No open files
            </p>
            <p className="text-[var(--text-secondary)] text-sm max-w-xs">
              Upload a screenplay or novel to open its first case file.
            </p>
            {!showUpload && (
              <button
                onClick={() => setShowUpload(true)}
                className="stamp !text-[13px] mt-2 px-5 py-3 text-[var(--accent-blue-contrast)] bg-[var(--accent-blue)] border-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
              >
                + New Document
              </button>
            )}
          </div>
        )}

        <div className="flex flex-col border-t-2 border-[var(--bg-border)]">
          {projects?.map((p, i) => {
            const isRenaming = renamingId === p.project_id;
            const isDeleting = deletingId === p.project_id;
            const statusLabel =
              p.severity === "critical" ? "REVIEW" : p.severity === "warning" ? "REVIEW" : "CLEAR";
            return (
              <div
                key={p.project_id}
                className={clsx(
                  "group flex items-center gap-5 border-b border-[var(--bg-border)] py-5 transition-colors hover:bg-[var(--bg-elevated)]",
                  isDeleting && "opacity-50 pointer-events-none",
                )}
              >
                <span className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--text-muted)] w-7 shrink-0">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <Link
                  href={isRenaming ? "#" : `/projects/${p.project_id}`}
                  onClick={(e) => isRenaming && e.preventDefault()}
                  className="flex items-baseline gap-4 min-w-0 flex-1"
                >
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
                        className="w-full max-w-xs bg-[var(--bg-elevated)] border border-[var(--accent-blue)] px-2 py-0.5 text-lg font-[family-name:var(--font-display)] font-semibold text-[var(--text-primary)] outline-none"
                      />
                    ) : (
                      <p className="font-[family-name:var(--font-display)] font-semibold text-lg sm:text-xl text-[var(--text-primary)] truncate">
                        {p.title}
                      </p>
                    )}
                  </div>
                  <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-wide text-[var(--text-secondary)] shrink-0 hidden sm:block uppercase">
                    v{p.latest_version_number} &middot; {p.version_count} version{p.version_count === 1 ? "" : "s"}
                  </p>
                </Link>
                <span
                  title={`${p.severity === "critical" ? "Verified conflicts found" : p.severity === "warning" ? "Unresolved / uncertain conflicts" : "No open conflicts"}`}
                  className={clsx(
                    "stamp !text-[10px] shrink-0 hidden sm:inline-flex",
                    p.severity === "resolved"
                      ? "text-[var(--severity-resolved)]"
                      : "text-[var(--severity-critical)]",
                  )}
                >
                  {statusLabel}
                </span>
                <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-muted)] shrink-0 hidden sm:block">
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
                <div className="flex items-center gap-1 shrink-0">
                  {isRenaming ? (
                    <>
                      <button
                        onClick={() => commitRename(p.project_id)}
                        title="Save"
                        className="p-1.5 text-[var(--severity-resolved)] hover:bg-[var(--bg-surface)] cursor-pointer"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setRenamingId(null)}
                        title="Cancel"
                        className="p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] cursor-pointer"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => startRename(p)}
                        title="Rename project"
                        className="p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] cursor-pointer"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(p)}
                        title="Delete project"
                        className="p-1.5 text-[var(--text-secondary)] hover:text-[var(--severity-critical)] hover:bg-[var(--bg-surface)] cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                  <Link
                    href={`/projects/${p.project_id}`}
                    title="Open project"
                    className="font-[family-name:var(--font-mono)] text-sm w-8 h-8 border border-[var(--bg-border)] flex items-center justify-center text-[var(--text-primary)] hover:border-[var(--accent-blue)] hover:text-[var(--accent-blue)] transition-colors ml-1"
                  >
                    &rarr;
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
