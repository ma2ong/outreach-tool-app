import { useEffect, useState } from "react";
import { fetchOpportunities, fetchOpportunityStats, updateOpportunity } from "../api";
import type { Opportunity, OpportunityStats } from "../types";
import { OPPORTUNITY_STAGES, OPPORTUNITY_STAGE_LABEL } from "../types";

const money = (value: number | null | undefined, currency = "USD") =>
  new Intl.NumberFormat("en-US", {
    style: "currency", currency, maximumFractionDigits: 0,
  }).format(value ?? 0);

function OpportunityEditor({ item, onSaved, onClose }: {
  item: Opportunity; onSaved: (item: Opportunity) => void; onClose: () => void;
}) {
  const [draft, setDraft] = useState<Opportunity>(item);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const set = (key: keyof Opportunity, value: unknown) =>
    setDraft((d) => ({ ...d, [key]: value }));
  async function save() {
    setSaving(true); setMsg("");
    try {
      const saved = await updateOpportunity(item.id, {
        title: draft.title,
        stage: draft.stage,
        amount: draft.amount,
        currency: draft.currency,
        probability: draft.probability,
        expected_close_date: draft.expected_close_date,
        next_action: draft.next_action,
        next_action_date: draft.next_action_date,
        use_case: draft.use_case,
        indoor_outdoor: draft.indoor_outdoor,
        width_m: draft.width_m,
        height_m: draft.height_m,
        quantity: draft.quantity,
        pixel_pitch: draft.pixel_pitch,
        destination: draft.destination,
        incoterm: draft.incoterm,
        competitor: draft.competitor,
        loss_reason: draft.loss_reason,
      });
      onSaved(saved); setDraft(saved); setMsg("已保存");
    } catch (e) {
      setMsg(String(e));
      // The save may well have landed before the error. Re-read this one opportunity so
      // the form shows the server's version rather than the guess it was left holding.
      const fresh = (await fetchOpportunities().catch(() => []))
        .find((o) => o.id === item.id);
      if (fresh) { onSaved(fresh); setDraft(fresh); }
    }
    finally { setSaving(false); }
  }
  const text = (key: keyof Opportunity, label: string, placeholder = "") => (
    <div className="field">
      <label>{label}</label>
      <input className="input" value={(draft[key] as string | null) ?? ""}
        placeholder={placeholder} onChange={(e) => set(key, e.target.value || null)} />
    </div>
  );
  const num = (key: keyof Opportunity, label: string, min = 0) => (
    <div className="field">
      <label>{label}</label>
      <input className="input" type="number" min={min}
        value={(draft[key] as number | null) ?? ""}
        onChange={(e) => set(key, e.target.value === "" ? null : Number(e.target.value))} />
    </div>
  );
  return (
    <div className="card" style={{ marginTop: 14, borderColor: "var(--blue)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>编辑商机 · {item.company_en}</h3>
        <button className="btn btn-sm" onClick={onClose}>关闭</button>
      </div>
      <div className="field-grid" style={{ marginTop: 12 }}>
        {text("title", "项目名称")}
        <div className="field">
          <label>阶段</label>
          <select className="input" value={draft.stage}
            onChange={(e) => set("stage", e.target.value)}>
            {OPPORTUNITY_STAGES.map((s) =>
              <option key={s} value={s}>{OPPORTUNITY_STAGE_LABEL[s]}</option>)}
          </select>
        </div>
        {num("amount", `金额（${draft.currency}）`)}
        {num("probability", "成交概率 %")}
        <div className="field">
          <label>预计成交日</label>
          <input className="input" type="date" value={draft.expected_close_date ?? ""}
            onChange={(e) => set("expected_close_date", e.target.value || null)} />
        </div>
        <div className="field">
          <label>下一步日期</label>
          <input className="input" type="date" value={draft.next_action_date ?? ""}
            onChange={(e) => set("next_action_date", e.target.value || null)} />
        </div>
        {text("next_action", "下一步动作", "例如：周五确认图纸与付款条款")}
        {text("use_case", "使用场景", "舞台租赁 / 教堂 / 商场 / 户外广告")}
        <div className="field">
          <label>室内 / 户外</label>
          <select className="input" value={draft.indoor_outdoor ?? ""}
            onChange={(e) => set("indoor_outdoor", e.target.value || null)}>
            <option value="">未确认</option><option value="indoor">室内</option>
            <option value="outdoor">户外</option><option value="both">室内+户外</option>
          </select>
        </div>
        {text("pixel_pitch", "像素间距", "P1.86 / P2.5 / P3.91")}
        {num("width_m", "宽度（米）", 0.1)}
        {num("height_m", "高度（米）", 0.1)}
        {num("quantity", "数量", 1)}
        {text("destination", "目的地 / 港口")}
        {text("incoterm", "贸易条款", "EXW / FOB / CIF / DDP")}
        {text("competitor", "竞争对手")}
        {text("loss_reason", "丢单原因", "价格 / 交期 / 竞争对手 / 项目取消")}
      </div>
      <button className="btn btn-primary" onClick={save} disabled={saving}>
        {saving ? "保存中…" : "保存商机"}
      </button>
      {msg && <span className={msg === "已保存" ? "muted" : "error-text"}
        style={{ marginLeft: 10 }}>{msg}</span>}
    </div>
  );
}

export function OpportunityPipeline({ onOpenLead, onChanged }: {
  onOpenLead: (no: number) => void; onChanged?: () => void;
}) {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [stats, setStats] = useState<OpportunityStats | null>(null);
  const [stage, setStage] = useState("");
  const [attention, setAttention] = useState(false);
  const [editing, setEditing] = useState<Opportunity | null>(null);
  const [err, setErr] = useState("");
  function load() {
    Promise.all([
      fetchOpportunities({ stage: stage || undefined, attention }),
      fetchOpportunityStats(),
    ]).then(([rows, summary]) => {
      setItems(rows); setStats(summary); setErr("");
      if (editing) setEditing(rows.find((r) => r.id === editing.id) ?? editing);
    }).catch((e) => setErr(String(e)));
  }
  useEffect(load, [stage, attention]);

  return (
    <>
      <div className="cards-row">
        <div className="card stat-card"><div className="stat-label">开放商机</div>
          <div className="stat-value">{stats?.open_count ?? 0}</div></div>
        <div className="card stat-card"><div className="stat-label">开放金额</div>
          <div className="stat-value">{money(stats?.open_amount)}</div></div>
        <div className="card stat-card"><div className="stat-label">加权预测</div>
          <div className="stat-value" style={{ color: "var(--green)" }}>{money(stats?.weighted_amount)}</div></div>
        <div className="card stat-card"><div className="stat-label">本月预计成交</div>
          <div className="stat-value">{money(stats?.closing_this_month)}</div></div>
        <div className="card stat-card"><div className="stat-label">需要处理</div>
          <div className="stat-value" style={{ color: "var(--warn)" }}>
            {stats?.attention_count ?? 0}
          </div>
          <div className="muted" style={{ fontSize: 12 }}>
            逾期 {stats?.overdue_count ?? 0} · 停滞 {stats?.stale_count ?? 0}
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
            <option value="">全部阶段</option>
            {OPPORTUNITY_STAGES.map((s) =>
              <option key={s} value={s}>{OPPORTUNITY_STAGE_LABEL[s]}</option>)}
          </select>
          <button className={`btn btn-sm${attention ? " btn-primary" : ""}`}
            onClick={() => setAttention(!attention)}>
            ⚠ 只看逾期/停滞
          </button>
          <span className="muted">共 {items.length} 个项目 · 默认先处理逾期动作和停滞商机</span>
        </div>
        {err && <div className="error-text">{err}</div>}
        <div className="table-wrap">
          <table className="table">
            <thead><tr>
              <th>客户 / 项目</th><th>阶段</th><th>金额</th><th>加权</th>
              <th>预计成交</th><th>下一步</th><th>LED 规格</th><th>状态</th><th></th>
            </tr></thead>
            <tbody>
              {items.map((o) => (
                <tr key={o.id}>
                  <td><button className="btn btn-sm" onClick={() => onOpenLead(o.lead_no)}>
                    {o.company_en}</button><div className="muted" style={{ fontSize: 12 }}>{o.title}</div></td>
                  <td><span className={`stage-badge stage-${o.stage}`}>
                    {OPPORTUNITY_STAGE_LABEL[o.stage]}</span></td>
                  <td className="num">{money(o.amount, o.currency)}</td>
                  <td className="num">{money(o.weighted_amount, o.currency)}</td>
                  <td>{o.expected_close_date || "—"}</td>
                  <td>{o.next_action || <span className="muted">未安排</span>}
                    <div className="muted" style={{ fontSize: 11 }}>{o.next_action_date}</div></td>
                  <td>{[o.indoor_outdoor, o.pixel_pitch,
                    o.width_m && o.height_m ? `${o.width_m}×${o.height_m}m` : null]
                    .filter(Boolean).join(" · ") || "—"}</td>
                  <td>
                    {o.overdue && <span className="badge" style={{ color: "var(--warn)" }}>逾期</span>}
                    {o.stale && <span className="badge" style={{ color: "var(--warn)" }}>停滞</span>}
                    {!o.overdue && !o.stale && <span className="muted">正常</span>}
                  </td>
                  <td><button className="btn btn-sm" onClick={() => setEditing(o)}>编辑</button></td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={9} className="muted">
                还没有符合条件的商机。去客户详情里点击“新建商机”开始管理项目。
              </td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      {editing && <OpportunityEditor item={editing}
        onSaved={(saved) => { setEditing(saved); load(); onChanged?.(); }} onClose={() => setEditing(null)} />}
    </>
  );
}
