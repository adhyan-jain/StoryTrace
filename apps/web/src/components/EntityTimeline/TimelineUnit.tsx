"use client";

import Link from "next/link";
import { ExcerptBox } from "@/components/ui/ExcerptBox";
import { SeverityBadge, severityColor } from "@/components/ui/SeverityBadge";
import type { ConflictWithVerdict, NarrativeUnit, UnitStateEvent } from "@/lib/types";

export function TimelineUnit({
  id,
  unit,
  events,
  conflict,
}: {
  id: string;
  unit: NarrativeUnit;
  events: UnitStateEvent[];
  conflict: ConflictWithVerdict | null;
}) {
  const dotColor = conflict ? severityColor(conflict.severity) : "var(--text-muted)";

  return (
    <div className="relative pl-8">
      <span
        className="absolute left-0 top-1.5 w-2.5 h-2.5 rounded-full border-2"
        style={{ backgroundColor: conflict ? dotColor : "var(--bg-base)", borderColor: dotColor }}
      />
      <span className="absolute left-[4.5px] top-4 bottom-[-1.5rem] w-px bg-[var(--bg-border)]" />

      <div className="flex items-baseline justify-between mb-2">
        <p className="text-sm font-medium text-[var(--text-primary)]">
          Unit {unit.sequence_number} — {unit.title}
        </p>
        <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-muted)] flex-shrink-0 ml-3">
          pg. {unit.page_start}–{unit.page_end}
        </span>
      </div>

      {events.length > 0 && (
        <div className="flex flex-col gap-1 mb-2">
          {events.map((e, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-secondary)]">{e.attribute}</span>
              <span className="font-[family-name:var(--font-mono)] text-[var(--text-primary)]">
                {e.value} <span className="text-[var(--text-muted)]">[{e.confidence.toFixed(2)}]</span>
              </span>
            </div>
          ))}
        </div>
      )}

      {events[0] && (
        <ExcerptBox className="mb-2">{events[0].raw_excerpt}</ExcerptBox>
      )}

      {conflict && (
        <div className="flex items-center gap-2 mt-2">
          <SeverityBadge severity={conflict.severity ?? "info"} />
          <span className="text-xs text-[var(--text-secondary)]">{conflict.description}</span>
          <Link
            href={`/analyze/${id}?conflict=${conflict.id}`}
            className="text-xs text-[var(--accent-blue)] hover:underline flex-shrink-0"
          >
            View Autopsy →
          </Link>
        </div>
      )}
    </div>
  );
}
