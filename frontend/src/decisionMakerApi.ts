export interface ContactCandidate {
  id: number;
  lead_no: number;
  name: string;
  title: string;
  email: string | null;
  linkedin: string | null;
  role_kind: "commercial" | "project";
  source_url: string;
  evidence: string;
  confidence: number;
  status: "new" | "promoted" | "dismissed";
  promoted_contact_id: number | null;
  company_en: string;
  country: string | null;
  website: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionMakerScanResult {
  lead_no: number;
  searched: boolean;
  reason?: string;
  roles?: string[];
  pages_checked: number;
  created: number;
  promoted: number;
  errors?: string[];
  candidates: ContactCandidate[];
}

async function detail(r: Response, fallback: string): Promise<never> {
  const body = await r.json().catch(() => null);
  throw new Error(body?.detail || fallback);
}

export async function fetchContactCandidates(leadNo: number): Promise<ContactCandidate[]> {
  const r = await fetch(`/api/decision-makers/candidates?lead_no=${leadNo}&status=new`);
  if (!r.ok) return detail(r, `decision maker candidates ${r.status}`);
  return r.json();
}

export async function scanDecisionMakers(leadNo: number): Promise<DecisionMakerScanResult> {
  const r = await fetch(`/api/decision-makers/scan/${leadNo}`, { method: "POST" });
  if (!r.ok) return detail(r, `decision maker scan ${r.status}`);
  return r.json();
}

export async function promoteContactCandidate(id: number): Promise<ContactCandidate> {
  const r = await fetch(`/api/decision-makers/candidates/${id}/promote`, { method: "POST" });
  if (!r.ok) return detail(r, `promote contact candidate ${r.status}`);
  return r.json();
}

export async function dismissContactCandidate(id: number): Promise<ContactCandidate> {
  const r = await fetch(`/api/decision-makers/candidates/${id}/dismiss`, { method: "POST" });
  if (!r.ok) return detail(r, `dismiss contact candidate ${r.status}`);
  return r.json();
}
