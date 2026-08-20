import { useEffect, useState } from "react";
import { fetchProducts, createProduct, deleteProduct, seedProducts, generateQuote } from "../api";
import type { Product } from "../types";

const BLANK = { model: "", pixel_pitch: "", brightness: "", use_case: "", ref_price_sqm: "" };

export function ProductsPanel() {
  const [prods, setProds] = useState<Product[]>([]);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [form, setForm] = useState({ ...BLANK });
  const [note, setNote] = useState("");
  const [quoteFile, setQuoteFile] = useState<{ file: string; path: string } | null>(null);
  const [msg, setMsg] = useState("");

  function reload() {
    fetchProducts().then((p) => { setProds(p); setPicked(new Set(p.map((x) => x.id))); })
      .catch((e) => setMsg(String(e)));
  }
  useEffect(reload, []);

  const toggle = (id: number) => setPicked((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function add() {
    if (!form.model.trim()) { setMsg("型号必填"); return; }
    try {
      await createProduct({
        model: form.model, pixel_pitch: form.pixel_pitch || null, brightness: form.brightness || null,
        use_case: form.use_case || null, ref_price_sqm: form.ref_price_sqm || null,
      });
      setForm({ ...BLANK }); reload();
    } catch (e) { setMsg("添加失败：" + String(e)); reload(); }
  }

  async function makeQuote() {
    if (picked.size === 0) { setMsg("请先勾选产品"); return; }
    try {
      const q = await generateQuote([...picked], note);
      setQuoteFile(q); setMsg("");
    } catch (e) { setMsg("生成失败：" + String(e)); }
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
          <h3 style={{ margin: 0 }}>产品库</h3>
          {prods.length === 0 && (
            <button className="btn btn-primary btn-sm" onClick={() => seedProducts().then(reload)}>一键载入默认产品（P0.7–P10 五档）</button>
          )}
        </div>
        {prods.length > 0 && (
          <table className="lead-table" style={{ marginTop: 10 }}>
            <thead><tr><th style={{ width: 32 }}></th><th>型号</th><th>点间距</th><th>亮度</th><th>应用场景</th><th>参考价 /m²</th><th></th></tr></thead>
            <tbody>
              {prods.map((p) => (
                <tr key={p.id}>
                  <td><input type="checkbox" checked={picked.has(p.id)} onChange={() => toggle(p.id)} /></td>
                  <td>{p.model}</td><td>{p.pixel_pitch}</td><td>{p.brightness}</td>
                  <td className="muted">{p.use_case}</td><td>{p.ref_price_sqm}</td>
                  <td><button className="btn btn-sm" onClick={() => deleteProduct(p.id).then(reload)}>删除</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          <input className="input" placeholder="型号" value={form.model} onChange={(e) => set("model", e.target.value)} style={{ width: 150 }} />
          <input className="input" placeholder="点间距" value={form.pixel_pitch} onChange={(e) => set("pixel_pitch", e.target.value)} style={{ width: 110 }} />
          <input className="input" placeholder="亮度" value={form.brightness} onChange={(e) => set("brightness", e.target.value)} style={{ width: 130 }} />
          <input className="input" placeholder="应用场景" value={form.use_case} onChange={(e) => set("use_case", e.target.value)} style={{ width: 220 }} />
          <input className="input" placeholder="参考价，如 USD 900-1800" value={form.ref_price_sqm} onChange={(e) => set("ref_price_sqm", e.target.value)} style={{ width: 180 }} />
          <button className="btn btn-sm" onClick={add}>+ 添加产品</button>
        </div>
      </div>

      <div className="card">
        <h3>快速产品报价卡</h3>
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          用于开发初期快速展示产品范围，不记录客户、版本和成交状态。正式报价请使用上方“正式报价”工作台。
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input className="input" placeholder="备注（可选，印在卡上），如 MOQ 10 sqm" value={note} onChange={(e) => setNote(e.target.value)} style={{ minWidth: 300 }} />
          <button className="btn btn-green" onClick={makeQuote}>生成报价卡（已选 {picked.size} 款）</button>
        </div>
        {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
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
    </>
  );
}
