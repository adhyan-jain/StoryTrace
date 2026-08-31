"use client";

import { useRouter } from "next/navigation";
import type { Entity } from "@/lib/types";

function EntityIcon({ type }: { type: Entity["type"] }) {
  const stroke = "var(--text-secondary)";
  if (type === "character") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21v-1a7 7 0 0 1 14 0v1" />
      </svg>
    );
  }
  if (type === "prop") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
        <rect x="4" y="8" width="16" height="12" rx="1" />
        <path d="M9 8V6a3 3 0 0 1 6 0v2" />
      </svg>
    );
  }
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
      <path d="M12 22s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  );
}

export function EntityList({ id, entities }: { id: string; entities: Entity[] }) {
  const router = useRouter();

  return (
    <div className="flex-1 overflow-y-auto">
      {entities.map((entity) => (
        <button
          key={entity.entity_id}
          onClick={() => router.push(`/analyze/${id}/entity/${entity.entity_id}`)}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
        >
          <EntityIcon type={entity.type} />
          <span className="truncate text-[13px] text-[var(--text-secondary)] flex-1">{entity.name}</span>
          {entity.finding_count > 0 && (
            <span className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--severity-warning)]">
              {entity.finding_count}
            </span>
          )}
        </button>
      ))}
      {entities.length === 0 && (
        <p className="px-3 py-6 text-center text-[13px] text-[var(--text-muted)]">No entities extracted yet.</p>
      )}
    </div>
  );
}
