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
        <p className="text-sm text-[var(--severity-critical)]">{error}</p>
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
    <div className="min-h-screen bg-[var(--bg-base)] px-8 py-8">
      <div className="max-w-2xl mx-auto">
        <Link href={`/analyze/${id}`} className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
          ← Back
        </Link>
        <div className="mt-4 mb-8">
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">
            {entity?.name ?? entityId} <span className="text-[var(--text-secondary)] font-normal">· {entity?.type ?? "entity"}</span>
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            {unitsWithEvents.length} units · {entityConflicts.length} findings
          </p>
        </div>

        <div className="flex flex-col gap-6">
          {unitsWithEvents.map(({ unit, events }) => {
            const conflict =
              entityConflicts.find((c) => c.prior_unit_id === unit.unit_id || c.current_unit_id === unit.unit_id) ?? null;
            return <TimelineUnit key={unit.unit_id} id={id} unit={unit} events={events} conflict={conflict} />;
          })}
          {unitsWithEvents.length === 0 && (
            <p className="text-sm text-[var(--text-muted)]">No state events extracted for this entity yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
