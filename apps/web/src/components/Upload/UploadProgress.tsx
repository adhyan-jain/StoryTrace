"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import type { OverviewResponse, PipelineStatus } from "@/lib/types";

const STEP_ORDER: PipelineStatus[] = ["parsing", "extracting", "detecting", "investigating"];

const STEPS: { key: PipelineStatus; label: string }[] = [
  { key: "parsing", label: "Parsing document" },
  { key: "extracting", label: "Extracting state events" },
  { key: "detecting", label: "Detecting candidates" },
  { key: "investigating", label: "Investigating conflicts" },
];

function stepState(step: PipelineStatus, current: PipelineStatus): "done" | "active" | "pending" {
  if (current === "complete") return "done";
  const stepIndex = STEP_ORDER.indexOf(step);
  const currentIndex = STEP_ORDER.indexOf(current);
  if (currentIndex > stepIndex) return "done";
  if (currentIndex === stepIndex) return "active";
  return "pending";
}

function stepDetail(step: PipelineStatus, overview: OverviewResponse): string | null {
  if (step === "extracting" && overview.total_units > 0) {
    return `${overview.units_extracted} of ${overview.total_units} units processed`;
  }
  if (step === "detecting" && stepState(step, overview.status) === "done") {
    return `${overview.candidates_detected} candidates found`;
  }
  if (step === "investigating" && overview.candidates_detected > 0) {
    return `${overview.verdicts_complete} of ${overview.candidates_detected} investigated`;
  }
  return null;
}

function useElapsed(startedAt: number) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(interval);
  }, [startedAt]);
  return elapsed;
}

export function UploadProgress({ overview, startedAt, stalled }: { overview: OverviewResponse; startedAt: number; stalled: boolean }) {
  const elapsed = useElapsed(startedAt);
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-8 px-6">
      <div className="w-full max-w-md">
        <div className="flex flex-col gap-5">
          {STEPS.map((step, i) => {
            const state = stepState(step.key, overview.status);
            const detail = stepDetail(step.key, overview);
            return (
              <div key={step.key} className="flex items-start gap-3">
                <div className="flex flex-col items-center">
                  <span
                    className={clsx(
                      "w-3 h-3 rounded-full flex-shrink-0 mt-0.5",
                      state === "active" && "animate-pulse",
                    )}
                    style={{
                      backgroundColor:
                        state === "done" ? "var(--severity-resolved)" : state === "active" ? "var(--accent-blue)" : "var(--bg-border)",
                    }}
                  />
                  {i < STEPS.length - 1 && <span className="w-px flex-1 min-h-6 bg-[var(--bg-border)] mt-1" />}
                </div>
                <div>
                  <p
                    className={clsx(
                      "text-sm",
                      state === "pending" ? "text-[var(--text-muted)]" : "text-[var(--text-primary)]",
                    )}
                  >
                    {step.label}
                  </p>
                  {detail && <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-secondary)] mt-0.5">{detail}</p>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-muted)]">
        {minutes}m {seconds.toString().padStart(2, "0")}s elapsed
      </p>
      {!stalled && overview.status !== "error" && (
        <p className="text-xs text-[var(--text-muted)] max-w-md text-center">
          A full screenplay usually takes 3–8 minutes to analyze — the agent is reading every scene and
          investigating flagged conflicts one at a time. This is expected, not a stall.
        </p>
      )}
      {stalled && (
        <p className="text-xs text-[var(--severity-warning)] max-w-md text-center">
          Processing is taking longer than expected. The pipeline may still be running — check back in a moment.
        </p>
      )}
      {overview.status === "error" && (
        <p className="text-xs text-[var(--severity-critical)] max-w-md text-center">{overview.error}</p>
      )}
    </div>
  );
}
