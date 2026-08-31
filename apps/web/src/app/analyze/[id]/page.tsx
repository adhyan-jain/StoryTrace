"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { getConflicts, getEntities, getOverview, getScenes, ApiError } from "@/lib/api";
import { TabBar } from "@/components/ui/TabBar";
import { ChapterList } from "@/components/Analysis/LeftPanel/ChapterList";
import { EntityList } from "@/components/Analysis/LeftPanel/EntityList";
import { SceneViewer } from "@/components/Analysis/CenterPanel/SceneViewer";
import { FindingsTab } from "@/components/Analysis/RightPanel/FindingsTab";
import { StateTab } from "@/components/Analysis/RightPanel/StateTab";
import { AutopsyTab } from "@/components/Analysis/RightPanel/AutopsyTab";
import { UploadProgress } from "@/components/Upload/UploadProgress";
import type { ConflictWithVerdict, Entity, NarrativeUnit, OverviewResponse } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;
const STALL_THRESHOLD_MS = 30000;

function Header({ id, overview, entityCount, findingCount }: { id: string; overview: OverviewResponse | null; entityCount: number; findingCount: number }) {
  const router = useRouter();
  return (
    <div className="px-4 py-3 border-b border-[var(--bg-border)] flex items-center justify-between flex-shrink-0">
      <div>
        <p className="text-sm font-medium text-[var(--text-primary)] truncate max-w-[200px]">
          {overview?.document_title ?? "Untitled document"}
        </p>
        <p className="text-xs text-[var(--text-secondary)] mt-0.5">
          {overview?.total_units ?? 0} units · {entityCount} entities · {findingCount} findings
        </p>
      </div>
      <button
        onClick={() => {
          localStorage.removeItem("storytrace_active_id");
          router.push("/");
        }}
        className="text-xs text-[var(--text-secondary)] border border-[var(--bg-border)] rounded-md px-2.5 py-1.5 hover:text-[var(--text-primary)] transition-colors cursor-pointer flex-shrink-0"
      >
        New document
      </button>
    </div>
  );
}

export default function AnalyzePage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [units, setUnits] = useState<NarrativeUnit[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [conflicts, setConflicts] = useState<ConflictWithVerdict[]>([]);

  const [leftTab, setLeftTab] = useState<"CHAPTERS" | "ENTITIES">("CHAPTERS");
  const [rightTab, setRightTab] = useState<"FINDINGS" | "STATE" | "AUTOPSY">("FINDINGS");
  const [activeUnitId, setActiveUnitId] = useState<string | null>(null);
  const [selectedConflictId, setSelectedConflictId] = useState<string | null>(null);

  const startedAt = useRef(Date.now());
  const lastProgress = useRef({ value: -1, at: Date.now() });
  const [stalled, setStalled] = useState(false);

  const loadFullData = useCallback(async () => {
    const [scenesData, entitiesData, conflictsData] = await Promise.all([
      getScenes(id),
      getEntities(id),
      getConflicts(id),
    ]);
    setUnits(scenesData);
    setEntities(entitiesData);
    setConflicts(conflictsData);

    const deepLinkedConflictId = searchParams.get("conflict");
    const deepLinkedConflict = deepLinkedConflictId ? conflictsData.find((c) => c.id === deepLinkedConflictId) : null;
    if (deepLinkedConflict) {
      setSelectedConflictId(deepLinkedConflict.id);
      setRightTab("AUTOPSY");
      setActiveUnitId(deepLinkedConflict.current_unit_id);
    } else {
      setActiveUnitId((current) => current ?? scenesData[2]?.unit_id ?? scenesData[0]?.unit_id ?? null);
    }
  }, [id, searchParams]);

  useEffect(() => {
    localStorage.setItem("storytrace_active_id", id);
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const data = await getOverview(id);
        if (cancelled) return;
        setOverview(data);
        setLoadError(null);

        const progressValue = data.units_extracted + data.candidates_detected + data.verdicts_complete;
        if (progressValue !== lastProgress.current.value) {
          lastProgress.current = { value: progressValue, at: Date.now() };
          setStalled(false);
        } else if (Date.now() - lastProgress.current.at > STALL_THRESHOLD_MS && data.status !== "complete" && data.status !== "error") {
          setStalled(true);
        }

        if (data.status === "complete") {
          await loadFullData();
        } else if (data.status !== "error") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        setLoadError(err instanceof ApiError ? err.message : "Failed to reach the StoryTrace API.");
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, loadFullData]);

  const activeUnit = units.find((u) => u.unit_id === activeUnitId) ?? null;

  const handleSelectConflict = useCallback((conflictId: string) => {
    setSelectedConflictId(conflictId);
    setRightTab("AUTOPSY");
  }, []);

  const handleJumpToUnit = useCallback((unitId: string) => {
    setActiveUnitId(unitId);
  }, []);

  if (loadError && !overview) {
    return (
      <div className="h-screen flex items-center justify-center bg-[var(--bg-base)] px-6">
        <p className="text-sm text-[var(--severity-critical)] text-center max-w-md">{loadError}</p>
      </div>
    );
  }

  if (!overview) {
    return <div className="h-screen bg-[var(--bg-base)]" />;
  }

  if (overview.status !== "complete") {
    return (
      <div className="flex h-screen bg-[var(--bg-base)] overflow-hidden">
        <div className="w-[280px] border-r border-[var(--bg-border)] bg-[var(--bg-surface)] flex flex-col">
          <Header id={id} overview={overview} entityCount={0} findingCount={0} />
        </div>
        <UploadProgress overview={overview} startedAt={startedAt.current} stalled={stalled} />
        <div className="w-[360px] border-l border-[var(--bg-border)] bg-[var(--bg-surface)]" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[var(--bg-base)] overflow-hidden">
      {/* Left Panel */}
      <div className="w-[280px] border-r border-[var(--bg-border)] bg-[var(--bg-surface)] flex flex-col flex-shrink-0">
        <Header id={id} overview={overview} entityCount={entities.length} findingCount={conflicts.length} />
        <TabBar tabs={["CHAPTERS", "ENTITIES"] as const} active={leftTab} onChange={setLeftTab} />
        {leftTab === "CHAPTERS" ? (
          <ChapterList units={units} activeUnitId={activeUnitId} onSelect={setActiveUnitId} />
        ) : (
          <EntityList id={id} entities={entities} />
        )}
      </div>

      {/* Center Panel */}
      <SceneViewer unit={activeUnit} onSelectConflict={handleSelectConflict} />

      {/* Right Panel */}
      <div className="w-[360px] border-l border-[var(--bg-border)] bg-[var(--bg-surface)] flex flex-col flex-shrink-0">
        <TabBar tabs={["FINDINGS", "STATE", "AUTOPSY"] as const} active={rightTab} onChange={setRightTab} />
        {rightTab === "FINDINGS" && <FindingsTab conflicts={conflicts} onSelect={handleSelectConflict} />}
        {rightTab === "STATE" && <StateTab units={units} activeUnit={activeUnit} />}
        {rightTab === "AUTOPSY" && <AutopsyTab conflictId={selectedConflictId} onJumpToUnit={handleJumpToUnit} />}
      </div>
    </div>
  );
}
