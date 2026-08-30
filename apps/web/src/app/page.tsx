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
    <div className="flex h-screen bg-[#fcfcfc] text-gray-900 overflow-hidden font-sans">
      {/* Left Column: Scene Navigator */}
      <div className="w-80 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-sm font-semibold tracking-wide text-gray-900">STORYTRACE</h1>
          <p className="text-xs text-gray-500 mt-1">reverend-insanity-c1-c500.epub</p>
        </div>
        {cachedFindings.length > 0 && (
          <Link
            href={flaggedOnly ? `/?unit=${activeUnit?.unit_id ?? ""}` : `/?unit=${activeUnit?.unit_id ?? ""}&flagged=1`}
            prefetch={false}
            className={clsx(
              "mx-3 mt-3 flex items-center justify-between rounded-md border px-3 py-2 text-xs font-medium transition-colors",
              flaggedOnly ? "border-red-200 bg-red-50 text-red-700" : "border-gray-200 text-gray-600 hover:bg-gray-50"
            )}
          >
            <span className="flex items-center gap-1.5">
              <TriangleAlert className="w-3.5 h-3.5" />
              {flaggedOnly ? "Showing flagged only" : "Show flagged chapters only"}
            </span>
            <span className={clsx("rounded-full px-1.5 py-0.5", flaggedOnly ? "bg-red-100" : "bg-gray-100")}>
              {findingsByUnit.size}
            </span>
          </Link>
        )}
        <div className="flex-1 overflow-y-auto p-2">
          {visibleUnits.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-gray-400">No flagged chapters in the first 100.</p>
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
                  "px-3 py-2 text-sm rounded-md mb-1 cursor-pointer flex justify-between items-center group transition-colors block",
                  isActive
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : findings
                    ? "text-red-600 hover:bg-red-50"
                    : "text-gray-600 hover:bg-gray-100"
                )}
              >
                <span className="flex items-center gap-1.5 truncate pr-2">
                  {findings && <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" aria-hidden="true" />}
                  <span className="truncate">{unit.title}</span>
                </span>
                {isActive ? (
                  <BookOpen className="w-4 h-4 text-blue-500 flex-shrink-0" />
                ) : findings ? (
                  <span className="text-[11px] text-red-500 flex-shrink-0">{findings.length}</span>
                ) : null}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Center Column: Screenplay Text */}
      <div className="flex-1 flex flex-col bg-[#f5f5f5] shadow-inner">
        <div className="p-4 border-b border-gray-200 bg-white flex justify-between items-center">
          <div className="flex gap-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
            <span>Pg. {activeUnit?.page_start} - {activeUnit?.page_end}</span>
            <span className="text-gray-300">|</span>
            <span>{activeUnit?.unit_type === 'chapter' ? 'Chapter' : 'Passage'} {activeUnit?.sequence_number}</span>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-12 flex justify-center">
          <div className="w-full max-w-2xl bg-white shadow-sm border border-gray-200 p-12 min-h-full font-serif text-[15px] leading-relaxed text-gray-800 whitespace-pre-wrap">
            <h2 className="text-xl font-bold mb-6 font-sans text-black">{activeUnit?.title}</h2>
            {/* raw_text keeps its own leading heading line for exact-provenance
                fidelity (see CLAUDE.md: raw_excerpt must be exact); drop just
                that one duplicate line from the on-screen body, not the data. */}
            {activeUnit?.raw_text.startsWith(activeUnit.title)
              ? activeUnit.raw_text.slice(activeUnit.title.length).replace(/^\n/, "")
              : activeUnit?.raw_text}
          </div>
        </div>
      </div>

      {/* Right Column: Findings/Autopsy */}
      <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-sm font-semibold">Continuity Findings</h2>
          <span
            className={clsx(
              "px-2 py-0.5 rounded-full text-xs font-medium",
              cachedFindings.length > 0 ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"
            )}
          >
            {cachedFindings.length} {cachedFindings.length === 1 ? "Issue" : "Issues"}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          {cachedFindings.length === 0 ? (
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 text-center">
              <p className="text-sm text-gray-500">Extraction and state detection for Reverend Insanity is pending integration with the LLM layer.</p>
              <p className="text-xs text-gray-400 mt-2">Parsed {units.length} total narrative units.</p>
            </div>
          ) : activeFindings.length === 0 ? (
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 text-center">
              <p className="text-sm text-gray-500">No continuity issues found in this chapter.</p>
            </div>
          ) : (
            activeFindings.map((finding) => (
              <div key={finding.id} className="p-4 rounded-lg border border-red-200 bg-red-50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-red-700">{finding.severity}</span>
                  <span className="text-xs text-gray-500">{finding.status}</span>
                </div>
                <p className="text-sm text-gray-800">{finding.description}</p>
                <p className="text-xs text-gray-400 mt-2">Entity: {finding.entity_id} · Confidence {(finding.confidence * 100).toFixed(0)}%</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
