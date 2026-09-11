import { useEffect, useState } from "react";
import { acknowledgeActivation, fetchActivation, fetchActivationPreview } from "../api";
import type { ActivationPreview, ActivationStatus, ActivationStep } from "../types";

const AGENT_WORK: Record<string, string> = {
  research_public_company_facts: "查公开公司资料并保留来源",
  qualify_and_route_prospects: "筛选客户并分配到合适序列",
  prepare_and_follow_approved_sequences: "按已批准序列准备和跟进",
  classify_replies_and_prepare_next_actions: "识别回复并安排下一步",
};
const ALLEN_OWNS: Record<string, string> = {
  pricing: "价格", discounts: "折扣", payment_terms: "账期与付款条件",
  delivery_promises: "交期承诺", commercial_negotiation: "商务谈判",
  explicit_handoffs: "你明确接管的客户",
};

export function ActivationPanel({ onGoto }: { onGoto: (page: string) => void }) {
  const [status, setStatus] = useState<ActivationStatus | null>(null);
  const [preview, setPreview] = useState<ActivationPreview | null>(null);
  const [reviewing, setReviewing] = useState<"plan" | "autonomy" | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchActivation().then(setStatus).catch((e) => setError(String(e)));
  }, []);

  async function openReview(step: "plan" | "autonomy") {
    setError("");
    try {
      setPreview(await fetchActivationPreview());
      setReviewing(step);
    } catch (e) { setError(String(e)); }
  }

  async function acknowledge() {
    if (!reviewing) return;
    setBusy(true); setError("");
    try {
      setStatus(await acknowledgeActivation(reviewing));
      setReviewing(null);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }

  function act(step: ActivationStep) {
    if (step.id === "plan" || step.id === "autonomy") openReview(step.id);
    else onGoto(step.action_page);
  }

  if (!status && !error) return null;
  if (!status) return <div className="error-text" style={{ marginBottom: 12 }}>{error}</div>;
  if (status.prepared) {
    const live = status.worker.active;
    return (
      <div className="activation-ready" data-testid="activation-ready">
        <span className="activation-led on" />
        <div><b>销售 Agent 已完成接班准备</b><span>{live ? "Worker 正在运行" : "准备完成；运行状态仍以顶部 Worker 为准"}</span></div>
      </div>
    );
  }

  return (
    <section className="card activation-panel" aria-label="销售 Agent 启用向导">
      <header className="activation-head">
        <div>
          <div className="activation-kicker">COMMISSIONING · {status.completed}/{status.total}</div>
          <h2>让销售 Agent 真正接班</h2>
          <p>沿着这条信号链走一遍。每一步都读取系统真实状态，不会偷偷开启发送权限。</p>
        </div>
        <div className="activation-meter" aria-label={`已完成 ${status.completed} 项`}>
          <i style={{ width: `${status.completed / status.total * 100}%` }} />
        </div>
      </header>
      <div className="activation-chain">
        {status.steps.map((step, index) => (
          <button key={step.id} className={`activation-step${step.complete ? " complete" : ""}`}
            onClick={() => act(step)}>
            <span className="activation-node">{step.complete ? "✓" : index + 1}</span>
            <span><b>{step.label}</b><small>{step.detail}</small></span>
            <em>{step.complete ? "已接通" : "去完成 →"}</em>
          </button>
        ))}
      </div>
      {reviewing && preview && (
        <div className="activation-review">
          <div>
            <h3>{reviewing === "plan" ? "一天的拟执行计划" : "当前权限边界"}</h3>
            {reviewing === "plan" ? (
              <>
                <p>目标市场：{preview.mission.target_markets.join("、")}；每天补足 {preview.mission.daily_qualified_leads} 家，最低评分 {preview.mission.minimum_fit_score}。</p>
                <ul>{preview.agent_work.map((x) => <li key={x}>{AGENT_WORK[x] ?? x}</li>)}</ul>
              </>
            ) : (
              <>
                <p>邮件自动跟进：{preview.email_autosend ? "已启用" : "关闭"}；社媒：{Object.entries(preview.social_modes).map(([k, v]) => `${k} ${v === "auto" ? "自动" : "手动"}`).join(" · ")}</p>
                <p><b>始终由你决定：</b>{preview.allen_owns.map((x) => ALLEN_OWNS[x] ?? x).join("、")}。</p>
              </>
            )}
          </div>
          <button className="btn btn-primary" onClick={acknowledge} disabled={busy}>
            {busy ? "记录中…" : reviewing === "plan" ? "我已看过这份计划" : "保持当前权限并确认"}
          </button>
        </div>
      )}
      {error && <div className="error-text" style={{ marginTop: 10 }}>{error}</div>}
    </section>
  );
}
