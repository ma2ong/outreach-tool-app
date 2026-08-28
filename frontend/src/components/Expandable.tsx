import { useEffect, useRef, type ReactNode } from "react";

/** Elements that own their own click and must never also toggle the card around them. */
const INTERACTIVE = "button, a, input, select, textarea, label, [data-no-toggle]";

/**
 * A card you open by clicking it, anywhere.
 *
 * Allen's note: "所有这种需要点击展开的框框，都要加一个直接点击框内任意一个位置都能展开,
 * 不要让我点击右边的按钮". Hunting for a small button on the far right of a wide row is
 * work the interface was making him do for no reason — the whole row is the target.
 *
 * The header keeps whatever buttons it had; a click that lands on one of those is that
 * button's click and nothing else, so "open the lead" still opens the lead.
 */
export function ExpandableCard(
  { open, onToggle, header, children, style, className = "card" }: {
    open: boolean;
    onToggle: (next: boolean) => void;
    header: ReactNode;
    children?: ReactNode;
    style?: React.CSSProperties;
    className?: string;
  },
) {
  return (
    <div
      className={className}
      style={{ cursor: "pointer", ...style }}
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={(e) => {
        if ((e.target as HTMLElement).closest(INTERACTIVE)) return;
        onToggle(!open);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onToggle(!open); }
      }}
    >
      {header}
      {open && children}
    </div>
  );
}

/**
 * Close a popover by clicking anywhere outside it — "点击框外面任意位置就能直接关闭它".
 *
 * Escape closes it too: once a panel can be dismissed by clicking away, the keyboard
 * should agree, or the two ways of leaving it disagree about whether it is modal.
 *
 * `pointerdown` rather than `click`, so a press that starts outside closes immediately
 * instead of waiting for a release that may land somewhere else entirely.
 */
export function useDismissOnOutside<T extends HTMLElement>(
  active: boolean, onDismiss: () => void,
) {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    if (!active) return;
    const away = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onDismiss();
    };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onDismiss(); };
    // Capture phase: a child that stops propagation must not also trap the dismissal.
    document.addEventListener("pointerdown", away, true);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", away, true);
      document.removeEventListener("keydown", key);
    };
  }, [active, onDismiss]);
  return ref;
}

/**
 * The same behaviour for a card that already has its own markup: spread these onto the
 * outer element instead of restructuring it around `ExpandableCard`.
 *
 *   <div className="card" {...cardToggle(open, setOpen)}> … </div>
 */
export function cardToggle(open: boolean, onToggle: (next: boolean) => void) {
  return {
    role: "button",
    tabIndex: 0,
    "aria-expanded": open,
    onClick: (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest(INTERACTIVE)) return;
      onToggle(!open);
    },
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onToggle(!open); }
    },
  };
}
