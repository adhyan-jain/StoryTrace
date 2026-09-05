"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { listVersions, ApiError } from "@/lib/api";
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
          {versions?.map((v) => (
            <Link
              key={v.story_universe_id}
              href={`/analyze/${v.story_universe_id}?project=${projectId}&version=${v.version_number}`}
              className="flex items-center gap-5 border-b border-[var(--bg-border)] py-5 hover:bg-[var(--bg-elevated)] transition-colors"
            >
              <span className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--text-muted)] w-7 shrink-0">
                {String(v.version_number).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-[family-name:var(--font-display)] font-semibold text-lg text-[var(--text-primary)]">
                  Version {v.version_number}
                </p>
                <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide text-[var(--text-secondary)] truncate">
                  {v.document_title}
                </p>
              </div>
              <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-muted)] shrink-0 hidden sm:block">
                {new Date(v.created_at).toLocaleString()}
              </span>
              <span className="font-[family-name:var(--font-mono)] text-sm w-8 h-8 border border-[var(--bg-border)] flex items-center justify-center text-[var(--text-primary)] shrink-0">
                &rarr;
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
