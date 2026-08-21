export interface QualificationGap {
  key: string;
  label: string;
  why: string;
  value: unknown;
}

export interface OpportunityCoaching {
  opportunity_id: number;
  lead_no: number;
  company_en: string;
  title: string;
  stage: string;
  amount: number | null;
  currency: string;
  health: number;
  severity: "critical" | "high" | "medium" | "low";
  urgency: number;
  qualification: {
    application: string;
    completeness: number;
    known: QualificationGap[];
    missing: QualificationGap[];
    next_question: string | null;
  };
  contact_coverage: {
    commercial_authority: boolean;
    project_authority: boolean;
    missing: { kind: string; label: string; reason: string }[];
    evidence: unknown[];
    contacts: number;
  };
  next_action: string | null;
  next_action_date: string | null;
  overdue: boolean;
  stale: boolean;
  open_task: { id: number; title: string; due_at: string | null } | null;
  fresh_signal: { headline?: string; suggested_angle?: string } | null;
  risks: string[];
  next_best_action: string;
}

export async function fetchOpportunityCoaching(limit = 100): Promise<OpportunityCoaching[]> {
  const r = await fetch(`/api/opportunities/coach?limit=${limit}`);
  if (!r.ok) throw new Error(`opportunity coach ${r.status}`);
  return r.json();
}

export async function fetchCustomer360(leadNo: number): Promise<Record<string, unknown>> {
  const r = await fetch(`/api/opportunities/customer/${leadNo}/360`);
  if (!r.ok) throw new Error(`customer 360 ${r.status}`);
  return r.json();
}
