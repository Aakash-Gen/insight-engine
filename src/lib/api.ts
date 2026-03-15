/**
 * ResearchMind API client — typed wrappers around all backend endpoints.
 * All mutating/authenticated requests attach the Supabase JWT as a Bearer token.
 */

import { supabase } from '@/lib/supabase';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Types (mirroring backend schemas)
// ---------------------------------------------------------------------------

export interface StartResearchRequest {
  topic: string;
  depth: 'quick' | 'standard' | 'deep';
  // user_id removed — backend extracts it from the JWT
}

export interface ResearchResponse {
  research_id: string;
  status: string;
  message: string;
}

export interface ReportSection {
  title: string;
  content: string;
  sources: string[];
}

export interface QualityBreakdown {
  source_diversity: number;
  recency: number;
  depth: number;
  cross_validation: number;
}

export interface ReportResponse {
  research_id: string;
  title: string;
  executive_summary: string;
  key_findings: string[];
  sections: ReportSection[];
  conflicting_perspectives: string;
  conclusion: string;
  sources: { url: string; title: string }[];
  overall_confidence: number;
  quality_breakdown: QualityBreakdown | null;
  created_at: string | null;
}

export interface ReportListItem {
  research_id: string;
  title: string;
  overall_confidence: number;
  depth: string;
  created_at: string | null;
}

export interface AgentLogEvent {
  research_id: string;
  agent: string;
  status: string;
  message: string;
  timestamp: string;
}

export interface CompletionEvent {
  type: 'complete';
  research_id: string;
  status: string;
}

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

/** Returns the current user's JWT access token, or null if not authenticated. */
async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

/** Returns Authorization header object, throws if no active session. */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  if (!token) throw new Error('Not authenticated.');
  return { Authorization: `Bearer ${token}` };
}

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`API ${response.status}: ${text}`);
  }
  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Research endpoints
// ---------------------------------------------------------------------------

/** POST /research/start — kick off a research session. */
export async function startResearch(payload: StartResearchRequest): Promise<ResearchResponse> {
  return request<ResearchResponse>('/research/start', {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(payload),
  });
}

/** POST /research/{id}/override — send human guidance mid-session. */
export async function sendOverride(researchId: string, message: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/research/${researchId}/override`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify({ message }),
  });
}

/**
 * GET /research/{id}/stream — subscribe to SSE log events.
 *
 * Auth: JWT is passed as a ?token= query param because the native EventSource
 * API does not support custom headers. The backend validates it identically.
 *
 * @returns A cleanup function that closes the EventSource.
 */
export async function streamResearch(
  researchId: string,
  onLog: (event: AgentLogEvent) => void,
  onComplete: (event: CompletionEvent) => void,
  onError: (error: Event) => void,
  onToken?: (agent: string, text: string) => void,
): Promise<() => void> {
  const token = await getAccessToken();
  if (!token) throw new Error('Not authenticated.');

  const url = `${BASE_URL}/research/${researchId}/stream?token=${encodeURIComponent(token)}`;
  const es = new EventSource(url);

  es.addEventListener('log', (e: MessageEvent) => {
    try { onLog(JSON.parse(e.data) as AgentLogEvent); } catch { /* ignore */ }
  });

  es.addEventListener('complete', (e: MessageEvent) => {
    try { onComplete(JSON.parse(e.data) as CompletionEvent); } catch { /* ignore */ }
    es.close();
  });

  es.addEventListener('token', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      onToken?.(data.agent as string, data.text as string);
    } catch { /* ignore */ }
  });

  es.addEventListener('error', (e: Event) => {
    onError(e);
    es.close();
  });

  return () => es.close();
}

// ---------------------------------------------------------------------------
// Reports endpoints
// ---------------------------------------------------------------------------

/** GET /reports/{id} — fetch a completed report (no auth required). */
export async function getReport(researchId: string): Promise<ReportResponse> {
  return request<ReportResponse>(`/reports/${researchId}`);
}

/** GET /reports/user/{userId} — list all reports for the authenticated user. */
export async function listReports(userId: string): Promise<ReportListItem[]> {
  return request<ReportListItem[]>(`/reports/user/${userId}`, {
    headers: await authHeaders(),
  });
}

/** DELETE /reports/{id} — soft-delete a report (owner only). */
export async function deleteReport(researchId: string): Promise<{ status: string; research_id: string }> {
  return request<{ status: string; research_id: string }>(`/reports/${researchId}`, {
    method: 'DELETE',
    headers: await authHeaders(),
  });
}

/**
 * GET /reports/{id}/export?format=md — download report as Markdown or plain text.
 * Returns a Blob suitable for triggering a browser download.
 */
export async function exportReport(researchId: string, format: 'md' | 'txt' = 'md'): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/reports/${researchId}/export?format=${format}`);
  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`API ${response.status}: ${text}`);
  }
  return response.blob();
}

/** POST /reports/{id}/ask — ask a follow-up question about a completed report. */
export async function askReport(researchId: string, question: string): Promise<{ answer: string; research_id: string }> {
  return request<{ answer: string; research_id: string }>(`/reports/${researchId}/ask`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

// ---------------------------------------------------------------------------
// Templates endpoints
// ---------------------------------------------------------------------------

export interface ResearchTemplate {
  id: string;
  title: string;
  description: string;
  topic_template: string;
  depth: 'quick' | 'standard' | 'deep';
  example_topic: string;
  tags: string[];
}

/** GET /templates — list all research templates. */
export async function listTemplates(): Promise<ResearchTemplate[]> {
  return request<ResearchTemplate[]>('/templates');
}

/** GET /templates/{id} — fetch a single template by ID. */
export async function getTemplate(templateId: string): Promise<ResearchTemplate> {
  return request<ResearchTemplate>(`/templates/${templateId}`);
}

/** GET /health — backend health check. */
export async function healthCheck(): Promise<{ status: string; model: string }> {
  return request<{ status: string; model: string }>('/health');
}
