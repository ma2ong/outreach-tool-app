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
  last_error: string | null;
  cycle_count: number;
  updated_at: string;
}

export interface RuntimeStatus {
  name: string;
  active: boolean;
  lease: RuntimeLease | null;
  state: RuntimeState | null;
  heartbeat_age_seconds: number | null;
  embedded_worker_enabled: boolean;
  dedicated_worker_expected: boolean;
}

export async function fetchRuntimeStatus(): Promise<RuntimeStatus> {
  const r = await fetch("/api/runtime/status");
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `runtime status ${r.status}`);
  }
  return r.json();
}
