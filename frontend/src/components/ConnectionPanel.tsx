import { useEffect, useState } from "react";
import { fetchChannels, connectChannel, channelStatus } from "../api";

const LABELS: Record<string, string> = { whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook" };

export function ConnectionPanel() {
  const [status, setStatus] = useState<Record<string, string>>({});
  const [active, setActive] = useState<string | null>(null);
  const [qrTick, setQrTick] = useState(0);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetchChannels().then(setStatus).catch((e) => setErr(`渠道状态加载失败：${String(e)}`));
  }, []);

  useEffect(() => {
    if (!active) return;
    const t = setInterval(async () => {
      try {
        const { status: st, error } = await channelStatus(active);
        setStatus((s) => ({ ...s, [active]: st }));
        setQrTick((n) => n + 1);
        // The launch happens after the connect call returned, so its failure arrives here.
        if (error) { setErr(error); clearInterval(t); setActive(null); return; }
        if (st === "connected") { clearInterval(t); setActive(null); setErr(""); }
      } catch (e) {
        setErr(`无法检查 ${LABELS[active]} 状态：${String(e)}`);
      }
    }, 3000);
    return () => clearInterval(t);
  }, [active]);

  async function connect(ch: string) {
    setErr("");
    setStatus((s) => ({ ...s, [ch]: "connecting" }));
    setActive(ch);
    try { await connectChannel(ch); }
    catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      setStatus((s) => ({ ...s, [ch]: "disconnected" }));
      setActive(null);
    }
  }

  const dot = (st: string) => st === "connected" ? "var(--green)" : st === "connecting" ? "var(--warn)" : "var(--gray)";
  return (
    <div className="card">
      <h3>渠道连接</h3>
      <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>
        服务每次重启后这里都显示「未检查」——登录其实还在。点一下「检查/连接」，若登录仍有效会在几秒内自动变「已连接」，不需要重新登录。
      </div>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
        {Object.keys(LABELS).map((ch) => (
          <div key={ch}>
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: dot(status[ch] || "disconnected"), marginRight: 6 }} />
            {LABELS[ch]}：{status[ch] === "connected" ? "已连接" : status[ch] === "connecting" ? "等待登录…" : "未检查"}
            {status[ch] !== "connected" && (
              <button className="btn btn-primary btn-sm" style={{ marginLeft: 10 }} onClick={() => connect(ch)}>检查/连接</button>
            )}
          </div>
        ))}
      </div>
      {err && <div className="error-text" style={{ marginTop: 10 }}>{err}</div>}
      {active === "whatsapp" && status.whatsapp === "connecting" && (
        <div style={{ marginTop: 14 }}>
          <div style={{ marginBottom: 6 }}>用手机 WhatsApp 扫描下方二维码登录（登录一次长期保持）：</div>
          <img alt="WhatsApp QR" src={`/api/channels/whatsapp/qr?t=${qrTick}`} style={{ width: 260, height: 260, background: "#fff", borderRadius: 8 }} />
        </div>
      )}
      {(active === "instagram" || active === "facebook") && status[active] === "connecting" && (
        <div className="muted" style={{ marginTop: 14 }}>
          已打开 {LABELS[active]} 窗口。如果里面已经是登录状态，几秒后会自动变「已连接」，你什么都不用做；
          如果显示登录页，请在那个窗口里登录（含验证码），登录后状态自动更新。
        </div>
      )}
    </div>
  );
}
