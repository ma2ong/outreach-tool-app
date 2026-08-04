export interface OutreachStatus {
  channel: string;
  status: string;
  touch_count: number;
  message_sent_date: string | null;
  reply_received: boolean;
  exclude_reason: string | null;
}
export interface Note {
  id: number;
  created_at: string | null;
  text: string;
}
export interface Lead {
  no: number;
  company_en: string;
  company_local: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  contact_name: string | null;
  title: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  instagram: string | null;
  facebook: string | null;
  linkedin: string | null;
  whatsapp_verified: boolean;
  email_status: string | null;
  do_not_contact: boolean;
  business: string | null;
  target_fit: string | null;
  stage: string;
  tags: string | null;
  follow_up_date: string | null;
  next_action: string | null;
  outreach: OutreachStatus[];
  notes: Note[];
}
export interface Template {
  id: number;
  name: string;
  channel: string;
  subject: string | null;
  body: string;
  lang: string | null;
}
export interface SequenceStep {
  step_order: number;
  day_offset: number;
  subject: string | null;
  body: string;
  image: string | null;
}
export interface Sequence {
  id: number;
  name: string;
  channel: string;
  active: boolean;
  steps: SequenceStep[];
  enrolled: number;
}
export interface DueItem {
  enrollment_id: number;
  lead_no: number;
  company_en: string;
  channel: string;
  sequence_id: number;
  sequence_name: string;
  step_order: number;
  subject: string | null;
  body: string;
  image: string | null;
}
export const STAGES = ["new", "contacted", "replied", "negotiating", "won", "lost"] as const;
export const STAGE_LABEL: Record<string, string> = {
  new: "新客户", contacted: "已联系", replied: "已回复",
  negotiating: "洽谈中", won: "成交", lost: "无效",
};
export interface Product {
  id: number;
  model: string;
  pixel_pitch: string | null;
  brightness: string | null;
  use_case: string | null;
  ref_price_sqm: string | null;
}
export interface Mailbox {
  id: number;
  email: string;
  smtp_host: string;
  port: number;
  imap_host: string | null;
  imap_port: number;
  username: string;
  daily_cap: number;
  active: boolean;
  sent_today: number;
}
export interface ChannelReach {
  have: number;
  messaged: number;
  replied: number;
  untouched: number;
}
export interface Stats {
  total: number;
  by_country: Record<string, number>;
  by_channel_status: Record<string, Record<string, number>>;
  reach: Record<string, ChannelReach>;
  funnel: { total: number; with_contact: number; touched: number; replied: number; follow_up_due: number };
}
export interface SendJob {
  id: string;
  status: string;
  done: number;
  total: number;
  result:
    | { sent: number; failed: number; skipped: number; deferred?: number; errors: { no: number; error: string }[] }
    | { error: string }
    | null;
}
export interface Candidate {
  domain: string;
  title: string;
  email: string | null;
  emails: string[];
  phone: string | null;
  instagram: string | null;
  facebook: string | null;
  linkedin: string | null;
  source?: string | null;
  icp_type?: string | null;
  fit_score?: number | null;
  country?: string | null;
  excluded?: boolean;
  exclude_reason?: string | null;
  duplicate_of: number | null;
}
export interface InboxMessage {
  id: number;
  lead_no: number;
  contact_id: number | null;
  channel: string;
  kind: string;
  from_addr: string | null;
  subject: string | null;
  body: string | null;
  received_at: string | null;
  is_read: number;
  handled_at: string | null;
  company_en: string;
  contact_name: string | null;
  country: string | null;
}
export interface Contact {
  id: number;
  lead_no: number;
  name: string | null;
  title: string | null;
  email: string | null;
  phone: string | null;
  linkedin: string | null;
  role: "decision_maker" | "influencer" | "technical" | "finance" | "other";
  is_primary: boolean;
  email_status: string | null;
  source: string;
  note: string | null;
  created_at: string;
  updated_at: string;
  company_en: string;
  country: string | null;
}
export interface Opportunity {
  id: number;
  lead_no: number;
  company_en: string;
  country: string | null;
  title: string;
  stage: string;
  amount: number | null;
  currency: string;
  probability: number;
  weighted_amount: number;
  expected_close_date: string | null;
  next_action: string | null;
  next_action_date: string | null;
  use_case: string | null;
  indoor_outdoor: string | null;
  width_m: number | null;
  height_m: number | null;
  quantity: number;
  pixel_pitch: string | null;
  destination: string | null;
  incoterm: string | null;
  competitor: string | null;
  loss_reason: string | null;
  overdue: boolean;
  stale: boolean;
  created_at: string;
  updated_at: string;
  last_activity_at: string;
}
export interface OpportunityStats {
  open_count: number;
  open_amount: number;
  weighted_amount: number;
  closing_this_month: number;
  won_this_month: number;
  attention_count: number;
  overdue_count: number;
  stale_count: number;
  by_stage: Record<string, number>;
}
export interface Activity {
  id: number;
  lead_no: number;
  opportunity_id: number | null;
  type: string;
  title: string;
  due_at: string | null;
  priority: "high" | "normal" | "low";
  status: "open" | "done" | "cancelled";
  source: "manual" | "reply" | "opportunity" | "legacy";
  source_ref: string | null;
  note: string | null;
  created_at: string;
  completed_at: string | null;
  updated_at: string;
  company_en: string;
  country: string | null;
  opportunity_title: string | null;
}
export interface ActivityStats {
  overdue: number;
  today: number;
  upcoming: number;
  no_due: number;
  open_count: number;
}
export interface ReadinessCheck {
  id: string;
  label: string;
  status: "ok" | "attention" | "blocked";
  detail: string;
  action_page: string;
}
export interface AutoSendStatus {
  enabled: boolean;
  last_date: string | null;
  last_result: string | null;
  preview: {
    due: number;
    sendable: number;
    will_send: number;
    oldest_due: string | null;
  };
}
export interface Readiness {
  status: "ready" | "attention" | "blocked";
  checks: ReadinessCheck[];
  metrics: {
    active_mailboxes: number;
    fallback_gmail: boolean;
    email_total: number;
    email_checked: number;
    email_verified_coverage: number;
    reply_sync_last_at: string | null;
    reply_sync_last_success_at: string | null;
    reply_sync_last_status: string | null;
    pending_replies: number;
    activities: ActivityStats;
    contacts: {
      total_contacts: number;
      companies_with_contacts: number;
      companies_without_contacts: number;
      named_contacts: number;
      decision_makers: number;
    };
    autosend: AutoSendStatus;
  };
}
export const OPPORTUNITY_STAGES = [
  "qualified", "requirements", "quoted", "negotiation", "won", "lost",
] as const;
export const OPPORTUNITY_STAGE_LABEL: Record<string, string> = {
  qualified: "确认项目",
  requirements: "确认规格",
  quoted: "已报价",
  negotiation: "谈判中",
  won: "已成交",
  lost: "已丢单",
};
export interface DiscoverJob {
  id: string;
  status: string;
  done: number;
  total: number;
  result: { candidates: Candidate[] } | { error: string } | null;
}
