import { useEffect, useState } from "react";
import { fetchRuntimeStatus } from "../runtimeApi";
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

export function WorkerRuntimeStatus() {
  const [status, setStatus] = useState<RuntimeStatus | null>(null);
  const [open, setOpen] = useState(false);

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

  const cycleFailed = status.state?.last_cycle_ok === 0;
  const mailDegraded = status.state?.last_email_poll_ok === 0;
  const active = status.active;
  const degraded = active && !cycleFailed && mailDegraded;
  const label = active
    ? degraded
      ? `Sales Worker 运行中 · 邮件同步异常`
      : `Sales Worker 运行中 · ${status.lease?.mode === "worker" ? "独立 Worker" : "内嵌"}`
    : status.dedicated_worker_expected
      ? "Sales Worker 未运行"
      : "Sales Worker 无活跃租约";
  const border = active && !cycleFailed && !mailDegraded
    ? "var(--green)"
    : degraded ? "var(--warn)" : "var(--danger)";
  const dot = active && !cycleFailed && !mailDegraded ? "●" : degraded ? "◆" : "⚠";

  return (
    <div style={{ position: "fixed", right: 16, bottom: 14, zIndex: 1000, maxWidth: 390 }}>
      {open && (
        <div className="card" style={{ marginBottom: 7, padding: 12, boxShadow: "0 8px 28px rgba(0,0,0,.22)" }}>
          <div style={{ fontWeight: 700, marginBottom: 5 }}>自主销售运行状态</div>
          <div className="muted" style={{ fontSize: 12, lineHeight: 1.55 }}>
            <div>执行模式：{status.lease?.mode === "worker" ? "独立 Worker" : status.lease?.mode === "embedded" ? "Web 内嵌 Worker" : "当前无 Leader"}</div>
            <div>心跳：{age(status.heartbeat_age_seconds)}</div>
            <div>最近周期：{when(status.state?.last_cycle_finished_at)}</div>
            <div>累计周期：{status.state?.cycle_count ?? 0}</div>
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
        title="查看自主销售 Worker 心跳和最近运行结果"
        style={{ borderColor: border, boxShadow: "0 3px 14px rgba(0,0,0,.18)" }}
      >
        <span style={{ color: border, marginRight: 5 }}>{dot}</span>{label}
      </button>
    </div>
  );
}
