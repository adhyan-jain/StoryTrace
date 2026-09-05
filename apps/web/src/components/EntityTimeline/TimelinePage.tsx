"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getConflicts, getEntities, getScenes, ApiError } from "@/lib/api";
import { TimelineUnit } from "./TimelineUnit";
import type { ConflictWithVerdict, Entity, NarrativeUnit } from "@/lib/types";

export function TimelinePage({ id, entityId }: { id: string; entityId: string }) {
  const [units, setUnits] = useState<NarrativeUnit[]>([]);
  const [entity, setEntity] = useState<Entity | null>(null);
  const [conflicts, setConflicts] = useState<ConflictWithVerdict[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getScenes(id), getEntities(id), getConflicts(id)])
      .then(([scenesData, entitiesData, conflictsData]) => {
        setUnits(scenesData);
        setEntity(entitiesData.find((e) => e.entity_id === entityId) ?? null);
        setConflicts(conflictsData);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load entity timeline."));
  }, [id, entityId]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
        <p className="font-[family-name:var(--font-mono)] text-sm text-[var(--severity-critical)]">{error}</p>
      </div>
    );
  }

  const unitsWithEvents = units
    .map((unit) => ({
      unit,
      events: unit.state_events.filter((e) => e.entity_id === entityId),
    }))
    .filter((u) => u.events.length > 0);

  const entityConflicts = conflicts.filter((c) => c.entity_id === entityId);

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <div className="grain-surface border-b-2 border-[var(--bg-border)] relative overflow-hidden">
        <div className="max-w-2xl mx-auto px-6 py-10 relative">
          <span
            className="ghost-index absolute -top-6 right-2 text-[7rem] select-none"
            aria-hidden="true"
          >
            {entity?.type === "character" ? "CH" : entity?.type === "prop" ? "PR" : "LO"}
          </span>
          <Link
            href={`/analyze/${id}`}
            className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-[var(--accent-blue)] hover:underline"
          >
            &larr; Back to Case File
          </Link>
          <div className="mt-4">
            <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.2em] text-[var(--text-secondary)] mb-1">
              Entity Dossier &middot; {entity?.type ?? "entity"}
            </p>
            <h1 className="font-[family-name:var(--font-heading)] uppercase text-4xl sm:text-5xl leading-[0.9] text-[var(--text-primary)]">
              {entity?.name ?? entityId}
            </h1>
            <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-wide text-[var(--text-secondary)] mt-3">
              {unitsWithEvents.length} units &middot; {entityConflicts.length} findings
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="flex flex-col gap-8">
          {unitsWithEvents.map(({ unit, events }) => {
            const conflict =
              entityConflicts.find((c) => c.prior_unit_id === unit.unit_id || c.current_unit_id === unit.unit_id) ?? null;
            return <TimelineUnit key={unit.unit_id} id={id} unit={unit} events={events} conflict={conflict} />;
          })}
          {unitsWithEvents.length === 0 && (
            <p className="font-[family-name:var(--font-mono)] text-sm text-[var(--text-muted)]">
              No state events extracted for this entity yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
