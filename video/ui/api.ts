import type { Props } from "../src/lib/types";

export type FormatInfo = {
  format: string;
  approved: boolean;
  problem: string | null;
  video: string[];
};

export type ProjectInfo = { id: string; title: string; formats: FormatInfo[] };

export type ScriptScene = {
  id: string;
  type: string;
  narration: string;
  onScreenText?: string;
  kicker?: string;
  emphasis?: string[];
  bullets?: string[];
  segments?: { language?: string; text: string; pauseAfterMs?: number }[];
  visual?: { kind: string; label?: string; sub?: string };
  durationTargetSec?: number;
  /** Khẳng định kiểm chứng được, `source` là số thứ tự (từ 1) trong meta.sources. */
  claims?: { text: string; source: number }[];
  [key: string]: unknown;
};

export type Script = {
  meta: { title: string; [key: string]: unknown };
  scenes: ScriptScene[];
  [key: string]: unknown;
};

export type FactItem = {
  sceneId: string;
  claim: string;
  verdict: "ok" | "doubtful" | "wrong" | "unsupported";
  note?: string;
};

export type Source = { index: number; title: string; url?: string; accessedAt?: string };

export type LinkStatus = { index: number; url: string; status: string; ok: boolean };

export type ReviewState = {
  project: string;
  format: string;
  title: string;
  script: Script;
  sources: Source[];
  assumptions: string[];
  hasResearch: boolean;
  /** Mô tả chuyển động từng cảnh (sceneId → các dòng theo thứ tự xảy ra). */
  motion: Record<string, string[]>;
  /** Ghi chú animation của người duyệt (sceneId → ghi chú). */
  notes: Record<string, string>;
  errors: string[];
  claimIssues: string[];
  factcheck: { items?: FactItem[] } | null;
  factcheckStale: boolean;
  approval: { status?: string; approvedAt?: string; note?: string };
  approvalProblem: string | null;
  aspects: string[];
  aspect: string;
  llm: string;
};

export type Job = {
  id: string;
  title: string;
  status: "running" | "done" | "failed";
  log: string[];
  current?: string;
  code: number | null;
  command: string;
};

async function call<T>(method: "GET" | "POST", url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error ?? `Lỗi ${response.status}`);
  }
  return data as T;
}

export const api = {
  projects: () => call<ProjectInfo[]>("GET", "/api/projects"),
  review: (project: string, format: string) =>
    call<ReviewState>(
      "GET",
      `/api/review?project=${encodeURIComponent(project)}&format=${encodeURIComponent(format)}`,
    ),
  // Chỉ dùng được khi kịch bản đã duyệt; server trả 403 nếu chưa.
  preview: (project: string, format: string, aspect: string) =>
    call<{ props: Props | null; errors: string[] }>("POST", "/api/preview", {
      project,
      format,
      aspect,
    }),
  saveNotes: (project: string, format: string, notes: Record<string, string>) =>
    call<Record<string, string>>("POST", "/api/notes", { project, format, notes }),
  check: (project: string, format: string, script: Script) =>
    call<{ errors: string[] }>("POST", "/api/check", { project, format, script }),
  links: (project: string, format: string) =>
    call<LinkStatus[]>("POST", "/api/links", { project, format }),
  research: (project: string, format: string) =>
    call<{ text: string }>(
      "GET",
      `/api/research?project=${encodeURIComponent(project)}&format=${encodeURIComponent(format)}`,
    ),
  save: (project: string, format: string, script: Script) =>
    call<ReviewState>("POST", "/api/script", { project, format, script }),
  approve: (body: {
    project: string;
    format: string;
    note: string;
    skipFactcheck: boolean;
    force: boolean;
  }) =>
    call<{ ok: boolean; message: string; state: ReviewState }>("POST", "/api/approve", body),
  reject: (project: string, format: string, note: string) =>
    call<{ ok: boolean; message: string; state: ReviewState }>("POST", "/api/reject", {
      project,
      format,
      note,
    }),
  startJob: (body: Record<string, unknown>) => call<Job>("POST", "/api/jobs", body),
  job: (id: string) => call<Job>("GET", `/api/jobs/${id}`),
};
