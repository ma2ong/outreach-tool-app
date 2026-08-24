export interface EngineeringOpportunity {
  id: number;
  lead_no: number;
  company_en: string;
  country: string | null;
  title: string;
  stage: string;
  width_m: number | null;
  height_m: number | null;
  quantity: number;
  pixel_pitch: string | null;
  input_voltage_v: number | null;
  controller_capacity_px: number | null;
  controller_output_ports: number | null;
  max_pixels_per_port: number | null;
  spare_pct: number | null;
}

export interface LayoutResult {
  name: string;
  cabinet_columns: number;
  cabinet_rows: number;
  cabinets_per_screen: number;
  total_cabinets: number;
  actual_width_m: number;
  actual_height_m: number;
  area_sqm_per_screen: number;
  area_sqm_project: number;
  delta_width_mm: number;
  delta_height_mm: number;
  delta_width_pct: number;
  delta_height_pct: number;
}

export interface EngineeringIntegrity {
  valid: boolean;
  errors: string[];
  warnings: string[];
  derived_checks: Record<string, number>;
}

export interface SolutionResult {
  status: string;
  ready: boolean;
  engineering_completeness_pct?: number;
  internal_only: boolean;
  selection: Record<string, unknown>;
  product: Record<string, unknown> | null;
  target?: Record<string, number>;
  layout_options?: LayoutResult[];
  selected_layout?: LayoutResult;
  resolution?: Record<string, number | string> | null;
  power?: Record<string, number | string | null> | null;
  control?: Record<string, number | string> | null;
  spares?: Record<string, number> | null;
  sections_ready?: Record<string, boolean>;
  engineering_integrity?: EngineeringIntegrity;
  engineering_errors?: string[];
  gaps: string[];
  safety_notes?: string[];
}

export interface QuoteStarter {
  description: string;
  model: string;
  pixel_pitch: string | null;
  width_m: number;
  height_m: number;
  quantity: number;
  area_sqm_per_screen: number;
  area_sqm_project: number;
  cabinets_per_screen: number;
  total_cabinets: number;
  screen_width_px: number | null;
  screen_height_px: number | null;
  pricing_unit_suggestion: string;
  note: string;
  unit_price: null;
}

export interface QuoteReadiness {
  opportunity_id: number;
  lead_no: number;
  company_en: string | null;
  title: string | null;
  internal_only: boolean;
  commercial_authority: string;
  technical_ready: boolean;
  ready_for_human_pricing: boolean;
  qualification_pct: number;
  product_status: string;
  solution_status: string;
  quote_starter: QuoteStarter | null;
  latest_quote: Record<string, unknown> | null;
  human_decisions: { key: string; label: string; decided: boolean; value: unknown; owner: string }[];
  blockers: string[];
  warnings: string[];
  safety: string[];
}

async function detail(r: Response, fallback: string): Promise<never> {
  const body = await r.json().catch(() => null);
  throw new Error(body?.detail || fallback);
}

export async function fetchEngineeringOpportunities(): Promise<EngineeringOpportunity[]> {
  const r = await fetch("/api/opportunities");
  if (!r.ok) return detail(r, `opportunities ${r.status}`);
  return r.json();
}

export async function updateEngineeringOpportunity(
  id: number,
  payload: Partial<Pick<EngineeringOpportunity,
    "width_m" | "height_m" | "quantity" | "input_voltage_v" |
    "controller_capacity_px" | "controller_output_ports" | "max_pixels_per_port" | "spare_pct">>,
): Promise<EngineeringOpportunity> {
  const r = await fetch(`/api/opportunities/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) return detail(r, `opportunity ${r.status}`);
  return r.json();
}

export async function fetchSolutionEngineering(
  opportunityId: number,
  productId?: number,
): Promise<SolutionResult> {
  const qs = productId ? `?product_id=${productId}` : "";
  const r = await fetch(`/api/opportunities/${opportunityId}/solution${qs}`);
  if (!r.ok) return detail(r, `solution ${r.status}`);
  return r.json();
}

export async function fetchQuoteReadiness(
  opportunityId: number,
  productId?: number,
): Promise<QuoteReadiness> {
  const qs = productId ? `?product_id=${productId}` : "";
  const r = await fetch(`/api/opportunities/${opportunityId}/quote-readiness${qs}`);
  if (!r.ok) return detail(r, `quote readiness ${r.status}`);
  return r.json();
}
