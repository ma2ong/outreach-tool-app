import type { Lead, Stats, SendJob, DiscoverJob } from "./types";

export async function fetchAuthStatus(): Promise<{ enabled: boolean; authed: boolean }> {
  const r = await fetch("/api/auth/status");
  if (!r.ok) throw new Error(`auth ${r.status}`);
  return r.json();
}

export async function login(password: string): Promise<void> {
  const r = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `login ${r.status}`);
  }
}

export async function fetchLeads(params: Record<string, string> = {}): Promise<Lead[]> {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  const r = await fetch(`/api/leads${qs ? "?" + qs : ""}`);
  if (!r.ok) throw new Error(`leads ${r.status}`);
  return r.json();
}

export async function fetchLeadsPage(params: Record<string, string> = {}): Promise<{ leads: Lead[]; total: number }> {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "")).toString();
  const r = await fetch(`/api/leads${qs ? "?" + qs : ""}`);
  if (!r.ok) throw new Error(`leads ${r.status}`);
  const total = Number(r.headers.get("X-Total-Count") ?? "0");
  return { leads: await r.json(), total };
}

export async function fetchStats(): Promise<Stats> {
  const r = await fetch("/api/stats");
  if (!r.ok) throw new Error(`stats ${r.status}`);
  return r.json();
}

export interface CampaignStat { campaign: string; channel: string; sent: number; leads: number; replied: number; reply_rate: number; last_sent: string | null }
export interface CountryStat { country: string; touched: number; replied: number; reply_rate: number }

export async function fetchCampaignStats(): Promise<{ campaigns: CampaignStat[]; countries: CountryStat[] }> {
  const r = await fetch("/api/stats/campaigns");
  if (!r.ok) throw new Error(`campaign stats ${r.status}`);
  return r.json();
}

export async function fetchQuota(): Promise<Record<string, { sent_today: number; cap: number; batch?: number; mailboxes?: boolean }>> {
  const r = await fetch("/api/send/quota");
  if (!r.ok) throw new Error(`quota ${r.status}`);
  return r.json();
}

export async function updateLead(no: number, fields: Partial<Lead>): Promise<Lead> {
  const r = await fetch(`/api/leads/${no}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!r.ok) throw new Error(`update ${r.status}`);
  return r.json();
}

export async function deleteLead(no: number, block = false): Promise<{ blocked_domain: string | null }> {
  const r = await fetch(`/api/leads/${no}?block=${block ? 1 : 0}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`delete ${r.status}`);
  return r.json();
}

export type BlockedDomain = { id: number; domain: string; reason: string | null; created_at: string | null };

export async function fetchBlocklist(): Promise<BlockedDomain[]> {
  const r = await fetch("/api/blocklist");
  if (!r.ok) throw new Error(`blocklist ${r.status}`);
  return r.json();
}

export async function addBlocked(value: string, reason?: string): Promise<BlockedDomain> {
  const r = await fetch("/api/blocklist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value, reason }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `block ${r.status}`);
  return r.json();
}

export async function removeBlocked(id: number): Promise<void> {
  const r = await fetch(`/api/blocklist/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`unblock ${r.status}`);
}

export async function addNote(no: number, text: string): Promise<Lead> {
  const r = await fetch(`/api/leads/${no}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!r.ok) throw new Error(`note ${r.status}`);
  return r.json();
}

export async function fetchTemplates(channel: string): Promise<import("./types").Template[]> {
  const r = await fetch(`/api/templates?channel=${encodeURIComponent(channel)}`);
  if (!r.ok) throw new Error(`templates ${r.status}`);
  return r.json();
}

export async function createTemplate(t: { name: string; channel: string; subject: string | null; body: string; lang?: string | null }): Promise<import("./types").Template> {
  const r = await fetch("/api/templates", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(t),
  });
  if (!r.ok) throw new Error(`template ${r.status}`);
  return r.json();
}

export async function deleteTemplate(id: number): Promise<void> {
  const r = await fetch(`/api/templates/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`template ${r.status}`);
}

export async function markReplied(no: number, channel: string): Promise<void> {
  const r = await fetch(`/api/leads/${no}/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel }),
  });
  if (!r.ok) throw new Error(`reply ${r.status}`);
}

export async function fetchProducts(): Promise<import("./types").Product[]> {
  const r = await fetch("/api/products");
  if (!r.ok) throw new Error(`products ${r.status}`);
  return r.json();
}

export async function createProduct(p: { model: string; pixel_pitch: string | null; brightness: string | null; use_case: string | null; ref_price_sqm: string | null }): Promise<import("./types").Product> {
  const r = await fetch("/api/products", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p),
  });
  if (!r.ok) throw new Error(`product ${r.status}`);
  return r.json();
}

export async function deleteProduct(id: number): Promise<void> {
  const r = await fetch(`/api/products/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`product ${r.status}`);
}

export async function seedProducts(): Promise<{ seeded: number }> {
  const r = await fetch("/api/products/seed", { method: "POST" });
  if (!r.ok) throw new Error(`seed ${r.status}`);
  return r.json();
}

export async function generateQuote(product_ids: number[], note: string): Promise<{ file: string; path: string }> {
  const r = await fetch("/api/quote", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_ids, note }),
  });
  if (!r.ok) throw new Error(`quote ${r.status}`);
  return r.json();
}

export async function startEmailSend(body: { lead_nos: number[]; subject: string; body: string; attachment?: string; campaign?: string }): Promise<{ job_id: string; eligible: number; selected: number }> {
  const r = await fetch("/api/send/email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`send ${r.status}`);
  return r.json();
}

export async function fetchJob(id: string): Promise<SendJob> {
  const r = await fetch(`/api/send/jobs/${id}`);
  if (!r.ok) throw new Error(`job ${r.status}`);
  return r.json();
}

export interface ScreenOpts { exclude_countries?: string[]; exclude_peers?: boolean }

export async function startDiscover(queries: string[], limit = 10, screen: ScreenOpts = {}): Promise<{ job_id: string }> {
  const r = await fetch("/api/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ queries, limit, ...screen }),
  });
  if (!r.ok) throw new Error(`discover ${r.status}`);
  return r.json();
}

export async function quickAddLead(body: { url: string; country?: string; company_en?: string }): Promise<{ duplicate_of: number | null; lead: Lead }> {
  const r = await fetch("/api/leads/quick_add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `quick_add ${r.status}`);
  }
  return r.json();
}

export async function startPageDiscover(url: string, limit = 40, screen: ScreenOpts = {}): Promise<{ job_id: string }> {
  const r = await fetch("/api/discover/page", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, limit, ...screen }),
  });
  if (!r.ok) throw new Error(`discover ${r.status}`);
  return r.json();
}

export async function fetchDiscoverJob(id: string): Promise<DiscoverJob> {
  const r = await fetch(`/api/discover/jobs/${id}`);
  if (!r.ok) throw new Error(`discover job ${r.status}`);
  return r.json();
}

export async function importLeads(country: string, candidates: {
  company_en: string; website: string; email: string | null; country?: string;
  phone?: string | null; instagram?: string | null; facebook?: string | null; linkedin?: string | null;
  source?: string | null; icp_type?: string | null; fit_score?: number | null;
}[]): Promise<{ imported: number; skipped: { company_en: string; website: string | null; duplicate_of?: number; blocked_domain?: string }[] }> {
  const r = await fetch("/api/leads/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ country, candidates }),
  });
  if (!r.ok) throw new Error(`import ${r.status}`);
  return r.json();
}

export async function startChannelSend(channel: string, lead_nos: number[], message: string, image?: string, campaign?: string): Promise<{ job_id: string; eligible: number; selected: number; will_send: number }> {
  const body: Record<string, unknown> = { channel, lead_nos, message };
  if (image) body.image = image;
  if (campaign) body.campaign = campaign;
  const r = await fetch("/api/send/channel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`send ${r.status}`);
  return r.json();
}

export async function fetchSequences(): Promise<import("./types").Sequence[]> {
  const r = await fetch("/api/sequences");
  if (!r.ok) throw new Error(`sequences ${r.status}`);
  return r.json();
}

export async function createSequence(s: {
  name: string; channel: string;
  steps: { day_offset: number; subject: string | null; body: string }[];
}): Promise<import("./types").Sequence> {
  const r = await fetch("/api/sequences", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(s),
  });
  if (!r.ok) throw new Error(`sequence ${r.status}`);
  return r.json();
}

export async function enrollLeads(sid: number, lead_nos: number[]): Promise<{ enrolled: number; selected: number }> {
  const r = await fetch(`/api/sequences/${sid}/enroll`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lead_nos }),
  });
  if (!r.ok) throw new Error(`enroll ${r.status}`);
  return r.json();
}

export async function fetchDue(channel = ""): Promise<import("./types").DueItem[]> {
  const r = await fetch(`/api/sequences/due${channel ? "?channel=" + channel : ""}`);
  if (!r.ok) throw new Error(`due ${r.status}`);
  return r.json();
}

export async function sendDue(enrollment_ids: number[]): Promise<{ job_id: string; will_send: number; selected: number }> {
  const r = await fetch("/api/sequences/send", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enrollment_ids }),
  });
  if (!r.ok) throw new Error(`send ${r.status}`);
  return r.json();
}

export async function fetchDuplicates(): Promise<{ groups: { keep: number; dups: number[]; company: string; website: string | null }[]; total_dups: number }> {
  const r = await fetch("/api/leads/duplicates");
  if (!r.ok) throw new Error(`duplicates ${r.status}`);
  return r.json();
}

export async function mergeDuplicates(): Promise<{ groups: number; removed: number }> {
  const r = await fetch("/api/leads/duplicates/merge", { method: "POST" });
  if (!r.ok) throw new Error(`merge ${r.status}`);
  return r.json();
}

export async function startVerify(lead_nos?: number[]): Promise<{ job_id: string }> {
  const r = await fetch("/api/leads/verify", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lead_nos: lead_nos ?? null }),
  });
  if (!r.ok) throw new Error(`verify ${r.status}`);
  return r.json();
}

export async function fetchVerifyJob(id: string): Promise<{ status: string; result: { checked: number; valid: number; role: number; invalid: number; unknown: number } | { error: string } | null }> {
  const r = await fetch(`/api/leads/verify/jobs/${id}`);
  if (!r.ok) throw new Error(`verify job ${r.status}`);
  return r.json();
}

export async function startClassify(lead_nos?: number[]): Promise<{ job_id: string }> {
  const r = await fetch("/api/leads/classify", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lead_nos: lead_nos ?? null }),
  });
  if (!r.ok) throw new Error(`classify ${r.status}`);
  return r.json();
}

export async function fetchClassifyJob(id: string): Promise<{ status: string; done: number; total: number; result: { checked: number; by_type: Record<string, number> } | { error: string } | null }> {
  const r = await fetch(`/api/leads/classify/jobs/${id}`);
  if (!r.ok) throw new Error(`classify job ${r.status}`);
  return r.json();
}

export async function pollReplies(): Promise<{ replies: number; bounces: number; delayed: number; unsubscribes: number; stored: number; lead_nos: number[]; since_days: number }> {
  const r = await fetch("/api/replies/poll", { method: "POST" });
  if (!r.ok) throw new Error(`poll ${r.status}`);
  return r.json();
}

export interface SocialScanResult {
  replies: number;
  auto: number;
  stored: number;
  threads: number;
  unmatched: string[];
  channels: { channel: string; replies: number; stored: number; threads: number; outgoing: number; unmatched: string[] }[];
  errors: { channel: string; error: string }[];
  skipped?: string[];
}

export async function scanSocial(): Promise<SocialScanResult> {
  const r = await fetch("/api/replies/scan", { method: "POST" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `scan ${r.status}`);
  }
  return r.json();
}

export async function fetchInbox(pendingOnly = false): Promise<import("./types").InboxMessage[]> {
  const r = await fetch(`/api/inbox${pendingOnly ? "?pending_only=1" : ""}`);
  if (!r.ok) throw new Error(`inbox ${r.status}`);
  return r.json();
}

export async function fetchInboxPending(): Promise<number> {
  const r = await fetch("/api/inbox/pending_count");
  if (!r.ok) throw new Error(`inbox ${r.status}`);
  return (await r.json()).count;
}

export async function markInboxRead(id: number): Promise<void> {
  const r = await fetch(`/api/inbox/${id}/read`, { method: "POST" });
  if (!r.ok) throw new Error(`inbox ${r.status}`);
}

export async function markInboxHandled(id: number): Promise<void> {
  const r = await fetch(`/api/inbox/${id}/handled`, { method: "POST" });
  if (!r.ok) throw new Error(`inbox handled ${r.status}`);
}

export async function fetchLead(no: number): Promise<Lead> {
  const r = await fetch(`/api/leads/${no}`);
  if (!r.ok) throw new Error(`lead ${r.status}`);
  return r.json();
}

export async function fetchOpportunities(params: {
  stage?: string; lead_no?: number; attention?: boolean;
} = {}): Promise<import("./types").Opportunity[]> {
  const qs = new URLSearchParams();
  if (params.stage) qs.set("stage", params.stage);
  if (params.lead_no !== undefined) qs.set("lead_no", String(params.lead_no));
  if (params.attention) qs.set("attention", "true");
  const r = await fetch(`/api/opportunities${qs.size ? "?" + qs.toString() : ""}`);
  if (!r.ok) throw new Error(`opportunities ${r.status}`);
  return r.json();
}

export async function fetchOpportunityStats(): Promise<import("./types").OpportunityStats> {
  const r = await fetch("/api/opportunities/stats");
  if (!r.ok) throw new Error(`opportunity stats ${r.status}`);
  return r.json();
}

export async function createOpportunity(data: {
  lead_no: number; title: string; stage?: string; amount?: number | null;
  currency?: string; probability?: number; expected_close_date?: string | null;
  next_action?: string | null; next_action_date?: string | null;
  use_case?: string | null; indoor_outdoor?: string | null;
  width_m?: number | null; height_m?: number | null; quantity?: number;
  pixel_pitch?: string | null; destination?: string | null; incoterm?: string | null;
  competitor?: string | null; loss_reason?: string | null;
}): Promise<import("./types").Opportunity> {
  const r = await fetch("/api/opportunities", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `opportunity ${r.status}`);
  }
  return r.json();
}

export async function updateOpportunity(
  id: number, data: Partial<import("./types").Opportunity>,
): Promise<import("./types").Opportunity> {
  const r = await fetch(`/api/opportunities/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `opportunity ${r.status}`);
  }
  return r.json();
}

export async function fetchActivities(params: {
  status?: string; scope?: string; lead_no?: number; opportunity_id?: number; limit?: number;
} = {}): Promise<import("./types").Activity[]> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.scope) qs.set("scope", params.scope);
  if (params.lead_no !== undefined) qs.set("lead_no", String(params.lead_no));
  if (params.opportunity_id !== undefined) qs.set("opportunity_id", String(params.opportunity_id));
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  const r = await fetch(`/api/activities${qs.size ? "?" + qs.toString() : ""}`);
  if (!r.ok) throw new Error(`activities ${r.status}`);
  return r.json();
}

export async function fetchActivityStats(): Promise<import("./types").ActivityStats> {
  const r = await fetch("/api/activities/stats");
  if (!r.ok) throw new Error(`activity stats ${r.status}`);
  return r.json();
}

export async function createActivity(data: {
  lead_no: number; opportunity_id?: number | null; type?: string; title: string;
  due_at?: string | null; priority?: string; note?: string | null;
}): Promise<import("./types").Activity> {
  const r = await fetch("/api/activities", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `activity ${r.status}`);
  }
  return r.json();
}

export async function updateActivity(
  id: number, data: Partial<import("./types").Activity>,
): Promise<import("./types").Activity> {
  const r = await fetch(`/api/activities/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `activity ${r.status}`);
  }
  return r.json();
}

export async function completeActivity(id: number): Promise<import("./types").Activity> {
  const r = await fetch(`/api/activities/${id}/complete`, { method: "POST" });
  if (!r.ok) throw new Error(`activity ${r.status}`);
  return r.json();
}

export interface HealthLead { no: number; company_en: string; website: string | null; country: string | null; reason?: string }

export async function scanHealth(): Promise<{ issues: Record<string, HealthLead[]>; total: number }> {
  const r = await fetch("/api/health/scan");
  if (!r.ok) throw new Error(`health ${r.status}`);
  return r.json();
}

export async function fetchCleanable(): Promise<{ leads: HealthLead[]; count: number }> {
  const r = await fetch("/api/health/cleanable");
  if (!r.ok) throw new Error(`cleanable ${r.status}`);
  return r.json();
}

export async function bulkDeleteLeads(nos: number[], block = false): Promise<{ deleted: number; blocked_domains: string[] }> {
  const r = await fetch("/api/leads/bulk_delete", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nos, block }),
  });
  if (!r.ok) throw new Error(`bulk delete ${r.status}`);
  return r.json();
}

export async function fixHealth(issues: string[]): Promise<Record<string, number>> {
  const r = await fetch("/api/health/fix", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ issues }),
  });
  if (!r.ok) throw new Error(`health ${r.status}`);
  return r.json();
}

export async function loadSeeds(): Promise<{ templates: number; sequence_ids: number[] }> {
  const r = await fetch("/api/seeds/load", { method: "POST" });
  if (!r.ok) throw new Error(`seeds ${r.status}`);
  return r.json();
}

export async function fetchMailboxes(): Promise<import("./types").Mailbox[]> {
  const r = await fetch("/api/mailboxes");
  if (!r.ok) throw new Error(`mailboxes ${r.status}`);
  return r.json();
}

export async function createMailbox(m: {
  email: string; smtp_host: string; port: number; imap_host?: string; imap_port?: number;
  username: string; password: string; daily_cap: number;
}): Promise<import("./types").Mailbox> {
  const r = await fetch("/api/mailboxes", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(m),
  });
  if (!r.ok) throw new Error(`mailbox ${r.status}`);
  return r.json();
}

export async function setMailboxActive(id: number, active: boolean): Promise<void> {
  const r = await fetch(`/api/mailboxes/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active }),
  });
  if (!r.ok) throw new Error(`mailbox ${r.status}`);
}

export async function testMailbox(id: number): Promise<void> {
  const r = await fetch(`/api/mailboxes/${id}/test`, { method: "POST" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `test ${r.status}`);
  }
}

export async function deleteMailbox(id: number): Promise<void> {
  const r = await fetch(`/api/mailboxes/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`mailbox ${r.status}`);
}

export async function fetchChannels(): Promise<Record<string, string>> {
  const r = await fetch("/api/channels");
  if (!r.ok) throw new Error(`channels ${r.status}`);
  return r.json();
}

export async function connectChannel(ch: string): Promise<void> {
  const r = await fetch(`/api/channels/${ch}/connect`, { method: "POST" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `connect ${r.status}`);
  }
}

export async function channelStatus(ch: string): Promise<string> {
  const r = await fetch(`/api/channels/${ch}/status`);
  if (!r.ok) throw new Error(`status ${r.status}`);
  return (await r.json()).status;
}

export async function fetchReadiness(): Promise<import("./types").Readiness> {
  const r = await fetch("/api/readiness");
  if (!r.ok) throw new Error(`readiness ${r.status}`);
  return r.json();
}

export async function setAutoSend(enabled: boolean): Promise<import("./types").AutoSendStatus> {
  const r = await fetch("/api/autosend", {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `autosend ${r.status}`);
  }
  return r.json();
}
