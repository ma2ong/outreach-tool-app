// 分页：总数、页码、每页条数、跳至第几页。
//
// 原来只有「← 上一页  第 3 / 27 页  下一页 →」。27 页的名单里想回到第 1 页要点 26 次，
// 想去第 20 页只能一路点过去。页码直接可点，是这里唯一重要的事。
import { useState } from "react";

const SIZES = [20, 50, 100, 200];

/** 当前页附近的页码 + 首尾，中间用省略号。1 … 4 5 [6] 7 8 … 27 */
export function pageNumbers(current: number, count: number, span = 2): (number | "…")[] {
  if (count <= 7) return Array.from({ length: count }, (_, i) => i + 1);
  const out: (number | "…")[] = [1];
  const from = Math.max(2, current - span);
  const to = Math.min(count - 1, current + span);
  if (from > 2) out.push("…");
  for (let p = from; p <= to; p++) out.push(p);
  if (to < count - 1) out.push("…");
  out.push(count);
  return out;
}

export function Pager({ page, pageCount, total, pageSize, onPage, onPageSize }: {
  page: number;            // 0 起
  pageCount: number;
  total: number;
  pageSize: number;
  onPage: (next: number) => void;
  onPageSize: (next: number) => void;
}) {
  const [jump, setJump] = useState("");
  const current = page + 1;

  function go() {
    const wanted = Number(jump.trim());
    // 页码之外的数字什么都不做：跳到一个不存在的页，比留在原地更让人困惑
    if (!Number.isInteger(wanted) || wanted < 1 || wanted > pageCount) { setJump(""); return; }
    onPage(wanted - 1);
    setJump("");
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
      <span className="muted">共 {total} 条</span>

      <button className="btn btn-sm" disabled={page <= 0} onClick={() => onPage(page - 1)}>‹</button>
      {pageNumbers(current, pageCount).map((p, i) =>
        p === "…"
          ? <span key={`gap${i}`} className="muted" style={{ padding: "0 2px" }}>…</span>
          : <button key={p} className={p === current ? "btn btn-sm btn-primary" : "btn btn-sm"}
              onClick={() => onPage(p - 1)}>{p}</button>)}
      <button className="btn btn-sm" disabled={page + 1 >= pageCount}
        onClick={() => onPage(page + 1)}>›</button>

      <select className="input" style={{ width: 100, fontSize: 12, padding: "2px 4px" }}
        value={pageSize} onChange={(e) => onPageSize(Number(e.target.value))}>
        {SIZES.map((s) => <option key={s} value={s}>{s} 条/页</option>)}
      </select>

      <span className="muted" style={{ marginLeft: 4 }}>跳至</span>
      <input className="input" style={{ width: 56, fontSize: 12, padding: "2px 4px" }}
        value={jump} onChange={(e) => setJump(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); go(); } }}
        onBlur={go} />
      <span className="muted">页</span>
    </div>
  );
}
