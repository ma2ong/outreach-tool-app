import { useEffect, useMemo, useState } from "react";
import {
  createBuyingSignal, fetchBuyingSignals, fetchIntelligenceSummary, fetchRankedAccounts,
  fetchSignalLeadOptions, signalToOpportunity, signalToTask, updateBuyingSignal,
} from "../salesIntelligenceApi";
import type { BuyingSignal, Lead, SalesIntelligenceAccount, SalesIntelligenceSummary } from "../types";

const SIGNAL_LABEL: Record<string, string> = {
  project: "项目发布", hiring: "招聘扩张", exhibition: "展会参展", distributor: "经销品牌",
  tender: "招标/中标", social: "社媒项目", site_change: "官网变化", location: "新地址",
  partnership: "合作伙伴", manual: "人工发现",
};
const SIGNAL_TYPES = Object.keys(SIGNAL_LABEL);
const USE_CASES = ["Rental", "Fixed Installation", "DOOH", "Retail", "Sports", "Church", "Control Room", "Broadcast", "Virtual Production"];

function localToday(): string {
  const d = new Date();
  const p = (v: number) => String(v).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function SalesIntelligencePanel({ onOpenLead, onChanged }: {
  onOpenLead: (leadNo: number) => void; onChanged: () => void;
}) {
  const [summary, setSummary] = useState<SalesIntelligenceSummary | null>(null);
  const [accounts, setAccounts] = useState<SalesIntelligenceAccount[]>([]);
  const [signals, setSignals] = useState<BuyingSignal[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState<number | "create" | null>(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [leadChoice, setLeadChoice] = useState("");
  const [signalType, setSignalType] = useState("project");
  const [headline, setHeadline] = useState("");
  const [evidence, setEvidence] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [occurredAt, setOccurredAt] = useState(localToday());
  const [confidence, setConfidence] = useState(70);
  const [useCase, setUseCase] = useState("");
  const [productFit, setProductFit] = useState("");
  const [angle, setAngle] = useState("");

  const leadOptions = useMemo(() => leads.map((lead) => ({
    lead, label: `#${lead.no} · ${lead.company_en}${lead.country ? ` · ${lead.country}` : ""}`,
  })), [leads]);

  async function load() {
    try {
      const [nextSummary, nextAccounts, nextSignals, nextLeads] = await Promise.all([
        fetchIntelligenceSummary(), fetchRankedAccounts(), fetchBuyingSignals(), fetchSignalLeadOptions(),
      ]);
      setSummary(nextSummary); setAccounts(nextAccounts); setSignals(nextSignals); setLeads(nextLeads);
      setErr("");
    } catch (e) { setErr(`销售雷达加载失败：${String(e)}`); }
  }

  useEffect(() => { load(); }, []);

  async function addSignal() {
    const selected = leadOptions.find((item) => item.label === leadChoice)?.lead;
    if (!selected) { setErr("请从客户建议列表中选择一家公司"); return; }
    if (!headline.trim() || !evidence.trim() || !sourceUrl.trim()) {
      setErr("信号标题、证据和来源 URL 都必须填写"); return;
    }
    setBusy("create"); setErr(""); setMsg("");
    try {
      await createBuyingSignal(selected.no, {
        signal_type: signalType, headline: headline.trim(), evidence: evidence.trim(),
        source_url: sourceUrl.trim(), confidence,
        ...(occurredAt ? { occurred_at: occurredAt } : {}),
        ...(useCase ? { use_case: useCase } : {}),
        ...(productFit.trim() ? { product_fit: productFit.trim() } : {}),
        ...(angle.trim() ? { suggested_angle: angle.trim() } : {}),
      });
      setMsg(`已记录 ${selected.company_en} 的采购信号；系统只会排序和建议，不会自动发送。`);
      setLeadChoice(""); setHeadline(""); setEvidence(""); setSourceUrl("");
      setOccurredAt(localToday()); setConfidence(70); setUseCase(""); setProductFit(""); setAngle("");
      await load();
    } catch (e) { setErr(`保存信号失败：${String(e)}`); }
    finally { setBusy(null); }
  }

  async function act(signal: BuyingSignal, action: "task" | "opportunity" | "dismiss") {
    setBusy(signal.id); setErr(""); setMsg("");
    try {
      if (action === "task") {
        await signalToTask(signal.id); setMsg("信号已转为今天的销售任务。仍需人工审核并执行触达。");
      } else if (action === "opportunity") {
        await signalToOpportunity(signal.id); setMsg("信号已建立商机，并安排两天内确认项目需求。");
      } else {
        await updateBuyingSignal(signal.id, { status: "dismissed" }); setMsg("已忽略该信号，不再参与评分。 ");
      }
      await load(); onChanged();
    } catch (e) { setErr(`处理信号失败：${String(e)}`); }
    finally { setBusy(null); }
  }

  const cards = [
    ["A 级优先客户", summary?.grade_a ?? 0, "今天最值得投入销售时间"],
    ["新采购信号", summary?.new_signals ?? 0, "都保留来源，等待人工审核"],
    ["缺决策人", summary?.missing_decision_maker ?? 0, "优先找 Owner / Purchasing / Project"],
    ["资料待补全", summary?.data_incomplete ?? 0, "缺官网证据、渠道或复检状态"],
  ] as const;

  return (
    <>
      <div className="cards-row" style={{ marginBottom: 16 }}>
        {cards.map(([label, value, note]) => <div className="card stat-card" key={label}>
          <div className="stat-label">{label}</div><div className="stat-value">{value}</div>
          <div className="muted" style={{ fontSize: 11 }}>{note}</div>
        </div>)}
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
          <div><h3 style={{ margin: 0 }}>客户优先级（可解释评分）</h3>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>不是成交概率：按 ICP、联系人、采购意向、互动和数据时效安排销售注意力。</div>
          </div>
          <button className="btn btn-sm" onClick={load}>刷新评分</button>
        </div>
        <div style={{ overflowX: "auto", marginTop: 12 }}>
          <table className="lead-table">
            <thead><tr><th>优先级</th><th>客户</th><th>五项分数</th><th>评分依据</th><th>下一最佳动作</th></tr></thead>
            <tbody>{accounts.map((account) => (
              <tr key={account.lead_no}>
                <td><b style={{ fontSize: 18 }}>{account.score}</b><div className="muted">{account.grade} 级</div></td>
                <td><button className="btn btn-sm" onClick={() => onOpenLead(account.lead_no)}>{account.company_en}</button>
                  <div className="muted" style={{ fontSize: 11 }}>{account.country || "未标国家"} · {account.target_fit || "未分级"}</div></td>
                <td>{account.components.map((component) => (
                  <span key={component.key} title={component.reasons.join("；")} style={{ display: "inline-block", marginRight: 8, whiteSpace: "nowrap" }}>
                    {component.label} <b>{component.score}</b>/{component.max}
                  </span>
                ))}</td>
                <td className="muted" style={{ maxWidth: 300 }}>
                  {account.components.flatMap((component) => component.reasons).slice(0, 3).join("；")}
                  {account.warnings.map((warning) => <div key={warning} className="error-text">{warning}</div>)}
                </td>
                <td style={{ minWidth: 260 }}><b>{account.next_action}</b></td>
              </tr>
            ))}</tbody>
          </table>
          {accounts.length === 0 && <div className="muted" style={{ padding: 20, textAlign: "center" }}>暂无可进入开发优先队列的客户。</div>}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
          <div><h3 style={{ margin: 0 }}>LED 采购信号</h3>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>没有来源和证据就不能保存；低可信信号也不会自动发送或自动建商机。</div>
          </div>
          <button className={`btn btn-sm${showForm ? " btn-primary" : ""}`} onClick={() => setShowForm(!showForm)}>＋ 录入采购信号</button>
        </div>
        {showForm && <div style={{ marginTop: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 2fr) 150px 150px 150px", gap: 8, marginBottom: 8 }}>
            <input className="input" list="signal-lead-options" value={leadChoice} onChange={(e) => setLeadChoice(e.target.value)} placeholder="输入并选择客户公司" />
            <datalist id="signal-lead-options">{leadOptions.map((item) => <option key={item.lead.no} value={item.label} />)}</datalist>
            <select className="input" value={signalType} onChange={(e) => setSignalType(e.target.value)}>{SIGNAL_TYPES.map((type) => <option key={type} value={type}>{SIGNAL_LABEL[type]}</option>)}</select>
            <select className="input" value={useCase} onChange={(e) => setUseCase(e.target.value)}><option value="">应用场景（可选）</option>{USE_CASES.map((item) => <option key={item}>{item}</option>)}</select>
            <input className="input" type="date" value={occurredAt} onChange={(e) => setOccurredAt(e.target.value)} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr", gap: 8, marginBottom: 8 }}>
            <input className="input" value={headline} onChange={(e) => setHeadline(e.target.value)} placeholder="信号标题，如：新体育馆 LED 记分屏招标" />
            <input className="input" type="url" value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="来源 URL（必填）" />
            <label className="muted" style={{ display: "flex", alignItems: "center", gap: 8 }}>可信度 {confidence}
              <input type="range" min="1" max="100" value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} />
            </label>
          </div>
          <textarea className="input" style={{ width: "100%", minHeight: 70, marginBottom: 8 }} value={evidence} onChange={(e) => setEvidence(e.target.value)} placeholder="证据原文或忠实摘要（必填，不要写推测）" />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr auto", gap: 8 }}>
            <input className="input" value={productFit} onChange={(e) => setProductFit(e.target.value)} placeholder="适合产品，如：Outdoor P6/P8" />
            <input className="input" value={angle} onChange={(e) => setAngle(e.target.value)} placeholder="建议切入点，如：确认尺寸、视距、安装日期和本地服务" />
            <button className="btn btn-primary" onClick={addSignal} disabled={busy === "create"}>{busy === "create" ? "保存中…" : "保存信号"}</button>
          </div>
        </div>}
        {(err || msg) && <div className={err ? "error-text" : "muted"} style={{ marginTop: 10 }}>{err || msg}</div>}

        <div style={{ overflowX: "auto", marginTop: 14 }}>
          <table className="lead-table">
            <thead><tr><th>客户 / 类型</th><th>证据</th><th>来源 / 时间</th><th>可信度</th><th>建议切入点</th><th>人工动作</th></tr></thead>
            <tbody>{signals.map((signal) => <tr key={signal.id}>
              <td><button className="btn btn-sm" onClick={() => onOpenLead(signal.lead_no)}>{signal.company_en}</button>
                <div className="muted">{SIGNAL_LABEL[signal.signal_type] || signal.signal_type}{signal.use_case ? ` · ${signal.use_case}` : ""}</div></td>
              <td><b>{signal.headline}</b><div className="muted" style={{ marginTop: 4, maxWidth: 360 }}>{signal.evidence}</div></td>
              <td><a href={signal.source_url} target="_blank" rel="noreferrer">查看来源 ↗</a>
                <div className="muted" style={{ fontSize: 11 }}>{signal.occurred_at || signal.captured_at.slice(0, 10)}</div></td>
              <td><b>{signal.confidence}</b>/100</td>
              <td>{signal.suggested_angle || <span className="muted">先核实再行动</span>}</td>
              <td style={{ whiteSpace: "nowrap" }}>
                <button className="btn btn-sm" disabled={busy === signal.id} onClick={() => act(signal, "task")}>建任务</button>{" "}
                <button className="btn btn-sm" disabled={busy === signal.id} onClick={() => act(signal, "opportunity")}>建商机</button>{" "}
                <button className="btn btn-sm" disabled={busy === signal.id} onClick={() => act(signal, "dismiss")}>忽略</button>
              </td>
            </tr>)}</tbody>
          </table>
          {signals.length === 0 && <div className="muted" style={{ padding: 20, textAlign: "center" }}>没有待审核的新信号。官网复检变化或人工发现会进入这里。</div>}
        </div>
      </div>
    </>
  );
}
