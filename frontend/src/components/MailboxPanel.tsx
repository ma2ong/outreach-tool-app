import { useEffect, useState } from "react";
import { fetchMailboxes, createMailbox, setMailboxActive, deleteMailbox, testMailbox } from "../api";
import type { Mailbox } from "../types";

const BLANK = {
  email: "", smtp_host: "", port: 465, imap_host: "", imap_port: 993,
  username: "", password: "", daily_cap: 40, imap_enabled: true,
};

export function MailboxPanel() {
  const [boxes, setBoxes] = useState<Mailbox[]>([]);
  const [form, setForm] = useState({ ...BLANK });
  const [msg, setMsg] = useState("");

  function reload() { fetchMailboxes().then(setBoxes).catch((e) => setMsg(String(e))); }
  useEffect(reload, []);

  async function add() {
    if (!form.email.trim() || !form.smtp_host.trim() || !form.password) { setMsg("邮箱、SMTP 服务器、密码必填"); return; }
    try {
      await createMailbox({ ...form, username: form.username || form.email });
      setForm({ ...BLANK }); setMsg("已添加发件邮箱"); reload();
    } catch (e) { setMsg("添加失败：" + String(e)); reload(); }
  }

  const [testing, setTesting] = useState<number | null>(null);
  async function test(b: Mailbox) {
    setTesting(b.id); setMsg(`正在登录 ${b.email} …`);
    try {
      const r = await testMailbox(b.id);
      setMsg(r.imap
        ? `✓ ${b.email} SMTP/IMAP 登录成功，可正常发信和同步回复`
        : `✓ ${b.email} SMTP 登录成功（只发信邮箱，未测 IMAP）—— 回复和退信要靠转发到能收信的邮箱`);
    }
    catch (e) { setMsg(`✗ ${b.email} ${String(e instanceof Error ? e.message : e)}`); }
    finally { setTesting(null); }
  }

  const totalCap = boxes.filter((b) => b.active).reduce((s, b) => s + Math.max(0, b.daily_cap - b.sent_today), 0);
  const set = (k: string, v: string | number) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h3>发件邮箱轮换（提升送达率）</h3>
      <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>
        单个邮箱群发几十封就容易被标记垃圾。配置多个发件邮箱后，群发会自动在它们之间轮流、各自遵守每日上限，摊薄风险。
        {boxes.length === 0
          ? " 当前未配置——群发仍走默认 Gmail（allenma2ong@gmail.com）。"
          : ` 当前 ${boxes.filter((b) => b.active).length} 个启用，今日剩余总额度 ${totalCap} 封。`}
        <br />Gmail 用应用专用密码：SMTP 服务器 smtp.gmail.com、端口 465。
      </div>

      {boxes.length > 0 && (
        <table className="lead-table" style={{ marginBottom: 12 }}>
          <thead><tr><th>邮箱</th><th>SMTP / IMAP</th><th>今日/上限</th><th>状态</th><th></th></tr></thead>
          <tbody>
            {boxes.map((b) => (
              <tr key={b.id}>
                <td>{b.email}</td>
                <td className="muted">
                  {b.smtp_host}:{b.port}<br />
                  {b.imap_enabled
                    ? `${b.imap_host || "未配置"}:${b.imap_port}`
                    : "只发信 · 不收信"}
                </td>
                <td className="num">{b.sent_today} / {b.daily_cap}</td>
                <td>
                  <button className={`btn btn-sm${b.active ? " btn-green" : ""}`}
                    onClick={() => setMailboxActive(b.id, !b.active).then(reload)}>
                    {b.active ? "启用中" : "已停用"}
                  </button>
                </td>
                <td>
                  <button className="btn btn-sm" style={{ marginRight: 6 }} disabled={testing === b.id} onClick={() => test(b)}
                    title="只登录不发信：同时验证 SMTP 发信与 IMAP 回复同步，避免发送或拉取回复时才发现配错">
                    {testing === b.id ? "测试中…" : "测试"}
                  </button>
                  <button className="btn btn-sm" onClick={() => deleteMailbox(b.id).then(reload)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <input className="input" placeholder="发件邮箱" value={form.email} onChange={(e) => set("email", e.target.value)} style={{ minWidth: 180 }} />
        <input className="input" placeholder="SMTP 服务器" value={form.smtp_host} onChange={(e) => set("smtp_host", e.target.value)} style={{ width: 150 }} />
        <input className="input" placeholder="端口" type="number" value={form.port} onChange={(e) => set("port", Number(e.target.value))} style={{ width: 80 }} />
        <input className="input" placeholder="IMAP（留空自动推断）" value={form.imap_host} onChange={(e) => set("imap_host", e.target.value)} style={{ width: 170 }} />
        <input className="input" placeholder="IMAP 端口" type="number" value={form.imap_port} onChange={(e) => set("imap_port", Number(e.target.value))} style={{ width: 95 }} />
        <input className="input" placeholder="用户名（默认同邮箱）" value={form.username} onChange={(e) => set("username", e.target.value)} style={{ width: 160 }} />
        <input className="input" placeholder="密码 / 应用专用码" type="password" value={form.password} onChange={(e) => set("password", e.target.value)} style={{ width: 160 }} />
        <input className="input" placeholder="日上限" type="number" value={form.daily_cap} onChange={(e) => set("daily_cap", Number(e.target.value))} style={{ width: 90 }} />
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
          title="勾上代表这个邮箱只负责发信，不去拉它的收件箱。适用于 SMTP 能用但 IMAP 未开通的邮箱（如 Zoho 免费版）——回复和退信要另配转发到一个能收信的邮箱。">
          <input type="checkbox" checked={!form.imap_enabled}
            onChange={(e) => setForm((f) => ({ ...f, imap_enabled: !e.target.checked }))} />
          只发信（不收信）
        </label>
        <button className="btn btn-primary" onClick={add}>添加</button>
      </div>
      {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
    </div>
  );
}
