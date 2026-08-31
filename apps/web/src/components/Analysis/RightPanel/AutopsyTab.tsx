"use client";

import { useEffect, useState } from "react";
import { getAutopsy, markIntentional, ApiError } from "@/lib/api";
import { ExcerptBox } from "@/components/ui/ExcerptBox";
import { SeverityBadge, StatusBadge, severityColor } from "@/components/ui/SeverityBadge";
import type { AutopsyResponse, InvestigationStep } from "@/lib/types";

function StepView({ step }: { step: InvestigationStep }) {
  if (step.step === "action") {
    return (
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">action</p>
        <ExcerptBox>
          {step.tool}({JSON.stringify(step.args)})
        </ExcerptBox>
      </div>
    );
  }
  if (step.step === "observation") {
    return (
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">observation</p>
        <ExcerptBox>{typeof step.result === "string" ? step.result : JSON.stringify(step.result, null, 2)}</ExcerptBox>
      </div>
    );
  }
  if (step.step === "verdict") {
    return (
      <div>
        <p className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">verdict</p>
        <div
          className="rounded-md border px-3 py-2 bg-[var(--bg-elevated)]"
          style={{ borderColor: severityColor((step.verdict.severity as never) ?? null) }}
        >
          <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-primary)]">{JSON.stringify(step.verdict, null, 2)}</p>
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
        <p className="text-sm text-[var(--text-primary)] font-medium">
          Conflict: {conflict.entity_name} · {conflict.attribute}
        </p>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Units {conflict.prior_unit_id.split("_").pop()} → {conflict.current_unit_id.split("_").pop()}
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
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1.5">
            Prior state (Unit {conflict.prior_unit_id.split("_").pop()}, pg. {conflict.prior_page ?? "?"})
          </p>
          <ExcerptBox>{conflict.prior_excerpt}</ExcerptBox>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1.5">
            Observed state (Unit {conflict.current_unit_id.split("_").pop()}, pg. {conflict.current_page ?? "?"})
          </p>
          <ExcerptBox>{conflict.current_excerpt}</ExcerptBox>
        </div>
      </div>

      {steps.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-2">Investigation trace</p>
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
          className="px-3 py-1.5 rounded-md text-xs font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] transition-colors cursor-pointer disabled:opacity-50"
        >
          Mark as Intentional
        </button>
        <button
          onClick={() => onJumpToUnit(conflict.prior_unit_id)}
          className="px-3 py-1.5 rounded-md text-xs font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          Jump to Unit {conflict.prior_unit_id.split("_").pop()}
        </button>
        <button
          onClick={() => onJumpToUnit(conflict.current_unit_id)}
          className="px-3 py-1.5 rounded-md text-xs font-medium text-[var(--text-secondary)] border border-[var(--bg-border)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          Jump to Unit {conflict.current_unit_id.split("_").pop()}
        </button>
      </div>
    </div>
  );
}
