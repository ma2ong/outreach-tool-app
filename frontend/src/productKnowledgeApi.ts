export interface KnowledgeProduct {
  id: number;
  model: string;
  pixel_pitch: string | null;
  brightness: string | null;
  use_case: string | null;
  ref_price_sqm: string | null;
  indoor_outdoor: string | null;
  refresh_rate_hz: number | null;
  maintenance_access: string | null;
  cabinet_size: string | null;
  control_system: string | null;
  notes: string | null;
  cabinet_width_mm: number | null;
  cabinet_height_mm: number | null;
  cabinet_resolution_w: number | null;
  cabinet_resolution_h: number | null;
  module_width_mm: number | null;
  module_height_mm: number | null;
  max_power_w_cabinet: number | null;
  avg_power_w_cabinet: number | null;
  agent_approved: number | boolean;
}

export interface ProductInput {
  model: string;
  pixel_pitch?: string | null;
  brightness?: string | null;
  use_case?: string | null;
  ref_price_sqm?: string | null;
  indoor_outdoor?: string | null;
  refresh_rate_hz?: number | null;
  maintenance_access?: string | null;
  cabinet_size?: string | null;
  control_system?: string | null;
  notes?: string | null;
  cabinet_width_mm?: number | null;
  cabinet_height_mm?: number | null;
  cabinet_resolution_w?: number | null;
  cabinet_resolution_h?: number | null;
  module_width_mm?: number | null;
  module_height_mm?: number | null;
  max_power_w_cabinet?: number | null;
  avg_power_w_cabinet?: number | null;
  agent_approved?: boolean;
}

export interface ApprovedCase {
  id: number;
  internal_name: string;
  public_label: string | null;
  country: string | null;
  application: string | null;
  indoor_outdoor: string | null;
  pixel_pitch: string | null;
  width_m: number | null;
  height_m: number | null;
  product_model: string | null;
  public_summary: string | null;
  source_url: string | null;
  shareable: number | boolean;
  created_at: string;
  updated_at: string;
}

export type CaseInput = Omit<ApprovedCase, "id" | "created_at" | "updated_at" | "shareable"> & {
  shareable?: boolean;
};

async function detail(r: Response, fallback: string): Promise<never> {
  const body = await r.json().catch(() => null);
  throw new Error(body?.detail || fallback);
}

export async function fetchKnowledgeProducts(): Promise<KnowledgeProduct[]> {
  const r = await fetch("/api/products");
  if (!r.ok) return detail(r, `products ${r.status}`);
  return r.json();
}

export async function createKnowledgeProduct(p: ProductInput): Promise<KnowledgeProduct> {
  const r = await fetch("/api/products", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p),
  });
  if (!r.ok) return detail(r, `product ${r.status}`);
  return r.json();
}

export async function updateKnowledgeProduct(id: number, p: Partial<ProductInput>): Promise<KnowledgeProduct> {
  const r = await fetch(`/api/products/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p),
  });
  if (!r.ok) return detail(r, `product ${r.status}`);
  return r.json();
}

export async function deleteKnowledgeProduct(id: number): Promise<void> {
  const r = await fetch(`/api/products/${id}`, { method: "DELETE" });
  if (!r.ok) return detail(r, `product ${r.status}`);
}

export async function seedKnowledgeProducts(): Promise<{ seeded: number }> {
  const r = await fetch("/api/products/seed", { method: "POST" });
  if (!r.ok) return detail(r, `seed ${r.status}`);
  return r.json();
}

export async function generateKnowledgeQuote(product_ids: number[], note: string): Promise<{ file: string; path: string }> {
  const r = await fetch("/api/quote", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_ids, note }),
  });
  if (!r.ok) return detail(r, `quote ${r.status}`);
  return r.json();
}

export async function fetchCases(): Promise<ApprovedCase[]> {
  const r = await fetch("/api/cases");
  if (!r.ok) return detail(r, `cases ${r.status}`);
  return r.json();
}

export async function createCase(c: CaseInput): Promise<ApprovedCase> {
  const r = await fetch("/api/cases", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(c),
  });
  if (!r.ok) return detail(r, `case ${r.status}`);
  return r.json();
}

export async function updateCase(id: number, c: Partial<CaseInput>): Promise<ApprovedCase> {
  const r = await fetch(`/api/cases/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(c),
  });
  if (!r.ok) return detail(r, `case ${r.status}`);
  return r.json();
}

export async function deleteCase(id: number): Promise<void> {
  const r = await fetch(`/api/cases/${id}`, { method: "DELETE" });
  if (!r.ok) return detail(r, `case ${r.status}`);
}

export async function fetchProductAdvice(opportunityId: number): Promise<Record<string, unknown>> {
  const r = await fetch(`/api/opportunities/${opportunityId}/products`);
  if (!r.ok) return detail(r, `product advice ${r.status}`);
  return r.json();
}
