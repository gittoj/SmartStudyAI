import type {
  ChildProfile, CreateChildRequest, ParentDashboard, PracticeFeedback, WorksheetResult, WorksheetSummary,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message); }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, { credentials: "include", ...init });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = typeof body === "object" && body !== null && "detail" in body ? (body as { detail: unknown }).detail : null;
    throw new ApiError(response.status, typeof detail === "string" ? detail : "Something went wrong. Please try again.");
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

const json = (method: string, body: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

export const login = (email: string, password: string) => request("/api/auth/login", json("POST", { email, password }));
export const logout = () => request<void>("/api/auth/logout", { method: "POST" });
export const listChildren = () => request<ChildProfile[]>("/api/children");
export const createChildProfile = (body: CreateChildRequest) => request<ChildProfile>("/api/children", json("POST", body));
export const selectChild = (childId: string, pin: string) => request<ChildProfile>(`/api/children/${childId}/select`, json("POST", { pin }));
export const getDashboard = (childId: string) => request<ParentDashboard>(`/api/dashboard/${childId}`);

export function uploadWorksheet(form: { childId: string; subject: string; topicHint?: string; file: File }) {
  const data = new FormData(); // multipart: file is binary, not JSON
  data.append("file", form.file);
  data.append("childId", form.childId);
  data.append("subject", form.subject);
  if (form.topicHint) data.append("topicHint", form.topicHint);
  return request<{ id: string }>("/api/worksheets", { method: "POST", body: data });
}

export const listReadyWorksheets = () => request<WorksheetSummary[]>("/api/practice/worksheets");
export const getPracticeWorksheet = (id: string) => request<WorksheetResult>(`/api/practice/worksheets/${id}`);
export const submitPracticeAnswer = (questionId: string, answer: string) =>
  request<PracticeFeedback>(`/api/practice/questions/${questionId}/answer`, json("POST", { answer }));
