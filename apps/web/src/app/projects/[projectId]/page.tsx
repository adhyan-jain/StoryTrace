"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { History } from "lucide-react";
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
    <div className="min-h-screen bg-[var(--bg-base)] px-4 py-8 sm:px-8 sm:py-10">
      <div className="max-w-4xl mx-auto">
        <Link href="/dashboard" className="text-sm text-[var(--accent-blue)]">
          &larr; My Documents
        </Link>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mt-4 mb-8">
          <h1 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">Versions</h1>
          <button
            onClick={() => setShowUpload((v) => !v)}
            className="px-4 py-2 rounded-md text-sm font-medium text-white bg-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
          >
            {showUpload ? "Cancel" : "Upload new version"}
          </button>
        </div>

        {showUpload && (
          <div className="mb-8 flex justify-center">
            <DropZone projectId={projectId} onUploaded={() => { setShowUpload(false); refresh(); }} />
          </div>
        )}

        {error && <p className="text-sm text-[var(--severity-critical)] mb-4">{error}</p>}
        {versions === null && !error && <ListSkeleton rows={2} />}

        {versions?.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-[var(--bg-border)] px-6 py-16 text-center">
            <History className="w-8 h-8 text-[var(--text-muted)]" strokeWidth={1.5} />
            <p className="text-[var(--text-primary)] text-sm font-medium">No versions yet</p>
            <p className="text-[var(--text-secondary)] text-sm max-w-xs">
              Upload a document to create the first version of this project.
            </p>
          </div>
        )}

        <div className="flex flex-col gap-2">
          {versions?.map((v) => (
            <Link
              key={v.story_universe_id}
              href={`/analyze/${v.story_universe_id}?project=${projectId}&version=${v.version_number}`}
              className="flex items-center justify-between gap-3 rounded-lg border border-[var(--bg-border)] bg-[var(--bg-surface)] px-4 py-3 hover:border-[var(--accent-blue)] transition-colors"
            >
              <div className="min-w-0">
                <p className="text-[var(--text-primary)] text-sm font-medium">Version {v.version_number}</p>
                <p className="text-[var(--text-muted)] text-xs truncate">{v.document_title}</p>
              </div>
              <span className="text-[var(--text-muted)] text-xs shrink-0 hidden sm:block">
                {new Date(v.created_at).toLocaleString()}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
