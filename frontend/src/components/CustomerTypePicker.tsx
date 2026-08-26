// 客户类型：勾选为主，仍然可以自己输入新的。docs/60 R3
//
// 之前这里是一个逗号分隔的自由文本框。自由文本的代价是同一个类型长出好几种写法
// （工程商 / 工程商 / 工程 商），之后再也筛不干净。所以默认给选项，但不锁死——
// 锁死会逼着他在别的字段里凑合记，那比不规范更糟。
import { useEffect, useRef, useState } from "react";

const SEPARATORS = /[,，、;；]/;

export function splitTypes(raw: string | null | undefined): string[] {
  return String(raw ?? "").split(SEPARATORS).map((t) => t.trim()).filter(Boolean);
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
  const [query, setQuery] = useState("");
  const box = useRef<HTMLDivElement>(null);
  const picked = splitTypes(value);

  useEffect(() => {
    if (!open) return;
    function away(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  function toggle(type: string) {
    const next = picked.includes(type) ? picked.filter((t) => t !== type) : [...picked, type];
    onChange(joinTypes(next));
  }

  function addTyped() {
    const fresh = query.trim();
    if (!fresh || picked.includes(fresh)) { setQuery(""); return; }
    onChange(joinTypes([...picked, fresh]));
    setQuery("");
  }

  const shown = options.filter((o) => !query.trim() || o.includes(query.trim()));
  const isNew = query.trim() && !options.some((o) => o === query.trim());

  return (
    <div ref={box} style={{ position: "relative" }}>
      <div className="input" style={{ minHeight: 34, display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", cursor: "pointer" }}
        onClick={() => setOpen(true)}>
        {picked.length === 0 && <span className="muted" style={{ fontSize: 13 }}>点击选择客户类型</span>}
        {picked.map((t) => (
          <span key={t} className="tag-chip" onClick={(e) => { e.stopPropagation(); toggle(t); }}
            title="点击移除">{t} ✕</span>
        ))}
      </div>

      {open && (
        <div className="card" style={{ position: "absolute", zIndex: 30, left: 0, right: 0, marginTop: 4, padding: 8 }}>
          <input className="input" autoFocus value={query} placeholder="搜索，或直接输入新建类型"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTyped(); } }} />
          <div style={{ maxHeight: 220, overflowY: "auto", marginTop: 6 }}>
            {shown.map((o) => (
              <div key={o} onClick={() => toggle(o)}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                         padding: "6px 4px", cursor: "pointer" }}>
                <span className="tag-chip">{o}</span>
                {picked.includes(o) && <span style={{ color: "var(--accent)" }}>✓</span>}
              </div>
            ))}
            {isNew && (
              <div onClick={addTyped} style={{ padding: "6px 4px", cursor: "pointer" }}>
                <span className="muted" style={{ fontSize: 12 }}>新建类型：</span>
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
