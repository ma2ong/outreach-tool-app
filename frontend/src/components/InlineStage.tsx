// 阶段：平时是一枚徽章，鼠标移上去才提示可改，点了才变成下拉。docs/60
//
// 列表里几百行同时显示几百个 <select> 边框，读起来像表单不像名单。编辑要能一步到位，
// 但不该一直摆在那里。
import { useEffect, useRef, useState } from "react";
import { STAGE_LABEL } from "../types";

export function InlineStage({ value, onChange }: {
  value: string | null;
  onChange: (next: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [hover, setHover] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const stage = value || "new";

  useEffect(() => {
    if (!editing) return;
    function away(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) setEditing(false);
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [editing]);

  if (editing) {
    return (
      <div ref={box}>
        <select className="input" autoFocus style={{ fontSize: 12, padding: "2px 4px" }}
          value={stage}
          onChange={(e) => { onChange(e.target.value); setEditing(false); }}
          onBlur={() => setEditing(false)}>
          {Object.entries(STAGE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
    );
  }

  return (
    <div ref={box} onClick={() => setEditing(true)}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer",
               whiteSpace: "nowrap" }}
      title="点击修改阶段">
      <span className={`stage-badge stage-${stage}`}>{STAGE_LABEL[stage] ?? stage}</span>
      {/* 位置常驻，只切换可见性：让图标凭空出现会把徽章推一下，每次鼠标经过都抖 */}
      <span className="muted" style={{ fontSize: 12, width: 12, display: "inline-block",
                                       visibility: hover ? "visible" : "hidden" }}>✎</span>
    </div>
  );
}
