// 客户类型只负责外发路由：Rental / Install / General。
// 历史中文标签在界面上自动折叠到三类；机器标签和其他业务标签继续保留，但不混进客户类型。
import { useEffect, useRef, useState } from "react";

const SEPARATORS = /[,，、;；]/;
const MACHINE = /^(icp|auto|sys):/i;
const TYPES = ["Rental", "Install", "General"] as const;

const ALIASES: Record<string, (typeof TYPES)[number]> = {
  rental: "Rental",
  "租赁商": "Rental",
  "租赁客户": "Rental",
  install: "Install",
  "工程商": "Install",
  "系统集成商": "Install",
  general: "General",
  "批发商": "General",
  "代理商": "General",
  "广告商": "General",
  outdoor: "General",
  "户外": "General",
  "户外为主": "General",
};

export function splitTypes(raw: string | null | undefined): string[] {
  return String(raw ?? "").split(SEPARATORS).map((t) => t.trim()).filter(Boolean);
}

function canonicalType(tag: string): (typeof TYPES)[number] | null {
  return ALIASES[tag] ?? ALIASES[tag.toLowerCase()] ?? null;
}

function selectedType(raw: string | null | undefined): (typeof TYPES)[number] | null {
  const found = new Set(
    splitTypes(raw)
      .filter((t) => !MACHINE.test(t))
      .map(canonicalType)
      .filter((t): t is (typeof TYPES)[number] => Boolean(t)),
  );
  if (found.has("General") || (found.has("Rental") && found.has("Install"))) return "General";
  if (found.has("Rental")) return "Rental";
  if (found.has("Install")) return "Install";
  return null;
}

// Keep everything that is not a customer-type label. Saving the picker must never erase
// classifier provenance (icp:*) or unrelated tags living in the same legacy column.
function preservedTags(raw: string | null | undefined): string[] {
  return splitTypes(raw).filter((t) => MACHINE.test(t) || canonicalType(t) === null);
}

export function joinTypes(types: string[]): string {
  return types.join(",");
}

export function CustomerTypePicker({ value, onChange }: {
  value: string | null;
  options: string[];
  onChange: (next: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const picked = selectedType(value);

  useEffect(() => {
    if (!open) return;
    function away(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  function choose(type: (typeof TYPES)[number]) {
    onChange(joinTypes([type, ...preservedTags(value)]));
    setOpen(false);
  }

  function clear() {
    onChange(joinTypes(preservedTags(value)));
    setOpen(false);
  }

  return (
    <div ref={box} style={{ position: "relative" }}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <div onClick={() => setOpen(true)}
        style={{ display: "flex", alignItems: "center", gap: 5, minHeight: 22, cursor: "pointer" }}>
        {picked ? <span className="tag-chip">{picked}</span> : <span className="muted">—</span>}
        <span className="muted" style={{ fontSize: 12, visibility: hover && !open ? "visible" : "hidden" }}>✎</span>
      </div>

      {open && (
        <div className="card" style={{ position: "absolute", zIndex: 30, left: 0, minWidth: 160,
                                       marginTop: 4, padding: 8 }}>
          {TYPES.map((type) => (
            <div key={type} onClick={() => choose(type)}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                       padding: "6px 4px", cursor: "pointer" }}>
              <span className="tag-chip">{type}</span>
              {picked === type && <span style={{ color: "var(--accent)" }}>✓</span>}
            </div>
          ))}
          {picked && (
            <div onClick={clear} className="muted"
              style={{ borderTop: "1px solid var(--border)", marginTop: 5, padding: "7px 4px 2px",
                       cursor: "pointer", fontSize: 12 }}>
              清除分类
            </div>
          )}
        </div>
      )}
    </div>
  );
}
