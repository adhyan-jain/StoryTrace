import type { Severity, VerdictStatus } from "@/lib/types";

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
