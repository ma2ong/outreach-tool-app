import { useEffect, useState } from "react";
import { fetchAgentStatus } from "../agentApi";
import type { AgentStatus } from "../agentApi";

/** The day's decisions, on the page Allen opens first. Silent when there is nothing
 *  to decide and nothing broken — an empty queue should not take up space. */
export function TodayPlanCard({ onGoto }: { onGoto: (page: string) => void }) {
  const [status, setStatus] = useState<AgentStatus | null>(null);

  useEffect(() => { fetchAgentStatus().then(setStatus).catch(() => setStatus(null)); }, []);
  if (!status) return null;

  const broken = Object.entries(status.llm.tasks).filter(([, v]) => !v.ok);
  const high = status.pending_by_risk?.high ?? 0;
  if (!status.pending && !broken.length) return null;

  return (
    <div className="card" style={{ marginBottom: 16, borderColor: high ? "var(--warn)" : undefined }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div className="stat-label">Agent 今日计划</div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>
            {status.pending ? `${status.pending} 条等你确认` : "模型接入有问题"}
            {high ? <span className="warn-text" style={{ fontSize: 13, marginLeft: 8 }}>其中 {high} 条要逐字看</span> : null}
          </div>
          <div className="muted" style={{ fontSize: 12 }}>
            {broken.length
              ? broken.map(([t, v]) => `${t === "draft" ? "起草" : "分类"}：${v.reason}`).join("；")
              : status.plan.last_result || status.last_result || ""}
          </div>
        </div>
        <button className="btn btn-green btn-sm" onClick={() => onGoto("agent")}>去处理 →</button>
      </div>
    </div>
  );
}
