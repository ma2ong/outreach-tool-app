export type Evidence = { claim: string; source: string };

export type Proposal = {
  id: number;
  kind: string;
  lead_no: number | null;
  company_en: string | null;
  country: string | null;
  inbox_message_id: number | null;
  title: string;
  reasoning: string;
  evidence: Evidence[] | null;
  payload: Record<string, any> | null;
  risk: "low" | "medium" | "high";
  status: string;
  reject_reason: string | null;
  decided_note: string | null;
  execution_result: string | null;
  backend: string | null;
  created_at: string;
};

export type AgentStatus = {
  last_at: string | null;
  last_result: string | null;
  unclassified: number;
  mission?: AgentMission;
  mission_progress?: {
    qualified_leads_imported_today: number;
    daily_target: number;
    remaining: number;
  };
  outcome?: {
    achieved: number; target: number; remaining: number; completion_pct: number; met: boolean;
    blockers: { code: string; message: string }[];
  };
  recent_runs?: {
    id: number; started_at: string; finished_at: string | null;
    status: string; result: Record<string, any>; incident: Record<string, any>; error: string;
  }[];
  safety_pause?: {
    code: string;
    reason: string;
    paused_at?: string;
    evidence?: Record<string, any>;
  } | null;
  takeovers?: {
    lead_no: number; channel: string; owner: "allen"; state: string;
    reason: string; source_message_id: number | null; next_action: string;
    due_at: string | null; updated_at: string; company_en: string; country: string | null;
  }[];
  pending: number;
  by_status: Record<string, number>;
  pending_by_risk: Record<string, number>;
  autonomy: Record<string, string>;
  llm: {
    calls: Record<string, any>;
    tasks: Record<string, { backend: string; ok: boolean; reason: string }>;
  };
  plan: {
    enabled: boolean;
    last_date: string | null;
    last_result: string | null;
    window: number[];
    attempts?: number;
    max_attempts?: number;
    retry_minutes?: number;
  };
};

export type AgentMission = {
  target_markets: string[];
  daily_qualified_leads: number;
  minimum_fit_score: number;
  auto_enroll: boolean;
};

export type AgentMeta = {
  kinds: string[];
  autonomy: string[];
  risks: string[];
  intents: Record<string, string>;
  quote_intents: string[];
  reject_reasons: Record<string, string>;
  backends: string[];
  tasks: string[];
};

async function jsonOrThrow(r: Response, what: string) {
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `${what} ${r.status}`);
  }
  return r.json();
}

export async function fetchAgentStatus(): Promise<AgentStatus> {
  return jsonOrThrow(await fetch("/api/agent/status"), "agent status");
}

export async function fetchAgentMission(): Promise<AgentMission> {
  return jsonOrThrow(await fetch("/api/agent/mission"), "agent mission");
}

export async function updateAgentMission(value: AgentMission): Promise<AgentMission> {
  return jsonOrThrow(await fetch("/api/agent/mission", {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  }), "agent mission");
}

export async function takeoverConversation(leadNo: number, channel: string, reason: string) {
  return jsonOrThrow(await fetch(`/api/agent/conversations/${leadNo}/${channel}/takeover`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  }), "conversation takeover");
}

export async function resumeConversation(leadNo: number, channel: string) {
  return jsonOrThrow(await fetch(`/api/agent/conversations/${leadNo}/${channel}/resume`, {
    method: "POST",
  }), "conversation resume");
}

export async function fetchAgentMeta(): Promise<AgentMeta> {
  return jsonOrThrow(await fetch("/api/agent/meta"), "agent meta");
}

export async function fetchProposals(params: Record<string, string> = {}): Promise<Proposal[]> {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  return jsonOrThrow(await fetch(`/api/agent/proposals${qs ? "?" + qs : ""}`), "proposals");
}

export async function approveProposal(id: number, payload?: Record<string, any>, note = ""): Promise<Proposal> {
  return jsonOrThrow(await fetch(`/api/agent/proposals/${id}/approve`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload, note }),
  }), "approve");
}

export async function rejectProposal(id: number, reason: string, note = ""): Promise<Proposal> {
  return jsonOrThrow(await fetch(`/api/agent/proposals/${id}/reject`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason, note }),
  }), "reject");
}

export async function setAutonomy(kind: string, level: string): Promise<{ autonomy: Record<string, string> }> {
  return jsonOrThrow(await fetch("/api/agent/autonomy", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, level }),
  }), "autonomy");
}

export async function setAgentBackend(task: string, backend: string) {
  return jsonOrThrow(await fetch("/api/agent/backend", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, backend }),
  }), "backend");
}

export async function startAgentRun(): Promise<{ job_id: string }> {
  return jsonOrThrow(await fetch("/api/agent/run", { method: "POST" }), "agent run");
}

export async function fetchAgentRunJob(jobId: string): Promise<{ status: string; result: any }> {
  return jsonOrThrow(await fetch(`/api/agent/run/${jobId}`), "agent job");
}

export async function setPlanEnabled(enabled: boolean) {
  return jsonOrThrow(await fetch("/api/agent/plan/enabled", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  }), "plan");
}

export async function startPlanRun(): Promise<{ job_id: string }> {
  return jsonOrThrow(await fetch("/api/agent/plan/run", { method: "POST" }), "plan run");
}

export async function fetchDailyReport(): Promise<{ text: string; targets: string[]; webhook_configured: boolean }> {
  return jsonOrThrow(await fetch("/api/agent/report"), "report");
}

export async function sendDailyReport(): Promise<{ sent: boolean; reason: string; text?: string }> {
  return jsonOrThrow(await fetch("/api/agent/report/send", { method: "POST" }), "report send");
}

export type Learning = {
  accuracy: {
    decided: number; executed: number; rejected: number; expired: number;
    failed: number; edited: number; accept_rate_pct: number; edit_rate_pct: number;
  };
  rejections: { kind: string; reason: string; label: string; count: number }[];
  edited_examples: { id: number; company: string | null; decided_at: string; agent: string; allen: string }[];
  examples_needed: number;
  guidance_active: boolean;
  weak_campaigns: { campaign: string; channel: string; leads: number; replied: number; last_sent: string }[];
};

export async function fetchLearning(): Promise<Learning> {
  return jsonOrThrow(await fetch("/api/agent/learning"), "learning");
}

/** What discovery returns: keyed on `domain`, named by `title`. `company_en` and
 *  `website` only come into being at import. */
export type FoundCandidate = {
  domain: string; title?: string | null; email?: string | null;
  country?: string | null; city?: string | null; phone?: string | null;
  instagram?: string | null; facebook?: string | null; linkedin?: string | null;
  icp_type?: string | null; fit_score?: number | null; brief?: string | null;
  hook?: string | null; source?: string | null; email_source?: string | null;
  excluded?: boolean; exclude_reason?: string | null;
};

// Titles that are not company names. Anti-bot interstitials come back as page titles
// when a site is shielded, and a tagline is not a name either. Letting these through is
// how the base ended up with companies called "Contact" and "Page not found".
const JUNK_TITLE = /^(contact|contact us|home|about|index|404|page not found)$/i;
const BLOCKED_PAGE = /checking your browser|robot challenge|just a moment|attention required|enable javascript|access denied/i;

/** Whether a scraped title can serve as the company's name. */
export function looksLikeAName(title: string | null | undefined): boolean {
  const t = (title || "").trim();
  if (!t || t.length > 40 || JUNK_TITLE.test(t) || BLOCKED_PAGE.test(t)) return false;
  return t.split(/\s+/).length <= 4;
}

/** "blipbillboards.com" -> "Blipbillboards". Ugly, but a lead named after its own
 *  domain is honest; one called "Contact" looks like a real answer and is not. */
export function nameFromDomain(domain: string): string {
  const label = (domain || "").split(".")[0].replace(/[-_]+/g, " ").trim();
  return label.split(" ").filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

/** The name to offer for a candidate: its title when that reads like a name, its own
 *  domain otherwise. A "Contact Foo" title is really about Foo. */
export function proposedName(c: FoundCandidate): string {
  const title = (c.title || "").trim().replace(/^contact\s+/i, "").trim();
  return looksLikeAName(title) ? title : nameFromDomain(c.domain);
}

export async function importCandidates(
  candidates: (FoundCandidate & { company_en?: string })[], country?: string,
) {
  // Mapped the same way the discovery page maps it, so both routes create the same lead.
  const payload = candidates.map((c) => ({
    country: c.country && !c.country.includes("/") ? c.country : undefined,
    company_en: (c.company_en || "").trim() || proposedName(c),
    website: c.domain, email: c.email, phone: c.phone,
    instagram: c.instagram, facebook: c.facebook, linkedin: c.linkedin,
    source: c.source, icp_type: c.icp_type, fit_score: c.fit_score,
    brief: c.brief, hook: c.hook, email_source: c.email_source,
  }));
  return jsonOrThrow(await fetch("/api/leads/import", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidates: payload, country }),
  }), "import");
}
