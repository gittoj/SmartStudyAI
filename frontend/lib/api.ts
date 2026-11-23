import type {
  ReportReason,
  ChildProfile, ChildSummary, CreateChildRequest, ParentAccount, ParentDashboard, PracticeFeedback,
  WorksheetResult, WorksheetStatusResponse, WorksheetSummary,
} from "./types";

// "/" means same-origin: requests go to this site's /api/*, which proxy.ts forwards to the backend.
const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const GENERIC = "Something went wrong. Please try again.";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message); }
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : GENERIC;
}

function messageFrom(body: unknown): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Please check the details and try again.";
  }
  return GENERIC;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { credentials: "include", ...init });
  } catch {
    throw new ApiError(0, "We could not reach the server. Please try again.");
  }
  if (!response.ok) throw new ApiError(response.status, messageFrom(await response.json().catch(() => null)));
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

const json = (method: string, body: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

// Parent account
export const register = (email: string, displayName: string, password: string) =>
  request<ParentAccount>("/api/auth/register", json("POST", { email, displayName, password }));
export const login = (email: string, password: string) =>
  request<ParentAccount>("/api/auth/login", json("POST", { email, password }));
export const logout = () => request<void>("/api/auth/logout", { method: "POST" });
export const getMe = () => request<ParentAccount>("/api/auth/me");

// Children
export const listChildren = () => request<ChildProfile[]>("/api/children");
export const createChildProfile = (body: CreateChildRequest) => request<ChildProfile>("/api/children", json("POST", body));
export const deleteChildProfile = (childId: string, confirmUsername: string) =>
  request<void>(`/api/children/${childId}`, json("DELETE", { confirmUsername }));
export const selectChild = (childId: string, pin: string) =>
  request<ChildProfile>(`/api/children/${childId}/select`, json("POST", { pin }));

// Dashboard and worksheets
export const getDashboard = (childId: string) => request<ParentDashboard>(`/api/dashboard/${childId}`);

export function uploadWorksheet(form: { childId: string; subject: string; topicHint?: string; file: File }) {
  const data = new FormData(); // multipart: the file is binary, not JSON
  data.append("file", form.file);
  data.append("childId", form.childId);
  data.append("subject", form.subject);
  if (form.topicHint) data.append("topicHint", form.topicHint);
  return request<{ id: string }>("/api/worksheets", { method: "POST", body: data });
}
export const getWorksheetStatus = (id: string) => request<WorksheetStatusResponse>(`/api/worksheets/${id}`);
export const retryWorksheet = (id: string) => request<{ id: string }>(`/api/worksheets/${id}/retry`, { method: "POST" });

// Child practice
export const listReadyWorksheets = () => request<WorksheetSummary[]>("/api/practice/worksheets");
export const getPracticeWorksheet = (id: string) => request<WorksheetResult>(`/api/practice/worksheets/${id}`);
export const submitPracticeAnswer = (questionId: string, answer: string) =>
  request<PracticeFeedback>(`/api/practice/questions/${questionId}/answer`, json("POST", { answer }));
export const reportQuestion = (questionId: string, reason: ReportReason) =>
  request<void>(`/api/practice/questions/${questionId}/report`, json("POST", { reason }));
export const resolveReport = (childId: string, reportId: string, resolution: "confirmed" | "dismissed") =>
  request<void>(`/api/dashboard/${childId}/reports/${reportId}`, json("POST", { resolution }));
export const getPracticeMe = () => request<ChildSummary>("/api/practice/me");
export const childLogout = () => request<void>("/api/children/session/logout", { method: "POST" });
export const removeWorksheet = (id: string) => request<void>(`/api/worksheets/${id}`, { method: "DELETE" });
