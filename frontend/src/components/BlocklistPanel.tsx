import { useEffect, useState } from "react";
import { fetchBlocklist, addBlocked, removeBlocked } from "../api";
import type { BlockedDomain } from "../api";

export function BlocklistPanel() {
  const [rows, setRows] = useState<BlockedDomain[]>([]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  function reload() { fetchBlocklist().then(setRows).catch((e) => setErr(String(e))); }
  useEffect(reload, []);

  async function add() {
    const v = value.trim();
    if (!v) return;
    setBusy(true); setErr("");
    try { await addBlocked(v, "手动添加"); setValue(""); reload(); }
    catch (e) { setErr(String(e)); }
    finally { setBusy(false); }
  }

  return (
    <div className="card" style={{ marginTop: 14 }}>
      <h3 style={{ margin: 0 }}>永不再收录（{rows.length}）</h3>
      <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
        按域名拦截：采集导入、快速添加、重跑采集脚本都会跳过这些公司。
        同行、中国厂的海外分公司放这里 —— 光删除挡不住，采集文件里还留着它们，下次导入会再进来。
      </div>
      <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
        <input className="input" style={{ flex: 1 }} value={value} placeholder="域名 / 官网 / 邮箱，如 xcolorledusa.com"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") add(); }} />
        <button className="btn btn-sm" onClick={add} disabled={busy}>加入名单</button>
      </div>
      {err && <div className="error-text" style={{ marginTop: 8 }}>{err}</div>}
      {rows.length === 0 ? (
        <div className="muted" style={{ marginTop: 10 }}>名单是空的。删除客户时勾选「同时加入永不再收录」就会出现在这里。</div>
      ) : (
        <div style={{ marginTop: 10 }}>
          {rows.map((r) => (
            <div key={r.id} className="note-item" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <b>{r.domain}</b>
              <span className="muted" style={{ fontSize: 12 }}>{r.reason || ""}</span>
              <button className="btn btn-sm" style={{ marginLeft: "auto" }}
                onClick={async () => { await removeBlocked(r.id); reload(); }}
                title="移出名单后，这家公司下次采集会重新被收录">移出</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
