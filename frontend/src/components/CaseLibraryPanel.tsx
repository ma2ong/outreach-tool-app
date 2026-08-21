import { useEffect, useState } from "react";
import { createCase, deleteCase, fetchCases, updateCase } from "../productKnowledgeApi";
import type { ApprovedCase } from "../productKnowledgeApi";

const BLANK = {
  internal_name: "",
  public_label: "",
  country: "",
  application: "",
  indoor_outdoor: "",
  pixel_pitch: "",
  width_m: "",
  height_m: "",
  product_model: "",
  public_summary: "",
  source_url: "",
};

export function CaseLibraryPanel() {
  const [items, setItems] = useState<ApprovedCase[]>([]);
  const [form, setForm] = useState({ ...BLANK });
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState<number | "new" | null>(null);

  function reload() {
    fetchCases().then(setItems).catch((e) => setMsg(String(e)));
  }
  useEffect(reload, []);

  const set = (key: keyof typeof BLANK, value: string) => setForm((f) => ({ ...f, [key]: value }));

  async function add() {
    if (!form.internal_name.trim()) { setMsg("内部案例名称必填"); return; }
    setBusy("new"); setMsg("");
    try {
      await createCase({
        internal_name: form.internal_name.trim(),
        public_label: form.public_label.trim() || null,
        country: form.country.trim() || null,
        application: form.application.trim() || null,
        indoor_outdoor: form.indoor_outdoor || null,
        pixel_pitch: form.pixel_pitch.trim() || null,
        width_m: form.width_m ? Number(form.width_m) : null,
        height_m: form.height_m ? Number(form.height_m) : null,
        product_model: form.product_model.trim() || null,
        public_summary: form.public_summary.trim() || null,
        source_url: form.source_url.trim() || null,
      });
      setForm({ ...BLANK });
      reload();
    } catch (e) { setMsg("添加失败：" + String(e instanceof Error ? e.message : e)); }
    finally { setBusy(null); }
  }

  async function toggle(caseRow: ApprovedCase) {
    setBusy(caseRow.id); setMsg("");
    try {
      await updateCase(caseRow.id, { shareable: !Boolean(caseRow.shareable) });
      reload();
    } catch (e) {
      setMsg("审批失败：" + String(e instanceof Error ? e.message : e));
    } finally { setBusy(null); }
  }

  async function remove(caseRow: ApprovedCase) {
    setBusy(caseRow.id); setMsg("");
    try { await deleteCase(caseRow.id); reload(); }
    catch (e) { setMsg("删除失败：" + String(e instanceof Error ? e.message : e)); }
    finally { setBusy(null); }
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h3 style={{ margin: 0 }}>Approved Case Library</h3>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            报价/订单不会自动变成案例。只有明确批准为“可对外引用”的案例，Agent 才能在客户回复中使用。
          </div>
        </div>
        <span className="tag">可公开 {items.filter((x) => Boolean(x.shareable)).length} / {items.length}</span>
      </div>

      {items.length > 0 && (
        <div style={{ overflowX: "auto", marginTop: 10 }}>
          <table className="lead-table">
            <thead><tr><th>内部名称</th><th>对外标签</th><th>规格</th><th>可公开摘要</th><th>Agent 权限</th><th></th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.internal_name}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{item.country || ""}</div>
                  </td>
                  <td>{item.public_label || <span className="muted">未填写</span>}</td>
                  <td className="muted" style={{ fontSize: 12 }}>
                    {[item.application, item.indoor_outdoor, item.pixel_pitch,
                      item.width_m && item.height_m ? `${item.width_m}×${item.height_m}m` : null,
                      item.product_model].filter(Boolean).join(" · ") || "—"}
                  </td>
                  <td className="muted" style={{ maxWidth: 360, fontSize: 12 }}>
                    {item.public_summary || "未填写。未填写时不能批准对外引用。"}
                  </td>
                  <td>
                    <button
                      className={`btn btn-sm${item.shareable ? " btn-green" : ""}`}
                      disabled={busy === item.id}
                      onClick={() => toggle(item)}
                      title="只有公开标签和可公开摘要都填写后，才能开启对外引用"
                    >
                      {item.shareable ? "✓ 允许 Agent 对外引用" : "禁止 Agent 对外引用"}
                    </button>
                  </td>
                  <td><button className="btn btn-sm" disabled={busy === item.id} onClick={() => remove(item)}>删除</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ borderTop: "1px solid var(--border)", marginTop: 12, paddingTop: 12 }}>
        <div className="stat-label">录入案例（新案例默认私有，不会进入 Agent 回复）</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          <input className="input" placeholder="内部案例名称*" value={form.internal_name} onChange={(e) => set("internal_name", e.target.value)} style={{ width: 190 }} />
          <input className="input" placeholder="对外标签，如 Korea pharmacy LED" value={form.public_label} onChange={(e) => set("public_label", e.target.value)} style={{ width: 230 }} />
          <input className="input" placeholder="国家" value={form.country} onChange={(e) => set("country", e.target.value)} style={{ width: 100 }} />
          <input className="input" placeholder="应用，如 Retail / Rental" value={form.application} onChange={(e) => set("application", e.target.value)} style={{ width: 180 }} />
          <select className="input" value={form.indoor_outdoor} onChange={(e) => set("indoor_outdoor", e.target.value)}>
            <option value="">室内/户外</option><option value="Indoor">Indoor</option><option value="Outdoor">Outdoor</option>
          </select>
          <input className="input" placeholder="点间距，如 P1.86" value={form.pixel_pitch} onChange={(e) => set("pixel_pitch", e.target.value)} style={{ width: 130 }} />
          <input className="input" placeholder="宽 m" value={form.width_m} onChange={(e) => set("width_m", e.target.value)} style={{ width: 85 }} />
          <input className="input" placeholder="高 m" value={form.height_m} onChange={(e) => set("height_m", e.target.value)} style={{ width: 85 }} />
          <input className="input" placeholder="产品型号" value={form.product_model} onChange={(e) => set("product_model", e.target.value)} style={{ width: 160 }} />
          <input className="input" placeholder="公开来源 URL（可选）" value={form.source_url} onChange={(e) => set("source_url", e.target.value)} style={{ minWidth: 260, flex: 1 }} />
        </div>
        <textarea
          className="input" rows={3} style={{ width: "100%", marginTop: 8, fontFamily: "inherit" }}
          placeholder="可公开摘要：只写你允许 Agent 对客户复述的事实。不能把内部客户名/未获授权信息写进这里。"
          value={form.public_summary} onChange={(e) => set("public_summary", e.target.value)}
        />
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8, flexWrap: "wrap" }}>
          <button className="btn btn-sm" onClick={add} disabled={busy === "new"}>{busy === "new" ? "添加中…" : "+ 添加私有案例"}</button>
          <span className="muted" style={{ fontSize: 12 }}>添加后仍需单独点击“允许 Agent 对外引用”。</span>
        </div>
      </div>
      {msg && <div className="error-text" style={{ marginTop: 8 }}>{msg}</div>}
    </div>
  );
}
