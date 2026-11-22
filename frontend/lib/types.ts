// Mirrors backend/app/schemas. Field names must not drift.
export type Level = "P2" | "P3" | "P4";
export type Subject = "mathematics" | "english";
export type WorksheetStatus = "uploaded" | "processing" | "ready" | "needs_review" | "failed";
export type Mastery = "not_started" | "needs_practice" | "developing" | "confident";
export type FailureReason = "unreadable" | "wrong_subject" | "too_long" | "unsupported_file" | "service_unavailable";

export interface ParentAccount { id: string; email: string; displayName: string; createdAt: string }
export interface ChildProfile { id: string; parentId: string; username: string; level: Level; createdAt: string }
export interface CreateChildRequest { username: string; level: Level; pin: string }

export interface WorkedExample { prompt: string; steps: string[]; answer: string }
export interface PracticeQuestion { id: string; prompt: string; choices: [string, string, string, string] }

export interface WorksheetResult {
  id: string; childId: string; subject: Subject; level: Level; topic: string;
  status: WorksheetStatus; explanation: string; workedExample: WorkedExample | null;
  practiceQuestions: PracticeQuestion[]; parentNote: string; failureReason?: FailureReason; createdAt: string;
}
export type WorksheetSummary = Pick<WorksheetResult, "id" | "subject" | "topic" | "status" | "createdAt">;
export type DashboardWorksheet = WorksheetSummary & { parentNote: string; failureReason?: FailureReason };

export interface PracticeFeedback {
  id: string; questionId: string; isCorrect: boolean; correctChoice: string;
  explanation: string; feedback: string; submittedAt: string;
}
export interface TopicProgress {
  childId: string; subject: Subject; level: Level; topic: string; mastery: Mastery;
  questionsAttempted: number; questionsCorrect: number; lastPractisedAt: string | null;
}
export interface ParentDashboard {
  child: Pick<ChildProfile, "id" | "username" | "level">;
  topics: TopicProgress[];
  recentWorksheets: DashboardWorksheet[];
}
export interface WorksheetStatusResponse {
  id: string; status: WorksheetStatus; parentNote: string; failureReason?: FailureReason; canRetry: boolean;
}
