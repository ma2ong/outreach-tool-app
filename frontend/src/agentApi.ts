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
  pending: number;
  by_status: Record<string, number>;
  pending_by_risk: Record<string, number>;
  autonomy: Record<string, string>;
  llm: {
    calls: Record<string, any>;
    tasks: Record<string, { backend: string; ok: boolean; reason: string }>;
  };
};

export type AgentMeta = {
  kinds: string[];
  autonomy: string[];
  risks: string[];
  intents: Record<string, string>;
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
