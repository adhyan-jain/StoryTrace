import type {
  AutopsyResponse,
  ConflictWithVerdict,
  Entity,
  NarrativeUnit,
  OverviewResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(`Could not reach the StoryTrace API at ${API_BASE}. Is the backend running?`, 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON, keep statusText
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<{ story_universe_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return request("/screenplay/upload", { method: "POST", body: form });
}

export async function getOverview(id: string): Promise<OverviewResponse> {
  return request(`/screenplay/${id}/overview`);
}

export async function getScenes(id: string): Promise<NarrativeUnit[]> {
  return request(`/screenplay/${id}/scenes`);
}

export async function getEntities(id: string): Promise<Entity[]> {
  return request(`/screenplay/${id}/entities`);
}

export async function getConflicts(id: string): Promise<ConflictWithVerdict[]> {
  return request(`/screenplay/${id}/conflicts`);
}

export async function getAutopsy(conflictId: string): Promise<AutopsyResponse> {
  return request(`/conflict/${conflictId}/autopsy`);
}

export async function markIntentional(conflictId: string): Promise<void> {
  await request(`/conflict/${conflictId}/intentional`, { method: "POST" });
}

export { ApiError };
