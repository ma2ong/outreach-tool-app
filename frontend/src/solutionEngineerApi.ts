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
  gaps: string[];
  safety_notes?: string[];
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
