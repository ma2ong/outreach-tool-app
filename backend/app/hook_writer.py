"""开场白引用客户自己的话，引不出就退回通用的那句（docs/93）。

354 封首封里只有 3 封说了一句只对那一家成立的话；239 封（67%）说的是类目
——「看到你们做租赁」，这句话对韩国那 300 家里的任何一家都成立。收信的人一天收五封
深圳来的信，他不是没看见，他看见了，然后认出这是那一类信。

`brief.py` 开头拒绝推断的理由没有过期：一句自信的编造发出去，客户知道那不是真的，
整封信从那句起就像机器写的。所以这里给模型的不是自由，是一条硬约束——

**它必须把话的出处交出来，而出处要逐字对得上抓到的页面正文。**

校验是机械的，不是承诺。docs/78 那张 Cloudflare 反爬页就是靠「自称有依据」被读成
一家 85 分集成商的。子串比对是这个模块里唯一不能省的一行。

失败永远向下退，不向上抛：模型的 → 正则的（`brief.build`）→ 通用的（docs/85）。
docs/80 R2 的理由没有变——没有开场白不是不发信的理由。
"""
from __future__ import annotations

import datetime as dt
import re

from app.agent import llm

MIN_QUOTE_CHARS = 12
# 한글/中文 一个字承载的信息比一个拉丁字母多得多，同样长度的门槛会把
# 「송파 지하주차장 LED 방향표지판」这种真正有内容的短语挡在外面。
MIN_QUOTE_CHARS_CJK = 6
MAX_WORDS_EN = 20
MAX_CHARS_KO = 40

_HANGUL = re.compile(r"[가-힣]")
_CJK = re.compile(r"[一-鿿]")
_ENDS = (".", "!", "?", "。", "！", "？")

# 一句夸奖既没有出处，也正好是「机器写的」那个味道。
_PRAISE = re.compile(
    r"\b(leading|leader|professional|impressive|excellent|renowned|prestigious|"
    r"outstanding|world[- ]class|top|best|premier|innovative)\b"
    r"|훌륭|최고|선도|유명", re.I)

SYSTEM = """You write the single opening line of a cold B2B email to an LED display buyer.

You are given one company's own web pages. Find one concrete thing the page says this
company has done or has — a named project, a venue, a client, a product line, a spec —
and write ONE SENTENCE that tells them you saw it.

Hard rules:
- The hook is a sentence YOU write, addressed to them. It is NOT the page text pasted
  back. A label, a heading, a product code or a registration number is not a sentence.
- `hook` is always ENGLISH, one sentence, at most 20 words, ending in a full stop —
  even when the page is Korean. The English letter uses this line.
- `hook_ko` is Korean, one sentence, at most 40 characters, ending in a full stop. Fill
  it only when the page is Korean; the Korean letter uses this line instead.
- `quote` is the fragment of the page the fact came from, copied character for
  character. It is evidence, not the hook.
- Never a compliment and never an adjective about them ("leading", "professional").
  Never our products, our specs or any price.
- If the page says nothing concrete about this company, return an empty hook. That is a
  correct answer.

Good:  quote "we supplied the main scoreboard at Estadio Nacional"
       hook  "Saw the scoreboard you installed at Estadio Nacional."
Bad:   hook  "we supplied the main scoreboard at Estadio Nacional"   (pasted, not written)
Bad:   hook  "Samsung official B2B dealer : Comolab (1466869)"       (a label, not a sentence)

Return JSON: {"hook": "...", "hook_ko": "...", "quote": "...", "source_url": "..."}"""


def ensure_schema(conn) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(leads)")}
    for name in ("hook_ko", "hook_quote", "hook_source_url", "hook_at"):
        if name not in cols:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {name} TEXT")
    conn.commit()


# jina 交回来的是 markdown：页面上写着 **CMS 구축 및 운영 유지보수**，人眼看到的和
# 模型引回来的都是没有星号的那一版。比对前把这些排版字符去掉，比的才是同一段文字。
# 这不是放宽「必须在页面上」，是让比对看见和人一样的东西。
_MARKUP = re.compile(r"[*_`#>|~\[\]]+")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", _MARKUP.sub(" ", str(text or ""))).strip().lower()


def quoted_from(quote: str, page_text: str) -> bool:
    """出处是不是页面上真有的一句话。归一化空白后逐字比对，短到没有信息量的不算。"""
    flat = _flat(quote)
    floor = MIN_QUOTE_CHARS_CJK if (_HANGUL.search(flat) or _CJK.search(flat))         else MIN_QUOTE_CHARS
    return len(flat) >= floor and flat in _flat(page_text)


def rejected(hook: str, korean: bool = False, quote: str = "") -> str:
    """开场白不合规的理由，合规则返回空字符串。

    试跑第一轮模型把引文原样交了回来（「삼성전자 공식 B2B 대리점 : 코모랩 (1466869)」
    同时出现在 hook、hook_ko 和 quote 三个字段里）。那是页面上的一个标签，不是一句话，
    而且它落进英文信里就是一句韩文。三条检查各挡一个。
    """
    line = str(hook or "").strip()
    if not line:
        return "空"
    if _PRAISE.search(line):
        return "是评价不是事实"
    if not line.endswith(_ENDS):
        return "不是一句话"
    # 句末标点是模型加的，比对时先去掉 —— 否则「原文 + 一个句号」就绕过了这条。
    flat = _flat(line).rstrip(".!?。！？")
    if quote and flat and flat in _flat(quote):
        return "把原文原样抄了回来"
    if korean:
        if len(line) > MAX_CHARS_KO:
            return f"韩语超过 {MAX_CHARS_KO} 字"
        if not _HANGUL.search(line):
            return "韩语档位里没有韩文"
    else:
        if len(line.split()) > MAX_WORDS_EN:
            return f"超过 {MAX_WORDS_EN} 个词"
        if _HANGUL.search(line) or _CJK.search(line):
            return "英文档位里混着非英文"
    return ""


def _is_korean(lead: dict) -> bool:
    return str(lead.get("country") or "").strip().lower() in {
        "south korea", "korea", "republic of korea", "대한민국"}


def improve(conn, lead: dict, page_text: str, source_url: str) -> dict | None:
    """给这家公司写一句引用得出的开场白。写不出就返回 None，绝不改动已有的 hook。"""
    if not str(page_text or "").strip():
        return None
    ensure_schema(conn)
    korean = _is_korean(lead)
    user = (f"company: {lead.get('company_en') or ''}\n"
            f"source_url: {source_url}\n"
            f"korean_market: {'yes' if korean else 'no'}\n"
            f"page text:\n{str(page_text)[:6000]}")
    try:
        data = llm.complete_json(conn, "hook", SYSTEM, user)
    except Exception:  # noqa: BLE001 — 模型的任何失败都只是「没有更好的开场白」
        return None

    hook = str(data.get("hook") or "").strip()
    quote = str(data.get("quote") or "").strip()
    if rejected(hook, quote=quote) or not quoted_from(quote, page_text):
        return None

    hook_ko = str(data.get("hook_ko") or "").strip()
    if korean:
        # 韩语信用的是这一句。它不合规就整条作废——半句韩语比没有更糟。
        if rejected(hook_ko, korean=True, quote=quote):
            return None
    else:
        hook_ko = ""

    now = dt.datetime.now(dt.UTC).isoformat()
    conn.execute(
        "UPDATE leads SET hook=?, hook_ko=?, hook_quote=?, hook_source_url=?, hook_at=?"
        " WHERE no=?",
        (hook, hook_ko, quote[:500], source_url[:500], now, lead["no"]))
    conn.commit()
    return {"hook": hook, "hook_ko": hook_ko, "quote": quote, "source_url": source_url}
