"use client";

import { useEffect, useState } from "react";
import { getVersionDiff, ApiError } from "@/lib/api";
import { DiffStatusBadge } from "@/components/ui/SeverityBadge";
import type { VersionDiffResponse } from "@/lib/types";

export function VersionDiffTab({ projectId, versionNumber }: { projectId: string; versionNumber: number }) {
  const [diff, setDiff] = useState<VersionDiffResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getVersionDiff(projectId, versionNumber)
      .then(setDiff)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load version diff."));
  }, [projectId, versionNumber]);

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--severity-critical)]">{error}</p>
      </div>
    );
  }

  if (!diff) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">Loading comparison...</p>
      </div>
    );
  }

  if (!diff.has_previous) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">
          This is the first version of this project -- nothing to compare against yet.
        </p>
      </div>
    );
  }

  const recurring = diff.conflicts.filter((c) => c.diff_status === "recurring");
  const fresh = diff.conflicts.filter((c) => c.diff_status === "new");
  const resolved = diff.conflicts.filter((c) => c.diff_status === "resolved_in_version");

  if (diff.conflicts.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">
          No continuity issues in either this version or the one before it.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-4">
      {resolved.length > 0 && (
        <p className="text-xs text-[var(--text-muted)]">
          &quot;No longer detected&quot; means the detector no longer flags this transition in the new draft -- not
          verified proof the gap was intentionally fixed.
        </p>
      )}

      {[
        { items: fresh, title: "New" },
        { items: recurring, title: "Still an issue" },
        { items: resolved, title: "No longer detected" },
      ].map(
        ({ items, title }) =>
          items.length > 0 && (
            <div key={title} className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                {title} ({items.length})
              </p>
              {items.map((c) => (
                <div
                  key={c.id}
                  className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-elevated)] p-3 flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-[var(--text-primary)]">
                      {c.entity_name} &middot; {c.attribute}
                    </span>
                    <DiffStatusBadge status={c.diff_status} />
                  </div>
                  <p className="text-xs text-[var(--text-secondary)]">{c.description}</p>
                </div>
              ))}
            </div>
          ),
      )}
    </div>
  );
}
