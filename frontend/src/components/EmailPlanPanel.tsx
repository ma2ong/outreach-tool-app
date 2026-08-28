// 邮件计划：今天要发谁、发什么、什么时候、哪些没发。docs/66 R5
//
// 这些以前只是仪表盘上一行小字，所以 Allen 直接问「邮件的计划在哪」。它和社媒私信是并列的
// 两件事，就该有并列的两个页面。
import { useEffect, useState } from "react";
import { ExpandableCard } from "./Expandable";

type Row = {
  lead_no: number; company: string | null; country: string | null;
  email: string | null; sequence: string | null; step: number | null;
  subject: string; body: string; local_time: string; reason?: string;
};

type Plan = {
  ready: Row[]; held: Row[];
  his_window: [number, number]; their_window: [number, number];
  status: { enabled?: boolean; last_result?: string; last_date?: string } | null;
};

async function fetchPlan(): Promise<Plan> {
  const r = await fetch("/api/autosend/plan");
  if (!r.ok) throw new Error(`email plan ${r.status}`);
  return r.json();
}

async function setEnabled(enabled: boolean): Promise<void> {
  const r = await fetch("/api/autosend", {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail || `切换失败 ${r.status}`);
}

function MailRow({ r, onOpenLead }: { r: Row; onOpenLead?: (no: number) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <ExpandableCard
      open={open} onToggle={setOpen}
      style={{ marginBottom: 6, opacity: r.reason ? 0.75 : 1 }}
      header={
        <>
          <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
            <span data-no-toggle style={{ fontWeight: 600, cursor: onOpenLead ? "pointer" : undefined }}
              onClick={() => onOpenLead?.(r.lead_no)}>{r.company || `#${r.lead_no}`}</span>
            <span className="muted" style={{ fontSize: 12 }}>
              {[r.country, r.email, r.sequence && `${r.sequence} 第 ${(r.step ?? 0) + 1} 步`]
                .filter(Boolean).join(" · ")}
            </span>
            <span className="muted" style={{ fontSize: 12, marginLeft: "auto" }}>
              对方当地 {r.local_time}
            </span>
            <span className="muted" style={{ fontSize: 12 }}>{open ? "收起 ▲" : "看正文 ▼"}</span>
          </div>
          {r.reason && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>没发：{r.reason}</div>}
        </>
      }
    >
      <div style={{ marginTop: 8 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.subject}</div>
        <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{r.body}</div>
      </div>
    </ExpandableCard>
  );
}

export function EmailPlanPanel({ onOpenLead }: { onOpenLead?: (no: number) => void }) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    fetchPlan().then(setPlan).catch((e) => setErr(String(e instanceof Error ? e.message : e)));
  }
  useEffect(load, []);

  async function toggle() {
    if (!plan) return;
    setBusy(true); setErr("");
    try {
      await setEnabled(!plan.status?.enabled);
      load();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally { setBusy(false); }
  }

  if (err && !plan) return <div className="error-text">加载失败：{err}</div>;
  if (!plan) return <div className="muted">读取中…</div>;

  const [hisFrom, hisTo] = plan.his_window;
  const [theirFrom, theirTo] = plan.their_window;

  return (
    <>
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <b style={{ fontSize: 13 }}>今日邮件计划</b>
          <span className="muted">序列到期的跟进邮件，按额度自动发出</span>
          <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={load}>刷新</button>
          <button className={plan.status?.enabled ? "btn btn-sm" : "btn btn-sm btn-primary"}
            disabled={busy} onClick={toggle}>
            {plan.status?.enabled ? "关闭自动发送" : "开启自动发送"}
          </button>
        </div>
        <div className="muted" style={{ fontSize: 12, marginTop: 6, lineHeight: 1.7 }}>
          {/* 两个窗口都写出来，否则「为什么这个点发」永远要来问 */}
          在你的上班时间 {hisFrom}–{hisTo} 点发出，同时避开收件人当地
          {theirFrom} 点前和 {theirTo} 点后；对方当地凌晨一律不发。<br />
          邮件不像私信会响，所以窗口比社媒宽得多——信在对方晚上到达，第二天一早就在收件箱最上面。
        </div>
        {plan.status?.last_result && (
          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
            上次运行：{plan.status.last_result}
          </div>
        )}
        {err && <div className="error-text" style={{ marginTop: 6 }}>{err}</div>}
      </div>

      <div style={{ marginBottom: 6 }}>
        <b style={{ fontSize: 13 }}>待发 {plan.ready.length} 封</b>
      </div>
      {plan.ready.length === 0 && (
        <div className="muted" style={{ marginBottom: 12 }}>
          今天没有到期的跟进邮件。序列里的下一步到期时会出现在这里。
        </div>
      )}
      {plan.ready.map((r) => <MailRow key={r.lead_no} r={r} onOpenLead={onOpenLead} />)}

      {plan.held.length > 0 && (
        <>
          <div style={{ margin: "14px 0 6px" }}>
            <b style={{ fontSize: 13 }}>暂时不发 {plan.held.length} 封</b>
            <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
              它们仍然到期，明天会再看一次
            </span>
          </div>
          {plan.held.map((r) => <MailRow key={r.lead_no} r={r} onOpenLead={onOpenLead} />)}
        </>
      )}
    </>
  );
}
