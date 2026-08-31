"use client";

import clsx from "clsx";
import type { NarrativeUnit } from "@/lib/types";

const DOT_COLOR: Record<string, string> = {
  critical: "var(--severity-critical)",
  warning: "var(--severity-warning)",
  resolved: "var(--severity-resolved)",
};

export function ChapterList({
  units,
  activeUnitId,
  onSelect,
}: {
  units: NarrativeUnit[];
  activeUnitId: string | null;
  onSelect: (unitId: string) => void;
}) {
  return (
    <div className="flex-1 overflow-y-auto">
      {units.map((unit) => {
        const isActive = unit.unit_id === activeUnitId;
        return (
          <button
            key={unit.unit_id}
            onClick={() => onSelect(unit.unit_id)}
            className={clsx(
              "w-full flex items-center gap-2 pl-3 pr-3 py-2 text-left border-l-2 transition-colors cursor-pointer",
              isActive
                ? "bg-[var(--bg-elevated)] border-[var(--accent-blue)]"
                : "border-transparent hover:bg-[var(--bg-elevated)]",
            )}
          >
            <span className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] w-6 text-right flex-shrink-0 tabular-nums">
              {unit.sequence_number}
            </span>
            <span
              className={clsx("truncate text-[13px] flex-1", isActive ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]")}
            >
              {unit.title}
            </span>
            {unit.severity && (
              <span
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: DOT_COLOR[unit.severity] }}
                aria-hidden="true"
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
