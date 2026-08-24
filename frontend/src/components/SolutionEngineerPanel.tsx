import { useEffect, useMemo, useState } from "react";
import { fetchKnowledgeProducts } from "../productKnowledgeApi";
import type { KnowledgeProduct } from "../productKnowledgeApi";
import {
  fetchEngineeringOpportunities, fetchSolutionEngineering, updateEngineeringOpportunity,
} from "../solutionEngineerApi";
import type { EngineeringOpportunity, SolutionResult } from "../solutionEngineerApi";

const n = (value: string): number | null => value.trim() === "" ? null : Number(value);
const shown = (value: unknown, suffix = "") => value == null ? "—" : `${String(value)}${suffix}`;

export function SolutionEngineerPanel() {
  const [opps, setOpps] = useState<EngineeringOpportunity[]>([]);
  const [products, setProducts] = useState<KnowledgeProduct[]>([]);
  const [oppId, setOppId] = useState("");
  const [productId, setProductId] = useState("");
  const [form, setForm] = useState({
    width_m: "", height_m: "", quantity: "1", input_voltage_v: "",
    controller_capacity_px: "", controller_output_ports: "",
    max_pixels_per_port: "", spare_pct: "",
  });
  const [result, setResult] = useState<SolutionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const approvedProducts = useMemo(() => products.filter((p) => Boolean(p.agent_approved)), [products]);
  const selectedOpp = useMemo(() => opps.find((o) => String(o.id) === oppId), [opps, oppId]);

  function load() {
    Promise.all([fetchEngineeringOpportunities(), fetchKnowledgeProducts()])
      .then(([o, p]) => {
        setOpps(o.filter((x) => !["won", "lost"].includes(x.stage)));
        setProducts(p);
        if (!oppId && o.length) setOppId(String(o.find((x) => !["won", "lost"].includes(x.stage))?.id ?? ""));
      })
      .catch((e) => setMsg(String(e)));
  }
  useEffect(load, []);

  useEffect(() => {
    if (!selectedOpp) return;
    setForm({
      width_m: selectedOpp.width_m?.toString() ?? "",
      height_m: selectedOpp.height_m?.toString() ?? "",
      quantity: selectedOpp.quantity?.toString() ?? "1",
      input_voltage_v: selectedOpp.input_voltage_v?.toString() ?? "",
      controller_capacity_px: selectedOpp.controller_capacity_px?.toString() ?? "",
      controller_output_ports: selectedOpp.controller_output_ports?.toString() ?? "",
      max_pixels_per_port: selectedOpp.max_pixels_per_port?.toString() ?? "",
      spare_pct: selectedOpp.spare_pct?.toString() ?? "",
    });
    setResult(null); setMsg("");
  }, [selectedOpp?.id]);

  const set = (key: keyof typeof form, value: string) => setForm((f) => ({ ...f, [key]: value }));

  async function calculate() {
    if (!selectedOpp) { setMsg("请先选择商机"); return; }
    setBusy(true); setMsg("");
    try {
      const updated = await updateEngineeringOpportunity(selectedOpp.id, {
        width_m: n(form.width_m),
        height_m: n(form.height_m),
        quantity: n(form.quantity) ?? 1,
        input_voltage_v: n(form.input_voltage_v),
        controller_capacity_px: n(form.controller_capacity_px),
        controller_output_ports: n(form.controller_output_ports),
        max_pixels_per_port: n(form.max_pixels_per_port),
        spare_pct: n(form.spare_pct),
      });
      setOpps((rows) => rows.map((row) => row.id === updated.id ? updated : row));
      const solution = await fetchSolutionEngineering(
        selectedOpp.id, productId ? Number(productId) : undefined,
      );
      setResult(solution);
      setMsg(solution.ready ? "已生成可复核工程配置" : "已计算可用部分；请按下方缺口补齐事实");
    } catch (e) {
      setMsg("计算失败：" + String(e instanceof Error ? e.message : e));
    } finally { setBusy(false); }
  }

  const layout = result?.selected_layout;
  const resolution = result?.resolution;
  const power = result?.power;
  const control = result?.control;
  const spares = result?.spares;

  return (
    <div className="card" style={{ marginBottom: 16, borderColor: "var(--blue)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <h3 style={{ margin: 0 }}>LED Solution Engineer / 项目配置工程师</h3>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            只使用商机事实 + 已批准产品的精确工程字段。自动算实际屏体、箱体、分辨率、功耗、控制容量和备品；不报价、不承诺交期。
          </div>
        </div>
        {result && <span className={result.ready ? "stage-badge stage-won" : "stage-badge stage-requirements"}>
          工程完整度 {result.engineering_completeness_pct ?? 0}%
        </span>}
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
        <select className="input" value={oppId} onChange={(e) => setOppId(e.target.value)} style={{ minWidth: 300 }}>
          <option value="">选择开放商机…</option>
          {opps.map((o) => <option key={o.id} value={o.id}>#{o.id} {o.company_en} · {o.title}</option>)}
        </select>
        <select className="input" value={productId} onChange={(e) => { setProductId(e.target.value); setResult(null); }} style={{ minWidth: 260 }}>
          <option value="">自动使用 Product Advisor 首选产品</option>
          {approvedProducts.map((p) => <option key={p.id} value={p.id}>{p.model} · {p.pixel_pitch || "未填 pitch"}</option>)}
        </select>
      </div>

      {selectedOpp && (
        <>
          <div className="field-grid" style={{ marginTop: 12 }}>
            <div className="field"><label>客户目标宽度 m</label><input className="input" type="number" min="0.1" step="0.001" value={form.width_m} onChange={(e) => set("width_m", e.target.value)} /></div>
            <div className="field"><label>客户目标高度 m</label><input className="input" type="number" min="0.1" step="0.001" value={form.height_m} onChange={(e) => set("height_m", e.target.value)} /></div>
            <div className="field"><label>同规格屏数量</label><input className="input" type="number" min="1" step="1" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} /></div>
            <div className="field"><label>输入电压 V（已核实）</label><input className="input" type="number" min="1" step="1" value={form.input_voltage_v} onChange={(e) => set("input_voltage_v", e.target.value)} placeholder="如 220 / 110" /></div>
            <div className="field"><label>单台控制器总像素容量</label><input className="input" type="number" min="1" step="1" value={form.controller_capacity_px} onChange={(e) => set("controller_capacity_px", e.target.value)} /></div>
            <div className="field"><label>单台输出端口数</label><input className="input" type="number" min="1" step="1" value={form.controller_output_ports} onChange={(e) => set("controller_output_ports", e.target.value)} /></div>
            <div className="field"><label>单端口最大像素</label><input className="input" type="number" min="1" step="1" value={form.max_pixels_per_port} onChange={(e) => set("max_pixels_per_port", e.target.value)} /></div>
            <div className="field"><label>内部备品比例 %</label><input className="input" type="number" min="0" max="100" step="0.1" value={form.spare_pct} onChange={(e) => set("spare_pct", e.target.value)} placeholder="不填则不计算" /></div>
          </div>
          <button className="btn btn-primary" onClick={calculate} disabled={busy}>
            {busy ? "计算中…" : "保存工程输入并计算"}
          </button>
          {msg && <span className="muted" style={{ marginLeft: 10 }}>{msg}</span>}
        </>
      )}

      {result && (
        <div style={{ marginTop: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 10 }}>
            <div style={{ border: "1px solid var(--border)", borderRadius: 7, padding: 10 }}>
              <strong>实际屏体 / 箱体</strong>
              <div className="muted" style={{ fontSize: 12, lineHeight: 1.7, marginTop: 5 }}>
                <div>产品：{shown(result.product?.model)}</div>
                <div>箱体排列：{layout ? `${layout.cabinet_columns} × ${layout.cabinet_rows}` : "—"}</div>
                <div>实际尺寸：{layout ? `${layout.actual_width_m} × ${layout.actual_height_m} m` : "—"}</div>
                <div>每屏箱体：{shown(layout?.cabinets_per_screen)}</div>
                <div>项目总箱体：{shown(layout?.total_cabinets)}</div>
                <div>尺寸差：{layout ? `宽 ${layout.delta_width_mm >= 0 ? "+" : ""}${layout.delta_width_mm}mm / 高 ${layout.delta_height_mm >= 0 ? "+" : ""}${layout.delta_height_mm}mm` : "—"}</div>
              </div>
            </div>
            <div style={{ border: "1px solid var(--border)", borderRadius: 7, padding: 10 }}>
              <strong>分辨率</strong>
              <div className="muted" style={{ fontSize: 12, lineHeight: 1.7, marginTop: 5 }}>
                <div>箱体分辨率：{shown(resolution?.cabinet_resolution)}</div>
                <div>每屏：{resolution ? `${shown(resolution.screen_width_px)} × ${shown(resolution.screen_height_px)} px` : "—"}</div>
                <div>每屏总像素：{shown(resolution?.pixels_per_screen)}</div>
                <div>项目总像素：{shown(resolution?.pixels_project)}</div>
              </div>
            </div>
            <div style={{ border: "1px solid var(--border)", borderRadius: 7, padding: 10 }}>
              <strong>功耗 / 电流</strong>
              <div className="muted" style={{ fontSize: 12, lineHeight: 1.7, marginTop: 5 }}>
                <div>最大功耗/屏：{shown(power?.max_power_w_per_screen, " W")}</div>
                <div>平均功耗/屏：{shown(power?.avg_power_w_per_screen, " W")}</div>
                <div>项目最大功耗：{shown(power?.max_power_w_project, " W")}</div>
                <div>理论最大电流/屏：{shown(power?.theoretical_max_current_a_per_screen, " A")}</div>
              </div>
            </div>
            <div style={{ border: "1px solid var(--border)", borderRadius: 7, padding: 10 }}>
              <strong>控制系统 / 备品</strong>
              <div className="muted" style={{ fontSize: 12, lineHeight: 1.7, marginTop: 5 }}>
                <div>最少控制器/屏：{shown(control?.minimum_controller_units_per_screen)}</div>
                <div>需要输出端口/屏：{shown(control?.required_output_ports_per_screen)}</div>
                <div>像素容量利用率：{shown(control?.pixel_capacity_utilization_pct, "%")}</div>
                <div>备品箱体：{shown(spares?.spare_cabinets)}</div>
                <div>备品模组：{shown(spares?.spare_modules)}</div>
              </div>
            </div>
          </div>

          {result.layout_options && result.layout_options.length > 1 && (
            <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>
              尺寸备选：{result.layout_options.map((x) => `${x.name} ${x.cabinet_columns}×${x.cabinet_rows}箱 = ${x.actual_width_m}×${x.actual_height_m}m`).join("；")}
            </div>
          )}
          {result.gaps.length > 0 && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--warn)", borderRadius: 7 }}>
              <strong>报价前需要补齐 / 确认</strong>
              <div className="muted" style={{ fontSize: 12, lineHeight: 1.7, marginTop: 4 }}>
                {result.gaps.map((gap, i) => <div key={i}>• {gap}</div>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
