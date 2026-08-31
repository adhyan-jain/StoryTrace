"use client";

import { useMemo } from "react";
import type { NarrativeUnit } from "@/lib/types";

interface EntityState {
  entityName: string;
  attributes: { attribute: string; value: string }[];
}

/** Replays every StateEvent up to and including the active unit's sequence
 * number, keeping only the latest value per (entity, attribute) -- the same
 * "state at unit" the agent's own get_state_at_unit tool computes in
 * ClickHouse, done client-side from data already on the page. */
function computeStateAtUnit(units: NarrativeUnit[], activeSequence: number): EntityState[] {
  const latest = new Map<string, { entityName: string; attribute: string; value: string; sequence: number }>();

  for (const unit of units) {
    if (unit.sequence_number > activeSequence) continue;
    for (const event of unit.state_events) {
      const key = `${event.entity_id}::${event.attribute}`;
      const existing = latest.get(key);
      if (!existing || unit.sequence_number >= existing.sequence) {
        latest.set(key, { entityName: event.entity_name, attribute: event.attribute, value: event.value, sequence: unit.sequence_number });
      }
    }
  }

  const byEntity = new Map<string, EntityState>();
  for (const { entityName, attribute, value } of latest.values()) {
    const entry = byEntity.get(entityName) ?? { entityName, attributes: [] };
    entry.attributes.push({ attribute, value });
    byEntity.set(entityName, entry);
  }
  return [...byEntity.values()];
}

export function StateTab({ units, activeUnit }: { units: NarrativeUnit[]; activeUnit: NarrativeUnit | null }) {
  const state = useMemo(
    () => (activeUnit ? computeStateAtUnit(units, activeUnit.sequence_number) : []),
    [units, activeUnit],
  );

  if (!activeUnit) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">Select a chapter to view its state.</p>
      </div>
    );
  }

  if (state.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">This unit has not been processed yet.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      {state.map((entity) => (
        <div key={entity.entityName}>
          <p className="text-sm font-medium text-[var(--text-primary)] mb-1.5">{entity.entityName}</p>
          <div className="flex flex-col gap-1 pl-3 border-l border-[var(--bg-border)]">
            {entity.attributes.map((attr) => (
              <div key={attr.attribute} className="flex items-baseline justify-between gap-3">
                <span className="text-xs text-[var(--text-secondary)]">{attr.attribute}</span>
                <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--text-primary)] text-right">{attr.value}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
