export type PipelineStatus = "parsing" | "extracting" | "detecting" | "investigating" | "complete" | "error";

export type Severity = "critical" | "warning" | "info";
export type VerdictStatus = "verified" | "resolved" | "uncertain" | "intentional" | "uninvestigated";
export type EntityType = "character" | "prop" | "location";

export interface OverviewResponse {
  total_units: number;
  units_extracted: number;
  candidates_detected: number;
  verdicts_complete: number;
  status: PipelineStatus;
  error: string | null;
  document_title: string | null;
}

export interface UnitStateEvent {
  entity_id: string;
  entity_name: string;
  attribute: string;
  value: string;
  confidence: number;
  raw_excerpt: string;
  conflict_id: string | null;
  severity: Severity | null;
}

export interface NarrativeUnit {
  unit_id: string;
  title: string;
  unit_type: string;
  sequence_number: number;
  page_start: number;
  page_end: number;
  raw_text: string;
  severity: Severity | "resolved" | null;
  state_events: UnitStateEvent[];
}

export interface Entity {
  entity_id: string;
  name: string;
  type: EntityType;
  finding_count: number;
}

export interface ConflictWithVerdict {
  id: string;
  entity_id: string;
  entity_name: string;
  attribute: string;
  prior_unit_id: string;
  prior_excerpt: string;
  prior_page: number | null;
  current_unit_id: string;
  current_excerpt: string;
  current_page: number | null;
  description: string;
  status: VerdictStatus;
  severity: Severity | null;
  confidence: number | null;
}

export type InvestigationStep =
  | { step: "action"; tool: string; args: Record<string, unknown> }
  | { step: "observation"; tool: string; result: unknown }
  | { step: "verdict"; verdict: Record<string, unknown> }
  | { step: "error"; message: string }
  | { step: "note"; message: string };

export interface AutopsyConflict {
  id: string;
  entity_id: string;
  entity_name: string;
  attribute: string;
  prior_unit_id: string;
  prior_excerpt: string;
  prior_page: number | null;
  current_unit_id: string;
  current_excerpt: string;
  current_page: number | null;
  description: string;
}

export interface AutopsyVerdict {
  status: VerdictStatus;
  severity: Severity;
  explanation: string;
  confidence: number;
}

export interface AutopsyResponse {
  conflict: AutopsyConflict;
  verdict: AutopsyVerdict | null;
  steps: InvestigationStep[];
}
