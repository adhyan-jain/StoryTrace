"use client";

import { HighlightedText } from "./HighlightedText";
import type { NarrativeUnit } from "@/lib/types";

export function SceneViewer({
  unit,
  onSelectConflict,
}: {
  unit: NarrativeUnit | null;
  onSelectConflict: (conflictId: string) => void;
}) {
  if (!unit) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[var(--text-muted)] text-sm">Select a chapter to view its text.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="px-6 py-3 border-b-2 border-[var(--bg-border)] flex items-center justify-between flex-shrink-0 bg-[var(--bg-elevated)]">
        <span className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide text-[var(--text-secondary)]">
          Exhibit {String(unit.sequence_number).padStart(2, "0")} &middot; {unit.title}
        </span>
        <span className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide text-[var(--text-muted)]">
          Pg. {unit.page_start}
          {unit.page_end !== unit.page_start ? `–${unit.page_end}` : ""}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-12 py-10 flex justify-center">
        <article
          className="w-full max-w-[680px] font-[family-name:var(--font-reader)] text-[16px] leading-[1.8] text-[var(--text-primary)] whitespace-pre-wrap"
        >
          <HighlightedText text={unit.raw_text} events={unit.state_events} onSelectConflict={onSelectConflict} />
        </article>
      </div>
    </div>
  );
}
