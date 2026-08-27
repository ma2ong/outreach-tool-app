// 哪套话术真的管用，按读信的人拆开看。docs/69
//
// 在这之前只有一个数字："361 封 1 个回复"。它把四个市场、五种客户类型、三个步骤压在一起，
// 答不出任何一个真正的问题——开场白不行？名单不对？还是第三封在耗人？
import { useEffect, useState } from "react";

type Row = Record<string, string | number | null> & {
  sent: number; leads: number; replied: number; reply_rate: number;
};

type Report = {
  by: string[]; days: number; rows: Row[];
  unmeasured: number; dimensions: string[];
};

const LABEL: Record<string, string> = {
  variant: "话术", step: "第几封", audience: "客户类型", market: "市场", channel: "渠道",
};

const CUTS: { keys: string; label: string }[] = [
  { keys: "variant,market", label: "话术 × 市场" },
  { keys: "variant,audience", label: "话术 × 客户类型" },
  { keys: "variant,step", label: "话术 × 第几封" },
  { keys: "variant", label: "只看话术" },
];

export function CopyExperiments() {
  const [cut, setCut] = useState(CUTS[0].keys);
  const [report, setReport] = useState<Report | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetch(`/api/stats/copy-experiments?by=${encodeURIComponent(cut)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setReport)
      .catch((e) => setErr(String(e instanceof Error ? e.message : e)));
  }, [cut]);

  if (err) return <div className="error-text">话术战绩加载失败：{err}</div>;
  if (!report) return <div className="muted">读取中…</div>;

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <b style={{ fontSize: 13 }}>话术战绩</b>
        <span className="muted" style={{ fontSize: 12 }}>近 {report.days} 天</span>
        <select className="input" style={{ width: 160, fontSize: 12, padding: "2px 4px" }}
          value={cut} onChange={(e) => setCut(e.target.value)}>
          {CUTS.map((c) => <option key={c.keys} value={c.keys}>{c.label}</option>)}
        </select>
      </div>

      {report.rows.length === 0 ? (
        <div className="muted" style={{ fontSize: 12, marginTop: 8, lineHeight: 1.7 }}>
          还没有带记录的发送。从现在起每封信都会记下用的哪套话术、发给哪种客户、第几封，
          积累几天这张表就有内容了。
        </div>
      ) : (
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table className="table">
            <thead><tr>
              {report.by.map((k) => <th key={k}>{LABEL[k] ?? k}</th>)}
              <th>发出</th><th>客户数</th><th>回复</th><th>回复率</th>
            </tr></thead>
            <tbody>
              {report.rows.map((r, i) => (
                <tr key={i}>
                  {report.by.map((k) => (
                    <td key={k}>{k === "step" ? `第 ${Number(r[k] ?? 0) + 1} 封` : (r[k] ?? "—")}</td>
                  ))}
                  <td className="num">{r.sent}</td>
                  <td className="num">{r.leads}</td>
                  <td className="num">{r.replied}</td>
                  <td className="num" style={{ fontWeight: r.reply_rate > 0 ? 600 : undefined }}>
                    {r.reply_rate}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {report.unmeasured > 0 && (
        // 未计量不是 0：把它算进分母会让每一套话术看起来都更差
        <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
          另有 {report.unmeasured} 封是记录这些字段之前发的，无法归入任何一套话术，
          所以不计入上表——那是「没测量」，不是「效果为零」。
        </div>
      )}
    </div>
  );
}
