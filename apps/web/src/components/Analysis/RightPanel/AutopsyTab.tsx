"use client";

import { useEffect, useState } from "react";
import { getAutopsy, markIntentional, ApiError } from "@/lib/api";
import { ExcerptBox } from "@/components/ui/ExcerptBox";
import { SeverityBadge, StatusBadge, severityColor } from "@/components/ui/SeverityBadge";
import type { AutopsyResponse, InvestigationStep } from "@/lib/types";

/** Renders a plain object as "key: value" lines instead of a raw JSON
 * blob -- readable at a glance instead of a wrapped, bracket-heavy dump. */
function KeyValueLines({ data }: { data: Record<string, unknown> }) {
  return (
    <>
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="flex gap-2">
          <span className="text-[var(--text-muted)] shrink-0">{key}:</span>
          <span className="text-[var(--text-primary)] break-all">
            {typeof value === "object" ? JSON.stringify(value) : String(value)}
          </span>
        </div>
      ))}
    </>
  );
}

/** The investigation tools return either a plain string, a single object,
 * or an array of objects (e.g. find_attribute_changes' per-sequence rows) --
 * format whichever shape shows up as readable lines instead of a raw
 * JSON.stringify dump. */
function FormattedResult({ result }: { result: unknown }) {
  if (typeof result === "string") return <>{result || "(empty)"}</>;
  if (Array.isArray(result)) {
    if (result.length === 0) return <>(no rows)</>;
    return (
      <div className="flex flex-col gap-2.5">
        {result.map((row, i) => (
          <div key={i} className="flex flex-col gap-0.5 pb-2 border-b border-[var(--bg-border)] last:border-0 last:pb-0">
            {row && typeof row === "object" ? (
              <KeyValueLines data={row as Record<string, unknown>} />
            ) : (
              <span>{String(row)}</span>
            )}
          </div>
        ))}
      </div>
    );
  }
  if (result && typeof result === "object") {
    return (
      <div className="flex flex-col gap-0.5">
        <KeyValueLines data={result as Record<string, unknown>} />
      </div>
    );
  }
  return <>{String(result)}</>;
}

function StepView({ step }: { step: InvestigationStep }) {
  if (step.step === "action") {
    return (
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">action</p>
        <ExcerptBox>
          <span className="font-medium">{step.tool}</span>
          <div className="flex flex-col gap-0.5 mt-1">
            <KeyValueLines data={step.args as Record<string, unknown>} />
          </div>
        </ExcerptBox>
      </div>
    );
  }
  if (step.step === "observation") {
    return (
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">observation</p>
        <ExcerptBox>
          <FormattedResult result={step.result} />
        </ExcerptBox>
      </div>
    );
  }
  if (step.step === "verdict") {
    return (
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">verdict</p>
        <div
          className="border px-3 py-2 bg-[var(--bg-elevated)]"
          style={{ borderColor: severityColor((step.verdict.severity as never) ?? null) }}
        >
          <div className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-primary)] flex flex-col gap-0.5">
            <KeyValueLines data={step.verdict as Record<string, unknown>} />
          </div>
        </div>
      </div>
    );
  }
  if (step.step === "error") {
    return (
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">error</p>
        <ExcerptBox className="text-[var(--severity-critical)]">{step.message}</ExcerptBox>
      </div>
    );
  }
  return (
    <div>
      <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">note</p>
      <ExcerptBox>{step.message}</ExcerptBox>
    </div>
  );
}

export function AutopsyTab({
  conflictId,
  onJumpToUnit,
}: {
  conflictId: string | null;
  onJumpToUnit: (unitId: string) => void;
}) {
  const [data, setData] = useState<AutopsyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    if (!conflictId) {
      setData(null);
      return;
    }
    setData(null);
    setError(null);
    getAutopsy(conflictId)
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load investigation."));
  }, [conflictId]);

  if (!conflictId) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">Select a finding to view its investigation.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--severity-critical)]">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-muted)]">Loading investigation...</p>
      </div>
    );
  }

  const { conflict, verdict, steps } = data;

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] text-[var(--accent-blue)] mb-1.5">
          Autopsy Report
        </p>
        <p className="text-sm text-[var(--text-primary)] font-medium">
          {conflict.entity_name} <span className="text-[var(--text-secondary)]">· {conflict.attribute}</span>
        </p>
        <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide text-[var(--text-secondary)] mt-1">
          Units {conflict.prior_unit_id.split("_").pop()} &rarr; {conflict.current_unit_id.split("_").pop()}
        </p>
        {verdict && (
          <div className="flex items-center gap-2 mt-2">
            <StatusBadge status={verdict.status} />
            <SeverityBadge severity={verdict.severity} />
            <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-muted)]">
              {(verdict.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1.5">
            Prior (Unit {conflict.prior_unit_id.split("_").pop()}, pg. {conflict.prior_page ?? "?"})
          </p>
          <ExcerptBox>{conflict.prior_excerpt}</ExcerptBox>
        </div>
        <div>
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1.5">
            Observed (Unit {conflict.current_unit_id.split("_").pop()}, pg. {conflict.current_page ?? "?"})
          </p>
          <ExcerptBox>{conflict.current_excerpt}</ExcerptBox>
        </div>
      </div>

      {steps.length > 0 && (
        <div>
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-2">
            Investigation trace
          </p>
          <div className="flex flex-col gap-3 pl-3 border-l border-[var(--bg-border)]">
            {steps.map((step, i) => (
              <StepView key={i} step={step} />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 pt-2 border-t border-[var(--bg-border)]">
        <button
          onClick={async () => {
            if (!conflictId) return;
            setMarking(true);
            await markIntentional(conflictId);
            const refreshed = await getAutopsy(conflictId);
            setData(refreshed);
            setMarking(false);
          }}
          disabled={marking}
          className="font-[family-name:var(--font-mono)] px-3 py-1.5 text-[11px] uppercase tracking-wide font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer disabled:opacity-50"
        >
          Mark as Intentional
        </button>
        <button
          onClick={() => onJumpToUnit(conflict.prior_unit_id)}
          className="font-[family-name:var(--font-mono)] px-3 py-1.5 text-[11px] uppercase tracking-wide font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
        >
          Jump to Unit {conflict.prior_unit_id.split("_").pop()}
        </button>
        <button
          onClick={() => onJumpToUnit(conflict.current_unit_id)}
          className="font-[family-name:var(--font-mono)] px-3 py-1.5 text-[11px] uppercase tracking-wide font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
        >
          Jump to Unit {conflict.current_unit_id.split("_").pop()}
        </button>
      </div>
    </div>
  );
}
