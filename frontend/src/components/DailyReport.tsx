// Agent 今日报告，按段落拆成「标签 + 值」的行。
//
// 报告本身是一段文本，因为它同时要发到 WhatsApp 和企业微信——那两个地方只能收文本，
// 所以文本是这份报告的唯一真相。这里不另建一个结构化接口去重复算一遍，而是就地把
// 「■ 段名 + 缩进行」拆开：格式变了，显示跟着变，不会出现两份对不上的报告。
//
// 排版跟 Agent 回答同一套：段名当左边的标签，内容跟在右边。日报是一眼扫完的东西，
// 卡片网格把六七段话撑成一屏，反而要人一格一格找。
import { useState } from "react";

type Section = { title: string; lines: string[]; bullets: string[] };

// 一眼要看到的那几段排在前面，其余按原顺序跟在后面。
const LEAD_SECTIONS = ["等你定的事", "客户那边的动静", "今天发出去的", "接下来"];

export function parseReport(text: string): { date: string; sections: Section[] } {
  const lines = (text || "").split("\n");
  // 标题行是「【2026-08-31 客户开发日报】」，只取日期——「客户开发日报」和上方的
  // 「今天做了什么」说的是同一件事，写两遍是噪音。
  const date = (lines[0]?.match(/【\s*([\d-]+)/)?.[1] ?? "").trim();
  const sections: Section[] = [];
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("■")) {
      sections.push({ title: line.replace("■", "").trim(), lines: [], bullets: [] });
      continue;
    }
    const body = line.trim();
    if (!body || sections.length === 0) continue;
    const current = sections[sections.length - 1];
    // 「· xxx」是上一行的明细，缩一级显示，不跟主行抢注意力。
    if (body.startsWith("·")) current.bullets.push(body.replace("·", "").trim());
    else current.lines.push(body);
  }
  const rank = (s: Section) => {
    const i = LEAD_SECTIONS.indexOf(s.title);
    return i === -1 ? LEAD_SECTIONS.length : i;
  };
  return { date, sections: sections.sort((a, b) => rank(a) - rank(b)) };
}

// 「没有」「没有真人回复」这类是空段：行留着（今天确实查过了），但不喊。
const isQuiet = (s: Section) =>
  s.lines.length === 0 || (s.lines.length === 1 && /^没有/.test(s.lines[0]));

function Row({ section }: { section: Section }) {
  const [open, setOpen] = useState(false);
  const quiet = isQuiet(section);
  // 「等你定的事」有内容时是今天唯一需要他动手的地方，标出来；其余一视同仁。
  const needsHim = section.title === "等你定的事" && !quiet;
  const shown = open ? section.bullets : section.bullets.slice(0, 3);
  return (
    <div style={{ display: "flex", gap: 10, fontSize: 13, padding: "3px 0",
                  opacity: quiet ? 0.65 : 1 }}>
      <span className="muted" style={{ flex: "none", width: 96 }}>
        {needsHim ? "⚠ " : ""}{section.title}
      </span>
      <div style={{ minWidth: 0 }}>
        {section.lines.length === 0 && <div className="muted">没有</div>}
        {section.lines.map((line, i) => (
          <div key={i} style={{ lineHeight: 1.55, color: needsHim ? "var(--warn)" : undefined }}>
            {line}
          </div>
        ))}
        {shown.map((b, i) => (
          <div key={i} className="muted" style={{ fontSize: 12, lineHeight: 1.5 }}>· {b}</div>
        ))}
        {section.bullets.length > 3 && (
          <button className="btn btn-sm" style={{ marginTop: 4 }} onClick={() => setOpen((v) => !v)}>
            {open ? "收起" : `还有 ${section.bullets.length - 3} 条`}
          </button>
        )}
      </div>
    </div>
  );
}

export function DailyReport({ text }: { text: string }) {
  const { date, sections } = parseReport(text);
  if (sections.length === 0) return null;
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
        <b style={{ fontSize: 14 }}>今天做了什么</b>
        <span className="muted" style={{ fontSize: 12 }}>{date}</span>
      </div>
      {sections.map((s) => <Row key={s.title} section={s} />)}
    </div>
  );
}
