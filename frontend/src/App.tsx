import { useEffect, useRef, useState } from "react";
import { fetchLead, fetchLeads, fetchLeadsPage, fetchStats, markReplied, fetchSequences, enrollLeads, startVerify, fetchVerifyJob, startClassify, fetchClassifyJob, fetchDuplicates, mergeDuplicates, fetchInboxPending, quickAddLead, fetchAuthStatus, login, fetchActivityStats, bulkDeleteLeads, mergeLeads } from "./api";
import type { ActivityStats, Lead, Stats, Sequence } from "./types";
import { Dashboard } from "./components/Dashboard";
import { LeadsTable } from "./components/LeadsTable";
import { LeadDrawer } from "./components/LeadDrawer";
import { OutreachPanel } from "./components/OutreachPanel";
import { DiscoveryPanel } from "./components/DiscoveryPanel";
import { SocialQueuePanel } from "./components/SocialQueuePanel";
import { BlocklistPanel } from "./components/BlocklistPanel";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { MailboxPanel } from "./components/MailboxPanel";
import { ProductsPanel } from "./components/ProductsPanel";
import { SequencesPanel } from "./components/SequencesPanel";
import { InboxPanel } from "./components/InboxPanel";
import { ConversationPanel } from "./components/ConversationPanel";
import { Pager } from "./components/Pager";
import { EmailPlanPanel } from "./components/EmailPlanPanel";
import { AutonomyControlCenter } from "./components/AutonomyControlCenter";
import { WorkerRuntimeStatus } from "./components/WorkerRuntimeStatus";
import { HealthPanel } from "./components/HealthPanel";
import { OpportunityPipeline } from "./components/OpportunityPipeline";
import { ActivitiesPanel } from "./components/ActivitiesPanel";
import { SalesDocumentsPanel } from "./components/SalesDocumentsPanel";
import { SalesIntelligencePanel } from "./components/SalesIntelligencePanel";
import { AgentPanel } from "./components/AgentPanel";

export type Page = "dashboard" | "agent" | "intelligence" | "activities" | "leads" | "opportunities" | "conversations" | "inbox" | "sequences" | "emailplan" | "socialqueue" | "discovery" | "products" | "channels";

function exportQuery(params: Record<string, string>): string {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  return qs ? "&" + qs : "";
}

const PAGES: { id: Page; label: string; ico: string }[] = [
  { id: "dashboard", label: "仪表盘", ico: "▦" },
  { id: "agent", label: "Agent", ico: "◉" },
  { id: "intelligence", label: "销售雷达", ico: "◎" },
  { id: "activities", label: "销售任务", ico: "✓" },
  { id: "leads", label: "客户库", ico: "☰" },
  { id: "opportunities", label: "商机管道", ico: "◇" },
  { id: "conversations", label: "客户对话", ico: "◗" },
  { id: "inbox", label: "收件箱", ico: "✉" },
  { id: "sequences", label: "跟进序列", ico: "⇉" },
  { id: "emailplan", label: "邮件计划", ico: "✈" },
  { id: "socialqueue", label: "社媒私信", ico: "◐" },
  { id: "discovery", label: "客户开发", ico: "⌕" },
  { id: "products", label: "报价订单", ico: "▤" },
  { id: "channels", label: "渠道连接", ico: "⇄" },
];

const NAV_GROUPS: { label: string; pages: Page[] }[] = [
  { label: "今日工作", pages: ["dashboard", "agent", "intelligence", "activities"] },
  { label: "客户与对话", pages: ["leads", "conversations", "inbox"] },
  { label: "开发计划", pages: ["discovery", "sequences", "emailplan", "socialqueue"] },
  { label: "商机与订单", pages: ["opportunities", "products"] },
  { label: "资料与设置", pages: ["channels"] },
];

function isPage(value: string): value is Page {
  return PAGES.some((item) => item.id === value);
}

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
            <div className="brand-name">MCVISUAL</div>
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

// 韩国和美国是他现在的两个主要市场（300 家和 525 家），一天里要选它们几十次；
// 其余国家按字母序，因为找它们靠的是拼写而不是记忆。
const PINNED_COUNTRIES = ["South Korea", "USA"];

function sortCountries(all: string[]): string[] {
  const pinned = PINNED_COUNTRIES.filter((c) => all.includes(c));
  const rest = all.filter((c) => !pinned.includes(c))
    .sort((a, b) => a.trim().localeCompare(b.trim()));
  return [...pinned, ...rest];
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
  const searchRef = useRef<HTMLInputElement>(null);
  const [sort, setSort] = useState("no");
  const [order, setOrder] = useState("asc");
  const [leadPage, setLeadPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [detail, setDetail] = useState<Lead | null>(null);
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [enrollMsg, setEnrollMsg] = useState("");
  // 客户库是管理客户的地方，勾一下不该弹出整个发信表单。触达改成点了才展开。
  const [outreachOpen, setOutreachOpen] = useState(false);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);
  const [bulkMsg, setBulkMsg] = useState("");
  // 手动合并：自动查重按官网/公司名分组，官网不同、名字拼写不同的同一家它看不出来（docs/109）
  const [mergeRows, setMergeRows] = useState<Lead[] | null>(null);
  const [mergeKeep, setMergeKeep] = useState(0);
  const [mergeBusy, setMergeBusy] = useState(false);
  const [err, setErr] = useState("");
  const [pendingReplies, setPendingReplies] = useState(0);
  const [activityStats, setActivityStats] = useState<ActivityStats | null>(null);
  const [authed, setAuthed] = useState<boolean | null>(null);
  useEffect(() => {
    fetchAuthStatus().then((s) => setAuthed(!s.enabled || s.authed)).catch((e) => {
      setErr(`无法读取登录状态：${String(e)}`); setAuthed(true);
    });
  }, []);

  const refreshPending = () => fetchInboxPending().then(setPendingReplies).catch((e) => setErr(String(e)));
  const refreshActivityStats = () => fetchActivityStats().then(setActivityStats).catch((e) => setErr(String(e)));
  useEffect(() => { refreshPending(); }, []);
  useEffect(() => { refreshActivityStats(); }, []);

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
    } catch (e) { setQuickMsg("添加失败：" + String(e)); reload(); }
    finally { setQuickBusy(false); }
  }

  // 每页条数记在本地：这是个人习惯，不该每次打开都退回默认
  const [pageSize, setPageSize] = useState(() => {
    const saved = Number(localStorage.getItem("leadPageSize"));
    return [20, 50, 100, 200].includes(saved) ? saved : 100;
  });
  const PAGE_SIZE = pageSize;

  useEffect(() => { fetchSequences().then(setSequences).catch((e) => setErr(String(e))); }, []);
  async function enroll(sid: number) {
    try {
      const r = await enrollLeads(sid, [...selected]);
      const skipped = r.selected - r.enrolled - r.wrong_language;
      const reasons = [skipped > 0 ? `${skipped} 家已在其中或已回复` : "",
                       r.wrong_language > 0 ? `${r.wrong_language} 家国家与序列语言不符` : ""]
        .filter(Boolean).join("，");
      setEnrollMsg(`已把 ${r.enrolled} 家加入序列${reasons ? `（跳过：${reasons}）` : ""}`);
      // Clear the selection: leaving it on is how the same fifty leads once landed in
      // both the English and the Korean sequence, two clicks apart.
      setSelected(new Set());
      fetchSequences().then(setSequences).catch((e) => setErr(String(e)));
    } catch (e) { setEnrollMsg("加入序列失败：" + String(e)); }
  }

  const MERGE_MAX = 10;
  // 面板里的那几行是打开那一刻的快照；勾选一变它就过期了，关掉比留着一份旧的安全
  useEffect(() => { setMergeRows(null); }, [selected]);
  async function openMerge() {
    if (mergeRows) { setMergeRows(null); return; }
    const nos = [...selected].sort((a, b) => a - b);
    if (nos.length > MERGE_MAX) {
      setBulkMsg(`一次最多合并 ${MERGE_MAX} 家。合并不可撤销，请分批确认。`); return;
    }
    setBulkMsg("");
    try {
      // 跨页全选时，勾中的客户可能不在当前这一页里，缺的按编号取回来
      const rows = await Promise.all(nos.map((no) => {
        const onPage = leads.find((l) => l.no === no);
        return onPage ? Promise.resolve(onPage) : fetchLead(no);
      }));
      setMergeRows(rows);
      setMergeKeep(rows[0].no);  // 默认最早入库的那条
    } catch (e) { setBulkMsg("读取选中客户失败：" + String(e)); }
  }
  async function doMerge() {
    if (!mergeRows) return;
    setMergeBusy(true);
    try {
      const r = await mergeLeads(mergeKeep, mergeRows.filter((l) => l.no !== mergeKeep).map((l) => l.no));
      setBulkMsg(`已把 ${r.merged} 家合并进 #${r.keep.no} ${r.keep.company_en ?? ""}`);
      setMergeRows(null); setSelected(new Set());
      setDetail(r.keep);  // 合并完直接看结果，不用再去表里找那一行
      reload();
    } catch (e) { setBulkMsg("合并失败：" + String(e instanceof Error ? e.message : e)); }
    finally { setMergeBusy(false); }
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
  useEffect(loadLeads, [country, channel, status, search, has, followUp, sort, order, leadPage, pageSize]);

  // Reset to first page whenever a filter/sort changes so offset stays valid.
  const filterReset = () => setLeadPage(0);
  // 清空之后光标留在框里：清空是为了打下一个词，不是为了看空列表。
  const clearSearch = () => { setSearch(""); filterReset(); searchRef.current?.focus(); };
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
    } catch (e) { setVerifying(false); setVerifyMsg("验证失败：" + String(e)); reload(); }
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
    } catch (e) { setDupPending(null); setVerifyMsg("查重失败：" + String(e)); reload(); }
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
    } catch (e) { setClassifying(false); setVerifyMsg("分级失败：" + String(e)); reload(); }
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
            <div className="brand-name">MCVISUAL</div>
            <div className="brand-sub">客户开发系统</div>
          </span>
        </div>
        {NAV_GROUPS.map((group) => (
          <div className="nav-group" key={group.label}>
            <div className="nav-group-label">{group.label}</div>
            {group.pages.map((id) => {
              const p = PAGES.find((item) => item.id === id)!;
              return (
                <button key={p.id} className={`nav-item${page === p.id ? " active" : ""}`} onClick={() => setPage(p.id)}>
                  <span className="ico">{p.ico}</span><span className="nav-label">{p.label}</span>
                  {p.id === "inbox" && pendingReplies > 0 && <span className="unread-dot">{pendingReplies}</span>}
                  {p.id === "activities" && !!activityStats && activityStats.overdue + activityStats.today > 0 &&
                    <span className="unread-dot">{activityStats.overdue + activityStats.today}</span>}
                </button>
              );
            })}
          </div>
        ))}
      </aside>
      <div className="main">
        <header className="topbar">
          <h2>{title}</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AutonomyControlCenter />
            <WorkerRuntimeStatus />
            <button className="btn btn-sm" onClick={toggleTheme} title="切换主题">
              {theme === "dark" ? "☀ 浅色" : "☾ 深色"}
            </button>
          </div>
        </header>
        <div className="content">
          {err && <div className="error-text" style={{ marginBottom: 12 }}>加载失败：{err}</div>}
          {page === "dashboard" && stats && (
            <Dashboard stats={stats} pendingReplies={pendingReplies} onGoto={(p) => { if (isPage(p)) setPage(p); }} onGotoFollowUp={() => {
              setCountry(""); setChannel(""); setStatus(""); setHas(""); setSearch("");
              setFollowUp("due"); setLeadPage(0); setPage("leads");
            }} />
          )}
          {page === "leads" && (
            <div className="page-fill">
              <div className="filter-bar">
                <select className="input" value={country} onChange={(e) => { setCountry(e.target.value); filterReset(); }}>
                  <option value="">全部国家</option>
                  {/* 国家为空的那一档要有名字：一个空白选项看不出选的是什么 */}
                  {stats && sortCountries(Object.keys(stats.by_country))
                    .map((c) => <option key={c} value={c}>{c.trim() || "（国家未知）"}</option>)}
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
                <span className="search-box">
                  <input ref={searchRef} className="input" placeholder="搜索公司/网站/城市" value={search}
                    onChange={(e) => { setSearch(e.target.value); filterReset(); }}
                    onKeyDown={(e) => { if (e.key === "Escape" && search) clearSearch(); }} />
                  {search && (
                    <button type="button" className="search-clear" onClick={clearSearch}
                      title="清空搜索（Esc）" aria-label="清空搜索">×</button>
                  )}
                </span>
                <button className={`btn btn-sm${followUp === "due" ? " btn-primary" : ""}`}
                  onClick={() => { setFollowUp(followUp === "due" ? "" : "due"); filterReset(); }}
                  title="只看已触达但超过7天没回复、或到跟进日期的客户">
                  待跟进{stats?.funnel?.follow_up_due ? ` ${stats.funnel.follow_up_due}` : ""}
                </button>
                {/* docs/86 R3: six bulk actions over zero customers is six things to
                    read past. An empty book has exactly one useful next step. */}
                {stats?.total === 0 ? (
                  <button className="btn btn-primary btn-sm" onClick={() => setPage("discovery")}>
                    去找客户 →
                  </button>
                ) : (<>
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
                </>)}
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
                onReply={reply} onOpen={setDetail} sort={sort} order={order} onSort={sortBy}
                onChanged={reload} />
              <Pager page={leadPage} pageCount={pageCount} total={total} pageSize={pageSize}
                onPage={setLeadPage}
                onPageSize={(n) => {
                  // 换了每页条数，当前的 offset 就不再指向同一批客户了，退回第一页
                  localStorage.setItem("leadPageSize", String(n));
                  setPageSize(n); setLeadPage(0);
                }} />
              {selected.size > 0 && (
                <div className="action-bar">
                  {/* 一条操作栏，不是一整张发信表单。取消就在这一行的右端——原来要滚回
                      表格里去找自己勾的那一格才能取消。 */}
                  <div className="select-bar">
                    <b>已选 {selected.size} 家</b>
                    <button className={`btn btn-sm${outreachOpen ? " btn-primary" : ""}`}
                      onClick={() => setOutreachOpen((v) => !v)}>
                      ✉ 触达{outreachOpen ? " ▲" : " ▼"}
                    </button>
                    {sequences.length > 0 && (
                      <select className="input btn-sm" style={{ width: 190 }} value=""
                        onChange={(e) => { if (e.target.value) enroll(Number(e.target.value)); }}>
                        <option value="">⇄ 加入跟进序列…</option>
                        {sequences.map((s) => <option key={s.id} value={s.id}>{s.name}（{s.channel}）</option>)}
                      </select>
                    )}
                    {selected.size >= 2 && (
                      <button className={`btn btn-sm${mergeRows ? " btn-primary" : ""}`} onClick={openMerge}
                        title="确认这几条是同一家公司时把它们合成一条：资料补齐、触达/对话/任务/商机转到保留的那条名下">
                        ⧉ 合并{mergeRows ? " ▲" : " ▼"}
                      </button>
                    )}
                    {confirmBulkDelete ? (
                      <>
                        <span className="warn-text" style={{ fontSize: 13 }}>
                          删除这 {selected.size} 家？触达记录、任务、跟进、商机一起消失，不可恢复
                        </span>
                        <button className="btn btn-sm btn-danger" onClick={async () => {
                          try {
                            const r = await bulkDeleteLeads([...selected]);
                            setBulkMsg(`已删除 ${r.deleted} 家`);
                            setSelected(new Set()); setConfirmBulkDelete(false); reload();
                          } catch (e) { setBulkMsg("删除失败：" + String(e)); }
                        }}>确认删除</button>
                        <button className="btn btn-sm" onClick={() => setConfirmBulkDelete(false)}>取消</button>
                      </>
                    ) : (
                      <button className="btn btn-sm btn-danger-ghost"
                        onClick={() => setConfirmBulkDelete(true)}>🗑 删除</button>
                    )}
                    {(enrollMsg || bulkMsg) && <span className="muted" style={{ fontSize: 13 }}>{enrollMsg || bulkMsg}</span>}
                    <button className="btn btn-sm" style={{ marginLeft: "auto" }}
                      onClick={() => { setSelected(new Set()); setOutreachOpen(false); setConfirmBulkDelete(false); setMergeRows(null); setBulkMsg(""); }}>
                      取消选择
                    </button>
                  </div>
                  {mergeRows && (
                    <div style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                      <div style={{ fontSize: 13, marginBottom: 6 }}>
                        保留哪一条？<span className="muted">（保留行已有的资料不会被覆盖，其余行只补它的空缺字段）</span>
                      </div>
                      {mergeRows.map((l) => (
                        <label key={l.no} style={{ display: "flex", gap: 8, alignItems: "baseline", padding: "3px 0", cursor: "pointer" }}>
                          <input type="radio" name="merge-keep" checked={mergeKeep === l.no}
                            onChange={() => setMergeKeep(l.no)} />
                          <b style={{ minWidth: 200 }}>#{l.no} {l.company_en}</b>
                          <span className="muted" style={{ fontSize: 12 }}>
                            {[l.website, l.email, l.phone, l.contact_name, l.country, l.stage].filter(Boolean).join(" · ") || "无资料"}
                          </span>
                        </label>
                      ))}
                      <div className="warn-text" style={{ fontSize: 12, margin: "8px 0" }}>
                        其余 {mergeRows.length - 1} 家的触达记录、对话、任务、商机、跟进序列会转到 #{mergeKeep} 名下，然后删除。不可撤销。
                      </div>
                      <button className="btn btn-sm btn-primary" onClick={doMerge} disabled={mergeBusy}>
                        {mergeBusy ? "合并中…" : `确认合并这 ${mergeRows.length} 家为 #${mergeKeep}`}
                      </button>
                    </div>
                  )}
                  {outreachOpen && (
                    <div style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                      <OutreachPanel selected={[...selected]} onDone={reload}
                        countries={[...new Set(leads.filter((l) => selected.has(l.no) && l.country).map((l) => l.country as string))]}
                        firstCompany={leads.find((l) => selected.has(l.no))?.company_en ?? ""} />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          {page === "agent" && <AgentPanel onOpenLead={openLead} />}
          {page === "intelligence" && <SalesIntelligencePanel onOpenLead={openLead} onChanged={() => { refreshActivityStats(); reload(); }} />}
          {page === "opportunities" && <OpportunityPipeline onOpenLead={openLead} onChanged={refreshActivityStats} />}
          {page === "activities" && <ActivitiesPanel onOpenLead={openLead} onChanged={refreshActivityStats} />}
          {page === "conversations" && <ConversationPanel onOpenLead={openLead} />}
          {page === "inbox" && <InboxPanel onOpenLead={openLead} onPendingChange={() => { refreshPending(); refreshActivityStats(); reload(); }} />}
          {page === "sequences" && <SequencesPanel onChanged={() => { reload(); refreshPending(); }} />}
          {page === "emailplan" && <EmailPlanPanel onOpenLead={openLead} />}
          {page === "socialqueue" && <SocialQueuePanel />}
          {page === "discovery" && <><DiscoveryPanel onImported={reload} /><BlocklistPanel /></>}
          {page === "products" && <><SalesDocumentsPanel /><ProductsPanel /></>}
          {page === "channels" && <><ConnectionPanel /><MailboxPanel /></>}
        </div>
      </div>
      {detail && (
        <LeadDrawer
          lead={detail}
          onClose={() => setDetail(null)}
          onChange={(u) => { setDetail(u); setLeads((ls) => ls.map((l) => (l.no === u.no ? u : l))); }}
          onDeleted={(no) => { setDetail(null); setLeads((ls) => ls.filter((l) => l.no !== no)); reload(); }}
          onTasksChange={refreshActivityStats}
        />
      )}
    </div>
  );
}
