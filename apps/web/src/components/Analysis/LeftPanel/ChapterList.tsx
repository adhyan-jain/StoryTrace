"use client";

import clsx from "clsx";
import type { NarrativeUnit } from "@/lib/types";

const FLAG_COLOR: Record<string, string> = {
  critical: "var(--severity-critical)",
  warning: "var(--severity-warning)",
  resolved: "var(--severity-resolved)",
};

export function ChapterList({
  units,
  activeUnitId,
  onSelect,
  diffColorByUnit,
}: {
  units: NarrativeUnit[];
  activeUnitId: string | null;
  onSelect: (unitId: string) => void;
  /** When set (a version comparison is active), every unit gets a dot --
   * red/orange from the map when the unit has a diff finding, green
   * otherwise -- instead of only showing a dot for units with a severity. */
  diffColorByUnit?: Record<string, string>;
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
              "w-full flex items-center gap-3 pl-3 pr-3 py-2.5 text-left border-l-2 transition-colors cursor-pointer",
              isActive
                ? "bg-[var(--bg-elevated)] border-[var(--accent-blue)]"
                : "border-transparent hover:bg-[var(--bg-elevated)]",
            )}
          >
            <span className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--text-muted)] w-6 flex-shrink-0 tabular-nums">
              {String(unit.sequence_number).padStart(2, "0")}
            </span>
            <span
              className={clsx("truncate text-[13px] flex-1", isActive ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]")}
            >
              {unit.title}
            </span>
            {diffColorByUnit ? (
              <span
                className="w-1.5 h-1.5 border flex-shrink-0"
                style={{ borderColor: diffColorByUnit[unit.unit_id] ?? "var(--severity-resolved)" }}
                aria-hidden="true"
              />
            ) : (
              unit.severity && (
                <span
                  className="w-1.5 h-1.5 border flex-shrink-0"
                  style={{ borderColor: FLAG_COLOR[unit.severity] }}
                  aria-hidden="true"
                />
              )
            )}
          </button>
        );
      })}
    </div>
  );
}
