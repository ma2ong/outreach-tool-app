import { useEffect, useMemo, useState } from "react";
import { completeActivity, createActivity, fetchLeads } from "../api";
import { fetchOwnedActivities, fetchOwnedActivityStats } from "../activityOwnershipApi";
import type { WorkOwner } from "../activityOwnershipApi";
import type { Activity, ActivityStats, Lead } from "../types";

const TYPE_LABEL: Record<string, string> = {
  task: "任务", call: "电话", email: "Email", whatsapp: "WhatsApp",
  instagram: "Instagram", meeting: "会议", quote: "报价",
};
const PRIORITY_LABEL: Record<string, string> = { high: "高", normal: "普通", low: "低" };

function today(): string {
  const d = new Date();
  const pad = (v: number) => String(v).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function dueLabel(task: Activity): string {
  if (!task.due_at) return "未设日期";
  if (task.due_at < today()) return `已逾期 · ${task.due_at}`;
  if (task.due_at === today()) return "今天";
  return task.due_at;
}

function sourceLabel(task: Activity): string {
  const source = task.source as string;
  if (source === "agent") return "Agent";
  if (source === "reply") return "客户回复";
  if (source === "opportunity") return "商机";
  if (source === "legacy") return "旧跟进";
  return "手工";
}

export function ActivitiesPanel({ onOpenLead, onChanged }: {
  onOpenLead: (leadNo: number) => void; onChanged: () => void;
}) {
  const [tasks, setTasks] = useState<Activity[]>([]);
  const [stats, setStats] = useState<ActivityStats | null>(null);
  const [humanStats, setHumanStats] = useState<ActivityStats | null>(null);
  const [agentStats, setAgentStats] = useState<ActivityStats | null>(null);
  const [workOwner, setWorkOwner] = useState<WorkOwner>("human");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [scope, setScope] = useState("");
  const [status, setStatus] = useState("open");
  const [leadChoice, setLeadChoice] = useState("");
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState(today());
  const [type, setType] = useState("task");
  const [priority, setPriority] = useState("normal");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const leadOptions = useMemo(
    () => leads.map((lead) => ({ lead, label: `#${lead.no} · ${lead.company_en}${lead.country ? ` · ${lead.country}` : ""}` })),
    [leads],
  );

  async function load() {
    try {
      const [items, humanSummary, agentSummary] = await Promise.all([
        fetchOwnedActivities(workOwner, { status, ...(status === "open" && scope ? { scope } : {}) }),
        fetchOwnedActivityStats("human"),
        fetchOwnedActivityStats("agent"),
      ]);
      setTasks(items);
      setHumanStats(humanSummary);
      setAgentStats(agentSummary);
      setStats(workOwner === "human" ? humanSummary : agentSummary);
      setErr("");
    } catch (e) { setErr(`任务加载失败：${String(e)}`); }
  }

  useEffect(() => { load(); }, [scope, status, workOwner]);
  useEffect(() => {
    fetchLeads().then(setLeads).catch((e) => setErr(`客户列表加载失败：${String(e)}`));
  }, []);

  async function addTask() {
    const selected = leadOptions.find((item) => item.label === leadChoice)?.lead;
    if (!selected) { setErr("请从客户建议列表中选择一家公司"); return; }
    if (!title.trim()) { setErr("请输入明确的下一步动作"); return; }
    setBusy(true); setErr("");
    try {
      await createActivity({
        lead_no: selected.no, title: title.trim(), type, priority,
        ...(dueAt ? { due_at: dueAt } : {}),
      });
      setTitle(""); setLeadChoice(""); setDueAt(today()); setType("task"); setPriority("normal");
      setWorkOwner("human"); setStatus("open"); setScope("");
      await load(); onChanged();
    } catch (e) { setErr(`新建失败：${String(e)}`); }
    finally { setBusy(false); }
  }

  async function finish(task: Activity) {
    if (workOwner === "agent") return;
    setBusy(true); setErr("");
    try { await completeActivity(task.id); await load(); onChanged(); }
    catch (e) { setErr(`完成任务失败：${String(e)}`); load(); onChanged(); }
    finally { setBusy(false); }
  }

  const filters: { key: string; label: string; count: number }[] = [
    { key: "overdue", label: "逾期", count: stats?.overdue ?? 0 },
    { key: "today", label: "今天", count: stats?.today ?? 0 },
    { key: "upcoming", label: "未来", count: stats?.upcoming ?? 0 },
    { key: "no_due", label: "未排日期", count: stats?.no_due ?? 0 },
  ];

  return (
    <>
      <div className="filter-bar" style={{ marginBottom: 12 }}>
        <button className={`btn${workOwner === "human" ? " btn-primary" : ""}`}
          onClick={() => { setWorkOwner("human"); setStatus("open"); setScope(""); }}>
          需要我处理 {humanStats?.open_count ?? 0}
        </button>
        <button className={`btn${workOwner === "agent" ? " btn-primary" : ""}`}
          onClick={() => { setWorkOwner("agent"); setStatus("open"); setScope(""); }}>
          Agent处理中 {agentStats?.open_count ?? 0}
        </button>
      </div>

      {workOwner === "agent" && (
        <div className="card" style={{ marginBottom: 12, padding: 14 }}>
          <b>这些不是你的待办。</b>
          <span className="muted" style={{ marginLeft: 8 }}>
            Worker 会自动读官网、做 ICP、查公开决策人、修复联系渠道并回收任务；失败会自动延期重试。
            这里只用于查看 Agent 正在做什么。
          </span>
        </div>
      )}

      <div className="cards-row" style={{ marginBottom: 16 }}>
        {filters.map((item) => (
          <button key={item.key} className="card stat-card" style={{ textAlign: "left", cursor: "pointer" }}
            onClick={() => { setStatus("open"); setScope(scope === item.key ? "" : item.key); }}>
            <div className="stat-label">{item.label}</div>
            <div className="stat-value" style={{ color: item.key === "overdue" && item.count ? "var(--danger)" : undefined }}>
              {item.count}
            </div>
          </button>
        ))}
      </div>

      {workOwner === "human" && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>＋ 安排下一步</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input className="input" list="activity-lead-options" style={{ minWidth: 260, flex: 1 }}
              value={leadChoice} onChange={(e) => setLeadChoice(e.target.value)} placeholder="输入并选择客户公司" />
            <datalist id="activity-lead-options">
              {leadOptions.map((item) => <option key={item.lead.no} value={item.label} />)}
            </datalist>
            <input className="input" style={{ minWidth: 260, flex: 2 }} value={title}
              onChange={(e) => setTitle(e.target.value)} placeholder="下一步动作，如：确认 P2.5 箱体尺寸" />
            <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
              {Object.entries(TYPE_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <input className="input" type="date" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
            <select className="input" value={priority} onChange={(e) => setPriority(e.target.value)}>
              {Object.entries(PRIORITY_LABEL).map(([value, label]) => <option key={value} value={value}>{label}优先级</option>)}
            </select>
            <button className="btn btn-primary" onClick={addTask} disabled={busy}>创建任务</button>
          </div>
          {err && <div className="error-text" style={{ marginTop: 8 }}>{err}</div>}
        </div>
      )}

      <div className="filter-bar">
        <button className={`btn btn-sm${status === "open" && !scope ? " btn-primary" : ""}`}
          onClick={() => { setStatus("open"); setScope(""); }}>全部未完成 {stats?.open_count ?? 0}</button>
        {filters.map((item) => (
          <button key={item.key} className={`btn btn-sm${status === "open" && scope === item.key ? " btn-primary" : ""}`}
            onClick={() => { setStatus("open"); setScope(item.key); }}>{item.label} {item.count}</button>
        ))}
        <button className={`btn btn-sm${status === "done" ? " btn-primary" : ""}`}
          onClick={() => { setStatus("done"); setScope(""); }}>最近完成</button>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {tasks.length === 0 ? (
          <div className="muted" style={{ padding: 24, textAlign: "center" }}>
            {status === "done"
              ? "还没有已完成任务"
              : workOwner === "agent"
                ? "Agent 后台队列已清空。"
                : "当前没有需要你处理的销售任务。"}
          </div>
        ) : (
          <table className="lead-table">
            <thead><tr><th>状态</th><th>日期</th><th>行动</th><th>客户</th><th>类型</th><th>优先级</th><th>来源</th></tr></thead>
            <tbody>{tasks.map((task) => (
              <tr key={task.id}>
                <td>{task.status === "open" ? (
                  workOwner === "human"
                    ? <button className="btn btn-sm" onClick={() => finish(task)} disabled={busy} title="标记已完成">✓</button>
                    : <span className="muted">⚙ Agent</span>
                ) : <span style={{ color: "var(--green)" }}>✓ 已完成</span>}</td>
                <td><span style={{ color: task.due_at && task.due_at < today() && task.status === "open" ? "var(--danger)" : undefined }}>
                  {dueLabel(task)}</span></td>
                <td><b>{task.title}</b>{task.opportunity_title && <div className="muted" style={{ fontSize: 12 }}>商机：{task.opportunity_title}</div>}</td>
                <td><button className="btn btn-sm" onClick={() => onOpenLead(task.lead_no)}>{task.company_en}</button>
                  <div className="muted" style={{ fontSize: 11 }}>{task.country}</div></td>
                <td>{TYPE_LABEL[task.type] ?? task.type}</td>
                <td>{PRIORITY_LABEL[task.priority] ?? task.priority}</td>
                <td className="muted">{sourceLabel(task)}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
      {workOwner === "agent" && err && <div className="error-text" style={{ marginTop: 8 }}>{err}</div>}
    </>
  );
}
