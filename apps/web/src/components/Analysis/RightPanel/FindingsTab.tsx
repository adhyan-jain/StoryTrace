"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import { ConflictCard } from "./ConflictCard";
import type { ConflictWithVerdict } from "@/lib/types";

type Filter = "critical" | "warning" | "resolved" | "uncertain";

const FILTER_COLOR: Record<Filter, string> = {
  critical: "var(--severity-critical)",
  warning: "var(--severity-warning)",
  resolved: "var(--severity-resolved)",
  uncertain: "var(--severity-uncertain)",
};

const SEVERITY_ORDER = { critical: 0, warning: 1, info: 2 } as const;

export function FindingsTab({
  conflicts,
  onSelect,
}: {
  conflicts: ConflictWithVerdict[];
  onSelect: (conflictId: string) => void;
}) {
  const [activeFilters, setActiveFilters] = useState<Set<Filter>>(new Set());

  const counts = useMemo(
    () => ({
      critical: conflicts.filter((c) => c.severity === "critical").length,
      warning: conflicts.filter((c) => c.severity === "warning").length,
      resolved: conflicts.filter((c) => c.status === "resolved").length,
      uncertain: conflicts.filter((c) => c.status === "uncertain").length,
    }),
    [conflicts],
  );

  const toggleFilter = (filter: Filter) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(filter)) next.delete(filter);
      else next.add(filter);
      return next;
    });
  };

  const filtered = useMemo(() => {
    if (activeFilters.size === 0) return conflicts;
    return conflicts.filter((c) => {
      return (
        (activeFilters.has("critical") && c.severity === "critical") ||
        (activeFilters.has("warning") && c.severity === "warning") ||
        (activeFilters.has("resolved") && c.status === "resolved") ||
        (activeFilters.has("uncertain") && c.status === "uncertain")
      );
    });
  }, [conflicts, activeFilters]);

  const sorted = useMemo(
    () =>
      [...filtered].sort((a, b) => {
        const rankA = a.severity ? SEVERITY_ORDER[a.severity] : 3;
        const rankB = b.severity ? SEVERITY_ORDER[b.severity] : 3;
        return rankA - rankB;
      }),
    [filtered],
  );

  if (conflicts.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">No continuity issues detected in this document.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex flex-wrap gap-1.5 p-3 border-b border-[var(--bg-border)] flex-shrink-0">
        {(Object.keys(counts) as Filter[]).map((filter) => (
          <button
            key={filter}
            onClick={() => toggleFilter(filter)}
            className={clsx(
              "text-[10px] font-semibold uppercase tracking-wide px-2 py-1 rounded-full border transition-colors cursor-pointer",
              activeFilters.has(filter) ? "text-[var(--bg-base)]" : "text-[var(--text-secondary)] border-[var(--bg-border)]",
            )}
            style={
              activeFilters.has(filter)
                ? { backgroundColor: FILTER_COLOR[filter], borderColor: FILTER_COLOR[filter] }
                : undefined
            }
          >
            {counts[filter]} {filter}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {sorted.map((conflict) => (
          <ConflictCard key={conflict.id} conflict={conflict} onClick={() => onSelect(conflict.id)} />
        ))}
      </div>
    </div>
  );
}
