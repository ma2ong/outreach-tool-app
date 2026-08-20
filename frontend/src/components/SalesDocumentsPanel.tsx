import { useEffect, useMemo, useState } from "react";
import { fetchContacts, fetchLeads, fetchOpportunities, fetchProducts } from "../api";
import {
  convertFormalQuoteToOrder, createFormalQuote, fetchOrders, fetchQuote, fetchQuotes,
  setFormalQuoteStatus, updateFormalQuote, updateSalesOrder,
} from "../salesDocumentsApi";
import type { QuoteInput, QuoteItemInput } from "../salesDocumentsApi";
import type { Contact, Lead, Opportunity, Product, Quote, QuoteSummary, SalesOrder } from "../types";


const QUOTE_STATUS: Record<string, string> = {
  draft: "草稿", sent: "已发送", accepted: "客户接受", rejected: "客户拒绝", expired: "已过期",
};
const ORDER_STATUS: Record<string, string> = {
  confirmed: "已确认", deposit: "已收定金", production: "生产中", inspection: "验货",
  shipped: "已发货", completed: "已完成", cancelled: "已取消",
};
const ORDER_STEPS = ["confirmed", "deposit", "production", "inspection", "shipped", "completed", "cancelled"];

function money(value: number, currency = "USD"): string {
  const code = /^[A-Za-z]{3}$/.test(currency) ? currency.toUpperCase() : "USD";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: code, maximumFractionDigits: 2,
    }).format(value || 0);
  } catch {
    return `${code} ${(value || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  }
}

function plusDays(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

let nextItemKey = 1;
interface ItemDraft {
  key: number;
  productId: string;
  description: string;
  model: string;
  pixelPitch: string;
  width: string;
  height: string;
  quantity: string;
  pricingUnit: "sqm" | "unit";
  unitPrice: string;
  note: string;
}

function blankItem(): ItemDraft {
  return {
    key: nextItemKey++, productId: "", description: "", model: "", pixelPitch: "",
    width: "", height: "", quantity: "1", pricingUnit: "sqm", unitPrice: "", note: "",
  };
}

interface FormDraft {
  title: string;
  currency: string;
  incoterm: string;
  destination: string;
  validUntil: string;
  paymentTerms: string;
  leadTime: string;
  warranty: string;
  shipping: string;
  discount: string;
}

function blankForm(): FormDraft {
  return {
    title: "", currency: "USD", incoterm: "FOB", destination: "",
    validUntil: plusDays(30), paymentTerms: "30% deposit, 70% before shipment",
    leadTime: "15-20 working days after deposit", warranty: "2 years",
    shipping: "0", discount: "0",
  };
}

function toItemInput(item: ItemDraft): QuoteItemInput {
  return {
    description: item.description.trim(), model: item.model.trim() || null,
    pixel_pitch: item.pixelPitch.trim() || null,
    width_m: item.width === "" ? null : Number(item.width),
    height_m: item.height === "" ? null : Number(item.height),
    quantity: Number(item.quantity), pricing_unit: item.pricingUnit,
    unit_price: Number(item.unitPrice), note: item.note.trim() || null,
  };
}

function lineEstimate(item: ItemDraft): number {
  const quantity = Number(item.quantity) || 0;
  const price = Number(item.unitPrice) || 0;
  return item.pricingUnit === "sqm"
    ? (Number(item.width) || 0) * (Number(item.height) || 0) * quantity * price
    : quantity * price;
}

function QuoteEditor({ leads, opportunities, products, editing, onSaved, onClose }: {
  leads: Lead[]; opportunities: Opportunity[]; products: Product[]; editing: Quote | null;
  onSaved: () => void; onClose: () => void;
}) {
  const leadLabel = (lead: Lead) => `#${lead.no} · ${lead.company_en}${lead.country ? ` · ${lead.country}` : ""}`;
  const [leadChoice, setLeadChoice] = useState(() => {
    const lead = editing && leads.find((item) => item.no === editing.lead_no);
    return lead ? leadLabel(lead) : "";
  });
  const [leadNo, setLeadNo] = useState<number | null>(editing?.lead_no ?? null);
  const [opportunityId, setOpportunityId] = useState(editing?.opportunity_id ? String(editing.opportunity_id) : "");
  const [contactId, setContactId] = useState(editing?.contact_id ? String(editing.contact_id) : "");
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [form, setForm] = useState<FormDraft>(() => editing ? {
    title: editing.title, currency: editing.currency, incoterm: editing.incoterm || "",
    destination: editing.destination || "", validUntil: editing.valid_until || "",
    paymentTerms: editing.payment_terms || "", leadTime: editing.lead_time || "",
    warranty: editing.warranty || "", shipping: String(editing.shipping), discount: String(editing.discount),
  } : blankForm());
  const [items, setItems] = useState<ItemDraft[]>(() => editing ? editing.items.map((item) => ({
    key: nextItemKey++, productId: "", description: item.description, model: item.model || "",
    pixelPitch: item.pixel_pitch || "", width: item.width_m === null ? "" : String(item.width_m),
    height: item.height_m === null ? "" : String(item.height_m), quantity: String(item.quantity),
    pricingUnit: item.pricing_unit, unitPrice: String(item.unit_price), note: item.note || "",
  })) : [blankItem()]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (leadNo === null) { setContacts([]); return; }
    fetchContacts(leadNo).then((rows) => {
      setContacts(rows);
      if (!contactId) {
        const primary = rows.find((contact) => contact.is_primary);
        if (primary) setContactId(String(primary.id));
      }
    }).catch((error) => setErr(`联系人加载失败：${String(error)}`));
  }, [leadNo]);

  const leadOpportunities = useMemo(
    () => opportunities.filter((item) => item.lead_no === leadNo && !["won", "lost"].includes(item.stage)),
    [opportunities, leadNo],
  );
  const estimatedSubtotal = items.reduce((sum, item) => sum + lineEstimate(item), 0);
  const estimatedTotal = estimatedSubtotal + (Number(form.shipping) || 0) - (Number(form.discount) || 0);

  function chooseLead(value: string) {
    setLeadChoice(value);
    const selected = leads.find((lead) => leadLabel(lead) === value);
    if (selected) {
      setLeadNo(selected.no); setOpportunityId(""); setContactId("");
    } else {
      // Never leave a hidden previous company selected while the visible text changed.
      setLeadNo(null); setOpportunityId(""); setContactId("");
    }
  }

  function chooseOpportunity(value: string) {
    setOpportunityId(value);
    const selected = leadOpportunities.find((item) => item.id === Number(value));
    if (!selected) return;
    setForm((current) => ({
      ...current, title: current.title || selected.title,
      currency: selected.currency || current.currency,
      destination: current.destination || selected.destination || "",
      incoterm: current.incoterm || selected.incoterm || "",
    }));
  }

  function setItem(key: number, field: keyof ItemDraft, value: string) {
    setItems((rows) => rows.map((item) => item.key === key ? { ...item, [field]: value } : item));
  }

  function chooseProduct(key: number, value: string) {
    const product = products.find((item) => item.id === Number(value));
    setItems((rows) => rows.map((item) => item.key !== key ? item : {
      ...item, productId: value,
      description: product ? `${product.model}${product.use_case ? ` · ${product.use_case}` : ""}` : item.description,
      model: product?.model || item.model, pixelPitch: product?.pixel_pitch || item.pixelPitch,
    }));
  }

  async function save() {
    if (leadNo === null) { setErr("请从客户建议列表中选择一家公司"); return; }
    if (!form.title.trim()) { setErr("请填写项目名称"); return; }
    if (items.some((item) => !item.description.trim() && !item.model.trim())) {
      setErr("每条明细都需要描述或型号"); return;
    }
    const payload: QuoteInput = {
      lead_no: leadNo, opportunity_id: opportunityId ? Number(opportunityId) : null,
      contact_id: contactId ? Number(contactId) : null, title: form.title.trim(),
      currency: form.currency.trim().toUpperCase(), incoterm: form.incoterm.trim() || null,
      destination: form.destination.trim() || null, valid_until: form.validUntil || null,
      payment_terms: form.paymentTerms.trim() || null, lead_time: form.leadTime.trim() || null,
      warranty: form.warranty.trim() || null, shipping: Number(form.shipping) || 0,
      discount: Number(form.discount) || 0, items: items.map(toItemInput),
    };
    setSaving(true); setErr("");
    try {
      if (editing) {
        const { lead_no: _leadNo, ...update } = payload;
        await updateFormalQuote(editing.id, update);
      } else {
        await createFormalQuote(payload);
      }
      onSaved();
    } catch (error) { setErr(String(error)); onSaved(); }
    finally { setSaving(false); }
  }

  return (
    <div className="card" style={{ marginBottom: 16, borderColor: "var(--blue)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <div><h3 style={{ margin: 0 }}>{editing ? `编辑 ${editing.quote_no}` : "＋ 新建正式报价"}</h3>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>金额由系统根据尺寸、数量和单价重新计算，保存后不可手改总额。</div></div>
        <button className="btn btn-sm" onClick={onClose}>关闭</button>
      </div>

      <div className="field-grid" style={{ marginTop: 14 }}>
        <div className="field"><label>客户公司 *</label>
          <input className="input" list="quote-lead-options" value={leadChoice}
            disabled={!!editing} onChange={(event) => chooseLead(event.target.value)} placeholder="输入并选择客户" />
          <datalist id="quote-lead-options">{leads.map((lead) => <option key={lead.no} value={leadLabel(lead)} />)}</datalist>
        </div>
        <div className="field"><label>关联商机</label>
          <select className="input" value={opportunityId} onChange={(event) => chooseOpportunity(event.target.value)}>
            <option value="">不关联商机</option>{leadOpportunities.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select>
        </div>
        <div className="field"><label>报价联系人</label>
          <select className="input" value={contactId} onChange={(event) => setContactId(event.target.value)}>
            <option value="">使用主联系人 / 暂不指定</option>{contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>{contact.name || contact.email || contact.phone}{contact.is_primary ? " · 主联系人" : ""}</option>
            ))}
          </select>
        </div>
        <div className="field"><label>项目名称 *</label>
          <input className="input" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="例如：Church P2.5 LED wall" />
        </div>
        <div className="field"><label>币种</label>
          <input className="input" maxLength={3} value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value })} />
        </div>
        <div className="field"><label>贸易条款</label>
          <input className="input" value={form.incoterm} onChange={(event) => setForm({ ...form, incoterm: event.target.value })} placeholder="EXW / FOB / CIF / DDP" />
        </div>
        <div className="field"><label>目的地 / 港口</label>
          <input className="input" value={form.destination} onChange={(event) => setForm({ ...form, destination: event.target.value })} />
        </div>
        <div className="field"><label>有效期至</label>
          <input className="input" type="date" value={form.validUntil} onChange={(event) => setForm({ ...form, validUntil: event.target.value })} />
        </div>
        <div className="field"><label>付款条件</label>
          <input className="input" value={form.paymentTerms} onChange={(event) => setForm({ ...form, paymentTerms: event.target.value })} />
        </div>
        <div className="field"><label>交期</label>
          <input className="input" value={form.leadTime} onChange={(event) => setForm({ ...form, leadTime: event.target.value })} />
        </div>
        <div className="field"><label>质保</label>
          <input className="input" value={form.warranty} onChange={(event) => setForm({ ...form, warranty: event.target.value })} />
        </div>
      </div>

      <div className="table-wrap" style={{ marginTop: 16 }}><table className="table">
        <thead><tr><th>产品</th><th>描述 / 型号</th><th>宽 × 高（m）</th><th>数量</th><th>计价</th><th>单价</th><th>小计估算</th><th></th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.key}>
          <td><select className="input" value={item.productId} onChange={(event) => chooseProduct(item.key, event.target.value)}>
            <option value="">手动填写</option>{products.map((product) => <option key={product.id} value={product.id}>{product.model}</option>)}
          </select></td>
          <td><input className="input" value={item.description} onChange={(event) => setItem(item.key, "description", event.target.value)} placeholder="产品描述" />
            <div style={{ display: "flex", gap: 4, marginTop: 4 }}><input className="input" style={{ minWidth: 90 }} value={item.model} onChange={(event) => setItem(item.key, "model", event.target.value)} placeholder="型号" />
              <input className="input" style={{ width: 78 }} value={item.pixelPitch} onChange={(event) => setItem(item.key, "pixelPitch", event.target.value)} placeholder="P2.5" /></div>
            <input className="input" style={{ marginTop: 4 }} value={item.note} onChange={(event) => setItem(item.key, "note", event.target.value)} placeholder="明细备注（可选）" />
          </td>
          <td><div style={{ display: "flex", gap: 4 }}><input className="input" type="number" min="0" step="0.01" style={{ width: 76 }} value={item.width} onChange={(event) => setItem(item.key, "width", event.target.value)} placeholder="宽" />
            <input className="input" type="number" min="0" step="0.01" style={{ width: 76 }} value={item.height} onChange={(event) => setItem(item.key, "height", event.target.value)} placeholder="高" /></div></td>
          <td><input className="input" type="number" min="1" step="1" style={{ width: 68 }} value={item.quantity} onChange={(event) => setItem(item.key, "quantity", event.target.value)} /></td>
          <td><select className="input" value={item.pricingUnit} onChange={(event) => setItem(item.key, "pricingUnit", event.target.value)}>
            <option value="sqm">每平方米</option><option value="unit">每件</option></select></td>
          <td><input className="input" type="number" min="0" step="0.01" style={{ width: 100 }} value={item.unitPrice} onChange={(event) => setItem(item.key, "unitPrice", event.target.value)} /></td>
          <td className="num">{money(lineEstimate(item), form.currency || "USD")}</td>
          <td><button className="btn btn-sm" disabled={items.length === 1} onClick={() => setItems((rows) => rows.filter((row) => row.key !== item.key))}>删除</button></td>
        </tr>)}</tbody>
      </table></div>
      <button className="btn btn-sm" style={{ marginTop: 8 }} onClick={() => setItems((rows) => [...rows, blankItem()])}>＋ 添加明细</button>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, flexWrap: "wrap", alignItems: "end", marginTop: 14 }}>
        <div className="field"><label>运费</label><input className="input" type="number" min="0" value={form.shipping} onChange={(event) => setForm({ ...form, shipping: event.target.value })} /></div>
        <div className="field"><label>折扣</label><input className="input" type="number" min="0" value={form.discount} onChange={(event) => setForm({ ...form, discount: event.target.value })} /></div>
        <div style={{ minWidth: 180, textAlign: "right" }}><div className="muted">保存前估算</div><div className="stat-value" style={{ fontSize: 24 }}>{money(Math.max(0, estimatedTotal), form.currency || "USD")}</div></div>
        <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? "保存中…" : editing ? "保存修改" : "创建报价草稿"}</button>
      </div>
      {err && <div className="error-text" style={{ marginTop: 10 }}>{err}</div>}
    </div>
  );
}

function OrderRow({ order, onSaved }: { order: SalesOrder; onSaved: () => void }) {
  const [draft, setDraft] = useState(order);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  useEffect(() => setDraft(order), [order]);

  async function save() {
    if (draft.status === "cancelled" && order.status !== "cancelled"
      && !window.confirm(`确认取消订单 ${order.order_no}？取消后不能恢复。`)) {
      return;
    }
    setBusy(true); setMsg("");
    try {
      await updateSalesOrder(order.id, {
        status: draft.status, deposit_amount: Number(draft.deposit_amount) || 0,
        paid_amount: Number(draft.paid_amount) || 0, expected_ship_date: draft.expected_ship_date,
        shipped_at: draft.shipped_at, tracking_no: draft.tracking_no, note: draft.note,
      });
      setMsg("已保存"); onSaved();
    } catch (error) { setMsg(String(error)); onSaved(); }
    finally { setBusy(false); }
  }
  const terminal = ["completed", "cancelled"].includes(order.status);
  return <tr>
    <td><b>{order.order_no}</b><div className="muted" style={{ fontSize: 11 }}>{order.quote_no}</div></td>
    <td>{order.company_en}<div className="muted" style={{ fontSize: 11 }}>{order.title}</div></td>
    <td><select className="input" disabled={terminal} value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value as SalesOrder["status"] })}>
      {ORDER_STEPS.map((status) => <option key={status} value={status}>{ORDER_STATUS[status]}</option>)}</select></td>
    <td className="num">{money(order.total, order.currency)}</td>
    <td><input className="input" type="number" min="0" style={{ width: 100 }} disabled={terminal} value={draft.deposit_amount} onChange={(event) => setDraft({ ...draft, deposit_amount: Number(event.target.value) })} /></td>
    <td><input className="input" type="number" min="0" style={{ width: 100 }} disabled={terminal} value={draft.paid_amount} onChange={(event) => setDraft({ ...draft, paid_amount: Number(event.target.value) })} />
      <div className="muted" style={{ fontSize: 11 }}>余 {money(order.balance, order.currency)}</div></td>
    <td><input className="input" type="date" disabled={terminal} value={draft.expected_ship_date || ""} onChange={(event) => setDraft({ ...draft, expected_ship_date: event.target.value || null })} /></td>
    <td><input className="input" type="date" disabled={terminal} value={draft.shipped_at || ""} onChange={(event) => setDraft({ ...draft, shipped_at: event.target.value || null })} title="实际发货日期" />
      <input className="input" style={{ width: 145, marginTop: 4 }} disabled={terminal} value={draft.tracking_no || ""} onChange={(event) => setDraft({ ...draft, tracking_no: event.target.value || null })} placeholder="物流单号" /></td>
    <td><input className="input" style={{ width: 170 }} disabled={terminal} value={draft.note || ""}
      onChange={(event) => setDraft({ ...draft, note: event.target.value || null })} placeholder="生产 / 验货 / 发货备注" /></td>
    <td><button className="btn btn-sm" disabled={busy || terminal} onClick={save}>{busy ? "保存中…" : "保存"}</button>
      {msg && <div className={msg === "已保存" ? "muted" : "error-text"} style={{ fontSize: 11, maxWidth: 150 }}>{msg}</div>}</td>
  </tr>;
}

export function SalesDocumentsPanel() {
  const [quotes, setQuotes] = useState<QuoteSummary[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [composeOpen, setComposeOpen] = useState(false);
  const [editing, setEditing] = useState<Quote | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function loadDocuments() {
    try {
      const [quoteRows, orderRows] = await Promise.all([fetchQuotes(), fetchOrders()]);
      setQuotes(quoteRows); setOrders(orderRows); setErr("");
    } catch (error) { setErr(`报价订单加载失败：${String(error)}`); }
  }
  useEffect(() => {
    loadDocuments();
    Promise.all([fetchLeads(), fetchOpportunities(), fetchProducts()])
      .then(([leadRows, opportunityRows, productRows]) => {
        setLeads(leadRows); setOpportunities(opportunityRows); setProducts(productRows);
      }).catch((error) => setErr(`基础资料加载失败：${String(error)}`));
  }, []);

  async function editQuote(id: number) {
    setBusy(true); setErr("");
    try { setEditing(await fetchQuote(id)); setComposeOpen(true); }
    catch (error) { setErr(String(error)); }
    finally { setBusy(false); }
  }

  async function transition(quote: QuoteSummary, status: string) {
    const prompts: Record<string, string> = {
      sent: "确认这份报价已经实际发送给客户？系统会安排 3 天后跟进。",
      accepted: "确认客户已经接受这份报价？接受后报价将锁定。",
      rejected: "确认将这份报价标记为客户拒绝/作废？",
      expired: "确认这份报价已经过期？",
    };
    if (prompts[status] && !window.confirm(prompts[status])) return;
    setBusy(true); setErr("");
    try {
      await setFormalQuoteStatus(quote.id, status);
    }
    catch (error) { setErr(String(error)); }
    finally {
      await Promise.all([loadDocuments(), fetchOpportunities().then(setOpportunities)]);
      setBusy(false);
    }
  }

  async function convert(quote: QuoteSummary) {
    if (!window.confirm(`将 ${quote.quote_no} 转为订单并把关联商机标记成交？`)) return;
    setBusy(true); setErr("");
    try {
      await convertFormalQuoteToOrder(quote.id);
    }
    catch (error) { setErr(String(error)); }
    finally {
      await Promise.all([loadDocuments(), fetchOpportunities().then(setOpportunities)]);
      setBusy(false);
    }
  }

  const draftCount = quotes.filter((quote) => quote.status === "draft").length;
  const sentCount = quotes.filter((quote) => quote.status === "sent").length;
  const receivable = orders.reduce<Record<string, number>>((totals, order) => {
    totals[order.currency] = (totals[order.currency] || 0) + order.balance;
    return totals;
  }, {});
  const receivableLabel = Object.entries(receivable)
    .map(([currency, value]) => money(value, currency)).join(" · ") || money(0);

  return <>
    <div className="cards-row" style={{ marginBottom: 16 }}>
      <div className="card stat-card"><div className="stat-label">报价草稿</div><div className="stat-value">{draftCount}</div></div>
      <div className="card stat-card"><div className="stat-label">等待客户决定</div><div className="stat-value" style={{ color: "var(--warn)" }}>{sentCount}</div></div>
      <div className="card stat-card"><div className="stat-label">执行中订单</div><div className="stat-value">{orders.filter((order) => !["completed", "cancelled"].includes(order.status)).length}</div></div>
      <div className="card stat-card"><div className="stat-label">订单待收款</div><div className="stat-value" style={{ color: "var(--green)", fontSize: 22 }}>{receivableLabel}</div></div>
    </div>

    {!composeOpen && <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
      <button className="btn btn-primary" onClick={() => { setEditing(null); setComposeOpen(true); }}>＋ 新建正式报价</button>
    </div>}
    {composeOpen && <QuoteEditor key={editing?.id ?? "new"} leads={leads} opportunities={opportunities}
      products={products} editing={editing} onClose={() => { setComposeOpen(false); setEditing(null); }}
      onSaved={async () => { setComposeOpen(false); setEditing(null); await loadDocuments(); }} />}
    {err && <div className="error-text" style={{ marginBottom: 10 }}>{err}</div>}

    <div className="card" style={{ marginBottom: 16, padding: 0, overflow: "hidden" }}>
      <div style={{ padding: "16px 16px 8px" }}><h3 style={{ margin: 0 }}>正式报价</h3>
        <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>“已发送”会同步商机金额并创建跟进任务；打印页可直接另存为 PDF。</div></div>
      <div className="table-wrap"><table className="table"><thead><tr>
        <th>报价号 / 项目</th><th>客户</th><th>联系人</th><th>状态</th><th>金额</th><th>条款 / 有效期</th><th>操作</th>
      </tr></thead><tbody>{quotes.map((quote) => <tr key={quote.id}>
        <td><b>{quote.quote_no}</b><div className="muted" style={{ fontSize: 11 }}>{quote.title}</div></td>
        <td>{quote.company_en}<div className="muted" style={{ fontSize: 11 }}>{quote.opportunity_title || "未关联商机"}</div></td>
        <td>{quote.contact_name || <span className="muted">主联系人未命名</span>}</td>
        <td><span className={`stage-badge stage-${quote.status}`}>{QUOTE_STATUS[quote.status]}</span>
          {quote.order_no && <div className="muted" style={{ fontSize: 11 }}>{quote.order_no}</div>}</td>
        <td className="num"><b>{money(quote.total, quote.currency)}</b><div className="muted" style={{ fontSize: 11 }}>商品 {money(quote.subtotal, quote.currency)}</div></td>
        <td>{quote.incoterm || "—"} · {quote.destination || "—"}<div className="muted" style={{ fontSize: 11 }}>有效至 {quote.valid_until || "未设置"}</div></td>
        <td><div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
          <button className="btn btn-sm" onClick={() => window.open(`/api/sales/quotes/${quote.id}/print`, "_blank", "noopener")}>打印 / PDF</button>
          {quote.status === "draft" && <><button className="btn btn-sm" disabled={busy} onClick={() => editQuote(quote.id)}>编辑</button>
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => transition(quote, "sent")}>标记已发送</button>
            <button className="btn btn-sm" disabled={busy} onClick={() => transition(quote, "rejected")}>作废</button></>}
          {quote.status === "sent" && <><button className="btn btn-green btn-sm" disabled={busy} onClick={() => transition(quote, "accepted")}>客户接受</button>
            <button className="btn btn-sm" disabled={busy} onClick={() => transition(quote, "rejected")}>客户拒绝</button>
            <button className="btn btn-sm" disabled={busy} onClick={() => transition(quote, "expired")}>已过期</button></>}
          {quote.status === "accepted" && !quote.order_id && <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => convert(quote)}>转为订单</button>}
        </div></td>
      </tr>)}{quotes.length === 0 && <tr><td colSpan={7} className="muted" style={{ padding: 24, textAlign: "center" }}>还没有正式报价。收到明确需求后，从“新建正式报价”开始。</td></tr>}</tbody></table></div>
    </div>

    <div className="card" style={{ marginBottom: 18, padding: 0, overflow: "hidden" }}>
      <div style={{ padding: "16px 16px 8px" }}><h3 style={{ margin: 0 }}>订单履约与收款</h3>
        <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>订单从已接受报价生成；余额、发货日期和物流信息统一保留在客户记录中。</div></div>
      <div className="table-wrap"><table className="table"><thead><tr>
        <th>订单号</th><th>客户 / 项目</th><th>状态</th><th>总额</th><th>计划定金</th><th>已收 / 余额</th><th>预计发货</th><th>实际发货 / 物流</th><th>备注</th><th></th>
      </tr></thead><tbody>{orders.map((order) => <OrderRow key={order.id} order={order} onSaved={loadDocuments} />)}
        {orders.length === 0 && <tr><td colSpan={10} className="muted" style={{ padding: 24, textAlign: "center" }}>还没有订单。客户接受正式报价后，可一键转为订单。</td></tr>}
      </tbody></table></div>
    </div>
  </>;
}
