"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { uploadDocument, ApiError } from "@/lib/api";

const ACCEPTED_EXTENSIONS = [".pdf", ".epub", ".fountain", ".txt"];

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isAccepted(filename: string): boolean {
  const lower = filename.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function DocumentIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="1.5">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <path d="M9 13h6M9 17h6M9 9h1" />
    </svg>
  );
}

interface DropZoneProps {
  /** When set, the upload becomes a new version of this project instead of
   * a new project -- used by the "Upload new version" flow on a project's
   * page. Navigates to /projects/[id] afterward instead of /analyze/[id]
   * so the new version shows up in the version list. */
  projectId?: string;
  onUploaded?: (result: { story_universe_id: string; project_id: string }) => void;
}

export function DropZone({ projectId, onUploaded }: DropZoneProps = {}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleFile = useCallback((candidate: File) => {
    if (!isAccepted(candidate.name)) {
      setError("Unsupported file type. Please upload a PDF, EPUB, Fountain, or plain text file.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(candidate);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) handleFile(dropped);
    },
    [handleFile],
  );

  const handleStart = useCallback(async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadDocument(file, projectId);
      if (onUploaded) {
        onUploaded(result);
      } else if (projectId) {
        router.push(`/projects/${projectId}`);
      } else {
        localStorage.setItem("storytrace_active_id", result.story_universe_id);
        router.push(`/analyze/${result.story_universe_id}`);
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.status === 0
            ? "Upload failed. Check that the backend is running on port 8000."
            : err.message
          : "Upload failed. Check that the backend is running on port 8000.";
      setError(message);
      setUploading(false);
    }
  }, [file, router]);

  return (
    <div className="flex flex-col items-center gap-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={clsx(
          "w-[600px] h-[320px] rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-3 transition-colors bg-[var(--bg-elevated)]",
          dragActive ? "border-[var(--accent-blue)]" : "border-[var(--bg-border)]",
        )}
      >
        {!file ? (
          <>
            <DocumentIcon />
            <p className="text-[var(--text-primary)] text-sm">Drop your screenplay or novel here</p>
            <p className="text-[var(--text-secondary)] text-xs">PDF, EPUB, Fountain (.fountain), or plain text (.txt)</p>
            <button
              onClick={() => inputRef.current?.click()}
              className="mt-2 px-4 py-2 rounded-md text-sm font-medium text-white bg-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer"
            >
              Browse files
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              className="hidden"
              onChange={(e) => {
                const selected = e.target.files?.[0];
                if (selected) handleFile(selected);
              }}
            />
          </>
        ) : (
          <>
            <DocumentIcon />
            <p className="text-[var(--text-primary)] text-sm font-medium">{file.name}</p>
            <p className="text-[var(--text-secondary)] text-xs">{formatSize(file.size)}</p>
            <div className="flex gap-2 mt-2">
              <button
                onClick={() => setFile(null)}
                disabled={uploading}
                className="px-4 py-2 rounded-md text-sm font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] transition-colors cursor-pointer disabled:opacity-50"
              >
                Change file
              </button>
              <button
                onClick={handleStart}
                disabled={uploading}
                className="px-4 py-2 rounded-md text-sm font-medium text-white bg-[var(--accent-blue)] hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
              >
                {uploading ? "Starting..." : "Start Analysis"}
              </button>
            </div>
          </>
        )}
      </div>
      {error && <p className="text-[var(--severity-critical)] text-sm max-w-[600px] text-center">{error}</p>}
      {file && !error && (
        <p className="text-[var(--text-muted)] text-xs max-w-[600px] text-center">
          Full analysis typically takes 3–8 minutes for a feature-length screenplay (longer for a full novel) — the
          agent reads every scene, then investigates each conflict it flags. It's safe to navigate away; processing
          continues in the background and you can check back on this project's page.
        </p>
      )}
    </div>
  );
}
