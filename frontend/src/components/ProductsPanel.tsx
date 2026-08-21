import { useEffect, useState } from "react";
import {
  createKnowledgeProduct, deleteKnowledgeProduct, fetchKnowledgeProducts,
  generateKnowledgeQuote, seedKnowledgeProducts, updateKnowledgeProduct,
} from "../productKnowledgeApi";
import type { KnowledgeProduct } from "../productKnowledgeApi";
import { CaseLibraryPanel } from "./CaseLibraryPanel";
import { SolutionEngineerPanel } from "./SolutionEngineerPanel";

const BLANK = {
  model: "", pixel_pitch: "", brightness: "", use_case: "", ref_price_sqm: "",
  indoor_outdoor: "", refresh_rate_hz: "", maintenance_access: "", cabinet_size: "",
  control_system: "", notes: "", cabinet_width_mm: "", cabinet_height_mm: "",
  cabinet_resolution_w: "", cabinet_resolution_h: "", module_width_mm: "",
  module_height_mm: "", max_power_w_cabinet: "", avg_power_w_cabinet: "",
};

export function ProductsPanel() {
  const [prods, setProds] = useState<KnowledgeProduct[]>([]);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [form, setForm] = useState({ ...BLANK });
  const [note, setNote] = useState("");
  const [quoteFile, setQuoteFile] = useState<{ file: string; path: string } | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState<number | "new" | null>(null);

  function reload() {
    fetchKnowledgeProducts().then((p) => { setProds(p); setPicked(new Set(p.map((x) => x.id))); })
      .catch((e) => setMsg(String(e)));
  }
  useEffect(reload, []);

  const toggle = (id: number) => setPicked((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const set = (k: keyof typeof BLANK, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const num = (value: string) => value ? Number(value) : null;

  async function add() {
    if (!form.model.trim()) { setMsg("型号必填"); return; }
    setBusy("new"); setMsg("");
    try {
      await createKnowledgeProduct({
        model: form.model,
        pixel_pitch: form.pixel_pitch || null,
        brightness: form.brightness || null,
        use_case: form.use_case || null,
        ref_price_sqm: form.ref_price_sqm || null,
        indoor_outdoor: form.indoor_outdoor || null,
        refresh_rate_hz: num(form.refresh_rate_hz),
        maintenance_access: form.maintenance_access || null,
        cabinet_size: form.cabinet_size || null,
        control_system: form.control_system || null,
        notes: form.notes || null,
        cabinet_width_mm: num(form.cabinet_width_mm),
        cabinet_height_mm: num(form.cabinet_height_mm),
        cabinet_resolution_w: num(form.cabinet_resolution_w),
        cabinet_resolution_h: num(form.cabinet_resolution_h),
        module_width_mm: num(form.module_width_mm),
        module_height_mm: num(form.module_height_mm),
        max_power_w_cabinet: num(form.max_power_w_cabinet),
        avg_power_w_cabinet: num(form.avg_power_w_cabinet),
        agent_approved: false,
      });
      setForm({ ...BLANK }); reload();
    } catch (e) { setMsg("添加失败：" + String(e instanceof Error ? e.message : e)); reload(); }
    finally { setBusy(null); }
  }

  async function toggleAgentApproval(product: KnowledgeProduct) {
    setBusy(product.id); setMsg("");
    try {
      await updateKnowledgeProduct(product.id, { agent_approved: !Boolean(product.agent_approved) });
      reload();
    } catch (e) { setMsg("审批失败：" + String(e instanceof Error ? e.message : e)); }
    finally { setBusy(null); }
  }

  async function remove(product: KnowledgeProduct) {
    setBusy(product.id); setMsg("");
    try { await deleteKnowledgeProduct(product.id); reload(); }
    catch (e) { setMsg("删除失败：" + String(e instanceof Error ? e.message : e)); }
    finally { setBusy(null); }
  }

  async function makeQuote() {
    if (picked.size === 0) { setMsg("请先勾选产品"); return; }
    try {
      const q = await generateKnowledgeQuote([...picked], note);
      setQuoteFile(q); setMsg("");
    } catch (e) { setMsg("生成失败：" + String(e instanceof Error ? e.message : e)); }
  }

  async function copyPath() {
    if (!quoteFile) return;
    try { await navigator.clipboard.writeText(quoteFile.path); setMsg("已复制路径，去客户库勾选客户，粘贴到发送面板的「附件」框即可。"); }
    catch { setMsg(`复制失败，请手动复制：${quoteFile.path}`); }
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <div>
            <h3 style={{ margin: 0 }}>产品库 / Agent 产品知识</h3>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              Agent 只读取明确批准的绿色产品行。参考价只用于人工报价卡；工程计算只使用下面明确录入的箱体/分辨率/功耗事实。
            </div>
          </div>
          {prods.length === 0 && (
            <button className="btn btn-primary btn-sm" onClick={() => seedKnowledgeProducts().then(reload)}>一键载入默认产品（默认不批准给 Agent）</button>
          )}
        </div>
        {prods.length > 0 && (
          <div style={{ overflowX: "auto", marginTop: 10 }}>
            <table className="lead-table">
              <thead><tr><th style={{ width: 32 }}></th><th>型号</th><th>核心规格</th><th>工程事实</th><th>应用</th><th>参考价 /m²</th><th>Agent 知识</th><th></th></tr></thead>
              <tbody>
                {prods.map((p) => (
                  <tr key={p.id}>
                    <td><input type="checkbox" checked={picked.has(p.id)} onChange={() => toggle(p.id)} /></td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{p.model}</div>
                      {p.notes && <div className="muted" style={{ fontSize: 11, maxWidth: 260 }}>{p.notes}</div>}
                    </td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {[p.indoor_outdoor, p.pixel_pitch, p.brightness,
                        p.refresh_rate_hz ? `${p.refresh_rate_hz}Hz` : null,
                        p.cabinet_size, p.maintenance_access, p.control_system]
                        .filter(Boolean).join(" · ") || "未记录技术规格"}
                    </td>
                    <td className="muted" style={{ fontSize: 11, minWidth: 210 }}>
                      <div>箱体：{p.cabinet_width_mm && p.cabinet_height_mm ? `${p.cabinet_width_mm}×${p.cabinet_height_mm}mm` : "—"}</div>
                      <div>分辨率：{p.cabinet_resolution_w && p.cabinet_resolution_h ? `${p.cabinet_resolution_w}×${p.cabinet_resolution_h}px` : "—"}</div>
                      <div>模组：{p.module_width_mm && p.module_height_mm ? `${p.module_width_mm}×${p.module_height_mm}mm` : "—"}</div>
                      <div>功耗：{p.max_power_w_cabinet ? `Max ${p.max_power_w_cabinet}W` : "—"}{p.avg_power_w_cabinet ? ` / Avg ${p.avg_power_w_cabinet}W` : ""}</div>
                    </td>
                    <td className="muted">{p.use_case || "—"}</td>
                    <td>{p.ref_price_sqm || "—"}</td>
                    <td>
                      <button
                        className={`btn btn-sm${p.agent_approved ? " btn-green" : ""}`}
                        disabled={busy === p.id}
                        onClick={() => toggleAgentApproval(p)}
                        title="开启后，Agent 只能使用这一行已经填写的事实；空字段仍视为未知"
                      >
                        {p.agent_approved ? "✓ 允许 Agent 使用" : "禁止 Agent 使用"}
                      </button>
                    </td>
                    <td><button className="btn btn-sm" disabled={busy === p.id} onClick={() => remove(p)}>删除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ borderTop: "1px solid var(--border)", marginTop: 12, paddingTop: 12 }}>
          <div className="stat-label">录入真实产品事实（新产品默认禁止 Agent 使用）</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
            <input className="input" placeholder="型号*" value={form.model} onChange={(e) => set("model", e.target.value)} style={{ width: 160 }} />
            <select className="input" value={form.indoor_outdoor} onChange={(e) => set("indoor_outdoor", e.target.value)}>
              <option value="">室内/户外</option><option value="Indoor">Indoor</option><option value="Outdoor">Outdoor</option>
            </select>
            <input className="input" placeholder="点间距，如 P1.86" value={form.pixel_pitch} onChange={(e) => set("pixel_pitch", e.target.value)} style={{ width: 130 }} />
            <input className="input" placeholder="亮度，如 800-1000 nits" value={form.brightness} onChange={(e) => set("brightness", e.target.value)} style={{ width: 180 }} />
            <input className="input" placeholder="刷新率 Hz" value={form.refresh_rate_hz} onChange={(e) => set("refresh_rate_hz", e.target.value)} style={{ width: 110 }} />
            <input className="input" placeholder="箱体说明，如 640×480mm" value={form.cabinet_size} onChange={(e) => set("cabinet_size", e.target.value)} style={{ width: 180 }} />
            <input className="input" placeholder="维护方式" value={form.maintenance_access} onChange={(e) => set("maintenance_access", e.target.value)} style={{ width: 150 }} />
            <input className="input" placeholder="控制系统/适配" value={form.control_system} onChange={(e) => set("control_system", e.target.value)} style={{ width: 180 }} />
            <input className="input" placeholder="应用场景" value={form.use_case} onChange={(e) => set("use_case", e.target.value)} style={{ minWidth: 220, flex: 1 }} />
          </div>
          <div className="muted" style={{ fontSize: 11, marginTop: 10 }}>Solution Engineer 精确工程字段（不知道就留空，系统不会猜）</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 6 }}>
            <input className="input" placeholder="箱体宽 mm" value={form.cabinet_width_mm} onChange={(e) => set("cabinet_width_mm", e.target.value)} style={{ width: 115 }} />
            <input className="input" placeholder="箱体高 mm" value={form.cabinet_height_mm} onChange={(e) => set("cabinet_height_mm", e.target.value)} style={{ width: 115 }} />
            <input className="input" placeholder="箱体像素宽" value={form.cabinet_resolution_w} onChange={(e) => set("cabinet_resolution_w", e.target.value)} style={{ width: 120 }} />
            <input className="input" placeholder="箱体像素高" value={form.cabinet_resolution_h} onChange={(e) => set("cabinet_resolution_h", e.target.value)} style={{ width: 120 }} />
            <input className="input" placeholder="模组宽 mm" value={form.module_width_mm} onChange={(e) => set("module_width_mm", e.target.value)} style={{ width: 115 }} />
            <input className="input" placeholder="模组高 mm" value={form.module_height_mm} onChange={(e) => set("module_height_mm", e.target.value)} style={{ width: 115 }} />
            <input className="input" placeholder="单箱最大功耗 W" value={form.max_power_w_cabinet} onChange={(e) => set("max_power_w_cabinet", e.target.value)} style={{ width: 145 }} />
            <input className="input" placeholder="单箱平均功耗 W" value={form.avg_power_w_cabinet} onChange={(e) => set("avg_power_w_cabinet", e.target.value)} style={{ width: 145 }} />
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
            <input className="input" placeholder="参考价（只给人工报价使用）" value={form.ref_price_sqm} onChange={(e) => set("ref_price_sqm", e.target.value)} style={{ width: 220 }} />
            <input className="input" placeholder="内部备注" value={form.notes} onChange={(e) => set("notes", e.target.value)} style={{ minWidth: 300, flex: 1 }} />
            <button className="btn btn-sm" onClick={add} disabled={busy === "new"}>{busy === "new" ? "添加中…" : "+ 添加产品"}</button>
          </div>
        </div>
        {msg && <div className="error-text" style={{ marginTop: 8 }}>{msg}</div>}
      </div>

      <SolutionEngineerPanel />

      <div className="card">
        <h3>快速产品报价卡</h3>
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          用于开发初期快速展示产品范围，不记录客户、版本和成交状态。正式报价请使用上方“正式报价”工作台。
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input className="input" placeholder="备注（可选，印在卡上）" value={note} onChange={(e) => setNote(e.target.value)} style={{ minWidth: 300 }} />
          <button className="btn btn-green" onClick={makeQuote}>生成报价卡（已选 {picked.size} 款）</button>
        </div>
        {quoteFile && (
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
              <button className="btn btn-primary btn-sm" onClick={copyPath}>📋 复制文件路径</button>
              <span className="muted num" style={{ fontSize: 12 }}>{quoteFile.path}</span>
            </div>
            <img src={`/api/quote/file/${quoteFile.file}`} alt="报价卡预览" style={{ maxWidth: "100%", borderRadius: 8, border: "1px solid var(--border)" }} />
          </div>
        )}
      </div>

      <CaseLibraryPanel />
    </>
  );
}
