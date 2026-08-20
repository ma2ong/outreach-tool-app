import { useEffect, useState } from "react";
import {
  approveProposal, fetchAgentMeta, fetchAgentRunJob, fetchAgentStatus, fetchDailyReport,
  fetchAgentMission, fetchProposals, rejectProposal, sendDailyReport, setAgentBackend, setAutonomy,
  setPlanEnabled, startAgentRun, startPlanRun, fetchLearning, importCandidates, proposedName,
  updateAgentMission, takeoverConversation, resumeConversation,
} from "../agentApi";
import type { AgentMeta, AgentMission, AgentStatus, FoundCandidate, Learning, Proposal } from "../agentApi";
import { setAutoSend } from "../api";

const KIND_LABEL: Record<string, string> = {
  reply_draft: "回复草稿",
  send_outreach: "发起触达",
  create_task: "建销售任务",
  enroll_sequence: "加入跟进序列",
  stop_sequence: "停掉跟进",
  discover_run: "跑一轮客户开发",
  build_opportunity: "建商机",
  mark_do_not_contact: "标记不再联系",
};

const LEVEL_LABEL: Record<string, string> = {
  off: "关闭",
  propose: "提议",
  auto: "自动",
};

const CHANNEL_LABEL: Record<string, string> = {
  email: "邮件", whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook",
};

const RISK = {
  high: { label: "高风险", color: "var(--danger)" },
  medium: { label: "中风险", color: "var(--warn)" },
  low: { label: "低风险", color: "var(--green)" },
};

const ACTIVE_KINDS = [
  "reply_draft", "create_task", "build_opportunity", "mark_do_not_contact",
  "send_outreach", "enroll_sequence", "stop_sequence", "discover_run",
];

/** The server's way of saying "this was already done" — an outcome, not a failure. */
const DONE_ALREADY = /已是\s*(executed|rejected|failed|expired)|不能重复/;

/** Why a run that did everything right can still change nothing on screen. */
function describePlan(r: any): string {
  if (!r) return "";
  if (r.error) return `计划失败：${r.error}`;
  const bits: string[] = [];
  if (r.proposed) bits.push(`新增 ${r.proposed} 条提议`);
  if (r.duplicates?.length) bits.push(`${r.duplicates.length} 条今天已经做过（去「已执行」看结果）`);
  if (r.rejected?.length) bits.push(`${r.rejected.length} 条不合规被丢弃`);
  if (!bits.length) return "计划跑完了，今天没有值得新排的动作。";
  return bits.join("，");
}

function describeRun(r: any): string {
  if (!r) return "";
  const bits: string[] = [];
  if (r.classified) bits.push(`分类 ${r.classified} 条回复`);
  if (r.draft) bits.push(`起草 ${r.draft} 封`);
  if (r.quote) bits.push(`${r.quote} 家要你报价`);
  if (r.nudge) bits.push(`社媒提醒 ${r.nudge} 条`);
  if (r.planned) bits.push(`今日计划 ${r.planned} 条`);
  if (!bits.length) {
    return r.safety_paused
      ? "跑完了。邮件自动跟进处于暂停中，所以这轮没有起草或发信。"
      : "跑完了，这轮没有需要处理的新回复。";
  }
  return bits.join("，");
}

function ProposalCard({ p, meta, onDone, takenOver = false }: {
  p: Proposal; meta: AgentMeta; onDone: () => void; takenOver?: boolean;
}) {
  const isDraft = p.kind === "reply_draft";
  const channel = String(p.payload?.channel ?? "email");
  const isDM = isDraft && channel !== "email";
  const [body, setBody] = useState(String(p.payload?.body ?? ""));
  const [subject, setSubject] = useState(String(p.payload?.subject ?? ""));
  const [open, setOpen] = useState(p.risk === "high");
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("wrong_intent");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const edited = isDraft && (body !== String(p.payload?.body ?? "") || subject !== String(p.payload?.subject ?? ""));

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setError("");
    try { await fn(); onDone(); }
    catch (e) {
      // A long discover_run finishes on the server after the request has already timed
      // out. Refreshing anyway is what makes a decided proposal leave the queue instead
      // of sitting there looking un-clicked. And "已是 executed" means the work is done,
      // not that anything failed — saying so in red is why it got clicked again.
      const msg = String(e instanceof Error ? e.message : e);
      if (!DONE_ALREADY.test(msg)) setError(msg);
      onDone();
    }
    finally { setBusy(false); }
  }

  const risk = RISK[p.risk] ?? RISK.medium;
  // discover_run writes payload.progress live while it runs. A pending proposal that
  // already has unfinished progress is not waiting for a click — it is mid-flight.
  const progress = p.payload?.progress as
    { status?: string; query_index?: number; query_total?: number; candidates?: number } | undefined;
  const running = !!progress && progress.status !== "complete";
  return (
    <div className="card" style={{ marginBottom: 12, borderColor: p.risk === "high" ? "var(--danger)" : undefined }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <span className="tag">{KIND_LABEL[p.kind] ?? p.kind}</span>
            {isDraft && <span className="tag">{CHANNEL_LABEL[channel] ?? channel}</span>}
            <span className="tag" style={{ color: risk.color, borderColor: risk.color }}>{risk.label}</span>
            {p.country && <span className="muted" style={{ fontSize: 12 }}>{p.country}</span>}
          </div>
          <div style={{ fontWeight: 700, marginTop: 6 }}>{p.title}</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{p.reasoning}</div>
        </div>
        <button className="btn btn-sm" onClick={() => setOpen(!open)}>{open ? "收起" : "展开"}</button>
      </div>

      {open && (
        <div style={{ marginTop: 12 }}>
          {isDraft ? (
            <>
              {!isDM && <>
                <label className="stat-label">主题</label>
                <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} style={{ width: "100%", marginBottom: 8 }} />
              </>}
              <label className="stat-label">正文（发出去的就是这里的内容）</label>
              <textarea className="input" rows={9} value={body} onChange={(e) => setBody(e.target.value)} style={{ width: "100%", fontFamily: "inherit" }} />
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                {isDM
                  ? `在 ${CHANNEL_LABEL[channel] ?? channel} 的对话里回复${p.company_en ? " " + p.company_en : ""}`
                  : `发给 ${String(p.payload?.to ?? "")}${p.payload?.mailbox_email ? ` · 从 ${p.payload.mailbox_email} 发出` : ""}`}
              </div>
            </>
          ) : (
            <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: 0 }}>
              {JSON.stringify(p.payload ?? {}, null, 2)}
            </pre>
          )}

          {!!p.evidence?.length && (
            <div style={{ marginTop: 10 }}>
              <div className="stat-label">依据</div>
              {p.evidence.map((e, i) => (
                <div key={i} className="muted" style={{ fontSize: 12 }}>· {e.claim} —— {e.source}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && <div className="error-text" style={{ marginTop: 8 }}>{error}</div>}
      {isDraft && takenOver && (
        <div className="error-text" style={{ marginTop: 8 }}>
          这个会话已由你接管，Agent 不会发送这份草稿。先在下方交回 Agent，或驳回草稿。
        </div>
      )}

      {rejecting ? (
        <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
            {Object.entries(meta.reject_reasons).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input className="input" placeholder="补充说明（可选）" value={note} onChange={(e) => setNote(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
          <button className="btn btn-sm" disabled={busy} onClick={() => act(() => rejectProposal(p.id, reason, note))}>确认驳回</button>
          <button className="btn btn-sm" onClick={() => setRejecting(false)}>取消</button>
        </div>
      ) : (
        <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {!takenOver && (
            <button className="btn btn-sm btn-green" disabled={busy || running}
              onClick={() => act(() => approveProposal(p.id, isDraft ? { ...p.payload, body, subject } : undefined))}>
              {busy || running
                ? `执行中…${progress?.query_total
                    ? ` 第 ${progress.query_index}/${progress.query_total} 个关键词`
                    : ""}${progress?.candidates ? `，已找到 ${progress.candidates} 个` : ""}`
                : edited ? "改后确认" : "确认"}
            </button>
          )}
          {isDraft && !takenOver && p.lead_no && (
            <button className="btn btn-sm" disabled={busy}
              onClick={() => act(() => takeoverConversation(
                p.lead_no!, channel, "Allen 在 Agent 页手动接管这个会话"))}>
              我来接管
            </button>
          )}
          <button className="btn btn-sm" disabled={busy} onClick={() => setRejecting(true)}>驳回</button>
        </div>
      )}
    </div>
  );
}

function FoundCandidates({ p, onDone }: { p: Proposal; onDone: () => void }) {
  const all: FoundCandidate[] = p.payload?.found ?? [];
  const audit = p.payload?.auto_import as {
    imported?: number; accepted?: number; enrolled?: number;
    verification?: Record<string, number>; rejected?: { domain: string; reason: string }[];
    missing_sequences?: string[];
  } | undefined;
  const usable = all.filter((c) => !c.excluded);
  const skipped = all.filter((c) => c.excluded);
  const [picked, setPicked] = useState<Set<number>>(() => new Set(usable.map((_, i) => i)));
  // The scraped title is often a tagline or an anti-bot page. No rule separates
  // "Key Code Media" from "Premium LED Video Walls", so the name is offered, not imposed.
  const [names, setNames] = useState<string[]>(() => usable.map(proposedName));
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState("");
  const [err, setErr] = useState("");
  if (!all.length) return null;

  if (audit) {
    return (
      <div style={{ marginTop: 10 }}>
        <div className="stat-label">自动找客审计</div>
        <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          候选 {all.length} · 通过质量门 {audit.accepted ?? 0} · 导入 {audit.imported ?? 0}
          {` · 邮箱验证 ${audit.verification?.checked ?? 0} · 加入序列 ${audit.enrolled ?? 0}`}
        </div>
        {!!audit.missing_sequences?.length && (
          <div className="error-text" style={{ fontSize: 12, marginTop: 4 }}>
            缺少 {audit.missing_sequences.join("、")}，这些客户没有加入错误语言的序列。
          </div>
        )}
        {!!audit.rejected?.length && (
          <details style={{ marginTop: 6 }}>
            <summary className="muted" style={{ fontSize: 12, cursor: "pointer" }}>
              {audit.rejected.length} 个候选未自动导入（查看原因）
            </summary>
            {audit.rejected.map((r, i) => (
              <div key={i} className="muted" style={{ fontSize: 12 }}>
                · {r.domain || "未知域名"} —— {r.reason}
              </div>
            ))}
          </details>
        )}
      </div>
    );
  }

  function toggle(i: number) {
    setPicked((s) => { const n = new Set(s); n.has(i) ? n.delete(i) : n.add(i); return n; });
  }

  async function doImport() {
    setBusy(true); setErr("");
    try {
      const r = await importCandidates(
        usable.filter((_, i) => picked.has(i))
              .map((c) => ({ ...c, company_en: names[usable.indexOf(c)] || proposedName(c) })),
        p.payload?.country ?? undefined);
      setDone(`导入 ${r.imported} 家${r.skipped?.length ? `，${r.skipped.length} 家已在库跳过` : ""}`);
      onDone();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      onDone();
    } finally { setBusy(false); }
  }

  return (
    <div style={{ marginTop: 10 }}>
      <div className="stat-label">搜到的候选（勾选后导入客户库）</div>
      <div style={{ maxHeight: 320, overflowY: "auto", margin: "6px 0" }}>
        {usable.map((c, i) => (
          <label key={i} style={{ display: "flex", gap: 8, alignItems: "baseline", padding: "3px 0" }}>
            <input type="checkbox" checked={picked.has(i)} onChange={() => toggle(i)} />
            <input className="input" style={{ width: 210, padding: "2px 6px", fontSize: 13 }}
              value={names[i] ?? ""} onClick={(e) => e.preventDefault()}
              onChange={(e) => setNames((n) => n.map((v, j) => (j === i ? e.target.value : v)))} />
            <span className="muted" style={{ fontSize: 12 }}>
              {[c.country, c.domain, c.email, c.icp_type].filter(Boolean).join(" · ")}
            </span>
            {c.title && c.title !== names[i] && (
              <span className="muted" style={{ fontSize: 11, opacity: 0.6 }}>
                官网标题：{c.title}
              </span>
            )}
          </label>
        ))}
      </div>
      {skipped.length > 0 && (
        <details style={{ marginBottom: 8 }}>
          <summary className="muted" style={{ fontSize: 12, cursor: "pointer" }}>
            {skipped.length} 家被自动筛掉（点开看原因）
          </summary>
          {skipped.map((c, i) => (
            <div key={i} className="muted" style={{ fontSize: 12 }}>
              · {c.title || c.domain} —— {c.exclude_reason}
            </div>
          ))}
        </details>
      )}
      {err && <div className="error-text" style={{ fontSize: 12 }}>{err}</div>}
      {done ? <div className="muted" style={{ fontSize: 12 }}>{done}</div> : (
        <button className="btn btn-green btn-sm" disabled={busy || !picked.size} onClick={doImport}>
          {busy ? "导入中…" : `导入选中 ${picked.size} 家`}
        </button>
      )}
    </div>
  );
}

function LearningView({ data }: { data: Learning | null }) {
  if (!data) return <div className="muted">加载中…</div>;
  const a = data.accuracy;
  return (
    <div>
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="stat-label">它提的建议，你怎么处理的</div>
        <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>
          {a.decided ? `${a.accept_rate_pct}% 被你确认` : "还没有决定过任何建议"}
        </div>
        <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          确认 {a.executed} · 驳回 {a.rejected} · 过期 {a.expired} · 执行失败 {a.failed}
          {a.executed ? ` · 其中 ${a.edited} 条是你改过才发的（${a.edit_rate_pct}%）` : ""}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <div className="stat-label">
          它有没有在学你的写法
        </div>
        {data.guidance_active ? (
          <>
            <div style={{ fontWeight: 700, color: "var(--green)", marginTop: 4 }}>
              已开始参考你改过的 {data.edited_examples.length} 个例子
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4, marginBottom: 8 }}>
              下面这些「原稿 → 你发出去的」会附在起草提示词后面。觉得哪条教坏了它，
              就在「已执行」里找到那条驳掉这个思路，或者直接告诉我删掉。
            </div>
            {data.edited_examples.map((e) => (
              <div key={e.id} style={{ borderTop: "1px solid var(--border)", padding: "8px 0" }}>
                <div className="muted" style={{ fontSize: 12 }}>{e.company ?? "某客户"}</div>
                <div style={{ fontSize: 13, opacity: 0.7 }}>原稿：{e.agent}</div>
                <div style={{ fontSize: 13, marginTop: 4 }}>你发的：{e.allen}</div>
              </div>
            ))}
          </>
        ) : (
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            还没有。要再攒 {data.examples_needed} 个你改过的草稿才会开始参考——
            样本太少就照着学，只会让它更差，而且很难发现。
          </div>
        )}
      </div>

      {data.rejections.length > 0 && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="stat-label">你驳回的理由（近 90 天）</div>
          {data.rejections.map((r, i) => (
            <div key={i} className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              · {r.label} —— {r.count} 次（{r.kind}）
            </div>
          ))}
        </div>
      )}

      {data.weak_campaigns.length > 0 && (
        <div className="card">
          <div className="stat-label">发够了量但一条回复都没有的话术</div>
          {data.weak_campaigns.map((c, i) => (
            <div key={i} className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              · {c.campaign}（{c.channel}）—— 发了 {c.leads} 家，0 回复，最后一次 {c.last_sent}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function AgentPanel({ onOpenLead }: { onOpenLead?: (no: number) => void }) {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [meta, setMeta] = useState<AgentMeta | null>(null);
  const [items, setItems] = useState<Proposal[]>([]);
  const [tab, setTab] = useState("pending");
  const [running, setRunning] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [report, setReport] = useState<{ text: string; webhook_configured: boolean } | null>(null);
  const [learning, setLearning] = useState<Learning | null>(null);
  const [missionDraft, setMissionDraft] = useState<AgentMission | null>(null);
  const [missionSaving, setMissionSaving] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [notice, setNotice] = useState("");

  function reload() {
    fetchAgentStatus().then(setStatus).catch((e) => setError(String(e)));
    if (tab === "learning") {
      fetchLearning().then(setLearning).catch((e) => setError(String(e)));
      setItems([]);
      return;
    }
    fetchProposals({ status: tab }).then(setItems).catch((e) => setError(String(e)));
  }
  useEffect(() => { fetchAgentMeta().then(setMeta).catch((e) => setError(String(e))); }, []);
  // During a local upgrade the already-running Python process may still expose the old
  // API until it is restarted. Keep the rest of Agent usable in that short window.
  useEffect(() => { fetchAgentMission().then(setMissionDraft).catch(() => undefined); }, []);
  useEffect(reload, [tab]);

  async function saveMission() {
    if (!missionDraft) return;
    setMissionSaving(true); setError("");
    try {
      setMissionDraft(await updateAgentMission(missionDraft));
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally { reload(); setMissionSaving(false); }
  }

  async function poll(jobId: string, get: (id: string) => Promise<{ status: string; result: any }>) {
    for (let i = 0; i < 240; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const job = await get(jobId);
      if (job.status !== "running") {
        if (job.status === "error") setError(String(job.result?.error ?? "运行失败"));
        return job;
      }
    }
    return null;
  }

  async function planNow() {
    setPlanning(true); setError(""); setNotice("");
    try {
      const { job_id } = await startPlanRun();
      const job = await poll(job_id, fetchAgentRunJob);
      setNotice(describePlan(job?.result));
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      reload();          // the run finished on the server even if the poll gave up
      setPlanning(false);
    }
  }

  async function resumeSending() {
    setResuming(true); setError("");
    try {
      await setAutoSend(true, true);   // the risk was shown above this button
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      reload();                       // the pause banner must reflect the server, not the click
      setResuming(false);
    }
  }

  async function runNow() {
    setRunning(true); setError(""); setNotice("");
    try {
      const { job_id } = await startAgentRun();
      const job = await poll(job_id, fetchAgentRunJob);
      setNotice(describeRun(job?.result));
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      reload();          // the run finished on the server even if the poll gave up
      setRunning(false);
    }
  }

  if (!status || !meta) return error ? <div className="error-text">{error}</div> : null;

  const broken = Object.entries(status.llm.tasks).filter(([, v]) => !v.ok);
  const takeovers = status.takeovers ?? [];
  const pause = status.safety_pause ?? null;
  // The pause gets its own banner with evidence and a way out; repeating it as a bare
  // blocker line would say the same thing twice and point nowhere.
  const blockers = (status.outcome?.blockers ?? []).filter((b) => b.code !== "safety_pause");
  const recentRuns = status.recent_runs ?? [];
  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <div className="stat-label">Agent 助手</div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
              {status.pending ? `${status.pending} 条提议等你确认` : "没有待确认的提议"}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {status.last_result || "还没有运行过"}
              {status.unclassified ? ` · ${status.unclassified} 条回复待分类` : ""}
            </div>
            {status.mission_progress && (
              <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>
                今日合格新客 {status.mission_progress.qualified_leads_imported_today}/
                {status.mission_progress.daily_target}
                {status.mission_progress.remaining > 0
                  ? ` · 还差 ${status.mission_progress.remaining} 家`
                  : " · 今日目标已完成"}
              </div>
            )}
            {!!blockers.length && (
              <div className="error-text" style={{ fontSize: 12, marginTop: 3 }}>
                当前阻塞：{blockers.map((b) => b.message).join("；")}
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <button className="btn btn-sm" disabled={running} onClick={runNow}>
              {running ? "运行中…" : "立刻跑一次"}
            </button>
            <button className="btn btn-sm" disabled={planning} onClick={planNow}>
              {planning ? "规划中…" : "出今日计划"}
            </button>
            <button className="btn btn-sm" onClick={() => setSettingsOpen(!settingsOpen)}>
              {settingsOpen ? "收起设置" : "任务书与自主度"}
            </button>
          </div>
        </div>

        {notice && (
          <div className="muted" style={{ marginTop: 10, fontSize: 12 }}>
            {notice}
          </div>
        )}

        {!pause && status.risk_ack && (
          <div className="muted" style={{ marginTop: 10, fontSize: 12 }}>
            自动发信在你确认风险后继续运行（确认时退信率 {status.risk_ack.bounce_rate}%）。
            退信率涨过 {(status.risk_ack.bounce_rate + (status.bounce_limit ?? 1)).toFixed(1)}%
            会重新暂停并再问你一次。
          </div>
        )}

        {pause && (
          <div style={{
            marginTop: 12, padding: "10px 12px", borderRadius: 6,
            background: "#fff4f4", border: "1px solid #f0c4c4",
          }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>邮件自动跟进已暂停</div>
            <div style={{ fontSize: 12, marginTop: 3 }}>{pause.reason}</div>
            {pause.evidence && (
              <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>
                近 {pause.evidence.days} 天发出 {pause.evidence.sends} 封，
                退信 {pause.evidence.bounced} 封（{pause.evidence.bounce_rate}%）
                {pause.evidence.unmeasured ? `，其中 ${pause.evidence.unmeasured} 封无法确认送达` : ""}
              </div>
            )}
            <div className="muted" style={{ fontSize: 12, marginTop: 5 }}>
              下一步：去「客户库」清理无效邮箱、在「渠道连接」确认发件箱能收退信。
              修好之前恢复，退信会继续累积并伤害发件域名信誉。
            </div>
            <button className="btn btn-sm" style={{ marginTop: 8 }}
                    disabled={resuming} onClick={resumeSending}>
              {resuming ? "恢复中…" : "我已了解风险，恢复自动发信"}
            </button>
          </div>
        )}

        {broken.length > 0 && (
          <div className="error-text" style={{ marginTop: 8, fontSize: 12 }}>
            {broken.map(([t, v]) => `${t === "draft" ? "起草" : "分类"}不可用：${v.reason}`).join("；")}
          </div>
        )}

        {settingsOpen && (
          <div style={{ marginTop: 14 }}>
            {missionDraft && (
              <div style={{ marginBottom: 14 }}>
                <div className="stat-label" style={{ marginBottom: 6 }}>长期销售任务书</div>
                <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 2fr) repeat(2, minmax(120px, 1fr))", gap: 8 }}>
                  <label style={{ fontSize: 12 }}>
                    目标市场（逗号分隔）
                    <input className="input" style={{ width: "100%", marginTop: 3 }}
                      value={missionDraft.target_markets.join(", ")}
                      onChange={(e) => setMissionDraft({
                        ...missionDraft,
                        target_markets: e.target.value.split(",").map((v) => v.trim()),
                      })} />
                  </label>
                  <label style={{ fontSize: 12 }}>
                    每日合格新客
                    <input className="input" type="number" min={0} max={20}
                      style={{ width: "100%", marginTop: 3 }}
                      value={missionDraft.daily_qualified_leads}
                      onChange={(e) => setMissionDraft({
                        ...missionDraft, daily_qualified_leads: Number(e.target.value),
                      })} />
                  </label>
                  <label style={{ fontSize: 12 }}>
                    自动导入最低匹配分
                    <input className="input" type="number" min={75} max={100}
                      style={{ width: "100%", marginTop: 3 }}
                      value={missionDraft.minimum_fit_score}
                      onChange={(e) => setMissionDraft({
                        ...missionDraft, minimum_fit_score: Number(e.target.value),
                      })} />
                  </label>
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 8, flexWrap: "wrap" }}>
                  <label style={{ fontSize: 12 }}>
                    <input type="checkbox" checked={missionDraft.auto_enroll}
                      onChange={(e) => setMissionDraft({ ...missionDraft, auto_enroll: e.target.checked })} />
                    {" "}验证后自动加入对应语言的邮件序列
                  </label>
                  <button className="btn btn-sm btn-green" disabled={missionSaving} onClick={saveMission}>
                    {missionSaving ? "保存中…" : "保存任务书"}
                  </button>
                  <span className="muted" style={{ fontSize: 12 }}>质量门最低锁定 75 分。</span>
                </div>
              </div>
            )}

            <div className="stat-label" style={{ marginBottom: 6 }}>
              自主度（每类动作各自调，默认「提议」——它想做什么都先问你）
            </div>
            {ACTIVE_KINDS.map((kind) => (
              <div key={kind} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <span style={{ width: 130, fontSize: 13 }}>{KIND_LABEL[kind]}</span>
                {meta.autonomy.map((level) => (
                  <button key={level}
                    className={`btn btn-sm${status.autonomy[kind] === level ? " btn-green" : ""}`}
                    onClick={() => setAutonomy(kind, level).then(reload)}>
                    {LEVEL_LABEL[level]}
                  </button>
                ))}
              </div>
            ))}
            <div className="muted" style={{ fontSize: 12, margin: "4px 0 12px" }}>
              调到「自动」后这一类不再问你，但照样留执行记录，可以随时调回来。
            </div>

            <div className="stat-label" style={{ marginBottom: 6 }}>每天早上自动出计划</div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, flexWrap: "wrap" }}>
              <button className={`btn btn-sm${status.plan.enabled ? " btn-green" : ""}`}
                onClick={() => setPlanEnabled(!status.plan.enabled).then(reload)}>
                {status.plan.enabled ? "已开启" : "已关闭"}
              </button>
              <span className="muted" style={{ fontSize: 12 }}>
                默认开启。每天 {status.plan.window[0]}:00–{status.plan.window[1]}:00 之间运行，动作按上方自主度执行；失败每 {status.plan.retry_minutes ?? 30} 分钟重试，最多 {status.plan.max_attempts ?? 3} 次
              </span>
            </div>
            {status.plan.last_result && (
              <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
                上次计划：{status.plan.last_result} · 今日尝试 {status.plan.attempts ?? 0}/{status.plan.max_attempts ?? 3}
              </div>
            )}

            {!!recentRuns.length && (
              <details style={{ marginBottom: 12 }}>
                <summary className="muted" style={{ fontSize: 12, cursor: "pointer" }}>
                  最近 {recentRuns.length} 次 Agent 运行记录
                </summary>
                {recentRuns.map((r) => (
                  <div key={r.id} className={r.status === "failed" ? "error-text" : "muted"}
                    style={{ fontSize: 12, marginTop: 3 }}>
                    · {new Date(r.started_at).toLocaleString()} · {r.status === "success" ? "完成" : `失败：${r.error}`}
                    {r.incident?.paused ? " · 已触发邮件安全暂停" : ""}
                  </div>
                ))}
              </details>
            )}

            <div className="stat-label" style={{ marginBottom: 6 }}>今日日报</div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, flexWrap: "wrap" }}>
              <button className="btn btn-sm" onClick={() => fetchDailyReport().then(setReport)}>看看今天写了什么</button>
              <button className="btn btn-sm" onClick={() => sendDailyReport().then((r) => {
                setReport({ text: r.text ?? "", webhook_configured: r.sent });
                if (!r.sent) setError(r.reason);
              })}>推到飞书</button>
              {report && !report.webhook_configured && (
                <span className="muted" style={{ fontSize: 12 }}>
                  想收到推送：把自己的 WhatsApp 号写进 backend/report_whatsapp.txt（最省事，本机已登录 WA），
                  或把机器人地址写进 backend/lark_webhook.txt（飞书）/ backend/wecom_webhook.txt（企业微信）
                </span>
              )}
            </div>
            {report?.text && (
              <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: "0 0 12px" }}>{report.text}</pre>
            )}

            <div className="stat-label" style={{ marginBottom: 6 }}>模型后端</div>
            {meta.tasks.map((task) => (
              <div key={task} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <span style={{ width: 130, fontSize: 13 }}>{task === "draft" ? "起草回复" : "分类与记忆"}</span>
                {meta.backends.map((b) => (
                  <button key={b}
                    className={`btn btn-sm${status.llm.tasks[task]?.backend === b ? " btn-green" : ""}`}
                    onClick={() => setAgentBackend(task, b).then(reload)}>
                    {b}
                  </button>
                ))}
              </div>
            ))}
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              今日调用：{Object.entries(status.llm.calls)
                .filter(([k]) => k !== "date" && k !== "cli_limit")
                .map(([k, v]) => `${k} ${v}`).join("，") || "暂无"}
              {status.llm.calls.cli_limit ? ` · Claude Code 每日上限 ${status.llm.calls.cli_limit} 次` : ""}
            </div>
          </div>
        )}
      </div>

      {!!takeovers.length && (
        <div className="card" style={{ marginBottom: 16, borderColor: "var(--warn)" }}>
          <div className="stat-label">由你接管的会话</div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
            报价、谈价或你手动接管后，Agent 不会抢回对话。处理完再明确交回。
          </div>
          {takeovers.map((t) => (
            <div key={`${t.lead_no}-${t.channel}`}
              style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between", marginTop: 6, flexWrap: "wrap" }}>
              <div style={{ fontSize: 13 }}>
                <strong>{t.company_en}</strong> · {CHANNEL_LABEL[t.channel] ?? t.channel}
                <span className="muted"> · {t.next_action || t.reason}</span>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {onOpenLead && <button className="btn btn-sm" onClick={() => onOpenLead(t.lead_no)}>打开客户</button>}
                <button className="btn btn-sm" onClick={() => resumeConversation(t.lead_no, t.channel)
                  .then(reload).catch((e) => setError(String(e)))}>交回 Agent</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        {[["pending", "待确认"], ["executed", "已执行"], ["rejected", "已驳回"],
          ["failed", "执行失败"], ["expired", "已过期"], ["learning", "学到了什么"]].map(([id, label]) => (
          <button key={id} className={`btn btn-sm${tab === id ? " btn-green" : ""}`} onClick={() => setTab(id)}>
            {label}{id === "pending" && status.pending ? ` (${status.pending})` : ""}
          </button>
        ))}
      </div>

      {error && <div className="error-text" style={{ marginBottom: 12 }}>{error}</div>}

      {tab === "learning" ? (
        <LearningView data={learning} />
      ) : items.length === 0 ? (
        <div className="muted">这里没有内容。</div>
      ) : items.map((p) => (
        <div key={p.id}>
          {tab === "pending" ? (
            <ProposalCard p={p} meta={meta} onDone={reload}
              takenOver={!!(p.lead_no && takeovers.some(
                (t) => t.lead_no === p.lead_no
                  && t.channel === String(p.payload?.channel ?? "email")))} />
          ) : (
            <div className="card" style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <div>
                  <span className="tag">{KIND_LABEL[p.kind] ?? p.kind}</span>
                  <span style={{ fontWeight: 600, marginLeft: 8 }}>{p.title}</span>
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    {p.execution_result || (p.reject_reason ? `${meta.reject_reasons[p.reject_reason] ?? p.reject_reason}${p.decided_note ? "：" + p.decided_note : ""}` : p.reasoning)}
                  </div>
                </div>
                {p.lead_no && onOpenLead && (
                  <button className="btn btn-sm" onClick={() => onOpenLead(p.lead_no!)}>打开客户</button>
                )}
              </div>
              {p.kind === "discover_run" && <FoundCandidates p={p} onDone={reload} />}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
