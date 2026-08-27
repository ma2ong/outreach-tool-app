// 客户类型：平时只是几个标签，鼠标移上去才出现编辑图标，点开才能改。docs/60 R3
//
// 之前这里是一个带边框的输入框，每个标签后面永远挂着一个 ✕。列表里几百行同时显示几百个
// 输入框和删除按钮，读起来像一张表单而不是一份名单，而且 ✕ 就在指针路过的地方——误删只是
// 时间问题。所以改成：默认只显示内容，编辑是一个要主动进入的状态。
import { useEffect, useRef, useState } from "react";

const SEPARATORS = /[,，、;；]/;
// 分类器把自己的中间产物写进同一列（icp:rental 有 191 条）。它不是客户类型，不该显示，
// 但也不能因为没显示就在保存时被抹掉。docs/60 R2.1
const MACHINE = /^(icp|auto|sys):/i;

export function splitTypes(raw: string | null | undefined): string[] {
  return String(raw ?? "").split(SEPARATORS).map((t) => t.trim()).filter(Boolean);
}

function humanTypes(raw: string | null | undefined): string[] {
  return splitTypes(raw).filter((t) => !MACHINE.test(t));
}

function machineTags(raw: string | null | undefined): string[] {
  return splitTypes(raw).filter((t) => MACHINE.test(t));
}

export function joinTypes(types: string[]): string {
  return types.join(",");
}

export function CustomerTypePicker({ value, options, onChange }: {
  value: string | null;
  options: string[];
  onChange: (next: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState(false);
  const [query, setQuery] = useState("");
  const box = useRef<HTMLDivElement>(null);
  const picked = humanTypes(value);
  // 写回时把没显示的机器标记接在后面：界面不显示它，不等于可以删掉它
  const commit = (types: string[]) => onChange(joinTypes([...types, ...machineTags(value)]));

  useEffect(() => {
    if (!open) return;
    function away(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) { setOpen(false); setQuery(""); }
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  function toggle(type: string) {
    commit(picked.includes(type) ? picked.filter((t) => t !== type) : [...picked, type]);
  }

  function addTyped() {
    const fresh = query.trim();
    if (!fresh || picked.includes(fresh)) { setQuery(""); return; }
    commit([...picked, fresh]);
    setQuery("");
  }

  const shown = options.filter((o) => !query.trim() || o.includes(query.trim()));
  const isNew = query.trim() && !options.some((o) => o === query.trim());

  return (
    <div ref={box} style={{ position: "relative" }}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <div onClick={() => setOpen(true)}
        style={{ display: "flex", flexWrap: "wrap", gap: 5, alignItems: "center",
                 minHeight: 22, cursor: "pointer" }}>
        {picked.map((t) => (
          // ✕ 只在编辑态出现：平时这里是一份名单，不是一排删除按钮
          <span key={t} className="tag-chip"
            onClick={open ? (e) => { e.stopPropagation(); toggle(t); } : undefined}
            title={open ? "点击移除" : undefined}>
            {t}{open && " ✕"}
          </span>
        ))}
        {picked.length === 0 && <span className="muted">—</span>}
        {/* 图标位置常驻，只切换可见性：凭空出现会把标签推一下，鼠标每次经过都抖 */}
        <span className="muted" style={{ fontSize: 12, width: 12, display: "inline-block",
                                         visibility: hover && !open ? "visible" : "hidden" }}>✎</span>
      </div>

      {open && (
        <div className="card" style={{ position: "absolute", zIndex: 30, left: 0, minWidth: 200,
                                       marginTop: 4, padding: 8 }}>
          <input className="input" autoFocus value={query} placeholder="搜索，或直接输入新建类型"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTyped(); } }} />
          <div style={{ maxHeight: 220, overflowY: "auto", marginTop: 6 }}>
            {shown.map((o) => (
              <div key={o} onClick={() => toggle(o)}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                         padding: "5px 4px", cursor: "pointer" }}>
                <span className="tag-chip">{o}</span>
                {picked.includes(o) && <span style={{ color: "var(--accent)" }}>✓</span>}
              </div>
            ))}
            {isNew && (
              <div onClick={addTyped} style={{ padding: "5px 4px", cursor: "pointer" }}>
                <span className="muted" style={{ fontSize: 12 }}>新建：</span>
                <span className="tag-chip">{query.trim()}</span>
              </div>
            )}
            {shown.length === 0 && !isNew && <div className="muted" style={{ padding: 6 }}>没有匹配的类型</div>}
          </div>
        </div>
      )}
    </div>
  );
}
