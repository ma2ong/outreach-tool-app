import { useEffect, useRef, useState } from "react";
import { startEmailSend, startChannelSend, fetchJob, fetchQuota, fetchTemplates, createTemplate, loadSeeds } from "../api";
import type { SendJob, Template } from "../types";

// 与 backend/app/outreach_defaults.py 保持一致。首封至少明确这家公司；有 hook 时再叠加官网线索。
const DEFAULT_SUBJECT = "{company} — LED display supply";
const DEFAULT_BODY = `Hi {contact},

{hook}

I came across {company} while looking at LED / AV companies in your market.

We manufacture indoor and outdoor LED displays, including P1.86, P2.5, P3.91 and P10, and supply integrators and rental companies directly.

If you have a current project, send me the screen size, viewing distance and indoor/outdoor use. I'll organize only the relevant specs and project references.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001`;

const DM_BODY = `Hi {name}, this is Allen from an LED display factory in Shenzhen, China. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing. Happy to share recent project references if you have upcoming LED display needs.`;

const KO_COUNTRIES = new Set(["Korea", "South Korea"]);
const LANG_NAME: Record<string, string> = { ko: "韩语", en: "英语" };

function recommendLang(countries: string[]): string {
  const ko = countries.filter((c) => KO_COUNTRIES.has(c)).length;
  return ko > countries.length - ko ? "ko" : "en";
}

export function OutreachPanel({ selected, countries = [], firstCompany = "", onDone }: { selected: number[]; countries?: string[]; firstCompany?: string; onDone: () => void }) {
  const [channel, setChannel] = useState("email");
  const [subject, setSubject] = useState(DEFAULT_SUBJECT);
  const [body, setBody] = useState(DEFAULT_BODY);
  const [dm, setDm] = useState(DM_BODY);
  const [job, setJob] = useState<SendJob | null>(null);
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [quota, setQuota] = useState<Record<string, { sent_today: number; cap: number; batch?: number; mailboxes?: boolean }>>({});
  const [templates, setTemplates] = useState<Template[]>([]);
  const [tplName, setTplName] = useState("");
  const [attachment, setAttachment] = useState("");
  const [tplLang, setTplLang] = useState("");
  const [campaign, setCampaign] = useState("");
  const wantLang = recommendLang(countries);
  const sortedTemplates = [...templates].sort((a, b) =>
    Number((b.lang || "en") === wantLang) - Number((a.lang || "en") === wantLang));

  const isEmail = channel === "email";
  const pollRef = useRef<number | null>(null);
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);
  useEffect(() => { fetchQuota().then(setQuota).catch((e) => setMsg(`额度加载失败：${String(e)}`)); }, [channel, sending]);
  useEffect(() => { fetchTemplates(channel).then(setTemplates).catch((e) => setMsg(`模板加载失败：${String(e)}`)); }, [channel]);

  function applyTemplate(id: string) {
    const t = templates.find((x) => String(x.id) === id);
    if (!t) return;
    if (isEmail) { if (t.subject) setSubject(t.subject); setBody(t.body); }
    else setDm(t.body);
  }

  async function saveTemplate() {
    const name = tplName.trim();
    if (!name) { setMsg("请先填模板名"); return; }
    try {
      await createTemplate({ name, channel, subject: isEmail ? subject : null, body: isEmail ? body : dm, lang: tplLang || null });
      setTplName(""); setMsg(`已保存模板「${name}」`);
      fetchTemplates(channel).then(setTemplates).catch((e) => setMsg(`模板刷新失败：${String(e)}`));
    } catch (e) { setMsg("保存模板失败：" + String(e)); }
  }

  async function send() {
    if (selected.length === 0) { setMsg("请先勾选客户"); return; }
    setSending(true); setMsg(""); setJob(null);
    try {
      const att = attachment.trim() || undefined;
      const camp = campaign.trim() || undefined;
      const start = isEmail
        ? await startEmailSend({ lead_nos: selected, subject, body, ...(att ? { attachment: att } : {}), ...(camp ? { campaign: camp } : {}) })
        : await startChannelSend(channel, selected, dm, att, camp);
      const unit = isEmail ? "有邮箱" : channel === "whatsapp" ? "有电话" : "有IG";
      if (start.eligible === 0) {
        setMsg(`已选 ${start.selected} 家，没有一家可发：这些客户要么缺${unit}，要么今天已被触达过，要么之前已发过 ${CH_NAME[channel]}。` +
          `请在上方筛选「渠道=${CH_NAME[channel]}、状态=未触达、联系方式=${unit}」再挑一批。`);
        setSending(false);
        return;
      }
      const willSend = (start as { will_send?: number }).will_send;
      if (willSend === 0) {
        setMsg(`符合条件 ${start.eligible} 家，但今日 ${CH_NAME[channel]} 发送额度已用完，明天再发。`);
        setSending(false);
        return;
      }
      const capNote = !isEmail && willSend !== undefined && willSend < start.eligible
        ? `，本批只发前 ${willSend} 家（防封号上限），其余 ${start.eligible - willSend} 家下次再发`
        : "";
      setMsg(`已选 ${start.selected} 家，符合条件（${unit}且未发过）${start.eligible} 家${capNote}，开始发送…`);
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = window.setInterval(async () => {
        const j = await fetchJob(start.job_id);
        setJob(j);
        if (j.status !== "running") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null; setSending(false); onDone();
        }
      }, 1500);
    } catch (e) { setMsg("发送失败：" + String(e)); setSending(false); }
  }

  const CH_NAME: Record<string, string> = { email: "Email", whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook" };
  const previewSubject = firstCompany ? subject.replaceAll("{name}", firstCompany).replaceAll("{company}", firstCompany) : subject;
  const previewBody = firstCompany ? body.replaceAll("{name}", firstCompany).replaceAll("{company}", firstCompany).replaceAll("{hook}", "") : body;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <h3 style={{ margin: 0, fontSize: 15 }}>触达（已选 {selected.length} 家）</h3>
        <select className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
          <option value="email">Email</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="instagram">Instagram</option>
          <option value="facebook">Facebook</option>
        </select>
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap", alignItems: "center" }}>
        <select className="input" value="" onChange={(e) => applyTemplate(e.target.value)} title="载入已存话术模板；按已选客户国家推荐对应语言的模板">
          <option value="">{templates.length ? "选择模板载入…" : "（暂无模板）"}</option>
          {sortedTemplates.map((t) => (
            <option key={t.id} value={t.id}>
              {(t.lang || "en") === wantLang && wantLang !== "en" ? "⭐ " : ""}{t.name}{t.lang ? `（${LANG_NAME[t.lang] ?? t.lang}）` : ""}
            </option>
          ))}
        </select>
        {wantLang !== "en" && <span className="muted" style={{ fontSize: 12 }}>已选客户多为{LANG_NAME[wantLang]}市场，推荐用{LANG_NAME[wantLang]}模板</span>}
        <input className="input" style={{ width: 140 }} placeholder="模板名" value={tplName} onChange={(e) => setTplName(e.target.value)} />
        <select className="input" value={tplLang} onChange={(e) => setTplLang(e.target.value)} title="模板语言，用于按客户国家推荐">
          <option value="">语言</option><option value="en">英语</option><option value="ko">韩语</option>
        </select>
        <button className="btn btn-sm" onClick={saveTemplate}>另存为模板</button>
        {templates.length === 0 && (
          <button className="btn btn-sm btn-primary" title="一键载入英语/韩语现成话术（首次触达+跟进+DM）"
            onClick={async () => {
              try {
                const r = await loadSeeds();
                setMsg(`已载入 ${r.templates} 条现成话术，在左边下拉里选`);
                fetchTemplates(channel).then(setTemplates).catch((e) => setMsg(`模板刷新失败：${String(e)}`));
              } catch (e) {
                setMsg("载入失败：" + String(e));
                fetchTemplates(channel).then(setTemplates).catch(() => undefined);
              }
            }}>✨ 载入现成话术</button>
        )}
      </div>
      {isEmail ? (
        <>
          {quota.email && (
            <div className="warn-text" style={{ marginBottom: 6 }}>
              ⚠️ 单个邮箱一天灌几十封冷邮件会被判垃圾，账号还可能被限。已强制：单次最多 {quota.email.batch} 封、
              每封间隔 16–28 秒。今日已发 {quota.email.sent_today}/{quota.email.cap}
              {quota.email.sent_today >= quota.email.cap ? "，已到日上限，明天再发" : ""}。
              {!quota.email.mailboxes && " 想发更多：在「渠道连接」页配几个发件邮箱，系统会自动轮换，上限按各箱之和累加。"}
            </div>
          )}
          <input className="input" style={{ width: "100%", marginBottom: 8 }} value={subject} onChange={(e) => setSubject(e.target.value)} />
          <textarea className="input" style={{ height: 150 }} value={body} onChange={(e) => setBody(e.target.value)} />
          {firstCompany && (
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              预览（发给 {firstCompany} 时）：{previewSubject} — {previewBody.slice(0, 120)}…
            </div>
          )}
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            可用变量：{"{name}"}/{"{company}"}=公司名 · {"{contact}"}=联系人（没有就只留 "Hi,"）· {"{country}"} · {"{city}"} · {"{hook}"}=按官网写的开场白（没有就自动省掉这句）。首封若最终文本没有客户特征或出现明确价格，会在发送前自动拦下。
          </div>
        </>
      ) : (
        <>
          <div className="warn-text" style={{ marginBottom: 6 }}>
            ⚠️ {CH_NAME[channel]} 自动私信有平台限制，已强制限速（每条间隔 1–5 分钟），单批上限 20 条。每条消息自动附带案例图。请先在「渠道连接」里确认已连接。
            {channel === "facebook" && " Facebook 对冷私信的封号最狠，日上限压到 20 条、间隔最长；只对开了私信的商家主页有效。"}
            {quota[channel] && ` 今日已发 ${quota[channel].sent_today}/${quota[channel].cap}${quota[channel].sent_today >= quota[channel].cap ? "，已到日上限，明天再发" : ""}`}
          </div>
          <textarea className="input" style={{ height: 100 }} value={dm} onChange={(e) => setDm(e.target.value)} />
          {firstCompany && (
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              预览（发给 {firstCompany} 时）：{dm.replaceAll("{name}", firstCompany).slice(0, 150)}
            </div>
          )}
        </>
      )}
      <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input className="input" style={{ flex: 2, minWidth: 260 }} value={attachment} onChange={(e) => setAttachment(e.target.value)}
          placeholder="附件路径（留空 = 默认案例图；可粘贴「产品报价」页生成的报价卡路径）" title="随消息发送的图片/附件文件路径" />
        <input className="input" style={{ flex: 1, minWidth: 160 }} value={campaign} onChange={(e) => setCampaign(e.target.value)}
          placeholder="Campaign 名（可选，用于回复率统计）" title="给这批发送起个名，仪表盘可看各批回复率；留空自动按渠道+日期" />
      </div>
      <div style={{ marginTop: 10, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button className="btn btn-green" onClick={send} disabled={sending}>
          {sending ? "发送中…" : isEmail ? "发送邮件" : `发送 ${channel === "whatsapp" ? "WhatsApp" : "Instagram"} 私信`}
        </button>
        <span className="muted" style={{ fontSize: 12 }}>
          为避免骚扰，同一客户每天最多一次批量触达；需要多渠道跟进时请错开日期。
        </span>
        {job && <span className="muted">进度 {job.done}/{job.total}
          {job.status === "done" && job.result && "sent" in job.result &&
            ` — 成功 ${job.result.sent}，失败 ${job.result.failed}，跳过 ${job.result.skipped}${job.result.deferred ? `，延后 ${job.result.deferred}` : ""}${job.result.held ? `，安全拦下 ${job.result.held}` : ""}`}
          {job.status === "done" && job.result && "holds" in job.result && (job.result.holds ?? []).length > 0 && (
            <div className="muted" style={{ marginTop: 6 }}>
              以下没有发出去：
              {(job.result.holds ?? []).slice(0, 5).map((h: any) => <div key={h.no}>· #{h.no} {h.detail}</div>)}
              {(job.result.holds ?? []).length > 5 && <div>· 还有 {(job.result.holds ?? []).length - 5} 家同样问题</div>}
            </div>
          )}
          {job.status === "error" && job.result && "error" in job.result && ` — 错误：${job.result.error}`}
        </span>}
      </div>
      {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
    </div>
  );
}
