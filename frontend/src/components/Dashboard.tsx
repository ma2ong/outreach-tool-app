import { useEffect, useRef, useState } from "react";
import { fetchQuota, fetchCampaignStats, fetchQualityStats, fetchDue, sendDue, fetchJob, fetchOpportunityStats, fetchActivityStats, type CampaignStat, type CountryStat, type QualityStat, type Deliverability } from "../api";
import type { Stats, ChannelReach, DueItem, SendJob, OpportunityStats, ActivityStats } from "../types";
import { fetchDailyReport } from "../agentApi";
import { fetchSocialQueue } from "../socialQueueApi";
import { StatCards } from "./StatCards";
import { ReadinessPanel } from "./ReadinessPanel";
import { DailyReport } from "./DailyReport";
import { TodayPlanCard } from "./TodayPlanCard";

const CH_LABEL: Record<string, string> = { email: "Email", whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook" };

// 邮箱质量分层：决定「这封信有没有人读」。role = info@/sales@ 这类公共邮箱。
const QUALITY_LABEL: Record<string, string> = {
  valid: "个人邮箱", role: "公共邮箱 info@/sales@", invalid: "已退信", unknown: "DNS 查不到", unverified: "未验证",
};

function ReachRow({ channel, r }: { channel: string; r: ChannelReach }) {
  const base = Math.max(r.have, 1);
  const messagedOnly = r.messaged - r.replied;
  const pct = (v: number) => `${(v / base) * 100}%`;
  return (
    <div className="reach-row">
      <span className="ch-name">{CH_LABEL[channel] ?? channel}</span>
      <div className="reach-track" title={`可发 ${r.have}｜已触达 ${r.messaged}｜已回复 ${r.replied}｜未触达可发 ${r.untouched}`}>
        {r.replied > 0 && <div style={{ width: pct(r.replied), background: "var(--green)" }} />}
        {messagedOnly > 0 && <div style={{ width: pct(messagedOnly), background: "var(--blue)" }} />}
        {r.untouched > 0 && <div style={{ width: pct(r.untouched), background: "var(--warn)" }} />}
      </div>
      <span className="reach-meta">可发 {r.have} · 已发 {r.messaged} · 还可发 <b>{r.untouched}</b></span>
    </div>
  );
}

export function Dashboard({ stats, pendingReplies, onGotoFollowUp, onGoto }: {
  stats: Stats; pendingReplies: number; onGotoFollowUp: () => void; onGoto: (page: string) => void;
}) {
  const [quota, setQuota] = useState<Record<string, { sent_today: number; cap: number; batch?: number }>>({});
  const [camps, setCamps] = useState<CampaignStat[]>([]);
  const [countryStats, setCountryStats] = useState<CountryStat[]>([]);
  const [dueSeq, setDueSeq] = useState<DueItem[]>([]);
  const [sending, setSending] = useState(false);
  const [sendJob, setSendJob] = useState<SendJob | null>(null);
  const [sendMsg, setSendMsg] = useState("");
  const [quality, setQuality] = useState<QualityStat[]>([]);
  const [deliver, setDeliver] = useState<Deliverability | null>(null);
  const [opportunityStats, setOpportunityStats] = useState<OpportunityStats | null>(null);
  // 今天 Agent 做了什么：以前 18 点推到 WhatsApp，现在就摆在这里 —— 这是每天第一眼看的屏幕。
  const [report, setReport] = useState<string>("");
  const [activityStats, setActivityStats] = useState<ActivityStats | null>(null);
  const [loadErrors, setLoadErrors] = useState<string[]>([]);
  const [socialPending, setSocialPending] = useState(0);
  const pollRef = useRef<number | null>(null);
  const reportLoadError = (name: string, error: unknown) => {
    setLoadErrors((old) => [...new Set([...old, `${name}：${String(error)}`])]);
  };
  function refreshDue() {
    fetchQuota().then(setQuota).catch((e) => reportLoadError("发送额度", e));
    fetchDue().then(setDueSeq).catch((e) => reportLoadError("跟进队列", e));
  }
  useEffect(() => {
    refreshDue();
    fetchCampaignStats().then((r) => { setCamps(r.campaigns); setCountryStats(r.countries); })
      .catch((e) => reportLoadError("回复率分析", e));
    fetchQualityStats().then((r) => { setQuality(r.quality); setDeliver(r.deliverability); })
      .catch((e) => reportLoadError("送达质量", e));
    fetchOpportunityStats().then(setOpportunityStats)
      .catch((e) => reportLoadError("商机统计", e));
    fetchActivityStats().then(setActivityStats)
      .catch((e) => reportLoadError("销售任务", e));
  }, []);
  // 组件卸载时清掉发送轮询，避免泄漏 + 对已卸载组件 setState
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);
  const due = stats.funnel?.follow_up_due ?? 0;

  // 今日能发出去的跟进（各渠道剩余额度封顶），既给"待发"数字也给一键发送用的 enrollment_id
  const todayPicks = (() => {
    const left: Record<string, number> = {};
    for (const [ch, q] of Object.entries(quota)) {
      left[ch] = Math.min(Math.max(0, q.cap - q.sent_today), q.batch ?? Number.MAX_SAFE_INTEGER);
    }
    const ids: number[] = [];
    for (const d of dueSeq) { if ((left[d.channel] ?? 0) > 0) { left[d.channel]--; ids.push(d.enrollment_id); } }
    return ids;
  })();
  const sendableToday = todayPicks.length;

  async function sendToday() {
    if (todayPicks.length === 0) return;
    setSending(true); setSendMsg(""); setSendJob(null);
    if (pollRef.current) clearInterval(pollRef.current);
    try {
      const start = await sendDue(todayPicks);
      setSendMsg(`本批发送 ${start.will_send} 条跟进…`);
      pollRef.current = window.setInterval(async () => {
        const j = await fetchJob(start.job_id);
        setSendJob(j);
        if (j.status !== "running") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setSending(false); refreshDue();
        }
      }, 1500);
    } catch (e) { setSendMsg("发送失败：" + String(e)); setSending(false); refreshDue(); }
  }

  const f = stats.funnel;
  const funnelBase = Math.max(f?.total ?? stats.total, 1);
  const stages = [
    { label: "客户总数", value: f?.total ?? stats.total },
    { label: "有联系方式", value: f?.with_contact ?? 0 },
    { label: "邮箱已验证", value: f?.verified ?? 0 },
    { label: "已触达", value: f?.touched ?? 0 },
    { label: "已回复", value: f?.replied ?? 0 },
    { label: "形成商机", value: f?.opportunity ?? 0 },
    { label: "正式报价", value: f?.quoted ?? 0 },
    { label: "生成订单", value: f?.ordered ?? 0 },
  ];

  const countries = Object.entries(stats.by_country).sort((a, b) => b[1] - a[1]).slice(0, 15);
  const maxC = countries[0]?.[1] ?? 1;
  useEffect(() => {
    fetchDailyReport().then((r) => setReport(r.text || "")).catch(() => setReport(""));
    fetchSocialQueue().then((q) => setSocialPending(q.awaiting_you)).catch(() => setSocialPending(0));
  }, []);

  // 今天唯一需要他动手的那些事，合成一栏。它们以前散在三个页面和四张卡上——
  // 「142 项逾期」要点进销售任务才看得到，而那正是最该先看见的一行。
  const decisions: { key: string; count: number; unit: string; what: string;
                     note?: string; go: string; page: string; urgent?: boolean }[] = [];
  // 只数确实在等他的：渠道是手动挡，或者渠道自动但国家压回了手动（韩国，docs/63）。
  // 挂在 auto 上的那些系统自己会发 —— 说它们在等他，等于两边互相等（docs/92 R6）。
  if (socialPending > 0) decisions.push({
    key: "social", count: socialPending, unit: "条", what: "社媒私信备好了，等你按发送",
    go: "去确认", page: "social" });
  if ((activityStats?.overdue ?? 0) > 0) decisions.push({
    key: "overdue", count: activityStats!.overdue, unit: "项", what: "销售任务已逾期",
    note: `全部未完成 ${activityStats?.open_count ?? 0}`, go: "去处理", page: "activities", urgent: true });
  if (pendingReplies > 0) decisions.push({
    key: "replies", count: pendingReplies, unit: "封", what: "客户回复等你处理",
    go: "去查看", page: "inbox", urgent: true });
  if (sendableToday > 0) decisions.push({
    key: "due", count: sendableToday, unit: "条", what: "跟进邮件今天额度内能发",
    note: dueSeq.length > sendableToday ? `到期 ${dueSeq.length} 条，其余明天` : undefined,
    go: "去发送", page: "sequences" });
  if (due > 0) decisions.push({
    key: "followup", count: due, unit: "家", what: "客户到了你设的跟进日期",
    go: "去跟进", page: "__followup" });

  // docs/86 R3. A book with nobody in it has nothing to report, and the twenty zeros
  // that used to fill this screen — quotas, a seven-band funnel, channel coverage, a
  // pipeline forecast — are noise a new user has to read past. Worse, the loudest thing
  // on the page was a red 收信中断 warning about a channel that had never been
  // connected. One next step is the whole screen until there is something to count.
  if (stats.total === 0) {
    return (
      <div className="card" style={{ maxWidth: 620, padding: "36px 34px" }}>
        <div className="stat-label" style={{ margin: "0 0 10px" }}>从这里开始</div>
        <h2 style={{ margin: "0 0 12px", fontSize: 26, lineHeight: 1.25 }}>
          客户库还是空的
        </h2>
        <p className="muted" style={{ margin: "0 0 8px", fontSize: 14.5, lineHeight: 1.65 }}>
          先找一批客户进来，这个系统的其他部分才有东西可做。
          在「客户开发」里填几个关键词、选好目标国家，它会自动搜索、打开官网、
          把邮箱和社媒读出来。
        </p>
        <p className="muted" style={{ margin: "0 0 20px", fontSize: 13 }}>
          话术已经装好了，找到客户后勾选加入跟进序列就能发。
        </p>
        <button className="btn btn-primary" onClick={() => onGoto("discovery")}>
          去找客户 →
        </button>
      </div>
    );
  }

  return (
    <>

      {decisions.length > 0 && (
        <div className="card" style={{ marginBottom: 16, borderLeft: "3px solid var(--warn)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <div className="stat-label" style={{ margin: 0 }}>⚠ 要你定的</div>
            <span className="muted" style={{ fontSize: 12 }}>今天只有这几件需要你动手</span>
          </div>
          {decisions.map((d) => (
            <div key={d.key} className="decision-row"
              onClick={() => (d.page === "__followup" ? onGotoFollowUp() : onGoto(d.page))}
              title={`打开${d.go}`}>
              <b className="decision-n" style={d.urgent ? { color: "var(--danger)" } : undefined}>{d.count}</b>
              <span className="muted" style={{ fontSize: 12 }}>{d.unit}</span>
              <span>{d.what}</span>
              {d.note && <span className="muted" style={{ fontSize: 12 }}>{d.note}</span>}
              {/* 跟进邮件就地能发：这一行以前带着「🚀 发送今日 N 条」按钮，
                  合并卡片时不能把它一起带走。看到的地方就是动手的地方。 */}
              {d.key === "due"
                ? <button className="btn btn-green btn-sm decision-go"
                    onClick={(e) => { e.stopPropagation(); sendToday(); }} disabled={sending}>
                    {sending ? "发送中…" : `发送 ${d.count} 条`}
                  </button>
                : <span className="decision-go">{d.go} →</span>}
            </div>
          ))}
          {(sendMsg || sendJob) && (
            <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
              {sendMsg}
              {sendJob && ` 进度 ${sendJob.done}/${sendJob.total}`}
              {sendJob?.status === "done" && sendJob.result && "sent" in sendJob.result &&
                ` — 成功 ${sendJob.result.sent}，失败 ${sendJob.result.failed}${sendJob.result.deferred ? `，延后 ${sendJob.result.deferred}` : ""}`}
            </div>
          )}
        </div>
      )}
      {report && <DailyReport text={report} />}
      <TodayPlanCard onGoto={onGoto} />
      <ReadinessPanel onGoto={onGoto} />
      {loadErrors.length > 0 && (
        <div className="card" style={{ marginBottom: 16, borderColor: "var(--danger)" }}>
          <b>部分数据加载失败</b>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            {loadErrors.join("；")}。请刷新页面；若持续出现，请检查后端服务。
          </div>
        </div>
      )}
      {deliver?.sync_broken && (
        <div className="card" style={{ marginBottom: 16, borderColor: "var(--warn)" }}>
          <div className="stat-label">⚠️ 收信中断</div>
          <div className="stat-value" style={{ color: "var(--warn)" }}>客户回复读不回来</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            收信一断，客户的回复就再也不会出现在收件箱里 —— 先去渠道连接把收信恢复。
          </div>
          <button className="btn btn-sm" style={{ marginTop: 8 }}
            onClick={() => onGoto("channels")}>去恢复收信 →</button>
        </div>
      )}
      <div className="card" style={{ marginBottom: 16, cursor: "pointer" }}
        onClick={() => onGoto("opportunities")} title="打开商机管道">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div className="stat-label">💰 商机管道</div>
            <div className="stat-value">
              {opportunityStats?.open_count ?? 0} 个开放项目
              <span className="muted" style={{ fontSize: 14, marginLeft: 10 }}>
                加权预测 USD {(opportunityStats?.weighted_amount ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              开放金额 USD {(opportunityStats?.open_amount ?? 0).toLocaleString()} ·
              逾期 {opportunityStats?.overdue_count ?? 0} · 停滞 {opportunityStats?.stale_count ?? 0}
            </div>
          </div>
          <span className="btn btn-primary btn-sm">管理商机 →</span>
        </div>
      </div>
      <StatCards stats={stats} />
      <div className="cards-row">
        {["email", "whatsapp", "instagram", "facebook"].map((ch) => quota[ch] && (
          <div key={ch} className="card stat-card">
            <div className="stat-label">今日 {CH_LABEL[ch]} 额度</div>
            <div className="stat-value">{quota[ch].sent_today}<span className="muted" style={{ fontSize: 15 }}> / {quota[ch].cap}</span></div>
            {quota[ch].sent_today >= quota[ch].cap && <div className="warn-text">已到日上限，明天再发</div>}
          </div>
        ))}
      </div>


      <div className="card" style={{ marginBottom: 16 }}>
        <h3>触达漏斗</h3>
        <div className="funnel-grid">
          {stages.map((s, i) => {
            const pct = Math.round((s.value / funnelBase) * 100);
            return (
              <div key={s.label} className="funnel-tile">
                <div className="stat-label">{s.label}</div>
                <div className="stat-value">{s.value}</div>
                <div className="muted" style={{ fontSize: 12 }}>{i === 0 ? "100%" : `${pct}% of 总数`}</div>
                <div className="funnel-track"><div className="funnel-bar" style={{ width: `${pct}%`, marginTop: 0 }} /></div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>渠道可发覆盖</h3>
        {["whatsapp", "email", "instagram"].map((ch) =>
          stats.reach?.[ch] ? <ReachRow key={ch} channel={ch} r={stats.reach[ch]} /> : null)}
        <div className="reach-legend">
          <span><i style={{ background: "var(--green)" }} />已回复</span>
          <span><i style={{ background: "var(--blue)" }} />已触达（未回复）</span>
          <span><i style={{ background: "var(--warn)" }} />未触达可发</span>
          <span><i style={{ background: "var(--surface-2)" }} />无此联系方式</span>
        </div>
        <div className="muted" style={{ fontSize: 12 }}>
          条形长度 = 有该联系方式的客户数；灰色轨道剩余部分为已排除/无联系方式。「还可发」是当前该渠道能立即发送的客户数。
        </div>
      </div>

      {(camps.length > 0 || countryStats.length > 0 || quality.length > 0) && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3>回复率分析</h3>
          {quality.length > 0 && (
            <>
              <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                按邮箱质量拆分 —— 公共邮箱（info@/sales@）很少有人认真读冷邮件。
                两边样本都攒够之后，回复率会直接告诉你还值不值得继续发。
              </div>
              <table className="lead-table" style={{ marginBottom: 14 }}>
                <thead><tr><th>邮箱类型</th><th>触达客户</th><th>已回复</th><th>回复率</th></tr></thead>
                <tbody>
                  {quality.map((q) => (
                    <tr key={q.quality}>
                      <td>{QUALITY_LABEL[q.quality] ?? q.quality}</td>
                      <td className="num">{q.touched}</td>
                      <td className="num">{q.replied}</td>
                      <td className="num" style={{ color: q.reply_rate >= 10 ? "var(--green)" : undefined }}>{q.reply_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          {camps.length > 0 && (
            <>
              <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>各批发送（Campaign）效果 —— 哪个话术/批次回复率高，下次就用它</div>
              <table className="lead-table" style={{ marginBottom: 14 }}>
                <thead><tr><th>Campaign</th><th>渠道</th><th>触达客户</th><th>已回复</th><th>回复率</th></tr></thead>
                <tbody>
                  {camps.slice(0, 10).map((c) => (
                    <tr key={c.campaign + c.channel}>
                      <td>{c.campaign}</td>
                      <td>{CH_LABEL[c.channel] ?? c.channel}</td>
                      <td className="num">{c.leads}</td>
                      <td className="num">{c.replied}</td>
                      <td className="num" style={{ color: c.reply_rate >= 10 ? "var(--green)" : undefined }}>{c.reply_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          {countryStats.length > 0 && (
            <>
              <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>各国家回复率（触达 ≥3 家才统计）—— 回复率高的市场值得加大投入</div>
              <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
                {countryStats.slice(0, 12).map((c) => (
                  <span key={c.country} className="muted" style={{ fontSize: 13 }}>
                    {c.country} <b style={{ color: c.reply_rate >= 10 ? "var(--green)" : "var(--fg)" }}>{c.reply_rate}%</b>
                    <span style={{ fontSize: 11 }}>（{c.replied}/{c.touched}）</span>
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      <div className="card" style={{ maxWidth: 560 }}>
        <h3>国家分布（前 15）</h3>
        {countries.map(([c, n]) => (
          <div key={c} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span style={{ width: 110, flex: "none" }}>{c}</span>
            <div style={{ flex: 1, background: "var(--surface-2)", borderRadius: 4, height: 14 }}>
              <div style={{ width: `${(n / maxC) * 100}%`, background: "var(--accent)", borderRadius: 4, height: 14 }} />
            </div>
            <span className="num muted" style={{ width: 40, textAlign: "right" }}>{n}</span>
          </div>
        ))}
      </div>
    </>
  );
}
