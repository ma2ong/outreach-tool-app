import type { BuyingSignal, Lead, SalesIntelligenceAccount, SalesIntelligenceSummary } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function fetchLeadIntelligence(leadNo: number): Promise<import("./types").LeadIntelligence> {
  return request("/api/leads/" + leadNo + "/intelligence");
}

export function fetchIntelligenceSummary(): Promise<SalesIntelligenceSummary> {
  return request("/api/sales-intelligence/summary");
}

export function fetchRankedAccounts(limit = 100): Promise<SalesIntelligenceAccount[]> {
  return request(`/api/sales-intelligence/ranked?limit=${limit}`);
}

export function fetchBuyingSignals(status = "new"): Promise<BuyingSignal[]> {
  return request(`/api/buying-signals?status=${encodeURIComponent(status)}&limit=200`);
}

export function fetchSignalLeadOptions(): Promise<Lead[]> {
  return request("/api/leads?limit=1000&sort=company_en&order=asc");
}

export function createBuyingSignal(leadNo: number, data: {
  signal_type: string; headline: string; evidence: string; source_url: string;
  occurred_at?: string; confidence: number; use_case?: string;
  product_fit?: string; suggested_angle?: string;
}): Promise<BuyingSignal> {
  return request(`/api/leads/${leadNo}/buying-signals`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
}

export function updateBuyingSignal(id: number, data: Partial<BuyingSignal>): Promise<BuyingSignal> {
  return request(`/api/buying-signals/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
}

export function signalToTask(id: number): Promise<unknown> {
  return request(`/api/buying-signals/${id}/task`, { method: "POST" });
}

export function signalToOpportunity(id: number): Promise<unknown> {
  return request(`/api/buying-signals/${id}/opportunity`, { method: "POST" });
}
