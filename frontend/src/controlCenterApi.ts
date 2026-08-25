export type ControlCenterReceipt = {
  id: number;
  kind: string;
  lead_no: number | null;
  company_en: string | null;
  country: string | null;
  title: string;
  risk: "low" | "medium" | "high";
  status: string;
  mode: "auto" | "approved" | "awaiting_approval" | "executing" | "not_executed";
  created_at: string | null;
  decided_at: string | null;
  executed_at: string | null;
  age_hours: number | null;
  result: string;
};

export type ControlCenterBlocker = {
  code: string;
  severity: "critical" | "high" | "medium" | "info";
  title: string;
  detail: string;
  action: string;
  count: number;
};

export type ControlCenterNextAction = {
  type: "account" | "opportunity";
  severity: string;
  lead_no: number | null;
  opportunity_id: number | null;
  company_en: string | null;
  title: string | null;
  due_at: string | null;
  score: number | null;
  action: string;
};

export type AgentQueueHealth = {
  open: number;
  due: number;
  stale: number;
  repeated_failures: number;
  last_sweep: null | {
    at?: string;
    processed?: number;
    done?: number;
    rescheduled?: number;
    failed?: number;
    materialized?: Record<string, number>;
  };
};

export type SalesTruthAccount = {
  lead_no: number;
  company_en: string | null;
  country: string | null;
  crm_stage: string;
  factual_state: string;
  repairable_anomalies: number;
  anomalies: { code: string; severity: string; detail: string; repairable: boolean }[];
};

export type SalesTruthHealth = {
  anomalous_accounts: number;
  repairable_anomalies: number;
  by_code: Record<string, number>;
  accounts: SalesTruthAccount[];
};

export type ControlCenterSnapshot = {
  generated_at: string;
  state: "healthy" | "attention" | "critical";
  state_label: string;
  counters: {
    awaiting_approval: number;
    high_risk_approval: number;
    auto_executed_today: number;
    approved_executed_today: number;
    failed_7d: number;
    human_takeovers: number;
    due_accounts: number;
    unhealthy_opportunities: number;
    unclassified_replies: number;
    agent_work_open: number;
    agent_work_due: number;
    agent_work_stale: number;
    agent_work_repeated_failures: number;
    sales_truth_anomalies: number;
    sales_truth_repairable: number;
  };
  agent_queue: AgentQueueHealth;
  sales_truth: SalesTruthHealth;
  autonomy: {
    by_kind: Record<string, string>;
    counts: Record<string, number>;
  };
  blockers: ControlCenterBlocker[];
  next_actions: ControlCenterNextAction[];
  approval_backlog: ControlCenterReceipt[];
  ledger: ControlCenterReceipt[];
  errors: { source: string; error: string }[];
};

async function jsonOrThrow(r: Response): Promise<ControlCenterSnapshot> {
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `control center ${r.status}`);
  }
  return r.json();
}

export async function fetchControlCenter(): Promise<ControlCenterSnapshot> {
  return jsonOrThrow(await fetch("/api/agent/control-center"));
}
