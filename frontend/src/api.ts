export type User = {
  id: number;
  username: string;
  is_admin: boolean;
};

export type Language = {
  id: string;
  display_name: string;
  implemented: boolean;
  available: boolean;
  runtime_detected: boolean;
  reason: string | null;
};

export type ProblemMeta = {
  slug: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  time_limit_ms: number;
  memory_limit_mb: number;
  tags: string[];
  solved: boolean;
  attempted: boolean;
};

export type Signature = {
  class_name: string;
  method: string;
  params: { name: string; type: string }[];
  return_type: string;
  compare: "exact" | "any_order";
};

export type ProblemDetail = ProblemMeta & {
  statement_md: string;
  signature: Signature;
  starter: Record<string, string>;
};

export type Submission = {
  id: number;
  problem_slug: string;
  language: string;
  status: string;
  verdict: string | null;
  details: Record<string, unknown> | null;
  compile_log: string | null;
  time_ms: number | null;
  created_at: string;
  judged_at: string | null;
  source?: string | null;
  username?: string;
  user_id?: number;
};

export type RunResult = {
  kind: "test";
  verdict: string;
  details: Record<string, unknown> | null;
  compile_log: string | null;
  time_ms: number | null;
  public_count: number;
};

export type RankEntry = {
  rank: number;
  username: string;
  time_ms: number;
  is_me: boolean;
};

export type Ranking = {
  slug: string;
  language: string;
  total: number;
  mine: RankEntry | null;
  entries: RankEntry[];
};

export type ScoreRow = {
  slug: string;
  title: string;
  language: string;
  time_ms: number;
  rank: number;
  total: number;
};

export type AdminStats = {
  users: number;
  submissions: number;
  accepted: number;
  problems: number;
  by_problem: { slug: string; title: string; submissions: number; accepted: number }[];
};

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
    }
  } catch {
    /* ignore */
  }
  return res.statusText;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { credentials: "include", ...init, headers });
  if (res.status === 401) {
    throw Object.assign(new Error("unauthorized"), { status: 401 });
  }
  if (!res.ok) {
    throw Object.assign(new Error(await parseError(res)), { status: res.status });
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const Auth = {
  me: () => api<User>("/api/auth/me"),
  login: (username: string, password: string) =>
    api<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  register: (username: string, password: string) =>
    api<User>("/api/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => api<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
};

export const Problems = {
  list: () => api<ProblemMeta[]>("/api/problems"),
  get: (slug: string) => api<ProblemDetail>(`/api/problems/${slug}`),
  submit: (slug: string, language: string, source: string) =>
    api<Submission>(`/api/problems/${slug}/submit`, {
      method: "POST",
      body: JSON.stringify({ language, source }),
    }),
  run: (slug: string, language: string, source: string) =>
    api<RunResult>(`/api/problems/${slug}/run`, {
      method: "POST",
      body: JSON.stringify({ language, source }),
    }),
  ranking: (slug: string, language: string) =>
    api<Ranking>(`/api/problems/${slug}/ranking?language=${encodeURIComponent(language)}`),
  getDraft: (slug: string, language: string) =>
    api<{ language: string; source: string; from_starter: boolean; updated_at: string | null }>(
      `/api/problems/${slug}/draft?language=${encodeURIComponent(language)}`,
    ),
  saveDraft: (slug: string, language: string, source: string) =>
    api(`/api/problems/${slug}/draft`, {
      method: "PUT",
      body: JSON.stringify({ language, source }),
    }),
};

export const Scores = {
  mine: () => api<ScoreRow[]>("/api/scores"),
};

export const Submissions = {
  list: (slug?: string) => api<Submission[]>(`/api/submissions${slug ? `?slug=${encodeURIComponent(slug)}` : ""}`),
  get: (id: number) => api<Submission>(`/api/submissions/${id}`),
};

export const Languages = {
  list: () => api<Language[]>("/api/languages"),
};

export const Admin = {
  stats: () => api<AdminStats>("/api/admin/stats"),
  submissions: (q?: { slug?: string; username?: string; language?: string }) => {
    const params = new URLSearchParams();
    if (q?.slug) params.set("slug", q.slug);
    if (q?.username) params.set("username", q.username);
    if (q?.language) params.set("language", q.language);
    const qs = params.toString();
    return api<Submission[]>(`/api/admin/submissions${qs ? `?${qs}` : ""}`);
  },
  submission: (id: number) => api<Submission>(`/api/admin/submissions/${id}`),
  create: (body: unknown) => api("/api/admin/problems", { method: "POST", body: JSON.stringify(body) }),
  update: (slug: string, body: unknown) =>
    api(`/api/admin/problems/${slug}`, { method: "PUT", body: JSON.stringify(body) }),
  replaceTests: (slug: string, tests: unknown[]) =>
    api(`/api/admin/problems/${slug}/tests`, { method: "PUT", body: JSON.stringify({ tests }) }),
  appendTests: (slug: string, tests: unknown[]) =>
    api(`/api/admin/problems/${slug}/tests:append`, { method: "POST", body: JSON.stringify({ tests }) }),
  reload: () => api<{ ok: boolean; count: number }>("/api/admin/reload", { method: "POST" }),
};
