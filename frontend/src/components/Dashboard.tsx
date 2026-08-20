import { useEffect, useRef, useState } from "react";
import { fetchQuota, fetchCampaignStats, fetchQualityStats, fetchDue, sendDue, fetchJob, fetchOpportunityStats, fetchActivityStats, type CampaignStat, type CountryStat, type QualityStat, type Deliverability } from "../api";
import type { Stats, ChannelReach, DueItem, SendJob, OpportunityStats, ActivityStats } from "../types";
import { StatCards } from "./StatCards";
import { ReadinessPanel } from "./ReadinessPanel";
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
  const [activityStats, setActivityStats] = useState<ActivityStats | null>(null);
  const [loadErrors, setLoadErrors] = useState<string[]>([]);
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
  return (
    <>
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
      {deliver && (deliver.danger || deliver.blind) && (
        <div className="card" style={{ marginBottom: 16, borderColor: deliver.blind ? "var(--warn)" : "var(--danger)" }}>
          <div className="stat-label">{deliver.blind ? (deliver.sync_broken ? "⚠️ 退信率测不准 · 收信中断" : "⚠️ 退信率偏低估") : "⚠️ 邮件送达率告警"}</div>
          <div className="stat-value" style={{ color: deliver.blind ? "var(--warn)" : "var(--danger)" }}>
            {deliver.sync_broken ? "收信中断" : `硬退信率 ${deliver.bounce_rate}%`}
            <span className="muted" style={{ fontSize: 14, marginLeft: 10 }}>
              近 {deliver.days} 天 {deliver.bounced} / {deliver.sends} 家
            </span>
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            {deliver.sync_broken
              ? "退信只能从收件箱读回来。收信一断，新的退信就再也不会被记下，这个数字会一路掉到 0，看起来像很健康 —— 先去渠道连接把收信恢复，在那之前不要拿它当判断依据。"
              : deliver.unmeasured > 0
                ? `近 ${deliver.days} 天有 ${deliver.unmeasured} 封是从收不到退信的邮箱发出去的，这部分退信永远不会回来 —— 实际退信率只会比 ${deliver.bounce_rate}% 更高。换回能收信的邮箱之后，这条提示会随着这批发送滑出统计窗口自动消失。`
                : "超过 2% 之后 Gmail 会限制你的发信、把后面的邮件投进垃圾箱 —— 那时候回复率再低，也不是话术的问题。先去客户库跑一遍邮箱验证，把验不过的排除掉再继续发。"}
          </div>
          <button className="btn btn-sm" style={{ marginTop: 8 }}
            onClick={() => onGoto(deliver.sync_broken ? "channels" : "leads")}>
            {deliver.sync_broken ? "去恢复收信 →" : "去验证邮箱 →"}
          </button>
        </div>
      )}
      <div className="card" style={{ marginBottom: 16, cursor: "pointer", borderColor: (activityStats?.overdue ?? 0) > 0 ? "var(--danger)" : undefined }}
        onClick={() => onGoto("activities")} title="打开销售任务">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div className="stat-label">✓ 今日销售任务</div>
            <div className="stat-value">
              今天 {activityStats?.today ?? 0} 项
              <span style={{ color: (activityStats?.overdue ?? 0) > 0 ? "var(--danger)" : undefined, marginLeft: 12 }}>
                逾期 {activityStats?.overdue ?? 0} 项
              </span>
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              全部未完成 {activityStats?.open_count ?? 0} · 未来 {activityStats?.upcoming ?? 0} · 未排日期 {activityStats?.no_due ?? 0}
            </div>
          </div>
          <span className="btn btn-primary btn-sm">开始处理 →</span>
        </div>
      </div>
      {(dueSeq.length > 0 || pendingReplies > 0) && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>☀️ 今日工作台</h3>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
            {dueSeq.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div>
                  <div className="stat-label">待发跟进</div>
                  <div className="stat-value">{sendableToday}<span className="muted" style={{ fontSize: 14 }}> / {dueSeq.length} 条</span></div>
                  <div className="muted" style={{ fontSize: 12 }}>今天额度内能发 {sendableToday} 条，其余明天继续</div>
                  {(sendMsg || sendJob) && (
                    <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                      {sendMsg}
                      {sendJob && ` 进度 ${sendJob.done}/${sendJob.total}`}
                      {sendJob?.status === "done" && sendJob.result && "sent" in sendJob.result &&
                        ` — 成功 ${sendJob.result.sent}，失败 ${sendJob.result.failed}${sendJob.result.deferred ? `，延后 ${sendJob.result.deferred}` : ""}`}
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <button className="btn btn-green btn-sm" onClick={sendToday} disabled={sending || sendableToday === 0}>
                    {sending ? "发送中…" : `🚀 发送今日 ${sendableToday} 条`}
                  </button>
                  <button className="btn btn-sm" onClick={() => onGoto("sequences")}>查看/编辑 →</button>
                </div>
              </div>
            )}
            {pendingReplies > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div>
                  <div className="stat-label">待处理回复</div>
                  <div className="stat-value" style={{ color: "var(--green)" }}>{pendingReplies} 封</div>
                  <div className="muted" style={{ fontSize: 12 }}>读过也不会消失；回复客户或安排下一步后再标记完成</div>
                </div>
                <button className="btn btn-green btn-sm" onClick={() => onGoto("inbox")}>去查看 →</button>
              </div>
            )}
          </div>
        </div>
      )}
      {due > 0 && (
        <div className="card" style={{ marginBottom: 16, borderColor: "var(--warn)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between" }}
          onClick={onGotoFollowUp} title="查看待跟进客户">
          <div>
            <div className="stat-label">⏰ 该跟进了</div>
            <div className="stat-value" style={{ color: "var(--warn)" }}>{due} 家客户</div>
            <div className="muted" style={{ fontSize: 12 }}>已触达超过 7 天没回复、或到了你设的跟进日期 —— 点这里去处理</div>
          </div>
          <span className="btn btn-primary btn-sm">去跟进 →</span>
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
