import { useEffect, useState } from "react";
import { updateLead, addNote, createOpportunity, fetchOpportunities, deleteLead, fetchActivities, createActivity, completeActivity, fetchLead } from "../api";
import type { Activity, Lead, Opportunity } from "../types";
import { STAGES, STAGE_LABEL, OPPORTUNITY_STAGE_LABEL } from "../types";

const CH_LABEL: Record<string, string> = { email: "Email", whatsapp: "WhatsApp", instagram: "Instagram" };
const STATE_TEXT: Record<string, string> = { replied: "已回复", messaged: "已触达" };

function fmtTs(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(+d) ? iso : d.toLocaleString();
}

function localToday(): string {
  const d = new Date();
  const pad = (v: number) => String(v).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function LeadDrawer({ lead, onClose, onChange, onDeleted, onTasksChange }: {
  lead: Lead; onClose: () => void; onChange: (l: Lead) => void; onDeleted: (no: number) => void;
  onTasksChange: () => void;
}) {
  const [draft, setDraft] = useState<Lead>(lead);
  const [note, setNote] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [showNewOpportunity, setShowNewOpportunity] = useState(false);
  const [projectTitle, setProjectTitle] = useState("");
  const [projectAmount, setProjectAmount] = useState("");
  const [projectClose, setProjectClose] = useState("");
  const [projectBusy, setProjectBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [blockToo, setBlockToo] = useState(true);
  const [openTasks, setOpenTasks] = useState<Activity[]>([]);
  const [doneTasks, setDoneTasks] = useState<Activity[]>([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDue, setTaskDue] = useState(localToday());
  const [taskType, setTaskType] = useState("task");
  const [taskBusy, setTaskBusy] = useState(false);

  async function loadTasks(leadNo: number) {
    const [open, done] = await Promise.all([
      fetchActivities({ lead_no: leadNo, status: "open" }),
      fetchActivities({ lead_no: leadNo, status: "done", limit: 3 }),
    ]);
    setOpenTasks(open); setDoneTasks(done.slice(0, 3));
  }

  useEffect(() => {
    setDraft(lead); setDirty(false); setConfirmDelete(false);
    setProjectTitle(`${lead.company_en} LED 项目`);
    fetchOpportunities({ lead_no: lead.no }).then(setOpportunities)
      .catch((e) => setErr(`商机加载失败：${String(e)}`));
    loadTasks(lead.no).catch((e) => setErr(`任务加载失败：${String(e)}`));
  }, [lead.no]);

  const set = (k: keyof Lead, v: string) => { setDraft((d) => ({ ...d, [k]: v })); setDirty(true); };

  async function save() {
    setSaving(true); setErr("");
    try {
      const updated = await updateLead(lead.no, {
        company_en: draft.company_en, country: draft.country, city: draft.city,
        contact_name: draft.contact_name, title: draft.title,
        email: draft.email, phone: draft.phone,
        website: draft.website, instagram: draft.instagram, facebook: draft.facebook,
        linkedin: draft.linkedin, business: draft.business, stage: draft.stage,
        tags: draft.tags,
      });
      setDraft(updated); setDirty(false); onChange(updated);
    } catch (e) { setErr(String(e)); } finally { setSaving(false); }
  }

  async function saveStage(stage: string) {
    setDraft((d) => ({ ...d, stage }));
    try { const u = await updateLead(lead.no, { stage }); onChange(u); }
    catch (e) { setErr(String(e)); }
  }

  async function submitNote() {
    const t = note.trim();
    if (!t) return;
    try { const u = await addNote(lead.no, t); setDraft(u); setNote(""); onChange(u); }
    catch (e) { setErr(String(e)); }
  }

  async function addProject() {
    if (!projectTitle.trim()) return;
    setProjectBusy(true); setErr("");
    try {
      await createOpportunity({
        lead_no: lead.no,
        title: projectTitle.trim(),
        ...(projectAmount ? { amount: Number(projectAmount) } : {}),
        ...(projectClose ? { expected_close_date: projectClose } : {}),
      });
      setOpportunities(await fetchOpportunities({ lead_no: lead.no }));
      setShowNewOpportunity(false); setProjectAmount(""); setProjectClose("");
      setProjectTitle(`${lead.company_en} LED 项目`);
    } catch (e) { setErr(String(e)); }
    finally { setProjectBusy(false); }
  }

  async function addTask() {
    if (!taskTitle.trim()) { setErr("请输入明确的下一步动作"); return; }
    setTaskBusy(true); setErr("");
    try {
      await createActivity({
        lead_no: lead.no, title: taskTitle.trim(), type: taskType,
        ...(taskDue ? { due_at: taskDue } : {}),
      });
      const updated = await fetchLead(lead.no);
      setDraft(updated); onChange(updated);
      await loadTasks(lead.no);
      setTaskTitle(""); setTaskDue(localToday()); setTaskType("task"); onTasksChange();
    } catch (e) { setErr(`新建任务失败：${String(e)}`); }
    finally { setTaskBusy(false); }
  }

  async function finishTask(taskId: number) {
    setTaskBusy(true); setErr("");
    try {
      await completeActivity(taskId);
      const updated = await fetchLead(lead.no);
      setDraft(updated); onChange(updated);
      await loadTasks(lead.no); onTasksChange();
    } catch (e) { setErr(`完成任务失败：${String(e)}`); }
    finally { setTaskBusy(false); }
  }

  const blockDomain = (draft.website || draft.email || "").replace(/^https?:\/\/(www\.)?/, "").split("/")[0].split("@").pop() || "";

  async function removeLead() {
    setDeleting(true); setErr("");
    try { await deleteLead(lead.no, blockToo && !!blockDomain); onDeleted(lead.no); }
    catch (e) { setErr(String(e)); setDeleting(false); setConfirmDelete(false); }
  }

  const field = (k: keyof Lead, label: string, type = "text") => (
    <div className="field">
      <label>{label}</label>
      <input className="input" type={type} value={(draft[k] as string) ?? ""} onChange={(e) => set(k, e.target.value)} />
    </div>
  );
  const tags = (draft.tags ?? "").split(",").map((t) => t.trim()).filter(Boolean);

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose} title="关闭">×</button>
        <h2>{draft.company_en}</h2>
        <div className="muted" style={{ marginBottom: 12 }}>#{lead.no} · {draft.country}{draft.city ? ` · ${draft.city}` : ""}</div>

        <div className="field">
          <label>销售阶段</label>
          <select className="input" value={draft.stage} onChange={(e) => saveStage(e.target.value)}>
            {STAGES.map((s) => <option key={s} value={s}>{STAGE_LABEL[s]}</option>)}
          </select>
        </div>

        <div className="field">
          <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}
            title="打开后此客户被所有发送路径排除：群发、WA/IG、跟进序列都不会再触达（客户要求退订或不想再联系时用）">
            <input type="checkbox" checked={!!draft.do_not_contact}
              onChange={async (e) => {
                const v = e.target.checked;
                setDraft((d) => ({ ...d, do_not_contact: v }));
                try { const u = await updateLead(lead.no, { do_not_contact: v }); onChange(u); }
                catch (er) { setErr(String(er)); }
              }} />
            🚫 不再联系（从所有发送中排除）
          </label>
          {!!draft.do_not_contact && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>已排除：群发、WhatsApp/Instagram、跟进序列都不会再发给这家。</div>}
        </div>

        <div className="section-title">下一步行动</div>
        <div className="card" style={{ padding: 10, marginBottom: 10 }}>
          <input className="input" style={{ width: "100%", marginBottom: 7 }} value={taskTitle}
            onChange={(e) => setTaskTitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") addTask(); }}
            placeholder="明确动作，如：确认 P2.5 箱体尺寸并发送报价" />
          <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
            <select className="input" value={taskType} onChange={(e) => setTaskType(e.target.value)}>
              <option value="task">任务</option><option value="call">电话</option>
              <option value="email">Email</option><option value="whatsapp">WhatsApp</option>
              <option value="instagram">Instagram</option><option value="meeting">会议</option>
              <option value="quote">报价</option>
            </select>
            <input className="input" type="date" value={taskDue} onChange={(e) => setTaskDue(e.target.value)} />
            <button className="btn btn-primary btn-sm" onClick={addTask} disabled={taskBusy}>安排任务</button>
          </div>
        </div>
        {openTasks.length === 0 ? <div className="muted">暂无未完成任务</div> : openTasks.map((task) => (
          <div key={task.id} className="note-item" style={{ marginBottom: 7, display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
            <div>
              <b>{task.title}</b>
              <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>
                {task.due_at ? (task.due_at < localToday() ? `⚠ 已逾期 · ${task.due_at}` : task.due_at === localToday() ? "今天" : task.due_at) : "未排日期"}
                {task.source === "reply" ? " · 客户回复" : task.source === "opportunity" ? " · 商机" : ""}
              </div>
            </div>
            <button className="btn btn-sm" onClick={() => finishTask(task.id)} disabled={taskBusy}>✓ 完成</button>
          </div>
        ))}
        {doneTasks.length > 0 && (
          <details style={{ marginTop: 8 }}>
            <summary className="muted" style={{ cursor: "pointer" }}>最近完成 {doneTasks.length} 项</summary>
            {doneTasks.map((task) => (
              <div key={task.id} className="muted" style={{ fontSize: 12, padding: "5px 0" }}>
                ✓ {task.title} · {fmtTs(task.completed_at)}
              </div>
            ))}
          </details>
        )}
        <div className="field">
          <label>标签（逗号分隔，如 hot,distributor,大项目）</label>
          <input className="input" value={draft.tags ?? ""} onChange={(e) => set("tags", e.target.value)} placeholder="hot, 经销商, 租赁" />
          {tags.length > 0 && <div style={{ marginTop: 5 }}>{tags.map((t) => <span key={t} className="tag-chip">{t}</span>)}</div>}
        </div>

        <div className="section-title">联系方式</div>
        <div className="field-grid">
          {field("email", "邮箱")}
          {field("phone", "电话 / WhatsApp")}
          {field("website", "官网")}
          {field("contact_name", "联系人")}
          {field("title", "职位")}
          {field("instagram", "Instagram")}
          {field("facebook", "Facebook")}
          {field("linkedin", "LinkedIn")}
        </div>
        <div className="field-grid">
          {field("company_en", "公司名")}
          {field("country", "国家")}
          {field("city", "城市")}
        </div>
        <div className="field">
          <label>业务描述</label>
          <textarea className="input" style={{ height: 64 }} value={draft.business ?? ""} onChange={(e) => set("business", e.target.value)} />
        </div>

        <button className="btn btn-primary" onClick={save} disabled={!dirty || saving}>
          {saving ? "保存中…" : dirty ? "保存修改" : "已保存"}
        </button>
        {err && <span className="error-text" style={{ marginLeft: 10 }}>{err}</span>}

        <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>LED 项目 / 商机</span>
          <button className="btn btn-sm" onClick={() => setShowNewOpportunity(!showNewOpportunity)}>
            ＋ 新建商机
          </button>
        </div>
        {showNewOpportunity && (
          <div className="card" style={{ padding: 10, marginBottom: 10 }}>
            <input className="input" style={{ width: "100%", marginBottom: 6 }}
              value={projectTitle} onChange={(e) => setProjectTitle(e.target.value)}
              placeholder="项目名称，如：教堂 P2.5 室内屏" />
            <div className="field-grid">
              <div className="field"><label>预估金额 USD（可选）</label>
                <input className="input" type="number" min="0" value={projectAmount}
                  onChange={(e) => setProjectAmount(e.target.value)} /></div>
              <div className="field"><label>预计成交日（可选）</label>
                <input className="input" type="date" value={projectClose}
                  onChange={(e) => setProjectClose(e.target.value)} /></div>
            </div>
            <button className="btn btn-primary btn-sm" onClick={addProject} disabled={projectBusy}>
              {projectBusy ? "创建中…" : "创建商机"}
            </button>
          </div>
        )}
        {opportunities.length === 0 ? <div className="muted">暂无明确项目；客户确认需求后在这里建商机。</div> :
          opportunities.map((o) => (
            <div key={o.id} className="note-item" style={{ marginBottom: 7 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <b>{o.title}</b>
                <span className={`stage-badge stage-${o.stage}`}>
                  {OPPORTUNITY_STAGE_LABEL[o.stage]}</span>
              </div>
              <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>
                {o.amount ? `${o.currency} ${o.amount.toLocaleString()} · ` : ""}
                概率 {o.probability}% · 下一步：{o.next_action || "未安排"}
                {o.overdue ? " · ⚠ 已逾期" : o.stale ? " · ⚠ 已停滞" : ""}
              </div>
            </div>
          ))}

        <div className="section-title">触达状态</div>
        {draft.outreach.length === 0 ? <div className="muted">尚未触达</div> :
          draft.outreach.map((o) => (
            <span key={o.channel} className={`badge badge-${o.status === "replied" ? "replied" : o.status === "messaged" ? "messaged" : "untouched"}`} style={{ marginRight: 6 }}>
              <i />{CH_LABEL[o.channel] ?? o.channel}：{STATE_TEXT[o.status] ?? o.status}
              {o.message_sent_date ? ` (${o.message_sent_date})` : ""}
            </span>
          ))}

        <div className="section-title">跟进记录</div>
        <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
          <input className="input" style={{ flex: 1 }} value={note} placeholder="加一条跟进，如：打了电话，要 P2.5 报价"
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submitNote(); }} />
          <button className="btn btn-sm" onClick={submitNote}>添加</button>
        </div>
        {draft.notes.length === 0 ? <div className="muted">还没有跟进记录</div> :
          draft.notes.map((n) => (
            <div key={n.id} className="note-item">
              <div className="ts">{fmtTs(n.created_at)}</div>
              <div>{n.text}</div>
            </div>
          ))}

        {/* 删除放最底部：不是客户（同行、中国厂的海外分公司）才用它。
            只是暂时不想联系，用上面的「不再联系」——那个可以撤销，这个不能。 */}
        <div className="section-title">删除客户</div>
        {confirmDelete ? (
          <div>
            <div style={{ marginBottom: 6 }}>
              确定删除 <b>{draft.company_en}</b>？触达记录、销售任务、跟进记录、商机会一起消失，<b>不可恢复</b>。
            </div>
            {blockDomain && (
              <label style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, cursor: "pointer" }}
                title="不加的话，下次跑采集导入时这家还会被重新收进来——采集文件里仍有它">
                <input type="checkbox" checked={blockToo} onChange={(e) => setBlockToo(e.target.checked)} />
                同时把 <b>{blockDomain}</b> 加入「永不再收录」（否则下次采集会再收进来）
              </label>
            )}
            <button className="btn btn-sm" style={{ background: "#c0392b", color: "#fff", borderColor: "#c0392b", marginRight: 8 }}
              onClick={removeLead} disabled={deleting}>
              {deleting ? "删除中…" : "确认删除"}
            </button>
            <button className="btn btn-sm" onClick={() => setConfirmDelete(false)} disabled={deleting}>取消</button>
          </div>
        ) : (
          <div>
            <button className="btn btn-sm" onClick={() => setConfirmDelete(true)}
              title="彻底删除这家公司及其全部记录。只是不想再联系的话，用上面的「不再联系」">
              🗑 从客户库删除
            </button>
            <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
              用于同行、中国厂的海外分公司这类根本不是客户的记录。只是不想再联系，请用上面的「不再联系」。
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
