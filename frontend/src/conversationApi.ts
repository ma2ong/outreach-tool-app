// 客户对话：按客户串起来的往来，不是按邮件。docs/56
async function jsonOrThrow(r: Response, what: string) {
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(detail || `${what} ${r.status}`);
  }
  return r.json();
}

export type ConversationRow = {
  no: number;
  company_en: string | null;
  country: string | null;
  stage: string | null;
  owner: string | null;
  state: string | null;
  next_action: string | null;
  due_at: string | null;
  sent_count: number;
  reply_count: number;
  unread: number;
  last_at: string | null;
};

export type ConversationEvent = {
  kind: "sent" | "received" | "activity";
  id: number;
  at: string | null;
  channel?: string;
  subject?: string | null;
  body?: string | null;
  campaign?: string;
  from?: string;
  message_kind?: string;
  activity_type?: string;
  title?: string;
  // 发件正文在 docs/56 R1 之前没有存过。缺的就是缺的，不拿模板重新渲染顶上。
  body_missing: boolean;
  quiet: boolean;
};

export type Conversation = {
  lead: {
    no: number; company_en: string | null; company_local: string | null;
    country: string | null; email: string | null; contact_name: string | null;
    title: string | null; stage: string | null; tags: string | null;
    do_not_contact: number;
  };
  events: ConversationEvent[];
  state: {
    channel: string; owner: string; state: string; reason: string | null;
    next_action: string | null; due_at: string | null; updated_at: string | null;
  } | null;
  requirements: {
    facts: {
      id: number; field: string; value: string; normalized_value: string;
      source_message_id: number; source_quote: string; opportunity_id: number | null;
    }[];
    conflicts: { field: string; values: string[]; opportunity_id: number | null }[];
  };
  sent_count: number;
  reply_count: number;
  missing_bodies: number;
  last_at: string | null;
};

export type ReplyBlocked = { blocked: true; reason: string; detail: string };

export async function fetchConversations(waitingOnly = false): Promise<ConversationRow[]> {
  return jsonOrThrow(await fetch(`/api/conversations?waiting_only=${waitingOnly ? 1 : 0}`),
    "conversations");
}

export async function fetchConversation(no: number): Promise<Conversation> {
  return jsonOrThrow(await fetch(`/api/conversations/${no}`), "conversation");
}

// 被 message_guard 拦下时返回 blocked，而不是抛错 —— 这是要 Allen 决定的一步，不是故障。
export async function sendReply(
  no: number, body: string, subject?: string, override = false,
): Promise<{ ok: true } | ReplyBlocked> {
  const res = await fetch(`/api/conversations/${no}/reply`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body, subject, override }),
  });
  if (res.status === 428) {
    const d = await res.json();
    const detail = d?.detail ?? d;
    return { blocked: true, reason: String(detail?.reason ?? "被拦下"), detail: String(detail?.detail ?? "") };
  }
  return jsonOrThrow(res, "send reply");
}
