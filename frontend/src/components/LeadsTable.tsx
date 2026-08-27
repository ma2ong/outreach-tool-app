import { useEffect, useState } from "react";
import type { MouseEvent, ReactNode } from "react";
import type { Lead } from "../types";
import { fetchCustomerTypes, updateLead } from "../api";
import { CustomerTypePicker } from "./CustomerTypePicker";
import { InlineStage } from "./InlineStage";

// 只有韩语公司名值得占一行：他做的是韩国市场，韩语为主英语为辅。葡语、西语公司名和英文名
// 几乎一样（"LedWave" / "LedWave"），显示出来只是重复。docs/60 R1
const HANGUL = /[ᄀ-ᇿ㄰-㆏ꥠ-꥿가-힣]/;

const CHANNELS = [
  { key: "email", label: "Email" },
  { key: "whatsapp", label: "WA" },
  { key: "instagram", label: "IG" },
];

/** Pick the most WhatsApp-likely number out of a free-text phone field. */
export function waNumber(phone: string): string | null {
  const parts = phone.split(/[/;,]/);
  const best = parts.find((p) => /wa/i.test(p)) ?? parts.find((p) => p.includes("+")) ?? parts[0];
  const digits = (best.match(/\d/g) || []).join("");
  return digits.length >= 8 && digits.length <= 15 ? digits : null;
}

function igUrl(handle: string): string {
  const h = handle.replace(/^@/, "");
  return h.includes("instagram.com") ? `https://${h.replace(/^https?:\/\//, "")}` : `https://instagram.com/${h}`;
}

function fbUrl(page: string): string {
  return page.includes("facebook.com") ? `https://${page.replace(/^https?:\/\//, "")}` : `https://facebook.com/${page}`;
}

function channelState(l: Lead, channel: string): "replied" | "messaged" | "untouched" {
  const o = l.outreach.find((x) => x.channel === channel);
  if (!o) return "untouched";
  if (o.status === "replied") return "replied";
  if (o.status === "messaged") return "messaged";
  return "untouched";
}

const STATE_TEXT = { replied: "已回复", messaged: "已触达", untouched: "未触达" } as const;

export function LeadsTable({ leads, selected, onToggle, onToggleAll, onReply, onOpen, sort, order, onSort, onChanged }: {
  leads: Lead[]; selected: Set<number>;
  onToggle: (no: number) => void; onToggleAll: (checked: boolean) => void;
  onReply: (no: number, channel: string) => void; onOpen: (l: Lead) => void;
  sort: string; order: string; onSort: (col: string) => void;
  onChanged?: () => void;
}) {
  const [typeOptions, setTypeOptions] = useState<string[]>([]);
  // 就地改过的值先记在本地：列表刷新是异步的，中间那一秒不该显示旧值
  const [patched, setPatched] = useState<Record<number, Partial<Lead>>>({});
  useEffect(() => {
    fetchCustomerTypes().then((r) => setTypeOptions(r.options)).catch(() => setTypeOptions([]));
  }, []);

  async function save(no: number, fields: Partial<Lead>) {
    setPatched((p) => ({ ...p, [no]: { ...p[no], ...fields } }));
    try {
      await updateLead(no, fields);
      onChanged?.();
    } catch {
      // 存不上就把本地那份撤掉，不要让界面显示一个其实没保存的值
      setPatched((p) => { const next = { ...p }; delete next[no]; return next; });
    }
  }

  const allChecked = leads.length > 0 && leads.every((l) => selected.has(l.no));
  const row = (l: Lead): Lead => ({ ...l, ...(patched[l.no] ?? {}) });
  const stop = (e: MouseEvent) => e.stopPropagation();
  const arrow = (col: string) => (sort === col ? (order === "asc" ? " ▲" : " ▼") : "");
  const Sortable = ({ col, children }: { col: string; children: ReactNode }) => (
    <th onClick={() => onSort(col)} style={{ cursor: "pointer", userSelect: "none" }} title="点击排序">
      {children}{arrow(col)}
    </th>
  );
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr>
          <th><input type="checkbox" checked={allChecked} onChange={(e) => onToggleAll(e.target.checked)} /></th>
          <Sortable col="no">#</Sortable><Sortable col="company_en">公司</Sortable>
          <Sortable col="stage">阶段</Sortable>
          <Sortable col="fit">客户类型</Sortable>
          <th>客户名称</th>
          <Sortable col="country">国家</Sortable>
          <th>邮箱</th><th>电话 / WhatsApp</th><th>IG</th><th>FB</th><th>渠道状态</th>
        </tr></thead>
        <tbody>
          {leads.map((l) => {
            const wa = l.phone ? waNumber(l.phone) : null;
            return (
              <tr key={l.no} onClick={() => onOpen(l)} style={{ cursor: "pointer" }}>
                <td onClick={stop}><input type="checkbox" checked={selected.has(l.no)} onChange={() => onToggle(l.no)} /></td>
                <td className="num muted">{l.no}</td>
                <td>
                  <div>{l.company_en}</div>
                  {/* 韩语名与英文名同等字号：他读的是韩文那一行 */}
                  {l.company_local && l.company_local !== l.company_en
                    && HANGUL.test(l.company_local) &&
                    <div>{l.company_local}</div>}
                </td>
                <td onClick={stop} style={{ whiteSpace: "nowrap" }}>
                  <InlineStage value={row(l).stage} onChange={(s) => save(l.no, { stage: s })} />
                </td>
                <td onClick={stop} style={{ minWidth: 150 }}>
                  <CustomerTypePicker value={row(l).tags ?? ""} options={typeOptions}
                    onChange={(next) => save(l.no, { tags: next })} />
                  {/* 他没标类型时，才退回系统推断的那一个 */}
                  {!row(l).tags && l.target_fit && l.target_fit !== "discovered" &&
                    <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>系统推断：{l.target_fit}</div>}
                </td>
                <td>{l.primary_contact
                  ? <>
                      <div>{l.primary_contact}</div>
                      {l.primary_title && <div className="muted" style={{ fontSize: 12 }}>{l.primary_title}</div>}
                    </>
                  : <span className="muted">—</span>}</td>
                <td>{l.country}</td>
                <td onClick={stop}>{l.email
                  ? <>
                      <a href={`mailto:${l.email}`}>{l.email}</a>
                      {l.email_status === "invalid" && <span title="邮箱无效（无 MX 记录），发送时自动跳过" style={{ color: "var(--warn)", marginLeft: 6, fontSize: 11 }}>⚠ 无效</span>}
                      {l.email_status === "role" && <span title="角色邮箱（info@/sales@ 等），可发但优先级较低" className="muted" style={{ marginLeft: 6, fontSize: 11 }}>角色</span>}
                    </>
                  : <span className="muted">—</span>}</td>
                <td className="num" onClick={stop}>{l.phone
                  ? (wa
                    ? <a href={`https://wa.me/${wa}`} target="_blank" rel="noreferrer"
                        title="点击打开 WhatsApp 对话" style={{ color: "var(--green)" }}>
                        {l.phone}{l.whatsapp_verified ? " ✓" : ""}
                      </a>
                    : l.phone)
                  : <span className="muted">—</span>}</td>
                <td onClick={stop}>{l.instagram
                  ? <a href={igUrl(l.instagram)} target="_blank" rel="noreferrer">@{l.instagram.replace(/^@/, "")}</a>
                  : <span className="muted">—</span>}</td>
                <td onClick={stop}>{l.facebook
                  ? <a href={fbUrl(l.facebook)} target="_blank" rel="noreferrer">{l.facebook.replace(/^https?:\/\/(www\.)?facebook\.com\//, "")}</a>
                  : <span className="muted">—</span>}</td>
                <td onClick={stop}>
                  {CHANNELS.map(({ key, label }) => {
                    const st = channelState(l, key);
                    const clickable = st === "messaged";
                    return (
                      <span key={key}
                        className={`badge badge-${st}${clickable ? " clickable" : ""}`}
                        style={{ marginRight: 4 }}
                        onClick={clickable ? () => onReply(l.no, key) : undefined}
                        title={clickable ? `${label} 已触达 — 点击标记为已回复` : `${label} ${STATE_TEXT[st]}`}>
                        <i />{label}
                      </span>
                    );
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
