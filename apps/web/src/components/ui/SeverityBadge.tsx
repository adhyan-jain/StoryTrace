import type { DiffStatus, Severity, VerdictStatus } from "@/lib/types";

const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "var(--severity-critical)",
  warning: "var(--severity-warning)",
  info: "var(--severity-info)",
};

const STATUS_COLOR: Record<VerdictStatus, string> = {
  verified: "var(--severity-critical)",
  resolved: "var(--severity-resolved)",
  uncertain: "var(--severity-uncertain)",
  intentional: "var(--severity-info)",
  uninvestigated: "var(--text-muted)",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
      style={{ color: SEVERITY_COLOR[severity], backgroundColor: `color-mix(in srgb, ${SEVERITY_COLOR[severity]} 15%, transparent)` }}
    >
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: VerdictStatus }) {
  return (
    <span
      className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded border"
      style={{ color: STATUS_COLOR[status], borderColor: `color-mix(in srgb, ${STATUS_COLOR[status]} 40%, transparent)` }}
    >
      {status}
    </span>
  );
}

export function severityColor(severity: Severity | null | undefined): string {
  if (!severity) return "var(--accent-blue)";
  return SEVERITY_COLOR[severity];
}

// Cross-version diff status -- a different concept from VerdictStatus (an
// in-document investigation outcome): "did this transition still trigger
// detection in the new draft, compared to the version before it." Kept as
// its own color family (orange for "no longer detected") rather than
// reusing --severity-resolved's green, so the two concepts never look
// interchangeable at a glance.
const DIFF_COLOR: Record<DiffStatus, string> = {
  new: "var(--severity-critical)",
  recurring: "var(--severity-critical)",
  resolved_in_version: "var(--diff-resolved)",
};

const DIFF_LABEL: Record<DiffStatus, string> = {
  new: "New issue",
  recurring: "Still an issue",
  resolved_in_version: "No longer detected",
};

export function DiffStatusBadge({ status }: { status: DiffStatus }) {
  const color = DIFF_COLOR[status];
  return (
    <span
      className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
      style={{ color, backgroundColor: `color-mix(in srgb, ${color} 15%, transparent)` }}
    >
      {DIFF_LABEL[status]}
    </span>
  );
}

export function diffStatusColor(status: DiffStatus): string {
  return DIFF_COLOR[status];
}
