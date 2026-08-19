import { useEffect, useState } from "react";
import {
  approveProposal, fetchAgentMeta, fetchAgentRunJob, fetchAgentStatus, fetchProposals,
  rejectProposal, setAgentBackend, setAutonomy, startAgentRun,
} from "../agentApi";
import type { AgentMeta, AgentStatus, Proposal } from "../agentApi";

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

// Phase B owns these; showing a dial that cannot do anything yet would be a lie.
const ACTIVE_KINDS = ["reply_draft", "create_task", "build_opportunity", "mark_do_not_contact"];

function ProposalCard({ p, meta, onDone }: { p: Proposal; meta: AgentMeta; onDone: () => void }) {
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
    catch (e) { setError(String(e instanceof Error ? e.message : e)); }
    finally { setBusy(false); }
  }

  const risk = RISK[p.risk] ?? RISK.medium;
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
          <button className="btn btn-sm btn-green" disabled={busy}
            onClick={() => act(() => approveProposal(p.id, isDraft ? { ...p.payload, body, subject } : undefined))}>
            {busy ? "执行中…" : edited ? "改后确认" : "确认"}
          </button>
          <button className="btn btn-sm" disabled={busy} onClick={() => setRejecting(true)}>驳回</button>
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
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);

  function reload() {
    fetchAgentStatus().then(setStatus).catch((e) => setError(String(e)));
    fetchProposals({ status: tab }).then(setItems).catch((e) => setError(String(e)));
  }
  useEffect(() => { fetchAgentMeta().then(setMeta).catch((e) => setError(String(e))); }, []);
  useEffect(reload, [tab]);

  async function runNow() {
    setRunning(true); setError("");
    try {
      const { job_id } = await startAgentRun();
      for (let i = 0; i < 240; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const job = await fetchAgentRunJob(job_id);
        if (job.status !== "running") {
          if (job.status === "error") setError(String(job.result?.error ?? "运行失败"));
          break;
        }
      }
      reload();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setRunning(false);
    }
  }

  if (!status || !meta) return error ? <div className="error-text">{error}</div> : null;

  const broken = Object.entries(status.llm.tasks).filter(([, v]) => !v.ok);
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
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <button className="btn btn-sm" disabled={running} onClick={runNow}>
              {running ? "运行中…" : "立刻跑一次"}
            </button>
            <button className="btn btn-sm" onClick={() => setSettingsOpen(!settingsOpen)}>
              {settingsOpen ? "收起设置" : "自主度与模型"}
            </button>
          </div>
        </div>

        {broken.length > 0 && (
          <div className="error-text" style={{ marginTop: 8, fontSize: 12 }}>
            {broken.map(([t, v]) => `${t === "draft" ? "起草" : "分类"}不可用：${v.reason}`).join("；")}
          </div>
        )}

        {settingsOpen && (
          <div style={{ marginTop: 14 }}>
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

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        {[["pending", "待确认"], ["executed", "已执行"], ["rejected", "已驳回"],
          ["failed", "执行失败"], ["expired", "已过期"]].map(([id, label]) => (
          <button key={id} className={`btn btn-sm${tab === id ? " btn-green" : ""}`} onClick={() => setTab(id)}>
            {label}{id === "pending" && status.pending ? ` (${status.pending})` : ""}
          </button>
        ))}
      </div>

      {error && <div className="error-text" style={{ marginBottom: 12 }}>{error}</div>}

      {items.length === 0 ? (
        <div className="muted">这里没有内容。</div>
      ) : items.map((p) => (
        <div key={p.id}>
          {tab === "pending" ? (
            <ProposalCard p={p} meta={meta} onDone={reload} />
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
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
