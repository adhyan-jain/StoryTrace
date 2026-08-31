import { BookOpen, TriangleAlert } from "lucide-react";
import clsx from "clsx";
import fs from 'fs';
import path from 'path';
import Link from 'next/link';

interface NarrativeUnit {
  unit_id: string;
  story_universe_id: string;
  document_id: string;
  unit_type: string;
  sequence_number: number;
  title: string;
  page_start: number;
  page_end: number;
  raw_text: string;
}

interface ContinuityFinding {
  id: string;
  unit_id: string;
  entity_id: string;
  description: string;
  severity: "critical" | "warning" | "info";
  status: string;
  confidence: number;
}

// Read once at module load instead of on every request/prefetch: this file is
// ~6MB, and re-parsing it per-render (including for each sidebar link's
// prefetch) was pegging the server at 100% CPU and starving real navigations.
let cachedUnits: NarrativeUnit[] = [];
try {
  const dataPath = path.join(process.cwd(), '../../data/processed/ri_parsed.json');
  const rawData = fs.readFileSync(dataPath, 'utf8');
  cachedUnits = JSON.parse(rawData);
} catch (error) {
  console.error("Could not load RI data:", error);
}

// Optional: only present once candidate detection / investigation has actually
// run for this document. Absent (rather than faked) until then, per the
// project's no-fake-intelligence rule.
let cachedFindings: ContinuityFinding[] = [];
try {
  const findingsPath = path.join(process.cwd(), '../../data/processed/ri_findings.json');
  cachedFindings = JSON.parse(fs.readFileSync(findingsPath, 'utf8'));
} catch {
  cachedFindings = [];
}

export default async function Home({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  const units = cachedUnits;

  // Display the first 100 chapters to avoid freezing the UI
  const displayUnits = units.slice(0, 100);

  const findingsByUnit = new Map<string, ContinuityFinding[]>();
  for (const finding of cachedFindings) {
    const list = findingsByUnit.get(finding.unit_id) ?? [];
    list.push(finding);
    findingsByUnit.set(finding.unit_id, list);
  }

  const params = await searchParams;
  const flaggedOnly = params?.flagged === "1";
  const visibleUnits = flaggedOnly ? displayUnits.filter(u => findingsByUnit.has(u.unit_id)) : displayUnits;

  // Get active unit from URL, default to chapter 1 (index 2 usually for RI)
  const activeUnitId = params?.unit;
  const activeUnit = displayUnits.find(u => u.unit_id === activeUnitId) || displayUnits[2] || displayUnits[0];
  const activeFindings = activeUnit ? findingsByUnit.get(activeUnit.unit_id) ?? [] : [];

  return (
    <div className="flex h-screen bg-background text-ink overflow-hidden font-[family-name:var(--font-ui)]">
      {/* Left Column: Chapter Navigator */}
      <div className="w-80 border-r border-line bg-chrome flex flex-col">
        <div className="px-4 pt-4 pb-3 border-b border-line">
          <h1 className="text-lg font-[family-name:var(--font-display)] italic tracking-tight text-ink">StoryTrace</h1>
          <p className="text-[11px] font-[family-name:var(--font-data)] text-ink-muted mt-0.5 tracking-wide">reverend-insanity-c1-c500.epub</p>
        </div>
        {cachedFindings.length > 0 && (
          <Link
            href={flaggedOnly ? `/?unit=${activeUnit?.unit_id ?? ""}` : `/?unit=${activeUnit?.unit_id ?? ""}&flagged=1`}
            prefetch={false}
            className={clsx(
              "mx-3 mt-3 flex items-center justify-between rounded-sm border px-3 py-2 text-xs font-medium transition-colors",
              flaggedOnly ? "border-flag/30 bg-flag-soft text-flag" : "border-line text-ink-muted hover:bg-black/[0.02]"
            )}
          >
            <span className="flex items-center gap-1.5">
              <TriangleAlert className="w-3.5 h-3.5" />
              {flaggedOnly ? "Showing flagged only" : "Show flagged chapters only"}
            </span>
            <span className={clsx("rounded-full px-1.5 py-0.5 font-[family-name:var(--font-data)]", flaggedOnly ? "bg-flag/10" : "bg-black/[0.04]")}>
              {findingsByUnit.size}
            </span>
          </Link>
        )}
        <div className="flex-1 overflow-y-auto py-2">
          {visibleUnits.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-ink-muted">No flagged chapters in the first 100.</p>
          )}
          {visibleUnits.map((unit) => {
            const findings = findingsByUnit.get(unit.unit_id);
            const isActive = unit.unit_id === activeUnit?.unit_id;
            return (
              <Link
                key={unit.unit_id}
                href={`/?unit=${unit.unit_id}${flaggedOnly ? "&flagged=1" : ""}`}
                prefetch={false}
                className={clsx(
                  "relative pl-4 pr-3 py-2 text-[13px] mb-px flex items-center gap-2.5 group transition-colors",
                  isActive ? "bg-accent-soft text-accent font-medium" : findings ? "text-flag hover:bg-flag-soft" : "text-ink-muted hover:bg-black/[0.025]"
                )}
              >
                {/* Signature: a red margin flag on the row, not just red text --
                    reads as a proofreader's mark on the manuscript, and doesn't
                    rely on color alone to say "this chapter has an issue". */}
                {findings && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 h-3.5 w-[3px] bg-flag rounded-r-sm"
                    aria-hidden="true"
                  />
                )}
                <span className="font-[family-name:var(--font-data)] text-[10px] text-ink-muted/70 w-6 text-right flex-shrink-0 tabular-nums">
                  {unit.sequence_number}
                </span>
                <span className="truncate flex-1">{unit.title}</span>
                {isActive ? (
                  <BookOpen className="w-3.5 h-3.5 text-accent flex-shrink-0" />
                ) : findings ? (
                  <span className="text-[10px] font-[family-name:var(--font-data)] text-flag/70 flex-shrink-0">{findings.length}</span>
                ) : null}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Center Column: Manuscript */}
      <div className="flex-1 flex flex-col bg-background">
        <div className="px-6 py-3 border-b border-line bg-chrome flex justify-between items-center">
          <div className="flex gap-3 text-[11px] font-[family-name:var(--font-data)] text-ink-muted uppercase tracking-wider">
            <span>Pg. {activeUnit?.page_start}–{activeUnit?.page_end}</span>
            <span className="text-line">/</span>
            <span>{activeUnit?.unit_type === 'chapter' ? 'Ch.' : 'Passage'} {activeUnit?.sequence_number}</span>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-12 py-10 flex justify-center">
          <article className="w-full max-w-2xl min-h-full font-[family-name:var(--font-reading)] text-[16px] leading-[1.85] text-ink whitespace-pre-wrap">
            <h2 className="text-[28px] font-[family-name:var(--font-display)] font-semibold leading-tight mb-8 text-ink not-italic">
              {activeUnit?.title}
            </h2>
            {/* raw_text keeps its own leading heading line for exact-provenance
                fidelity (see CLAUDE.md: raw_excerpt must be exact); drop just
                that one duplicate line from the on-screen body, not the data. */}
            {activeUnit?.raw_text.startsWith(activeUnit.title)
              ? activeUnit.raw_text.slice(activeUnit.title.length).replace(/^\n/, "")
              : activeUnit?.raw_text}
          </article>
        </div>
      </div>

      {/* Right Column: Continuity Findings */}
      <div className="w-96 border-l border-line bg-chrome flex flex-col">
        <div className="px-4 py-3.5 border-b border-line">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-[family-name:var(--font-display)] font-semibold text-ink">Continuity Findings</h2>
          </div>
          {cachedFindings.length > 0 && (
            <div className="flex items-center gap-3 mt-2 text-[11px] font-[family-name:var(--font-data)]">
              <span
                className={clsx(
                  "px-1.5 py-0.5 rounded-sm",
                  activeFindings.length > 0 ? "bg-flag-soft text-flag" : "bg-black/[0.04] text-ink-muted"
                )}
              >
                {activeFindings.length} in this chapter
              </span>
              <span className="text-ink-muted">{cachedFindings.length} total across the book</span>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {cachedFindings.length === 0 ? (
            <div className="bg-background p-4 rounded-sm border border-line text-center">
              <p className="text-sm text-ink-muted">Extraction and state detection for Reverend Insanity is pending integration with the LLM layer.</p>
              <p className="text-xs font-[family-name:var(--font-data)] text-ink-muted/70 mt-2">Parsed {units.length} total narrative units.</p>
            </div>
          ) : activeFindings.length === 0 ? (
            <div className="bg-background p-4 rounded-sm border border-line text-center">
              <p className="text-sm text-ink-muted">No continuity issues found in this chapter.</p>
            </div>
          ) : (
            activeFindings.map((finding) => (
              <div key={finding.id} className="pl-3 pr-4 py-3 border-l-2 border-flag bg-background rounded-r-sm">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-[family-name:var(--font-data)] font-medium uppercase tracking-wide text-flag">{finding.severity}</span>
                  <span className="text-[11px] font-[family-name:var(--font-data)] text-ink-muted">{finding.status}</span>
                </div>
                <p className="text-sm text-ink leading-snug">{finding.description}</p>
                <p className="text-[11px] font-[family-name:var(--font-data)] text-ink-muted/80 mt-2">{finding.entity_id} · {(finding.confidence * 100).toFixed(0)}% confidence</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
