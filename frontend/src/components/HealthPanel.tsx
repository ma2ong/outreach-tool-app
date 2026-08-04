import { useState } from "react";
import { scanHealth, fixHealth, fetchCleanable, bulkDeleteLeads, type HealthLead } from "../api";

const ISSUE_META: Record<string, { title: string; hint: string; fixable: boolean; fixLabel?: string; blockDefault?: boolean }> = {
  peer: { title: "同行 / 供应商", hint: "中国·港台 LED 厂（+86 电话或 .cn 域名）——发给他们纯浪费额度", fixable: true, fixLabel: "标为不再联系", blockDefault: true },
  directory: { title: "B2B 目录站 / 平台", hint: "alibaba、tradekey 这类平台，不是买家", fixable: true, fixLabel: "标为不再联系", blockDefault: true },
  stale_stage: { title: "阶段没跟上", hint: "已经发过消息，销售阶段却还停在「新客户」", fixable: true, fixLabel: "推进到「已联系」" },
  no_contact: { title: "没有任何联系方式", hint: "邮箱/电话/IG/FB 全空——留着占位，永远发不出去。补不到资料就勾选删掉", fixable: false },
  junk_name: { title: "公司名可疑", hint: "抓成了 Contact / Home 这种网页标题，发信开头会很怪。能改名就打开改，改不了就删", fixable: false },
};

export function HealthPanel({ onFixed }: { onFixed: () => void }) {
  const [issues, setIssues] = useState<Record<string, HealthLead[]> | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [blockToo, setBlockToo] = useState(false);
  const [smart, setSmart] = useState<HealthLead[] | null>(null);

  async function scan() {
    setBusy(true); setMsg("体检中…");
    try {
      const r = await scanHealth();
      setIssues(r.issues); setPicked(new Set()); setSmart(null);
      setMsg(r.total === 0 ? "客户库很干净，没发现问题 ✓" : `发现 ${r.total} 处问题`);
    } catch (e) { setMsg("体检失败：" + String(e)); }
    finally { setBusy(false); }
  }

  async function fix(key: string) {
    setBusy(true);
    try {
      const done = await fixHealth([key]);
      setMsg(`已处理 ${Object.values(done).reduce((a, b) => a + b, 0)} 条`);
      await scan(); onFixed();
    } catch (e) { setMsg("处理失败：" + String(e)); }
    finally { setBusy(false); }
  }

  function toggleOpen(key: string) {
    const next = openKey === key ? null : key;
    setOpenKey(next);
    setPicked(new Set());
    setBlockToo(!!ISSUE_META[key]?.blockDefault);
  }

  function toggle(no: number) {
    setPicked((p) => { const n = new Set(p); n.has(no) ? n.delete(no) : n.add(no); return n; });
  }

  async function deletePicked() {
    if (picked.size === 0) return;
    setBusy(true);
    try {
      const r = await bulkDeleteLeads([...picked], blockToo);
      setMsg(`已删除 ${r.deleted} 条`
        + (r.blocked_domains.length ? `，${r.blocked_domains.length} 个域名已加入永不再收录` : ""));
      await scan(); onFixed();
    } catch (e) { setMsg("删除失败：" + String(e)); }
    finally { setBusy(false); }
  }

  // 智能清理：后端算出"确定是死数据"的集合（无任何联系方式 + 从未触达 + 无跟进/商机），
  // 先给出预览再删 —— 删除不可撤销，不能点一下就直接动手。
  async function previewSmart() {
    setBusy(true); setMsg("");
    try {
      const r = await fetchCleanable();
      setSmart(r.leads);
      if (r.count === 0) setMsg("没有可以放心自动删的客户 —— 剩下的都有联系方式或有跟进记录，需要你自己判断");
    } catch (e) { setMsg("检查失败：" + String(e)); }
    finally { setBusy(false); }
  }

  async function runSmart() {
    if (!smart?.length) return;
    setBusy(true);
    try {
      const r = await bulkDeleteLeads(smart.map((l) => l.no), false);
      setMsg(`智能清理完成：删除 ${r.deleted} 条`);
      setSmart(null); await scan(); onFixed();
    } catch (e) { setMsg("清理失败：" + String(e)); }
    finally { setBusy(false); }
  }

  const keys = issues ? Object.keys(issues).filter((k) => issues[k].length) : [];
  return (
    <div className="card" style={{ marginBottom: 10, padding: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <button className="btn btn-sm btn-primary" onClick={scan} disabled={busy}>
          {busy ? "体检中…" : "🩺 开始体检"}
        </button>
        <button className="btn btn-sm" onClick={previewSmart} disabled={busy}
          title="自动挑出确定是死数据的客户：没有任何联系方式、从未触达、没有跟进记录和商机。先给预览再删">
          ✨ 一键智能清理
        </button>
        <span className="muted" style={{ fontSize: 12 }}>
          查出正在浪费你触达额度的数据：混进来的同行、B2B 平台、没联系方式的空客户、抓错的公司名
        </span>
        {msg && <span className="muted" style={{ fontSize: 12 }}>{msg}</span>}
      </div>

      {smart && smart.length > 0 && (
        <div className="note-item" style={{ marginTop: 10, borderLeft: "3px solid #c0392b" }}>
          <div><b>智能清理将删除 {smart.length} 条</b> —— 都是没有任何联系方式、从未触达、也没有任何跟进记录和商机的空记录，<b>不可恢复</b>。</div>
          <div className="muted" style={{ fontSize: 12, margin: "4px 0" }}>
            {smart.slice(0, 8).map((l) => `#${l.no} ${l.company_en}`).join("、")}
            {smart.length > 8 ? ` …等 ${smart.length} 条` : ""}
          </div>
          <button className="btn btn-sm" style={{ background: "#c0392b", color: "#fff", borderColor: "#c0392b", marginRight: 8 }}
            onClick={runSmart} disabled={busy}>确认删除这 {smart.length} 条</button>
          <button className="btn btn-sm" onClick={() => setSmart(null)} disabled={busy}>取消</button>
        </div>
      )}

      {keys.length > 0 && (
        <div style={{ marginTop: 10 }}>
          {keys.map((k) => {
            const meta = ISSUE_META[k] ?? { title: k, hint: "", fixable: false };
            const list = issues![k];
            const open = openKey === k;
            return (
              <div key={k} className="note-item">
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <strong>{meta.title}</strong>
                  <span className="warn-text">{list.length} 条</span>
                  <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={() => toggleOpen(k)}>
                    {open ? "收起" : "逐条挑选删除"}
                  </button>
                  {meta.fixable && (
                    <button className="btn btn-sm btn-green" onClick={() => fix(k)} disabled={busy}>
                      一键{meta.fixLabel}（{list.length}）
                    </button>
                  )}
                </div>
                <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{meta.hint}</div>
                {!open ? (
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    {list.slice(0, 6).map((l) => `#${l.no} ${l.website || l.company_en}`).join("、")}
                    {list.length > 6 ? ` …等 ${list.length} 条` : ""}
                  </div>
                ) : (
                  <div style={{ marginTop: 6 }}>
                    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
                      <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, cursor: "pointer" }}>
                        <input type="checkbox" checked={picked.size === list.length && list.length > 0}
                          onChange={(e) => setPicked(e.target.checked ? new Set(list.map((l) => l.no)) : new Set())} />
                        全选（{list.length}）
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, cursor: "pointer" }}
                        title="删除后把域名加入「永不再收录」，下次采集不会再把它们收进来">
                        <input type="checkbox" checked={blockToo} onChange={(e) => setBlockToo(e.target.checked)} />
                        同时加入永不再收录
                      </label>
                      <button className="btn btn-sm" style={{ background: "#c0392b", color: "#fff", borderColor: "#c0392b" }}
                        onClick={deletePicked} disabled={busy || picked.size === 0}>
                        删除选中（{picked.size}）
                      </button>
                    </div>
                    <div style={{ maxHeight: 260, overflowY: "auto" }}>
                      {list.map((l) => (
                        <label key={l.no} style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 0", fontSize: 13, cursor: "pointer" }}>
                          <input type="checkbox" checked={picked.has(l.no)} onChange={() => toggle(l.no)} />
                          <span className="muted">#{l.no}</span>
                          <b>{l.company_en}</b>
                          <span className="muted">{l.website || ""}</span>
                          <span className="muted" style={{ marginLeft: "auto" }}>{l.country || ""}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
