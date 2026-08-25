import { useEffect, useState } from "react";
import { updateLead, addNote, createOpportunity, fetchOpportunities, deleteLead, fetchActivities, createActivity, completeActivity, fetchLead, fetchContacts, createContact, updateContact, setPrimaryContact, deleteContact, recheckLead } from "../api";
import type { Activity, Contact, Lead, LeadIntelligence, Opportunity } from "../types";
import { fetchLeadIntelligence } from "../salesIntelligenceApi";
import { fetchLeadMemory, writeLeadMemory, forgetLeadMemory, type MemoryItem } from "../agentApi";
import { STAGES, STAGE_LABEL, OPPORTUNITY_STAGE_LABEL } from "../types";

const CH_LABEL: Record<string, string> = { email: "Email", whatsapp: "WhatsApp", instagram: "Instagram" };
const STATE_TEXT: Record<string, string> = { replied: "已回复", messaged: "已触达" };
const ROLE_LABEL: Record<string, string> = {
  decision_maker: "决策人 / 采购", influencer: "影响人", technical: "技术",
  finance: "财务", other: "其他 / 未确认",
};
// 这个邮箱是官网联系页上写给买家的，还是页脚扒的，还是自己敲进去的——决定它值多少信任。
const SOURCE_LABEL: Record<string, string> = {
  "site.contact-page": "官网联系页", "site.homepage": "官网首页", manual: "手动录入",
};

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

function ContactCard({ contact, onRefresh, onError }: {
  contact: Contact; onRefresh: () => Promise<void>; onError: (message: string) => void;
}) {
  const [draft, setDraft] = useState(contact);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [memoryItems, setMemoryItems] = useState<MemoryItem[]>([]);
  const [memoryDraft, setMemoryDraft] = useState("");
  const [memoryKind, setMemoryKind] = useState<"profile" | "log">("profile");
  useEffect(() => setDraft(contact), [contact]);
  const set = (key: keyof Contact, value: string | null) =>
    setDraft((old) => ({ ...old, [key]: value }));
  async function save() {
    setBusy(true); onError("");
    try {
      await updateContact(contact.id, {
        name: draft.name, title: draft.title, email: draft.email, phone: draft.phone,
        linkedin: draft.linkedin, role: draft.role, note: draft.note,
      });
      await onRefresh();
    } catch (e) { onError(`保存联系人失败：${String(e)}`); }
    finally { setBusy(false); }
  }
  async function makePrimary() {
    setBusy(true); onError("");
    try { await setPrimaryContact(contact.id); await onRefresh(); }
    catch (e) { onError(`设置主要联系人失败：${String(e)}`); }
    finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); onError("");
    try { await deleteContact(contact.id); await onRefresh(); }
    catch (e) { onError(`删除联系人失败：${String(e)}`); }
    finally { setBusy(false); }
  }
  return (
    <div className="note-item" style={{ marginBottom: 9 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", marginBottom: 7 }}>
        <div>
          <b>{draft.name || draft.email || draft.phone || "未命名联系人"}</b>
          {contact.is_primary && <span className="badge badge-replied" style={{ marginLeft: 7 }}><i />主要联系人</span>}
          <span className="muted" style={{ marginLeft: 7, fontSize: 12 }}>{ROLE_LABEL[draft.role]}</span>
        </div>
        {!contact.is_primary && <button className="btn btn-sm" onClick={makePrimary} disabled={busy}>设为主要</button>}
      </div>
      <div className="field-grid">
        <div className="field"><label>姓名</label><input className="input" value={draft.name ?? ""} onChange={(e) => set("name", e.target.value || null)} /></div>
        <div className="field"><label>职位</label><input className="input" value={draft.title ?? ""} onChange={(e) => set("title", e.target.value || null)} /></div>
        <div className="field"><label>邮箱</label><input className="input" value={draft.email ?? ""} onChange={(e) => set("email", e.target.value || null)} /></div>
        <div className="field"><label>电话 / WhatsApp</label><input className="input" value={draft.phone ?? ""} onChange={(e) => set("phone", e.target.value || null)} /></div>
        <div className="field"><label>LinkedIn</label><input className="input" value={draft.linkedin ?? ""} onChange={(e) => set("linkedin", e.target.value || null)} /></div>
        <div className="field"><label>采购角色</label>
          <select className="input" value={draft.role} onChange={(e) => set("role", e.target.value)}>
            {Object.entries(ROLE_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      </div>
      <div className="field"><label>联系人备注</label>
        <input className="input" value={draft.note ?? ""} onChange={(e) => set("note", e.target.value || null)} placeholder="例如：负责技术确认，偏好 WhatsApp" />
      </div>
      <button className="btn btn-primary btn-sm" onClick={save} disabled={busy}>保存联系人</button>
      {confirmDelete ? <>
        <button className="btn btn-sm" style={{ marginLeft: 7, color: "var(--danger)" }} onClick={remove} disabled={busy}>确认删除</button>
        <button className="btn btn-sm" style={{ marginLeft: 5 }} onClick={() => setConfirmDelete(false)}>取消</button>
      </> : <button className="btn btn-sm" style={{ marginLeft: 7 }} onClick={() => setConfirmDelete(true)}>删除</button>}
    </div>
  );
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
  const [memoryItems, setMemoryItems] = useState<MemoryItem[]>([]);
  const [memoryDraft, setMemoryDraft] = useState("");
  const [memoryKind, setMemoryKind] = useState<"profile" | "log">("profile");
  const [deleting, setDeleting] = useState(false);
  const [blockToo, setBlockToo] = useState(true);
  const [openTasks, setOpenTasks] = useState<Activity[]>([]);
  const [doneTasks, setDoneTasks] = useState<Activity[]>([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDue, setTaskDue] = useState(localToday());
  const [taskType, setTaskType] = useState("task");
  const [taskBusy, setTaskBusy] = useState(false);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [showNewContact, setShowNewContact] = useState(false);
  const [contactName, setContactName] = useState("");
  const [contactTitle, setContactTitle] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactRole, setContactRole] = useState("other");
  const [contactBusy, setContactBusy] = useState(false);
  const [rechecking, setRechecking] = useState(false);
  const [recheckMsg, setRecheckMsg] = useState("");
  const [intelligence, setIntelligence] = useState<LeadIntelligence | null>(null);

  async function runRecheck() {
    setRechecking(true); setRecheckMsg(""); setErr("");
    try {
      const r = await recheckLead(lead.no);
      setDraft(r.lead); onChange(r.lead);
      fetchLeadIntelligence(lead.no).then(setIntelligence).catch(() => undefined);
      setRecheckMsg(r.changed
        ? `官网有更新：${(r.notes ?? []).join("；")}`
        : `官网没有变化，下次 ${r.next_due} 再看`);
    } catch (e) { setErr(`复检失败：${String(e)}`); }
    finally { setRechecking(false); }
  }

  async function loadTasks(leadNo: number) {
    const [open, done] = await Promise.all([
      fetchActivities({ lead_no: leadNo, status: "open" }),
      fetchActivities({ lead_no: leadNo, status: "done", limit: 3 }),
    ]);
    setOpenTasks(open); setDoneTasks(done.slice(0, 3));
  }

  async function refreshContacts() {
    const [rows, updated] = await Promise.all([fetchContacts(lead.no), fetchLead(lead.no)]);
    setContacts(rows); setDraft(updated); onChange(updated);
  }

  useEffect(() => {
    setDraft(lead); setDirty(false); setConfirmDelete(false);
    setProjectTitle(`${lead.company_en} LED 项目`);
    fetchOpportunities({ lead_no: lead.no }).then(setOpportunities)
      .catch((e) => setErr(`商机加载失败：${String(e)}`));
    loadTasks(lead.no).catch((e) => setErr(`任务加载失败：${String(e)}`));
    fetchContacts(lead.no).then(setContacts)
      .catch((e) => setErr("联系人加载失败：" + String(e)));
    fetchLeadIntelligence(lead.no).then(setIntelligence)
      .catch((e) => setErr("销售评分加载失败：" + String(e)));
    setMemoryDraft("");
    fetchLeadMemory(lead.no).then((m) => setMemoryItems(m.items))
      .catch((e) => setErr("客户记忆加载失败：" + String(e)));
  }, [lead.no]);

  async function submitMemory() {
    const text = memoryDraft.trim();
    if (!text) return;
    try {
      await writeLeadMemory(lead.no, text, memoryKind);
      setMemoryDraft("");
      setMemoryItems((await fetchLeadMemory(lead.no)).items);
    } catch (e) { setErr("记忆保存失败：" + String(e)); }
  }

  async function dropMemory(itemId: number) {
    try {
      await forgetLeadMemory(lead.no, itemId);
      setMemoryItems((await fetchLeadMemory(lead.no)).items);
    } catch (e) { setErr("记忆删除失败：" + String(e)); }
  }

  const set = (k: keyof Lead, v: string) => { setDraft((d) => ({ ...d, [k]: v })); setDirty(true); };

  async function save() {
    setSaving(true); setErr("");
    try {
      const updated = await updateLead(lead.no, {
        company_en: draft.company_en, country: draft.country, city: draft.city,
        website: draft.website, instagram: draft.instagram, facebook: draft.facebook,
        business: draft.business, stage: draft.stage,
        tags: draft.tags, brief: draft.brief, hook: draft.hook,
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
    } catch (e) { setErr(`完成任务失败：${String(e)}`); await loadTasks(lead.no); onTasksChange(); }
    finally { setTaskBusy(false); }
  }

  async function addContact() {
    if (![contactName, contactEmail, contactPhone].some((value) => value.trim())) {
      setErr("联系人至少填写姓名、邮箱或电话"); return;
    }
    setContactBusy(true); setErr("");
    try {
      await createContact({
        lead_no: lead.no, name: contactName || null, title: contactTitle || null,
        email: contactEmail || null, phone: contactPhone || null, role: contactRole,
      });
      setContactName(""); setContactTitle(""); setContactEmail(""); setContactPhone("");
      setContactRole("other"); setShowNewContact(false); await refreshContacts();
    } catch (e) { setErr(`新建联系人失败：${String(e)}`); await refreshContacts(); }
    finally { setContactBusy(false); }
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

        <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>客户简介</span>
          <button className="btn btn-sm" onClick={runRecheck} disabled={rechecking || !draft.website}
            title={draft.website ? "重新读一遍官网：补上缺的联系方式，官网改了就提示" : "没有官网，无法复检"}>
            {rechecking ? "复检中…" : "复检官网"}
          </button>
        </div>
        {draft.brief
          ? <div className="note-item" style={{ marginBottom: 8 }}>{draft.brief}</div>
          : <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
              官网没写出可以引用的具体信息，简介留空——宁可空着，也不编一句发出去被客户看穿。
            </div>}
        <div className="field">
          <label>开场白（消息模板里写 {"{hook}"}）</label>
          <input className="input" value={draft.hook ?? ""} onChange={(e) => set("hook", e.target.value)}
            placeholder="留空则消息里这句自动消失" />
        </div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
          邮箱来源：{SOURCE_LABEL[draft.email_source ?? ""] ?? "未标注"}
          {draft.recheck_due ? ` · 下次复检 ${draft.recheck_due}` : ""}
        </div>
        {recheckMsg && <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>{recheckMsg}</div>}

        <div className="section-title">销售优先级</div>
        {intelligence ? <div className="card" style={{ padding: 10, marginBottom: 10 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
            <b style={{ fontSize: 22 }}>{intelligence.score}</b>
            <span>{intelligence.grade} 级</span>
            <span className="muted">不是成交概率</span>
          </div>
          <div style={{ marginBottom: 7 }}><b>下一步：</b>{intelligence.next_action}</div>
          <div className="muted" style={{ fontSize: 12 }}>
            {intelligence.components.map((component) =>
              component.label + " " + component.score + "/" + component.max).join(" · ")}
          </div>
          {intelligence.warnings.map((warning) =>
            <div className="error-text" key={warning} style={{ marginTop: 4 }}>{warning}</div>)}
          {intelligence.signals.length > 0 && <div style={{ marginTop: 9 }}>
            <b>采购信号与证据</b>
            {intelligence.signals.slice(0, 5).map((signal) => <div className="note-item" key={signal.id} style={{ marginTop: 6 }}>
              <b>{signal.headline}</b> · 可信度 {signal.confidence}/100
              <div className="muted" style={{ marginTop: 3 }}>{signal.evidence}</div>
              <a href={signal.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>查看来源 ↗</a>
            </div>)}
          </div>}
        </div> : <div className="muted" style={{ marginBottom: 8 }}>正在计算可解释销售优先级…</div>}

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

        <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>联系人（{contacts.length}）</span>
          <button className="btn btn-sm" onClick={() => setShowNewContact(!showNewContact)}>＋ 新建联系人</button>
        </div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          主要联系人是邮件、WhatsApp 和话术个性化的默认对象；次要联系人不会被自动群发。
        </div>
        {showNewContact && (
          <div className="card" style={{ padding: 10, marginBottom: 10 }}>
            <div className="field-grid">
              <div className="field"><label>姓名</label><input className="input" value={contactName} onChange={(e) => setContactName(e.target.value)} /></div>
              <div className="field"><label>职位</label><input className="input" value={contactTitle} onChange={(e) => setContactTitle(e.target.value)} /></div>
              <div className="field"><label>邮箱</label><input className="input" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} /></div>
              <div className="field"><label>电话 / WhatsApp</label><input className="input" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} /></div>
              <div className="field"><label>采购角色</label>
                <select className="input" value={contactRole} onChange={(e) => setContactRole(e.target.value)}>
                  {Object.entries(ROLE_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </div>
            </div>
            <button className="btn btn-primary btn-sm" onClick={addContact} disabled={contactBusy}>添加联系人</button>
          </div>
        )}
        {contacts.length === 0 ? <div className="muted">还没有联系人；添加采购、技术或财务联系人后再安排触达。</div> :
          contacts.map((contact) => <ContactCard key={contact.id} contact={contact}
            onRefresh={refreshContacts} onError={setErr} />)}

        <div className="section-title">公司渠道与资料</div>
        <div className="field-grid">
          {field("website", "官网")}
          {field("instagram", "Instagram")}
          {field("facebook", "Facebook")}
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

        {/* 客户记忆：Agent 从往来里合成的事实，加上 Allen 手写的。手写的 Agent 不会改。 */}
        <div className="section-title">客户记忆</div>
        <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
          <select className="input" style={{ width: 110 }} value={memoryKind}
            onChange={(e) => setMemoryKind(e.target.value as "profile" | "log")}>
            <option value="profile">长期</option>
            <option value="log">阶段性</option>
          </select>
          <input className="input" style={{ flex: 1 }} value={memoryDraft}
            placeholder="记一条 Agent 看不出来的事，如：老板不喜欢被追，等他主动"
            onChange={(e) => setMemoryDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submitMemory(); }} />
          <button className="btn btn-sm" onClick={submitMemory}>记住</button>
        </div>
        {memoryItems.length === 0 ? <div className="muted">还没有记忆；Agent 每次收到回复会自己补充。</div> :
          memoryItems.map((m) => (
            <div key={m.id} className="note-item" style={{ display: "flex", gap: 8 }}>
              <span className={`badge badge-${m.kind === "profile" ? "messaged" : "untouched"}`}>
                <i />{m.kind === "profile" ? "长期" : "阶段性"}
              </span>
              <div style={{ flex: 1 }}>
                {m.content}
                <div className="ts">{m.origin === "explicit" ? "我记的" : "Agent 从往来里总结"}</div>
              </div>
              <button className="btn btn-sm" onClick={() => dropMemory(m.id)}>删除</button>
            </div>
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
