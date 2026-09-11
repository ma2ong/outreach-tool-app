import { useEffect, useState } from "react";
import { fetchRuntimeStatus, resolveDelivery } from "../runtimeApi";
import type { RuntimeStatus } from "../runtimeApi";


function age(seconds: number | null): string {
  if (seconds == null) return "暂无心跳";
  if (seconds < 60) return `${seconds} 秒前`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟前`;
  return `${Math.floor(minutes / 60)} 小时前`;
}

function when(value: string | null | undefined): string {
  if (!value) return "尚未完成周期";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function mb(value: number | null | undefined): string {
  if (value == null) return "未知";
  return `${Math.round(value / 1024 / 1024)} MB`;
}

const CAPABILITY_LABEL: Record<string, string> = {
  backup: "数据库备份",
  email_poll: "邮件拉取",
  email_send: "邮件发送",
  social_scan: "社媒扫描",
  social_send: "社媒队列/发送",
  website_recheck: "官网复检",
  sequence_maintenance: "Sequence 维护",
  agent: "Agent",
};

export function WorkerRuntimeStatus() {
  const [status, setStatus] = useState<RuntimeStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [resolutionError, setResolutionError] = useState("");

  useEffect(() => {
    let alive = true;
    const load = () => fetchRuntimeStatus()
      .then((data) => { if (alive) setStatus(data); })
      // Before login the API may correctly return 401. Stay invisible rather than
      // placing an alarming red badge on top of the login screen.
      .catch(() => undefined);
    load();
    const timer = window.setInterval(load, 15_000);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);

  if (!status) return null;

  const reconcile = async (id: number, outcome: "sent" | "not_sent") => {
    const wording = outcome === "sent"
      ? "确认这条消息已经送达？系统会补齐发送记录并推进 Sequence。"
      : "确认这条消息没有送达？确认后系统才允许再次发送。";
    if (!window.confirm(wording)) return;
    setResolutionError("");
    try {
      await resolveDelivery(id, outcome);
      setStatus(await fetchRuntimeStatus());
    } catch (error) {
      setResolutionError(error instanceof Error ? error.message : "核对失败");
    }
  };

  const cycleFailed = status.state?.last_cycle_ok === 0;
  const mailDegraded = status.state?.last_email_poll_ok === 0;
  const productionCritical = status.production?.status === "critical";
  const productionDegraded = status.production?.status === "degraded";
  const failedCapabilities = status.capabilities.filter((item) => item.consecutive_failures > 0);
  const active = status.active;
  const degraded = active && !cycleFailed && !productionCritical && (mailDegraded || productionDegraded || failedCapabilities.length > 0);
  const label = productionCritical
    ? "Sales Worker · 系统健康异常"
    : active
      ? degraded
        ? mailDegraded ? "Sales Worker 运行中 · 邮件/系统需检查" : "Sales Worker 运行中 · 系统需检查"
        : `Sales Worker 运行中 · ${status.lease?.mode === "worker" ? "独立 Worker" : "内嵌"}`
      : status.dedicated_worker_expected
        ? "Sales Worker 未运行"
        : "Sales Worker 无活跃租约";
  const border = active && !cycleFailed && !mailDegraded && !productionCritical && !productionDegraded
    ? "var(--green)"
    : degraded ? "var(--warn)" : "var(--danger)";
  const dot = active && !cycleFailed && !mailDegraded && !productionCritical && !productionDegraded
    ? "●" : degraded ? "◆" : "⚠";

  return (
    // 顶栏里的一行，不再占用列表底部：那两枚浮标压着最后一行客户和页码
    <div style={{ position: "relative" }}>
      {open && (
        <div className="card" style={{
          position: "absolute", right: 0, top: 32, width: "min(430px, calc(100vw - 28px))",
          zIndex: 80, padding: 12, boxShadow: "0 8px 28px rgba(0,0,0,.22)",
        }}>
            <div style={{ fontWeight: 700, marginBottom: 5 }}>进程与业务能力状态</div>
          <div className="muted" style={{ fontSize: 12, lineHeight: 1.55 }}>
            <div>执行模式：{status.lease?.mode === "worker" ? "独立 Worker" : status.lease?.mode === "embedded" ? "Web 内嵌 Worker" : "当前无 Leader"}</div>
            <div>心跳：{age(status.heartbeat_age_seconds)}</div>
            <div>最近周期：{when(status.state?.last_cycle_finished_at)}</div>
            <div>累计周期：{status.state?.cycle_count ?? 0}</div>
            {(status.state?.standby_count ?? 0) > 0 && (
              <div style={{ color: "var(--warn)", marginTop: 4 }}>
                已拦截 {status.state?.standby_count} 次重复启动；最近一次 {when(status.state?.last_standby_at)}。待命进程没有执行销售周期。
              </div>
            )}
            <div style={{ marginTop: 7, fontWeight: 650 }}>业务能力</div>
            {status.capabilities.length === 0 && <div>尚未执行任何后台能力。</div>}
            {status.capabilities.map((item) => (
              <div key={item.name} style={{ marginTop: 4 }}>
                <span style={{ color: item.consecutive_failures || item.status === "stalled" ? "var(--danger)" : item.status === "succeeded" ? "var(--green)" : "var(--muted)" }}>
                  {item.consecutive_failures ? "⚠" : "●"}
                </span>{" "}{CAPABILITY_LABEL[item.name] || item.name}：
                {item.status === "stalled" ? "运行超过 20 分钟，请检查 · " : item.status === "running" ? "正在执行 · " : item.status === "disabled" ? "已关闭 · " : item.status === "not_configured" ? "尚未连接 · " : item.status === "idle" ? "等待下次执行 · " : item.status === "partial" ? "部分完成 · " : ""}
                {item.consecutive_failures
                  ? `连续失败 ${item.consecutive_failures} 次 · ${item.last_error || "未记录原因"}`
                  : `最近成功 ${when(item.last_success_at)} · 本次处理 ${item.processed_count}`}
              </div>
            ))}
            <div style={{ marginTop: 7, fontWeight: 650 }}>
              待人工核对的发送：{status.unresolved_deliveries.length}
            </div>
            {status.unresolved_deliveries.map((item) => (
              <div key={item.id} style={{ marginTop: 6, padding: 7, border: "1px solid var(--border)", borderRadius: 6 }}>
                <div>{item.company_en || `客户 #${item.lead_no}`} · {item.source_kind === "reply" ? "客户回复" : "Sequence 跟进"} · {item.channel} · {item.target}</div>
                <div className="muted">{when(item.created_at)} · {item.last_error || "进程中断，结果未知"}</div>
                <div style={{ marginTop: 5, display: "flex", gap: 6 }}>
                  <button className="btn btn-sm" onClick={() => reconcile(item.id, "sent")}>确认已发送</button>
                  <button className="btn btn-sm" onClick={() => reconcile(item.id, "not_sent")}>确认未发送，允许重试</button>
                </div>
              </div>
            ))}
            {resolutionError && <div className="error-text" style={{ marginTop: 5 }}>{resolutionError}</div>}
            <div style={{ marginTop: 7, fontWeight: 650 }}>生产健康</div>
            <div>数据库：{status.production.database.status === "ok" ? "正常" : `异常（${status.production.database.quick_check}）`}</div>
            <div>最近备份：{status.production.backup.date || "没有"} · {status.production.backup.verified ? "已校验" : "未通过校验"} · 共 {status.production.backup.count} 份</div>
            <div>磁盘可用：{mb(status.production.disk.free_bytes)}</div>
            <div>前端构建：{status.production.frontend.built ? "存在" : "缺失"}</div>
            <div>Python：{status.production.python.version}（CI 基线 {status.production.python.ci_baseline}）</div>
            {!status.production.python.matches_ci_minor && (
              <div style={{ color: "var(--warn)", marginTop: 4 }}>
                当前 Python 与 CI 基线不同；能运行不代表有同等回归覆盖，出现依赖异常时优先对齐 Python 3.14。
              </div>
            )}
            {status.production.warnings.map((item) => (
              <div key={item} style={{ color: "var(--warn)", marginTop: 4 }}>◆ {item}</div>
            ))}
            {status.production.critical.map((item) => (
              <div key={item} className="error-text" style={{ marginTop: 4 }}>⚠ {item}</div>
            ))}
            {status.state?.last_email_poll_ok === 0 && (
              <div style={{ color: "var(--warn)", marginTop: 5 }}>
                Worker 仍在运行，但最近一次邮箱同步没有完整成功；系统会缩短间隔自动重试。
              </div>
            )}
            {status.state?.last_cycle_ok === 0 && (
              <div className="error-text" style={{ marginTop: 5 }}>
                最近周期失败：{status.state.last_error || "未记录错误详情"}
              </div>
            )}
            {!active && status.dedicated_worker_expected && (
              <div className="error-text" style={{ marginTop: 5 }}>
                Web 已关闭内嵌 Worker，但没有活跃的独立 Worker。请确认 `python -m app.worker` 正在持续运行。
              </div>
            )}
            {!active && !status.dedicated_worker_expected && (
              <div className="error-text" style={{ marginTop: 5 }}>
                当前没有活跃销售循环。若刚启动应用可稍后再看；持续无心跳则需要检查后台线程或数据库。
              </div>
            )}
          </div>
        </div>
      )}
      <button
        className="btn btn-sm"
        onClick={() => setOpen((v) => !v)}
        title="查看自主销售 Worker、数据库备份和生产健康"
        style={{ borderColor: border, whiteSpace: "nowrap" }}
      >
        <span style={{ color: border, marginRight: 5 }}>{dot}</span>{label}
      </button>
    </div>
  );
}
