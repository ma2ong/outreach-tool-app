import { useEffect, useRef, useState } from "react";
import { fetchLead, fetchLeads, fetchLeadsPage, fetchStats, markReplied, fetchSequences, enrollLeads, startVerify, fetchVerifyJob, startClassify, fetchClassifyJob, fetchDuplicates, mergeDuplicates, fetchInboxUnread, quickAddLead, fetchAuthStatus, login } from "./api";
import type { Lead, Stats, Sequence } from "./types";
import { Dashboard } from "./components/Dashboard";
import { LeadsTable } from "./components/LeadsTable";
import { LeadDrawer } from "./components/LeadDrawer";
import { OutreachPanel } from "./components/OutreachPanel";
import { DiscoveryPanel } from "./components/DiscoveryPanel";
import { BlocklistPanel } from "./components/BlocklistPanel";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { MailboxPanel } from "./components/MailboxPanel";
import { ProductsPanel } from "./components/ProductsPanel";
import { SequencesPanel } from "./components/SequencesPanel";
import { InboxPanel } from "./components/InboxPanel";
import { HealthPanel } from "./components/HealthPanel";
import { OpportunityPipeline } from "./components/OpportunityPipeline";

type Page = "dashboard" | "leads" | "opportunities" | "inbox" | "sequences" | "discovery" | "products" | "channels";

function exportQuery(params: Record<string, string>): string {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  return qs ? "&" + qs : "";
}

const PAGES: { id: Page; label: string; ico: string }[] = [
  { id: "dashboard", label: "仪表盘", ico: "▦" },
  { id: "leads", label: "客户库", ico: "☰" },
  { id: "opportunities", label: "商机管道", ico: "◇" },
  { id: "inbox", label: "收件箱", ico: "✉" },
  { id: "sequences", label: "跟进序列", ico: "⇉" },
  { id: "discovery", label: "客户开发", ico: "⌕" },
  { id: "products", label: "产品报价", ico: "▤" },
  { id: "channels", label: "渠道连接", ico: "⇄" },
];

function useTheme(): [string, () => void] {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);
  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))];
}

function LoginGate({ onSuccess }: { onSuccess: () => void }) {
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function submit() {
    if (!pw) return;
    setBusy(true); setErr("");
    try { await login(pw); onSuccess(); }
    catch (e) { setErr(String(e instanceof Error ? e.message : e)); }
    finally { setBusy(false); }
  }
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="card" style={{ width: 340, textAlign: "center" }}>
        <div className="brand" style={{ justifyContent: "center", marginBottom: 14 }}>
          <span className="pixel-logo"><i /><i /><i /><i /></span>
          <span>
            <div className="brand-name">Maxcolor</div>
            <div className="brand-sub">客户开发系统</div>
          </span>
        </div>
        <input className="input" type="password" style={{ width: "100%", marginBottom: 10 }}
          placeholder="访问密码" value={pw} autoFocus
          onChange={(e) => setPw(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }} />
        <button className="btn btn-primary" style={{ width: "100%" }} onClick={submit} disabled={busy}>
          {busy ? "登录中…" : "登录"}
        </button>
        {err && <div className="error-text" style={{ marginTop: 10 }}>{err}</div>}
      </div>
    </div>
  );
}

export function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [theme, toggleTheme] = useTheme();
  const [stats, setStats] = useState<Stats | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [country, setCountry] = useState("");
  const [channel, setChannel] = useState("");
  const [status, setStatus] = useState("");
  const [has, setHas] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("no");
  const [order, setOrder] = useState("asc");
  const [leadPage, setLeadPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [detail, setDetail] = useState<Lead | null>(null);
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [enrollMsg, setEnrollMsg] = useState("");
  const [err, setErr] = useState("");
  const [unread, setUnread] = useState(0);
  const [authed, setAuthed] = useState<boolean | null>(null);
  useEffect(() => {
    fetchAuthStatus().then((s) => setAuthed(!s.enabled || s.authed)).catch(() => setAuthed(true));
  }, []);

  const refreshUnread = () => fetchInboxUnread().then(setUnread).catch((e) => setErr(String(e)));
  useEffect(() => { refreshUnread(); }, []);

  // 追踪所有轮询定时器，组件卸载时统一清掉（防泄漏 + 对已卸载组件 setState）
  const timers = useRef<Set<number>>(new Set());
  useEffect(() => () => { timers.current.forEach((id) => clearInterval(id)); }, []);

  async function openLead(no: number) {
    try { setDetail(await fetchLead(no)); } catch (e) { setErr(String(e)); }
  }

  const [healthOpen, setHealthOpen] = useState(false);
  const [quickOpen, setQuickOpen] = useState(false);
  const [quickUrl, setQuickUrl] = useState("");
  const [quickCountry, setQuickCountry] = useState("");
  const [quickName, setQuickName] = useState("");
  const [quickBusy, setQuickBusy] = useState(false);
  const [quickMsg, setQuickMsg] = useState("");
  async function quickAdd() {
    if (!quickUrl.trim()) { setQuickMsg("请粘贴客户主页或官网链接"); return; }
    setQuickBusy(true); setQuickMsg("添加中…官网链接会自动深挖联系方式（十几秒）");
    try {
      const r = await quickAddLead({ url: quickUrl.trim(),
        ...(quickCountry.trim() ? { country: quickCountry.trim() } : {}),
        ...(quickName.trim() ? { company_en: quickName.trim() } : {}) });
      if (r.duplicate_of) {
        setQuickMsg(`这家已在库（#${r.duplicate_of}），已打开详情`);
      } else {
        setQuickMsg(`已添加 #${r.lead.no} ${r.lead.company_en}，已打开详情可补充信息`);
        setQuickUrl(""); setQuickName("");
        reload();
      }
      setDetail(r.lead);
    } catch (e) { setQuickMsg("添加失败：" + String(e)); }
    finally { setQuickBusy(false); }
  }

  const PAGE_SIZE = 50;

  useEffect(() => { fetchSequences().then(setSequences).catch((e) => setErr(String(e))); }, []);
  async function enroll(sid: number) {
    try {
      const r = await enrollLeads(sid, [...selected]);
      setEnrollMsg(`已把 ${r.enrolled} 家加入序列（${r.selected - r.enrolled} 家已在其中或已回复被跳过）`);
      fetchSequences().then(setSequences).catch((e) => setErr(String(e)));
    } catch (e) { setEnrollMsg("加入序列失败：" + String(e)); }
  }

  function loadLeads() {
    fetchLeadsPage({ country, channel, status, search, has, follow_up: followUp,
      sort, order, limit: String(PAGE_SIZE), offset: String(leadPage * PAGE_SIZE) })
      .then(({ leads, total }) => { setLeads(leads); setTotal(total); })
      .catch((e) => setErr(String(e)));
  }
  function reload() {
    fetchStats().then(setStats).catch((e) => setErr(String(e)));
    loadLeads();
  }
  useEffect(() => { fetchStats().then(setStats).catch((e) => setErr(String(e))); }, []);
  useEffect(loadLeads, [country, channel, status, search, has, followUp, sort, order, leadPage]);

  // Reset to first page whenever a filter/sort changes so offset stays valid.
  const filterReset = () => setLeadPage(0);
  function sortBy(col: string) {
    if (sort === col) { setOrder(order === "asc" ? "desc" : "asc"); }
    // 契合分默认高分在前（最优买家类型 rental/integrator 浮顶），其余列默认升序
    else { setSort(col); setOrder(col === "fit" ? "desc" : "asc"); }
    filterReset();
  }

  async function reply(no: number, channel: string) {
    try { await markReplied(no, channel); reload(); } catch (e) { setErr(String(e)); }
  }

  const [verifyMsg, setVerifyMsg] = useState("");
  const [verifying, setVerifying] = useState(false);
  async function verifyEmails() {
    setVerifying(true); setVerifyMsg("验证邮箱中（查 MX 记录）…");
    try {
      const scope = selected.size > 0 ? [...selected] : undefined;
      const { job_id } = await startVerify(scope);
      const poll = window.setInterval(async () => {
        const j = await fetchVerifyJob(job_id);
        if (j.status !== "running") {
          clearInterval(poll); timers.current.delete(poll); setVerifying(false);
          if (j.result && "checked" in j.result) {
            const r = j.result;
            setVerifyMsg(`已验证 ${r.checked} 个邮箱：有效 ${r.valid}，角色邮箱 ${r.role}，无效 ${r.invalid}（发送时自动跳过），无法判定 ${r.unknown}`);
            reload();
          } else if (j.result && "error" in j.result) { setVerifyMsg("验证失败：" + j.result.error); }
        }
      }, 1500);
      timers.current.add(poll);
    } catch (e) { setVerifying(false); setVerifyMsg("验证失败：" + String(e)); }
  }

  const [classifying, setClassifying] = useState(false);
  const [dupPending, setDupPending] = useState<number | null>(null);
  async function checkOrMergeDups() {
    try {
      if (dupPending === null) {
        const d = await fetchDuplicates();
        if (d.total_dups === 0) { setVerifyMsg("没有发现重复客户 ✓"); return; }
        setDupPending(d.total_dups);
        setVerifyMsg(`发现 ${d.groups.length} 组重复（共 ${d.total_dups} 条冗余）。合并会保留最早一条并补齐缺失字段、保住已回复状态。再点一次按钮确认合并。`);
      } else {
        const r = await mergeDuplicates();
        setDupPending(null);
        setVerifyMsg(`已合并 ${r.groups} 组，删除 ${r.removed} 条重复客户。`);
        reload();
      }
    } catch (e) { setDupPending(null); setVerifyMsg("查重失败：" + String(e)); }
  }
  async function classifyLeads() {
    setClassifying(true); setVerifyMsg("客户分级中（逐个读官网判断客户类型，较慢）…");
    try {
      const scope = selected.size > 0 ? [...selected] : undefined;
      const { job_id } = await startClassify(scope);
      const poll = window.setInterval(async () => {
        const j = await fetchClassifyJob(job_id);
        if (j.status === "running") { setVerifyMsg(`客户分级中 ${j.done}${j.total ? "/" + j.total : ""}…`); return; }
        clearInterval(poll); timers.current.delete(poll); setClassifying(false);
        if (j.result && "checked" in j.result) {
          const types = Object.entries(j.result.by_type).map(([t, n]) => `${t} ${n}`).join("，");
          setVerifyMsg(`已分级 ${j.result.checked} 家：${types || "未识别出类型"}。按"客户类型"列排序可优先打高价值客户。`);
          reload();
        } else if (j.result && "error" in j.result) { setVerifyMsg("分级失败：" + j.result.error); }
      }, 2000);
      timers.current.add(poll);
    } catch (e) { setClassifying(false); setVerifyMsg("分级失败：" + String(e)); }
  }

  const shown = leads;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const toggle = (no: number) => setSelected((s) => { const n = new Set(s); if (n.has(no)) { n.delete(no); } else { n.add(no); } return n; });
  const toggleAll = (checked: boolean) => setSelected(checked ? new Set(shown.map((l) => l.no)) : new Set());

  async function selectAllFiltered() {
    try {
      const all = await fetchLeads({ country, channel, status, search, has, follow_up: followUp });
      setSelected(new Set(all.map((l) => l.no)));
    } catch (e) { setErr(String(e)); }
  }

  if (authed === null) return null;
  // 登录成功后整页刷新，让所有初始数据加载重跑一遍
  if (!authed) return <LoginGate onSuccess={() => window.location.reload()} />;

  const title = PAGES.find((p) => p.id === page)!.label;
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="pixel-logo"><i /><i /><i /><i /></span>
          <span>
            <div className="brand-name">Maxcolor</div>
            <div className="brand-sub">客户开发系统</div>
          </span>
        </div>
        {PAGES.map((p) => (
          <button key={p.id} className={`nav-item${page === p.id ? " active" : ""}`} onClick={() => setPage(p.id)}>
            <span className="ico">{p.ico}</span><span className="nav-label">{p.label}</span>
            {p.id === "inbox" && unread > 0 && <span className="unread-dot">{unread}</span>}
          </button>
        ))}
      </aside>
      <div className="main">
        <header className="topbar">
          <h2>{title}</h2>
          <button className="btn btn-sm" onClick={toggleTheme} title="切换主题">
            {theme === "dark" ? "☀ 浅色" : "☾ 深色"}
          </button>
        </header>
        <div className="content">
          {err && <div className="error-text" style={{ marginBottom: 12 }}>加载失败：{err}</div>}
          {page === "dashboard" && stats && (
            <Dashboard stats={stats} unread={unread} onGoto={(p) => setPage(p as Page)} onGotoFollowUp={() => {
              setCountry(""); setChannel(""); setStatus(""); setHas(""); setSearch("");
              setFollowUp("due"); setLeadPage(0); setPage("leads");
            }} />
          )}
          {page === "leads" && (
            <>
              <div className="filter-bar">
                <select className="input" value={country} onChange={(e) => { setCountry(e.target.value); filterReset(); }}>
                  <option value="">全部国家</option>
                  {stats && Object.keys(stats.by_country).sort().map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <select className="input" value={channel} onChange={(e) => { setChannel(e.target.value); filterReset(); }}>
                  <option value="">全部渠道</option>
                  <option value="email">Email</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="instagram">Instagram</option>
                </select>
                <select className="input" value={status} onChange={(e) => { setStatus(e.target.value); filterReset(); }}>
                  <option value="">全部状态</option>
                  <option value="untouched">未触达</option>
                  <option value="messaged">已触达</option>
                  <option value="replied">已回复</option>
                </select>
                <select className="input" value={has} onChange={(e) => { setHas(e.target.value); filterReset(); }}>
                  <option value="">全部联系方式</option>
                  <option value="phone">有电话/WA</option>
                  <option value="instagram">有 IG</option>
                  <option value="email">有邮箱</option>
                </select>
                <input className="input" placeholder="搜索公司/网站/城市" value={search} onChange={(e) => { setSearch(e.target.value); filterReset(); }} />
                <button className={`btn btn-sm${followUp === "due" ? " btn-primary" : ""}`}
                  onClick={() => { setFollowUp(followUp === "due" ? "" : "due"); filterReset(); }}
                  title="只看已触达但超过7天没回复、或到跟进日期的客户">
                  待跟进{stats?.funnel?.follow_up_due ? ` ${stats.funnel.follow_up_due}` : ""}
                </button>
                <a className="btn btn-sm"
                  href={`/api/leads/export?fmt=xlsx${exportQuery({ country, channel, status, has, follow_up: followUp, search })}`}
                  title="按当前筛选导出 Excel">⬇ 导出 Excel</a>
                <button className="btn btn-sm" onClick={verifyEmails} disabled={verifying}
                  title="查 MX 记录验证邮箱有效性，无效邮箱发送时自动跳过（降 bounce 保送达）。勾选客户则只验证选中的，否则验证全部。">
                  {verifying ? "验证中…" : selected.size > 0 ? `✓ 验证选中邮箱` : "✓ 验证全部邮箱"}
                </button>
                <button className="btn btn-sm" onClick={classifyLeads} disabled={classifying}
                  title="读官网内容自动判断客户类型（租赁/集成商/经销商/标识厂/终端）+ 契合分，写入客户类型列。勾选客户则只分级选中的。">
                  {classifying ? "分级中…" : selected.size > 0 ? "★ 分级选中客户" : "★ 分级全部客户"}
                </button>
                <button className={`btn btn-sm${dupPending !== null ? " btn-primary" : ""}`} onClick={checkOrMergeDups}
                  title="按网站/公司名找出重复客户；确认后合并（保留最早一条，补齐字段，不丢已回复状态）">
                  {dupPending !== null ? `⚠ 确认合并 ${dupPending} 条重复` : "⧉ 查重合并"}
                </button>
                <button className={`btn btn-sm${healthOpen ? " btn-primary" : ""}`} onClick={() => setHealthOpen(!healthOpen)}
                  title="体检客户库：找出混进来的同行/B2B平台、没联系方式的空客户、抓错的公司名、阶段没跟上的客户">
                  🩺 客户库体检
                </button>
                <button className={`btn btn-sm${quickOpen ? " btn-primary" : ""}`} onClick={() => setQuickOpen(!quickOpen)}
                  title="在 IG/FB/LinkedIn/官网看到客户，粘贴链接一键入库；官网会自动深挖邮箱/电话/社媒/分级">
                  ＋ 快速添加
                </button>
                <span className="muted">共 {total} 条 · 已选 {selected.size}</span>
                {total > shown.length && selected.size < total && (
                  <button className="btn btn-sm" onClick={selectAllFiltered}
                    title="选中当前筛选条件下的全部客户（跨页），用于批量入序列/触达">全选 {total} 条</button>
                )}
                {selected.size > 0 && (
                  <button className="btn btn-sm" onClick={() => setSelected(new Set())}>清空选择</button>
                )}
              </div>
              {healthOpen && <HealthPanel onFixed={reload} />}
              {quickOpen && (
                <div className="card" style={{ marginBottom: 10, padding: 12 }}>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    <input className="input" style={{ flex: 2, minWidth: 280 }} value={quickUrl}
                      onChange={(e) => setQuickUrl(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") quickAdd(); }}
                      placeholder="粘贴链接：instagram.com/账号 · facebook.com/主页 · linkedin.com/company/… · 官网" />
                    <input className="input" style={{ width: 110 }} value={quickCountry}
                      onChange={(e) => setQuickCountry(e.target.value)} placeholder="国家（可选）" />
                    <input className="input" style={{ width: 150 }} value={quickName}
                      onChange={(e) => setQuickName(e.target.value)} placeholder="公司名（可选）" />
                    <button className="btn btn-green btn-sm" onClick={quickAdd} disabled={quickBusy}>
                      {quickBusy ? "添加中…" : "添加入库"}
                    </button>
                  </div>
                  {quickMsg && <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{quickMsg}</div>}
                </div>
              )}
              {verifyMsg && <div className="muted" style={{ marginBottom: 8 }}>{verifyMsg}</div>}
              <LeadsTable leads={shown} selected={selected} onToggle={toggle} onToggleAll={toggleAll}
                onReply={reply} onOpen={setDetail} sort={sort} order={order} onSort={sortBy} />
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
                <button className="btn btn-sm" disabled={leadPage <= 0} onClick={() => setLeadPage(leadPage - 1)}>← 上一页</button>
                <span className="muted">第 {leadPage + 1} / {pageCount} 页</span>
                <button className="btn btn-sm" disabled={leadPage + 1 >= pageCount} onClick={() => setLeadPage(leadPage + 1)}>下一页 →</button>
              </div>
              {selected.size > 0 && (
                <div className="action-bar">
                  {sequences.length > 0 && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
                      <span className="muted" style={{ fontSize: 13 }}>把已选 {selected.size} 家加入序列：</span>
                      <select className="input" value="" onChange={(e) => { if (e.target.value) enroll(Number(e.target.value)); }}>
                        <option value="">选择一个序列…</option>
                        {sequences.map((s) => <option key={s.id} value={s.id}>{s.name}（{s.channel}）</option>)}
                      </select>
                      {enrollMsg && <span className="muted">{enrollMsg}</span>}
                    </div>
                  )}
                  <OutreachPanel selected={[...selected]} onDone={reload}
                    countries={[...new Set(leads.filter((l) => selected.has(l.no) && l.country).map((l) => l.country as string))]}
                    firstCompany={leads.find((l) => selected.has(l.no))?.company_en ?? ""} />
                </div>
              )}
            </>
          )}
          {page === "opportunities" && <OpportunityPipeline onOpenLead={openLead} />}
          {page === "inbox" && <InboxPanel onOpenLead={openLead} onUnreadChange={() => { refreshUnread(); reload(); }} />}
          {page === "sequences" && <SequencesPanel onChanged={() => { reload(); refreshUnread(); }} />}
          {page === "discovery" && <><DiscoveryPanel onImported={reload} /><BlocklistPanel /></>}
          {page === "products" && <ProductsPanel />}
          {page === "channels" && <><ConnectionPanel /><MailboxPanel /></>}
        </div>
      </div>
      {detail && (
        <LeadDrawer
          lead={detail}
          onClose={() => setDetail(null)}
          onChange={(u) => { setDetail(u); setLeads((ls) => ls.map((l) => (l.no === u.no ? u : l))); }}
          onDeleted={(no) => { setDetail(null); setLeads((ls) => ls.filter((l) => l.no !== no)); reload(); }}
        />
      )}
    </div>
  );
}
