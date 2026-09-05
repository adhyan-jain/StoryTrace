"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { getConflicts, getEntities, getOverview, getReport, getScenes, getVersionDiff, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TabBar } from "@/components/ui/TabBar";
import { diffStatusColor } from "@/components/ui/SeverityBadge";
import { ChapterList } from "@/components/Analysis/LeftPanel/ChapterList";
import { EntityList } from "@/components/Analysis/LeftPanel/EntityList";
import { SceneViewer } from "@/components/Analysis/CenterPanel/SceneViewer";
import { FindingsTab } from "@/components/Analysis/RightPanel/FindingsTab";
import { StateTab } from "@/components/Analysis/RightPanel/StateTab";
import { AutopsyTab } from "@/components/Analysis/RightPanel/AutopsyTab";
import { VersionDiffTab } from "@/components/Analysis/RightPanel/VersionDiffTab";
import { UploadProgress } from "@/components/Upload/UploadProgress";
import type { ConflictWithVerdict, Entity, NarrativeUnit, OverviewResponse } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;
const STALL_THRESHOLD_MS = 30000;

function Header({
  id,
  overview,
  entityCount,
  findingCount,
}: {
  id: string;
  overview: OverviewResponse | null;
  entityCount: number;
  findingCount: number;
}) {
  const router = useRouter();

  async function handleDownloadReport() {
    try {
      const markdown = await getReport(id);
      const blob = new Blob([markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `storytrace-report-${id}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Best-effort -- a failed download isn't worth a blocking error state.
    }
  }

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
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={handleDownloadReport}
          className="text-xs text-[var(--text-secondary)] border border-[var(--bg-border)] rounded-md px-2.5 py-1.5 hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          Download report
        </button>
        <button
          onClick={() => {
            localStorage.removeItem("storytrace_active_id");
            router.push("/dashboard");
          }}
          className="text-xs text-[var(--text-secondary)] border border-[var(--bg-border)] rounded-md px-2.5 py-1.5 hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          My Documents
        </button>
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const projectId = searchParams.get("project");
  const versionNumber = searchParams.get("version") ? Number(searchParams.get("version")) : null;
  const hasVersionComparison = Boolean(projectId && versionNumber && versionNumber > 1);

  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [units, setUnits] = useState<NarrativeUnit[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [conflicts, setConflicts] = useState<ConflictWithVerdict[]>([]);
  const [diffColorByUnit, setDiffColorByUnit] = useState<Record<string, string> | undefined>(undefined);

  const [leftTab, setLeftTab] = useState<"CHAPTERS" | "ENTITIES">("CHAPTERS");
  const [rightTab, setRightTab] = useState<"FINDINGS" | "STATE" | "AUTOPSY" | "DIFF">("FINDINGS");
  const [activeUnitId, setActiveUnitId] = useState<string | null>(null);
  const [selectedConflictId, setSelectedConflictId] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) router.replace("/login");
  }, [authLoading, user, router]);

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

    if (projectId && versionNumber) {
      try {
        const diff = await getVersionDiff(projectId, versionNumber);
        if (diff.has_previous) {
          const colorByUnit: Record<string, string> = {};
          for (const c of diff.conflicts) {
            if (c.diff_status === "new" || c.diff_status === "recurring") {
              colorByUnit[c.current_unit_id] = diffStatusColor(c.diff_status);
            }
          }
          setDiffColorByUnit(colorByUnit);
        }
      } catch {
        // Comparison is a bonus view -- a failure here shouldn't block the
        // rest of the analysis page from rendering.
      }
    }
  }, [id, searchParams, projectId, versionNumber]);

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

  if (authLoading || !user) return null;

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
      <div className="flex flex-col h-screen bg-[var(--bg-base)] overflow-hidden">
        <Header id={id} overview={overview} entityCount={0} findingCount={0} />
        <div className="flex flex-1 overflow-hidden">
          <div className="w-[280px] border-r border-[var(--bg-border)] bg-[var(--bg-surface)] flex flex-col" />
          <UploadProgress overview={overview} startedAt={startedAt.current} stalled={stalled} />
          <div className="w-[360px] border-l border-[var(--bg-border)] bg-[var(--bg-surface)]" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[var(--bg-base)] overflow-hidden">
      <Header id={id} overview={overview} entityCount={entities.length} findingCount={conflicts.length} />
      <div className="flex flex-1 overflow-hidden">
      {/* Left Panel */}
      <div className="w-[280px] border-r border-[var(--bg-border)] bg-[var(--bg-surface)] flex flex-col flex-shrink-0">
        <TabBar tabs={["CHAPTERS", "ENTITIES"] as const} active={leftTab} onChange={setLeftTab} />
        {leftTab === "CHAPTERS" ? (
          <ChapterList
            units={units}
            activeUnitId={activeUnitId}
            onSelect={setActiveUnitId}
            diffColorByUnit={diffColorByUnit}
          />
        ) : (
          <EntityList id={id} entities={entities} />
        )}
      </div>

      {/* Center Panel */}
      <SceneViewer unit={activeUnit} onSelectConflict={handleSelectConflict} />

      {/* Right Panel */}
      <div className="w-[360px] border-l border-[var(--bg-border)] bg-[var(--bg-surface)] flex flex-col flex-shrink-0">
        <TabBar
          tabs={
            hasVersionComparison
              ? (["FINDINGS", "STATE", "AUTOPSY", "DIFF"] as const)
              : (["FINDINGS", "STATE", "AUTOPSY"] as const)
          }
          active={rightTab}
          onChange={setRightTab}
        />
        {rightTab === "FINDINGS" && <FindingsTab conflicts={conflicts} onSelect={handleSelectConflict} />}
        {rightTab === "STATE" && <StateTab units={units} activeUnit={activeUnit} />}
        {rightTab === "AUTOPSY" && <AutopsyTab conflictId={selectedConflictId} onJumpToUnit={handleJumpToUnit} />}
        {rightTab === "DIFF" && projectId && versionNumber && (
          <VersionDiffTab projectId={projectId} versionNumber={versionNumber} />
        )}
      </div>
      </div>
    </div>
  );
}
