import { useEffect, useState } from "react";
import { useDismissOnOutside } from "./Expandable";
import { fetchControlCenter } from "../controlCenterApi";
import type {
  ControlCenterBlocker, ControlCenterNextAction, ControlCenterReceipt, ControlCenterSnapshot,
} from "../controlCenterApi";

const MODE_LABEL: Record<string, string> = {
  auto: "自动",
  approved: "你确认后",
  awaiting_approval: "等待确认",
  executing: "执行中",
  not_executed: "未执行",
};

const KIND_LABEL: Record<string, string> = {
  reply_draft: "回复草稿",
  send_outreach: "发起触达",
  create_task: "销售任务",
  enroll_sequence: "加入序列",
  stop_sequence: "停止序列",
  discover_run: "客户开发",
  build_opportunity: "建立商机",
  mark_do_not_contact: "停止联系",
};

const SEVERITY_LABEL: Record<string, string> = {
  critical: "严重",
  high: "高",
  medium: "中",
  info: "信息",
};

const FACT_LABEL: Record<string, string> = {
  never_contacted: "未触达",
  contacted: "已触达",
  human_replied: "真人已回复",
  quoted: "已报价",
  quote_accepted: "报价已接受",
  ordered: "已下单",
  won: "已成交",
  lost: "已丢单",
};

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div style={{ padding: "8px 10px", border: "1px solid var(--border)", borderRadius: 8, minWidth: 92 }}>
      <div className="muted" style={{ fontSize: 11 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.2 }}>{value}</div>
      {hint && <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>{hint}</div>}
    </div>
  );
}

function Blocker({ item }: { item: ControlCenterBlocker }) {
  return (
    <div style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", gap: 7, alignItems: "baseline", flexWrap: "wrap" }}>
        <span className="tag">{SEVERITY_LABEL[item.severity] ?? item.severity}</span>
        <strong style={{ fontSize: 13 }}>{item.title}</strong>
      </div>
      <div className="muted" style={{ fontSize: 11, marginTop: 3 }}>{item.detail}</div>
      <div style={{ fontSize: 11, marginTop: 3 }}>下一步：{item.action}</div>
    </div>
  );
}

function NextAction({ item }: { item: ControlCenterNextAction }) {
  return (
    <div style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
        <div style={{ fontSize: 12 }}>
          <strong>{item.company_en || "未命名客户"}</strong>
          <span className="muted"> · {item.type === "opportunity" ? "商机" : "客户"}</span>
        </div>
        <span className="muted" style={{ fontSize: 11 }}>
          {item.due_at ? `日期 ${item.due_at}` : "未定日期"}
          {item.score != null ? ` · ${item.type === "opportunity" ? "健康" : "优先级"} ${item.score}` : ""}
        </span>
      </div>
      <div style={{ fontSize: 11, marginTop: 2 }}>{item.action}</div>
    </div>
  );
}

function Receipt({ item }: { item: ControlCenterReceipt }) {
  const when = item.executed_at || item.decided_at || item.created_at;
  return (
    <div style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
        <div style={{ fontSize: 12 }}>
          <span className="tag">{MODE_LABEL[item.mode] ?? item.mode}</span>{" "}
          <span className="muted">{KIND_LABEL[item.kind] ?? item.kind}</span>{" "}
          <strong>{item.company_en || item.title}</strong>
        </div>
        <span className="muted" style={{ fontSize: 10 }}>{when ? new Date(when).toLocaleString() : ""}</span>
      </div>
      {item.company_en && <div style={{ fontSize: 11, marginTop: 2 }}>{item.title}</div>}
      {item.result && <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>{item.result}</div>}
    </div>
  );
}

export function AutonomyControlCenter() {
  const [data, setData] = useState<ControlCenterSnapshot | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [available, setAvailable] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const value = await fetchControlCenter();
      setData(value); setAvailable(true); setError("");
    } catch (e) {
      const msg = String(e instanceof Error ? e.message : e);
      if (/401|login required/i.test(msg)) setAvailable(false);
      else { setAvailable(true); setError(msg); }
    } finally { setLoading(false); }
  }

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 60_000);
    return () => clearInterval(timer);
  }, []);

  // Clicking anywhere outside closes it — a panel this wide is easier to dismiss by
  // clicking the page than by finding its corner again.
  const shell = useDismissOnOutside<HTMLDivElement>(open, () => setOpen(false));

  if (!available) return null;

  const c = data?.counters;
  const queue = data?.agent_queue;
  const truth = data?.sales_truth;
  const sweep = queue?.last_sweep;
  const state = data?.state ?? "attention";
  const stateText = state === "healthy" ? "自主销售正常" : state === "critical" ? "自主销售有严重阻塞" : "自主销售需要关注";
  const dot = "●";

  return (
    <div style={{ position: "relative" }} ref={shell}>
      {open && (
        <div className="card" style={{
          position: "absolute", right: 0, top: 32, zIndex: 80,
          width: "min(680px, calc(100vw - 28px))",
          maxHeight: "76vh", overflowY: "auto", padding: 14,
          boxShadow: "0 12px 42px rgba(0,0,0,.22)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
            <div>
              <div className="stat-label">Autonomy Control Center</div>
              <div style={{ fontSize: 17, fontWeight: 700 }}>{data?.state_label || "读取自主销售状态…"}</div>
              {data && <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>更新于 {new Date(data.generated_at).toLocaleString()}</div>}
            </div>
            <button className="btn btn-sm" disabled={loading} onClick={load}>{loading ? "刷新中…" : "刷新"}</button>
          </div>

          {error && <div className="error-text" style={{ marginTop: 8 }}>{error}</div>}

          {c && (
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginTop: 12 }}>
              <Stat label="等你确认" value={c.awaiting_approval} hint={`高风险 ${c.high_risk_approval}`} />
              <Stat label="Agent待处理" value={c.agent_work_open} hint={`到期 ${c.agent_work_due}`} />
              <Stat label="Agent长期积压" value={c.agent_work_stale} />
              <Stat label="Agent反复失败" value={c.agent_work_repeated_failures} />
              <Stat label="销售事实异常" value={c.sales_truth_anomalies} hint={`可自愈 ${c.sales_truth_repairable}`} />
              <Stat label="今日自动完成" value={c.auto_executed_today} />
              <Stat label="今日你确认后" value={c.approved_executed_today} />
              <Stat label="近7天失败" value={c.failed_7d} />
              <Stat label="你接管会话" value={c.human_takeovers} />
              <Stat label="到期客户" value={c.due_accounts} />
              <Stat label="高风险商机" value={c.unhealthy_opportunities} />
            </div>
          )}

          {!!data?.capabilities.length && (
            <div style={{ marginTop: 12 }}>
              <div className="stat-label">业务能力健康（区别于进程存活）</div>
              {data.capabilities.map((item) => (
                <div key={item.name} style={{ fontSize: 11, marginTop: 4 }}>
                  <span style={{ color: item.consecutive_failures || item.status === "stalled" ? "var(--danger)" : item.status === "succeeded" ? "var(--green)" : "var(--muted)" }}>
                    {item.consecutive_failures ? "⚠" : "●"}
                  </span>{" "}{item.name} · {item.status === "stalled" ? "运行超过 20 分钟，请检查 · " : item.status === "running" ? "正在执行 · " : item.status === "disabled" ? "已关闭 · " : item.status === "not_configured" ? "尚未连接 · " : item.status === "idle" ? "等待下次执行 · " : item.status === "partial" ? "部分完成 · " : ""}{item.consecutive_failures
                    ? `连续失败 ${item.consecutive_failures} 次：${item.last_error || "未知错误"}`
                    : `最近成功 ${item.last_success_at ? new Date(item.last_success_at).toLocaleString() : "尚无"}，本次处理 ${item.processed_count}`}
                </div>
              ))}
            </div>
          )}

          {truth && truth.accounts.length > 0 && (
            <details style={{ marginTop: 10 }}>
              <summary className="stat-label" style={{ cursor: "pointer" }}>
                Sales Truth / 销售事实一致性 · {truth.anomalous_accounts} 个客户
              </summary>
              {truth.accounts.slice(0, 8).map((item) => (
                <div key={item.lead_no} style={{ padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 12 }}>
                    <strong>{item.company_en || `客户 #${item.lead_no}`}</strong>{" "}
                    <span className="muted">CRM {item.crm_stage} → 事实 {FACT_LABEL[item.factual_state] ?? item.factual_state}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>
                    {item.anomalies[0]?.detail}
                    {item.repairable_anomalies ? ` · 可自愈 ${item.repairable_anomalies}` : ""}
                  </div>
                </div>
              ))}
            </details>
          )}

          {sweep && (
            <div style={{ marginTop: 10, padding: "8px 10px", border: "1px solid var(--border)", borderRadius: 8 }}>
              <div className="stat-label">最近一次 Agent 队列消化</div>
              <div style={{ fontSize: 11, marginTop: 3 }}>
                处理 {sweep.processed ?? 0} · 完成 {sweep.done ?? 0} · 延后复查 {sweep.rescheduled ?? 0} · 失败重试 {sweep.failed ?? 0}
              </div>
              {sweep.at && <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>{new Date(sweep.at).toLocaleString()}</div>}
            </div>
          )}

          {!!data?.blockers.length && (
            <div style={{ marginTop: 14 }}>
              <div className="stat-label">为什么没有完全自动推进</div>
              {data.blockers.map((item) => <Blocker key={item.code} item={item} />)}
            </div>
          )}

          {!!data?.next_actions.length && (
            <div style={{ marginTop: 14 }}>
              <div className="stat-label">下一最佳动作</div>
              {data.next_actions.slice(0, 8).map((item, i) => <NextAction key={`${item.type}-${item.lead_no}-${item.opportunity_id}-${i}`} item={item} />)}
            </div>
          )}

          {!!data?.ledger.length && (
            <details style={{ marginTop: 14 }}>
              <summary className="stat-label" style={{ cursor: "pointer" }}>最近行动账本（查看谁授权、做了什么）</summary>
              {data.ledger.slice(0, 12).map((item) => <Receipt key={item.id} item={item} />)}
            </details>
          )}

          {data && (
            <div className="muted" style={{ fontSize: 10, marginTop: 12 }}>
              自主度：自动 {data.autonomy.counts.auto ?? 0} · 提议 {data.autonomy.counts.propose ?? 0} · 关闭 {data.autonomy.counts.off ?? 0}。
              控制中心只读；CRM stage 保留人工判断，Agent 的通信/商业事实优先使用可验证证据。
            </div>
          )}
        </div>
      )}

      {/* 在顶栏里就不用浮标的阴影和最小宽度了，那是给悬浮在内容上方准备的 */}
      <button className="btn btn-sm" onClick={() => setOpen(!open)} style={{ whiteSpace: "nowrap" }}>
        <span style={{ marginRight: 6 }}>{dot}</span>{stateText}
        {c?.awaiting_approval ? ` · 待确认 ${c.awaiting_approval}` : ""}
      </button>
    </div>
  );
}
