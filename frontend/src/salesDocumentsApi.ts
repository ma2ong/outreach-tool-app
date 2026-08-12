import type { Quote, QuoteSummary, SalesOrder } from "./types";


async function result<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const detail = (await response.json().catch(() => null))?.detail;
    throw new Error(detail || `${fallback} ${response.status}`);
  }
  return response.json();
}

export interface QuoteItemInput {
  description: string;
  model?: string | null;
  pixel_pitch?: string | null;
  width_m?: number | null;
  height_m?: number | null;
  quantity: number;
  pricing_unit: "sqm" | "unit";
  unit_price: number;
  note?: string | null;
}

export interface QuoteInput {
  lead_no: number;
  opportunity_id?: number | null;
  contact_id?: number | null;
  title: string;
  currency: string;
  incoterm?: string | null;
  destination?: string | null;
  valid_until?: string | null;
  payment_terms?: string | null;
  lead_time?: string | null;
  warranty?: string | null;
  shipping: number;
  discount: number;
  items: QuoteItemInput[];
}

export async function fetchQuotes(): Promise<QuoteSummary[]> {
  return result(await fetch("/api/sales/quotes"), "quotes");
}

export async function fetchQuote(id: number): Promise<Quote> {
  return result(await fetch(`/api/sales/quotes/${id}`), "quote");
}

export async function createFormalQuote(data: QuoteInput): Promise<Quote> {
  return result(await fetch("/api/sales/quotes", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  }), "quote");
}

export async function updateFormalQuote(id: number, data: Omit<QuoteInput, "lead_no">): Promise<Quote> {
  return result(await fetch(`/api/sales/quotes/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  }), "quote");
}

export async function setFormalQuoteStatus(id: number, status: string): Promise<Quote> {
  return result(await fetch(`/api/sales/quotes/${id}/status`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }),
  }), "quote status");
}

export async function convertFormalQuoteToOrder(id: number): Promise<SalesOrder> {
  return result(await fetch(`/api/sales/quotes/${id}/order`, { method: "POST" }), "order");
}

export async function fetchOrders(): Promise<SalesOrder[]> {
  return result(await fetch("/api/sales/orders"), "orders");
}

export async function updateSalesOrder(id: number, data: Partial<SalesOrder>): Promise<SalesOrder> {
  return result(await fetch(`/api/sales/orders/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  }), "order");
}
