export interface RuntimeLease {
  name: string;
  owner: string;
  mode: "embedded" | "worker" | string;
  acquired_at: string;
  heartbeat_at: string;
  expires_at: string;
}

export interface RuntimeState {
  name: string;
  owner: string | null;
  mode: string | null;
  last_cycle_started_at: string | null;
  last_cycle_finished_at: string | null;
  last_cycle_ok: number | null;
  last_email_poll_ok: number | null;
  last_error: string | null;
  cycle_count: number;
  last_standby_at: string | null;
  last_standby_owner: string | null;
  standby_count: number;
  updated_at: string;
}

export interface CapabilityHealth {
  name: string;
  status?: "disabled" | "not_configured" | "idle" | "running" | "stalled" | "partial" | "failed" | "succeeded";
  running_since?: string | null;
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_output_at: string | null;
  last_error: string | null;
  consecutive_failures: number;
  processed_count: number;
  updated_at: string;
}

export interface UnresolvedDelivery {
  id: number;
  lead_no: number;
  company_en: string | null;
  channel: string;
  target: string;
  subject: string | null;
  body: string;
  source_kind: "sequence" | "reply" | string;
  status: "pending" | "unknown";
  last_error: string | null;
  created_at: string;
}

export interface ProductionHealth {
  status: "ok" | "degraded" | "critical" | string;
  critical: string[];
  warnings: string[];
  database: { status: string; quick_check: string };
  backup: {
    status: string;
    verified: boolean;
    path: string | null;
    date: string | null;
    age_days: number | null;
    count: number;
    size_bytes: number;
    quick_check: string;
  };
  disk: { status: string; free_bytes: number | null; total_bytes: number | null };
  frontend: { status: string; built: boolean; size_bytes: number };
  server: {
    status: string;
    last_crash_unrecovered: boolean;
    last_crash_mtime: number | null;
    last_start_mtime: number | null;
  };
  auth_enabled: boolean;
  python: { version: string; ci_baseline: string; matches_ci_minor: boolean };
}

export interface RuntimeStatus {
  name: string;
  active: boolean;
  lease: RuntimeLease | null;
  state: RuntimeState | null;
  heartbeat_age_seconds: number | null;
  embedded_worker_enabled: boolean;
  dedicated_worker_expected: boolean;
  capabilities: CapabilityHealth[];
  unresolved_deliveries: UnresolvedDelivery[];
  production: ProductionHealth;
}

export async function resolveDelivery(id: number, outcome: "sent" | "not_sent"): Promise<void> {
  const r = await fetch(`/api/runtime/delivery-intents/${id}/resolve`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ outcome }),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `delivery resolution ${r.status}`);
  }
}

export async function fetchRuntimeStatus(): Promise<RuntimeStatus> {
  const r = await fetch("/api/runtime/status");
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `runtime status ${r.status}`);
  }
  return r.json();
}
