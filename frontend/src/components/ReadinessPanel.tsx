import { useState } from "react";
import { cardToggle } from "./Expandable";
import { fetchReadiness, setAutoSend } from "../api";
import type { Readiness } from "../types";

const STATUS = {
  ok: { icon: "✓", color: "var(--green)" },
  attention: { icon: "!", color: "var(--warn)" },
  blocked: { icon: "×", color: "var(--danger)" },
};

export function ReadinessPanel({ onGoto, data, onChanged }: {
  onGoto: (page: string) => void;
  data: Readiness | null;
  onChanged: (value: Readiness) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function toggle() {
    if (!data) return;
    const enabling = !data.metrics.autosend.enabled;
    let acknowledged = false;
    if (enabling && data.metrics.autosend.safety_pause) {
      acknowledged = window.confirm(
        `邮件因安全风险暂停：\n\n${data.metrics.autosend.safety_pause.reason}\n\n` +
        "只有在完成退信、邮箱验证和监测修复后才应恢复。仍要启用吗？",
      );
      if (!acknowledged) return;
    }
    setBusy(true); setError("");
    try {
      await setAutoSend(enabling, acknowledged);
      onChanged(await fetchReadiness());
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  if (!data) {
    return error ? <div className="error-text" style={{ marginBottom: 12 }}>{error}</div> : null;
  }
  const auto = data.metrics.autosend;
  const problemCount = data.checks.filter((c) => c.status !== "ok").length;
  return (
    <div className="card" style={{ marginBottom: 16, cursor: "pointer", borderColor: data.status === "blocked" ? "var(--danger)" : undefined }} {...cardToggle(open, setOpen)}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div className="stat-label">每日就绪中心</div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>
            {data.status === "ready" ? "系统已准备好" : data.status === "blocked" ? "存在阻塞项" : `${problemCount} 项需要处理`}
          </div>
          <div className="muted" style={{ fontSize: 12 }}>
            到期邮件 {auto.preview.due} 条，今日安全额度内预计发送 {auto.preview.will_send} 条
            {auto.preview.oldest_due ? ` · 最早逾期 ${auto.preview.oldest_due}` : ""}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={`btn btn-sm${auto.enabled ? " btn-green" : ""}`} onClick={toggle} disabled={busy}>
            {busy ? "更新中…" : auto.enabled ? "自动邮件：已启用" : "自动邮件：关闭"}
          </button>
          <button className="btn btn-sm" onClick={() => setOpen(!open)}>{open ? "收起" : "查看检查项"}</button>
        </div>
      </div>
      {auto.last_result && <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>上次自动运行：{auto.last_result}</div>}
      {auto.safety_pause && (
        <div className="error-text" style={{ marginTop: 8 }}>
          安全暂停：{auto.safety_pause.reason}
        </div>
      )}
      {error && <div className="error-text" style={{ marginTop: 8 }}>{error}</div>}
      {open && (
        <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
          {data.checks.map((c) => {
            const meta = STATUS[c.status];
            return (
              <button key={c.id} className="btn" onClick={() => onGoto(c.action_page)}
                style={{ display: "flex", textAlign: "left", alignItems: "center", gap: 10, justifyContent: "flex-start" }}>
                <b style={{ color: meta.color, fontSize: 18, width: 16 }}>{meta.icon}</b>
                <span><b>{c.label}</b><br /><span className="muted" style={{ fontSize: 12 }}>{c.detail}</span></span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
