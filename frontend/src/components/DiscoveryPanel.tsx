import { useEffect, useState } from "react";
import { startDiscover, startPageDiscover, fetchDiscoverJob, importLeads, fetchDiscoverySources } from "../api";
import type { Candidate, DiscoverySource, SourceReport } from "../types";

const ICP_LABEL: Record<string, string> = {
  rental: "租赁公司", integrator: "AV集成商", reseller: "经销商",
  signage: "标识/广告牌", "end-user": "终端用户",
};

const MARKETS = ["USA", "Canada", "Mexico", "Brazil", "Chile", "Argentina", "Colombia", "Peru",
  "UK", "Germany", "France", "Spain", "Italy", "Netherlands", "Poland",
  "UAE", "Saudi Arabia", "South Korea", "Japan", "Australia", "South Africa",
  "India", "Thailand", "Vietnam", "Indonesia", "Philippines", "Turkey"];

const DEFAULT_QUERIES = `LED video wall installer contact
LED display rental company contact
AV integrator LED screen contact`;

// One click appends a proven angle as an extra search line.
const PRESET_QUERIES = ["LED signage company", "stage production LED screen rental",
  "church AV LED wall", "LED screen distributor", "digital billboard company"];

// 低客单价/低转化市场，一键排除；中国/香港/台湾（同行）由"排除同行"开关单独管
const EXCLUDABLE = ["India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal",
  "Nigeria", "Kenya", "Ghana", "Myanmar", "Cambodia", "Vietnam", "Indonesia"];

export function DiscoveryPanel({ onImported }: { onImported: () => void }) {
  const [mode, setMode] = useState<"search" | "page">("search");
  const [query, setQuery] = useState(DEFAULT_QUERIES);
  const [url, setUrl] = useState("");
  const [country, setCountry] = useState("USA");
  const [cands, setCands] = useState<Candidate[]>([]);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [excludePeers, setExcludePeers] = useState(true);
  const [excluded, setExcluded] = useState<Set<string>>(new Set(["India", "Pakistan"]));
  const [showExcluded, setShowExcluded] = useState(false);
  // 一个名录页抓出 0 家，几乎总是因为公司名单在 JS 里（docs/124）。这时候才提议开浏览器：
  // 它会弹出一个真的 Chrome 窗口，所以由他按，不由系统替他按。
  const [browserOffer, setBrowserOffer] = useState(false);
  // 渠道表。不选 = 只跑无人值守的那几条（DuckDuckGo / Naver）；点名一条要弹窗或要登录的，
  // 就是 Allen 自己按的按钮 —— 定时器永远点不到。docs/128 R1
  const [sources, setSources] = useState<DiscoverySource[]>([]);
  const [channels, setChannels] = useState<Set<string>>(new Set());
  const [report, setReport] = useState<SourceReport[]>([]);

  useEffect(() => { fetchDiscoverySources().then((r) => setSources(r.sources)).catch(() => {}); }, []);

  const queryLines = query.split("\n").map((l) => l.trim()).filter(Boolean);
  // 一条渠道声明了几种读法，最便宜的排在前面；只勾一条渠道时按它自己的第一种读法跑。
  const engineFor = (name: string) => sources.find((s) => s.name === name)?.engines[0];
  const toggleChannel = (name: string) => setChannels((s) => {
    const n = new Set(s); if (n.has(name)) { n.delete(name); } else { n.add(name); } return n;
  });

  async function run(engine: "jina" | "browser" = "jina") {
    if (mode === "page" && !url.trim()) { setMsg("请粘贴名录/经销商页 URL"); return; }
    if (mode === "search" && queryLines.length === 0) { setMsg("请至少填一行搜索关键词"); return; }
    setBusy(true); setCands([]); setPicked(new Set()); setBrowserOffer(false); setReport([]);
    setMsg(engine === "browser" ? "浏览器读取中…（屏幕上会弹出一个 Chrome 窗口，读完自动关）"
      : mode === "page" ? "抓取名录中…" : "搜索深挖中…");
    try {
      // 每行一条搜索；选了国家自动拼进关键词，结果按域名合并去重
      const composed = queryLines.map((l) => (country.trim() ? `${l} ${country.trim()}` : l));
      const screen = { exclude_countries: [...excluded], exclude_peers: excludePeers };
      const { job_id } = mode === "page"
        ? await startPageDiscover(url.trim(), 40, screen, undefined, undefined, engine)
        : await startDiscover(composed, 10, screen, [...channels],
          [...channels].length === 1 ? engineFor([...channels][0]) : undefined);
      const poll = setInterval(async () => {
        const j = await fetchDiscoverJob(job_id);
        setMsg(`进度 ${j.done}/${j.total}`);
        if (j.status !== "running") {
          clearInterval(poll); setBusy(false);
          if (j.result && "candidates" in j.result) {
            const all = j.result.candidates;
            setCands(all);
            setReport(j.result.sources || []);
            // 被排除的（同行/目录站/排除国家）绝不自动勾选。
            // docs/78 R3：还要有 hook 或 brief——没有一句能引用的话，就没有一封能写的信。
            // 从页面上扒到一个电话就自动打勾，是那几篇 naver 博客混进客户库的原因。
            // 不要求 ICP 有类型：那会连 avidex 这种真集成商一起挡掉。手动仍可勾任何一条。
            setPicked(new Set(all
              .filter((c) => !c.excluded && !c.duplicate_of
                && (c.email || c.phone || c.instagram) && (c.hook || c.brief))
              .map((c) => c.domain)));
            const cut = all.filter((c) => c.excluded).length;
            if (mode === "page" && all.length === 0 && engine === "jina") {
              setBrowserOffer(true);
              setMsg("这一页没抓到公司——它的名单多半在 JavaScript 里，源码上读不到。");
            } else {
              setMsg(`找到 ${all.length} 个候选${cut ? `，其中 ${cut} 家已筛掉（同行/目录站/排除国家）` : ""}`);
            }
          } else if (j.result && "error" in j.result) {
            setMsg("失败：" + j.result.error);
          }
        }
      }, 2000);
    } catch (e) { setBusy(false); setMsg("失败：" + String(e)); }
  }

  const toggleExcluded = (c: string) => setExcluded((s) => {
    const n = new Set(s); if (n.has(c)) { n.delete(c); } else { n.add(c); } return n;
  });

  async function doImport() {
    const chosen = cands.filter((c) => picked.has(c.domain));
    if (chosen.length === 0) { setMsg("请先勾选要导入的候选"); return; }
    try {
      const res = await importLeads(country, chosen.map((c) => ({
        // 探测到的国家更准（搜韩国也会混进别国公司）；"USA/Canada" 这类模糊值退回面板国家
        country: c.country && !c.country.includes("/") ? c.country : undefined,
        company_en: c.title, website: c.domain, email: c.email,
        phone: c.phone, instagram: c.instagram, facebook: c.facebook, linkedin: c.linkedin,
        source: c.source, icp_type: c.icp_type, fit_score: c.fit_score,
        // 开发时已经从官网读出来的东西，以前在这一步全丢了：接口一直收 brief/hook/
        // email_source/city/buying_signals，这里一个都没传。库里 645 家没有开场白就是
        // 这么来的，而没有开场白的客户进不了社媒私信队列（docs/52），等于永久出局。
        brief: c.brief, hook: c.hook, email_source: c.email_source, city: c.city,
        buying_signals: c.buying_signals,
      })));
      const dups = res.skipped.filter((s) => s.duplicate_of);
      const blocked = res.skipped.filter((s) => s.blocked_domain);
      const skipNote = dups.length
        ? `；${dups.length} 家已在库跳过（${dups.map((s) => `${s.website ?? s.company_en} → #${s.duplicate_of}`).join("、")}）`
        : "";
      const blockNote = blocked.length
        ? `；${blocked.length} 家在「永不再收录」名单里跳过（${blocked.map((s) => s.blocked_domain).join("、")}）`
        : "";
      const junk = res.skipped.filter((s) => s.not_a_company);
      const junkNote = junk.length
        ? `；${junk.length} 家读到的是反爬页/博客，不是公司（${junk.map((s) => s.website).join("、")}）`
        : "";
      const gained = res.enriched_fields
        ? `，另给 ${dups.length} 家已有客户补上了 ${res.enriched_fields} 项信息`
        : "";
      setMsg(`已导入 ${res.imported} 家${gained}${skipNote}${blockNote}${junkNote}`);
      // 表格状态列同步为已在库，避免误以为没导进去
      const dupMap = new Map(res.skipped.map((s) => [s.website, s.duplicate_of]));
      setCands((cs) => cs.map((c) => (picked.has(c.domain) && !c.duplicate_of
        ? { ...c, duplicate_of: dupMap.get(c.domain) ?? -1 } : c)));
      setPicked(new Set());
      onImported();
    } catch (e) { setMsg("导入失败：" + String(e)); }
  }

  const toggle = (d: string) => setPicked((s) => { const n = new Set(s); if (n.has(d)) { n.delete(d); } else { n.add(d); } return n; });
  const dash = <span className="muted">—</span>;
  return (
    <div className="card">
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <button className={`btn btn-sm${mode === "search" ? " btn-primary" : ""}`} onClick={() => setMode("search")}>关键词搜索</button>
        <button className={`btn btn-sm${mode === "page" ? " btn-primary" : ""}`} onClick={() => setMode("page")}>名录 / 竞品经销商页</button>
      </div>
      {mode === "search" ? (
        <>
          <h3>搜索深挖：官网自动提取邮箱 / 电话 / WhatsApp / IG / FB</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
            一行一条搜索，多行会依次跑并按域名合并去重；选了目标国家会自动拼进每条关键词。
          </div>
          <textarea className="input" style={{ width: "100%", height: 74, marginBottom: 6 }}
            value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder={"一行一条，如：\nLED video wall installer contact\nLED display rental company contact"} />
          <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span className="muted" style={{ fontSize: 12 }}>加一条：</span>
            {PRESET_QUERIES.map((p) => (
              <button key={p} className="btn btn-sm" disabled={query.includes(p)}
                onClick={() => setQuery((q) => (q.trim() ? q.trimEnd() + "\n" : "") + p)}>＋{p}</button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap", alignItems: "center" }}>
            <label className="muted" style={{ fontSize: 13 }}>目标国家</label>
            <input className="input" list="market-list" style={{ width: 150 }} value={country}
              onChange={(e) => setCountry(e.target.value)} placeholder="选择或输入国家" />
            <datalist id="market-list">
              {MARKETS.map((m) => <option key={m} value={m} />)}
            </datalist>
            <button className="btn btn-primary" onClick={() => run()} disabled={busy}>
              {busy ? "搜索中…" : `搜索深挖（${queryLines.length} 条）`}
            </button>
          </div>
          {channels.has("instagram") && (
            <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
              Instagram 搜的是<b>账号名</b>，不是描述：<code>pantallas led</code>、
              <code>led screen rental</code> 这种短词能搜到公司，
              <code>LED video wall installer contact</code> 这种长句一个账号都搜不到。
            </div>
          )}
          <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap", alignItems: "center" }}>
            <span className="muted" style={{ fontSize: 12 }}>
              渠道{channels.size === 0 ? "（不选＝自动跑免费的那几条）" : ""}：
            </span>
            {sources.map((s) => (
              <button key={s.name} className={`btn btn-sm${channels.has(s.name) ? " btn-primary" : ""}`}
                disabled={!s.available}
                title={s.available
                  ? `${s.engines.join(" / ")}${s.unattended ? "" : " · 要开窗口或要登录，只在你点的时候跑"}`
                  : s.reason}
                onClick={() => toggleChannel(s.name)}>
                {s.label}{s.available ? "" : " · 未启用"}
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <h3>从名录 / 竞品经销商页批量挖客户</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
            粘贴一个「列出很多公司」的页面 URL —— 竞品的 where-to-buy / distributors 页（如 Absen、Leyard 经销商列表），或展会参展商名录（ISE / InfoComm / LED China）。系统会抓出页面里的公司域名，逐个深挖联系方式。这些是 LED 行业最精准的现成买家池。
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
            <input className="input" style={{ flex: 1, minWidth: 260 }} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…  经销商页 / 参展商名录 URL" />
            <input className="input" style={{ width: 90 }} value={country} onChange={(e) => setCountry(e.target.value)} placeholder="国家" />
            <button className="btn btn-primary" onClick={() => run()} disabled={busy}>{busy ? "抓取中…" : "抓取名录"}</button>
          </div>
          {browserOffer && (
            <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>
              <button className="btn btn-sm" onClick={() => run("browser")} disabled={busy}>
                用浏览器读这一页
              </button>
              <span style={{ marginLeft: 8 }}>
                会打开一个 Chrome 窗口，翻页读完再关，约一两分钟。只取公司域名，公司名和联系方式仍旧从各家官网读。
              </span>
            </div>
          )}
        </>
      )}
      {report.length > 0 && (
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          {report.map((r) => (
            <span key={r.name} style={{ marginRight: 12 }}>
              {r.name}：{r.status === "ok" ? `${r.found} 家` : `${r.status}${r.reason ? " —— " + r.reason : ""}`}
            </span>
          ))}
        </div>
      )}
      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, marginBottom: 10 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 13, cursor: "pointer" }}
            title="搜 LED 关键词会大量搜到中国 LED 厂（我们的同行）和 alibaba/tradekey 这类目录站，它们不是买家。开启后自动筛掉：+86 电话、.cn 域名、B2B 平台。">
            <input type="checkbox" checked={excludePeers} onChange={(e) => setExcludePeers(e.target.checked)} />
            排除同行/供应商（中国·港台 LED 厂 + B2B 目录站）
          </label>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginTop: 6 }}>
          <span className="muted" style={{ fontSize: 12 }}>再排除这些市场：</span>
          {EXCLUDABLE.map((c) => (
            <button key={c} className={`btn btn-sm${excluded.has(c) ? " btn-primary" : ""}`}
              onClick={() => toggleExcluded(c)}>{excluded.has(c) ? "✓ " : ""}{c}</button>
          ))}
        </div>
      </div>
      {msg && <div className="muted" style={{ marginBottom: 10 }}>{msg}</div>}
      {cands.length > 0 && (
        <>
          {cands.some((c) => c.excluded) && (
            <label className="muted" style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 5, marginBottom: 6, cursor: "pointer" }}>
              <input type="checkbox" checked={showExcluded} onChange={(e) => setShowExcluded(e.target.checked)} />
              显示被筛掉的 {cands.filter((c) => c.excluded).length} 家（默认隐藏；显示后仍可手动勾选导入）
            </label>
          )}
          <div className="table-wrap">
            <table className="table">
              <thead><tr>
                <th></th><th>网站</th><th>国家</th><th>类型</th><th>开场白</th><th>邮箱</th><th>电话 / WhatsApp</th><th>IG</th><th>FB</th><th>状态</th>
              </tr></thead>
              <tbody>
                {cands.filter((c) => showExcluded || !c.excluded).map((c) => (
                  <tr key={c.domain} style={c.excluded ? { opacity: 0.5 } : undefined}>
                    {/* 已在库的也可以勾：导入重复不是白跑，它会把这次读到的联系方式、
                        职位、最近项目补到那家已有客户身上（docs/68 R4.3）。以前这个
                        勾选框是灰的，那条价值从界面上根本够不着。 */}
                    <td><input type="checkbox" disabled={c.duplicate_of === -1}
                      checked={picked.has(c.domain)} onChange={() => toggle(c.domain)}
                      title={c.duplicate_of && c.duplicate_of > 0 ? "已在库；勾选并导入会用这次读到的信息补全那家客户" : undefined} /></td>
                    <td><a href={`https://${c.domain}`} target="_blank" rel="noreferrer">{c.domain}</a></td>
                    <td>{c.excluded
                      ? <span className="warn-text" title="被筛掉：不会自动勾选">🚫 {c.exclude_reason}</span>
                      : c.country || dash}</td>
                    <td>{c.icp_type && c.icp_type !== "unknown"
                      ? <span title={`契合分 ${c.fit_score}`}>{ICP_LABEL[c.icp_type] ?? c.icp_type} <span className="muted">{c.fit_score}</span></span>
                      : dash}</td>
                    {/* 决定一条能不能勾的就是这一格：没有一句能引用的话，就没有一封能写的信。
                        以前它不在表上，所以自动没勾的行看不出为什么。 */}
                    <td style={{ maxWidth: 260 }}>{c.hook
                      ? <span title={c.brief || c.hook}>{c.hook}</span>
                      : <span className="warn-text" title="官网没读出可引用的具体信息，不会自动勾选">没有可引用的话</span>}</td>
                    <td>{c.email || dash}</td>
                    <td className="num">{c.phone
                      ? <a href={`https://wa.me/${c.phone.replace(/\D/g, "")}`} target="_blank" rel="noreferrer" style={{ color: "var(--green)" }}>{c.phone}</a>
                      : dash}</td>
                    <td>{c.instagram
                      ? <a href={`https://instagram.com/${c.instagram}`} target="_blank" rel="noreferrer">@{c.instagram}</a>
                      : dash}</td>
                    <td>{c.facebook
                      ? <a href={`https://facebook.com/${c.facebook}`} target="_blank" rel="noreferrer">{c.facebook}</a>
                      : dash}</td>
                    <td>{c.duplicate_of === -1
                      ? <span style={{ color: "var(--green)" }}>已导入 ✓</span>
                      : c.duplicate_of
                        ? <span className="warn-text">已在库 #{c.duplicate_of}</span>
                        : <span style={{ color: "var(--green)" }}>新</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="btn btn-green" style={{ marginTop: 10 }} onClick={doImport}>
            导入选中（{picked.size}）
          </button>
        </>
      )}
    </div>
  );
}
