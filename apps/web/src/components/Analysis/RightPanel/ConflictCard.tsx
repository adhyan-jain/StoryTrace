"use client";

import { SeverityBadge, StatusBadge, severityColor } from "@/components/ui/SeverityBadge";
import type { ConflictWithVerdict } from "@/lib/types";

export function ConflictCard({
  conflict,
  onClick,
}: {
  conflict: ConflictWithVerdict;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-[var(--bg-elevated)] border border-[var(--bg-border)] overflow-hidden cursor-pointer hover:border-[var(--text-muted)] transition-colors"
      style={{ borderLeft: `3px solid ${severityColor(conflict.severity)}` }}
    >
      <div className="p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          {conflict.severity ? (
            <SeverityBadge severity={conflict.severity} />
          ) : (
            <span className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-[0.1em]">
              pending
            </span>
          )}
          <StatusBadge status={conflict.status} />
        </div>
        <p className="font-[family-name:var(--font-display)] font-semibold text-sm text-[var(--text-primary)]">
          {conflict.entity_name} <span className="font-normal text-[var(--text-secondary)]">· {conflict.attribute}</span>
        </p>
        <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
          Unit {conflict.prior_unit_id.split("_").pop()} &rarr; Unit {conflict.current_unit_id.split("_").pop()}
        </p>
        <div className="flex flex-col gap-1.5">
          <p className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--text-secondary)] truncate border-l border-[var(--bg-border)] pl-2">
            PRIOR: {conflict.prior_excerpt}
          </p>
          <p className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--text-secondary)] truncate border-l border-[var(--bg-border)] pl-2">
            CURRENT: {conflict.current_excerpt}
          </p>
        </div>
      </div>
    </button>
  );
}
