"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Pencil, Check, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { listVersions, renameProjectVersion, ApiError } from "@/lib/api";
import type { ProjectVersion } from "@/lib/types";
import { DropZone } from "@/components/Upload/DropZone";
import { ListSkeleton } from "@/components/ui/Skeleton";

export default function ProjectPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [versions, setVersions] = useState<ProjectVersion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [renamingVersion, setRenamingVersion] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

  function refresh() {
    listVersions(projectId)
      .then(setVersions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load versions."));
  }

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, projectId]);

  function startRename(v: ProjectVersion) {
    setRenamingVersion(v.version_number);
    setRenameValue(v.document_title);
    setTimeout(() => renameInputRef.current?.select(), 0);
  }

  async function commitRename(versionNumber: number) {
    const title = renameValue.trim();
    setRenamingVersion(null);
    const previous = versions;
    if (!title || !previous) return;
    setVersions(previous.map((v) => (v.version_number === versionNumber ? { ...v, document_title: title } : v)));
    try {
      await renameProjectVersion(projectId, versionNumber, title);
    } catch (err) {
      setVersions(previous);
      setError(err instanceof ApiError ? err.message : "Could not rename version.");
    }
  }

  if (authLoading || !user) return null;

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <div className="grain-surface border-b-2 border-[var(--bg-border)] relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-8 py-10 sm:px-14 relative">
          <span
            className="ghost-index absolute -top-8 right-2 sm:right-6 text-[8rem] sm:text-[10rem] select-none"
            aria-hidden="true"
          >
            {String(versions?.length ?? 0).padStart(2, "0")}
          </span>

          <Link
            href="/dashboard"
            className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-[var(--accent-blue)] hover:underline"
          >
            &larr; Case Log
          </Link>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mt-4 relative">
            <h1 className="font-[family-name:var(--font-heading)] uppercase text-5xl sm:text-6xl leading-[0.85] tracking-tight text-[var(--text-primary)]">
              Version
              <br />
              History
            </h1>
            <button
              onClick={() => setShowUpload((v) => !v)}
              className="stamp !text-[13px] px-5 py-2.5 shrink-0 text-[var(--accent-blue-contrast)] bg-[var(--accent-blue)] border-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
            >
              {showUpload ? "Cancel" : "+ Upload New Version"}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-8 py-10 sm:px-14">
        {showUpload && (
          <div className="mb-10 flex justify-center">
            <DropZone projectId={projectId} onUploaded={() => { setShowUpload(false); refresh(); }} />
          </div>
        )}

        {error && (
          <p className="font-[family-name:var(--font-mono)] text-sm text-[var(--severity-critical)] mb-4 border border-[var(--severity-critical)] px-3 py-2 inline-block">
            {error}
          </p>
        )}
        {versions === null && !error && <ListSkeleton rows={2} />}

        {versions?.length === 0 && (
          <div className="flex flex-col items-center gap-3 border-2 border-dashed border-[var(--bg-border)] px-6 py-20 text-center">
            <p className="font-[family-name:var(--font-heading)] uppercase text-2xl text-[var(--text-primary)]">
              No versions yet
            </p>
            <p className="text-[var(--text-secondary)] text-sm max-w-xs">
              Upload a document to create the first version of this project.
            </p>
          </div>
        )}

        <div className="flex flex-col border-t-2 border-[var(--bg-border)]">
          {versions?.map((v) => {
            const isRenaming = renamingVersion === v.version_number;
            return (
              <div
                key={v.story_universe_id}
                className="flex items-center gap-5 border-b border-[var(--bg-border)] py-5 hover:bg-[var(--bg-elevated)] transition-colors"
              >
                <span className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--text-muted)] w-7 shrink-0">
                  {String(v.version_number).padStart(2, "0")}
                </span>
                <Link
                  href={isRenaming ? "#" : `/analyze/${v.story_universe_id}?project=${projectId}&version=${v.version_number}`}
                  onClick={(e) => isRenaming && e.preventDefault()}
                  className="min-w-0 flex-1"
                >
                  <p className="font-[family-name:var(--font-display)] font-semibold text-lg text-[var(--text-primary)]">
                    Version {v.version_number}
                  </p>
                  {isRenaming ? (
                    <input
                      ref={renameInputRef}
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onClick={(e) => e.preventDefault()}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitRename(v.version_number);
                        if (e.key === "Escape") setRenamingVersion(null);
                      }}
                      className="mt-0.5 w-full max-w-xs bg-[var(--bg-elevated)] border border-[var(--accent-blue)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide text-[var(--text-primary)] outline-none"
                    />
                  ) : (
                    <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide text-[var(--text-secondary)] truncate">
                      {v.document_title}
                    </p>
                  )}
                </Link>
                <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-muted)] shrink-0 hidden sm:block">
                  {new Date(v.created_at).toLocaleString()}
                </span>
                <div className="flex items-center gap-1 shrink-0">
                  {isRenaming ? (
                    <>
                      <button
                        onClick={() => commitRename(v.version_number)}
                        title="Save"
                        className="p-1.5 text-[var(--severity-resolved)] hover:bg-[var(--bg-surface)] cursor-pointer"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setRenamingVersion(null)}
                        title="Cancel"
                        className="p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] cursor-pointer"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => startRename(v)}
                      title="Rename version"
                      className="p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] cursor-pointer"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                  )}
                  <Link
                    href={`/analyze/${v.story_universe_id}?project=${projectId}&version=${v.version_number}`}
                    title="Open version"
                    className="font-[family-name:var(--font-mono)] text-sm w-8 h-8 border border-[var(--bg-border)] flex items-center justify-center text-[var(--text-primary)] hover:border-[var(--accent-blue)] hover:text-[var(--accent-blue)] transition-colors shrink-0"
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
