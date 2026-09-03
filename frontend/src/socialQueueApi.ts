// 今日社媒私信队列：Agent 备好，Allen 确认后一键发。
// 发送始终是一次明确的请求，前端没有任何自动触发的路径 —— 这是 docs/52 的边界。
export type SocialQueueItem = {
  id: number;
  lead_no: number;
  company_en: string;
  country: string | null;
  website: string | null;
  channel: "whatsapp" | "instagram" | "facebook";
  target: string;
  body: string;
  rank_order: number;
  edited: number;
  status: string;
};

export type SocialQueue = {
  date: string;
  items: SocialQueueItem[];
  // 真正在等 Allen 的条数 —— auto 渠道的行不算（docs/92 R6）。仪表盘数的是这个，
  // 不是 items.length：三个渠道挂在 auto 上六天，屏幕却一直写「等你按发送」。
  awaiting_you: number;
  per_channel: Record<string, number>;
};

export type QueueBuildResult = {
  date: string;
  queued: number;
  per_channel: Record<string, number>;
  held: number;
  holds: { lead_no: number; company: string; reason: string; detail: string }[];
};

async function jsonOrThrow(r: Response, what: string) {
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `${what} ${r.status}`);
  }
  return r.json();
}

export async function fetchSocialQueue(): Promise<SocialQueue> {
  return jsonOrThrow(await fetch("/api/social-queue"), "social queue");
}

export async function buildSocialQueue(): Promise<QueueBuildResult> {
  return jsonOrThrow(await fetch("/api/social-queue/build", { method: "POST" }), "build queue");
}

export async function editSocialQueueItem(id: number, body: string): Promise<void> {
  await jsonOrThrow(await fetch(`/api/social-queue/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  }), "edit queue item");
}

export async function dropSocialQueueItem(id: number): Promise<void> {
  await jsonOrThrow(await fetch(`/api/social-queue/${id}`, { method: "DELETE" }), "drop queue item");
}

export async function sendSocialQueue(ids: number[]): Promise<{ job_id: string; will_send: number }> {
  return jsonOrThrow(await fetch("/api/social-queue/send", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  }), "send queue");
}

// 自动挡按渠道分设。升到 auto 要照抄渠道名 —— 那个账号被封是不可恢复的。
export type SocialMode = "off" | "manual" | "auto";

export type SocialAutonomy = {
  modes: Record<string, SocialMode>;
  // attempted / error 从 docs/92 R5 开始有：一条都没发成的那种运行，以前和「今天没到点」
  // 写成同一种沉默，于是发送失败了六天，屏幕上看不出任何区别。
  last_run: { at: string; channels: Record<string, number>; failed: number;
              attempted?: number; error?: string } | null;
  send_at: string;
};

export async function fetchSocialAutonomy(): Promise<SocialAutonomy> {
  return jsonOrThrow(await fetch("/api/social-queue/autonomy"), "social autonomy");
}

export async function setSocialMode(channel: string, mode: SocialMode, confirm = ""): Promise<void> {
  await jsonOrThrow(await fetch("/api/social-queue/autonomy", {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel, mode, confirm }),
  }), "set mode");
}
