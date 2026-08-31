"use client";

import { Tooltip } from "@/components/ui/Tooltip";
import { severityColor } from "@/components/ui/SeverityBadge";
import type { UnitStateEvent } from "@/lib/types";

interface Span {
  start: number;
  end: number;
  event: UnitStateEvent;
}

/** Finds each state event's raw_excerpt in the raw text and returns
 * non-overlapping spans (first match wins on overlap) to wrap in <mark>. */
function findSpans(text: string, events: UnitStateEvent[]): Span[] {
  const spans: Span[] = [];
  for (const event of events) {
    if (!event.raw_excerpt) continue;
    const start = text.indexOf(event.raw_excerpt);
    if (start === -1) continue;
    const end = start + event.raw_excerpt.length;
    const overlaps = spans.some((s) => start < s.end && end > s.start);
    if (!overlaps) spans.push({ start, end, event });
  }
  return spans.sort((a, b) => a.start - b.start);
}

export function HighlightedText({
  text,
  events,
  onSelectConflict,
}: {
  text: string;
  events: UnitStateEvent[];
  onSelectConflict: (conflictId: string) => void;
}) {
  const spans = findSpans(text, events);
  if (spans.length === 0) {
    return <>{text}</>;
  }

  const pieces: React.ReactNode[] = [];
  let cursor = 0;
  spans.forEach((span, i) => {
    if (span.start > cursor) pieces.push(text.slice(cursor, span.start));
    const color = severityColor(span.event.severity);
    pieces.push(
      <Tooltip
        key={i}
        content={
          <div className="flex flex-col gap-0.5">
            <div>Entity: {span.event.entity_name}</div>
            <div>Attribute: {span.event.attribute}</div>
            <div>Value: {span.event.value}</div>
            <div>Confidence: {span.event.confidence.toFixed(2)}</div>
          </div>
        }
      >
        <mark
          onClick={() => span.event.conflict_id && onSelectConflict(span.event.conflict_id)}
          className="bg-transparent"
          style={{
            borderBottom: `2px solid ${color}`,
            cursor: span.event.conflict_id ? "pointer" : "default",
            color: "inherit",
          }}
        >
          {text.slice(span.start, span.end)}
        </mark>
      </Tooltip>,
    );
    cursor = span.end;
  });
  if (cursor < text.length) pieces.push(text.slice(cursor));

  return <>{pieces}</>;
}
