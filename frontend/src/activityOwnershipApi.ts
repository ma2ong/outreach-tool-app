import type { Activity, ActivityStats } from "./types";

export type WorkOwner = "human" | "agent";

export async function fetchOwnedActivities(
  workOwner: WorkOwner,
  params: { status?: string; scope?: string; limit?: number } = {},
): Promise<Activity[]> {
  const qs = new URLSearchParams({ work_owner: workOwner });
  if (params.status) qs.set("status", params.status);
  if (params.scope) qs.set("scope", params.scope);
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  const r = await fetch(`/api/activities?${qs.toString()}`);
  if (!r.ok) throw new Error(`activities ${r.status}`);
  return r.json();
}

export async function fetchOwnedActivityStats(workOwner: WorkOwner): Promise<ActivityStats> {
  const r = await fetch(`/api/activities/stats?work_owner=${encodeURIComponent(workOwner)}`);
  if (!r.ok) throw new Error(`activity stats ${r.status}`);
  return r.json();
}
