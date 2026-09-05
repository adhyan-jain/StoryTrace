import type {
  AuthResponse,
  AutopsyResponse,
  ConflictWithVerdict,
  Entity,
  NarrativeUnit,
  OverviewResponse,
  ProjectSummary,
  ProjectVersion,
  UploadResponse,
  User,
  VersionDiffResponse,
} from "./types";
import { getStoredToken, handleSessionExpired } from "./auth";

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
  const token = getStoredToken();
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
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
    // A 401 on a request that carried a token means the token expired or was
    // rejected -- bounce to /login rather than letting every caller up the
    // stack invent its own handling. A 401 with no token (e.g. bad
    // credentials on /auth/login) is a normal auth failure, not an expired
    // session, so it's left for the caller to show as a form error.
    if (res.status === 401 && token) {
      handleSessionExpired();
    }
    throw new ApiError(detail, res.status);
  }
  if (res.headers.get("content-type")?.includes("text/markdown")) {
    return res.text() as Promise<T>;
  }
  return res.json() as Promise<T>;
}

// -- Auth --------------------------------------------------------------

export async function signup(email: string, password: string): Promise<AuthResponse> {
  return request("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<User> {
  return request("/auth/me");
}

// -- Documents / pipeline ------------------------------------------------

export async function uploadDocument(file: File, projectId?: string): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (projectId) form.append("project_id", projectId);
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

export async function getReport(id: string): Promise<string> {
  return request(`/screenplay/${id}/report`);
}

// -- Projects / versions / diff ------------------------------------------

export async function listProjects(): Promise<ProjectSummary[]> {
  return request("/projects");
}

export async function listVersions(projectId: string): Promise<ProjectVersion[]> {
  return request(`/projects/${projectId}/versions`);
}

export async function getVersionDiff(projectId: string, versionNumber: number): Promise<VersionDiffResponse> {
  return request(`/projects/${projectId}/versions/${versionNumber}/diff`);
}

export async function renameProject(projectId: string, title: string): Promise<void> {
  await request(`/projects/${projectId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function deleteProject(projectId: string): Promise<void> {
  await request(`/projects/${projectId}`, { method: "DELETE" });
}

export { ApiError };
