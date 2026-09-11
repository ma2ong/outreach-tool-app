"""ICP classification: what kind of LED buyer is this company, and how good a fit?

Classifies a company from its website text into a buyer type and a 0-100 fit score
so the rep works the highest-value prospects first. Categories reflect how LED
display buyers actually differ in value to a manufacturer:

- rental      : event/staging companies — buy repeatedly, price-driven, best fit
- integrator  : AV/system integrators — project pipelines, recurring, best fit
- reseller    : distributors/wholesalers of displays — volume, strong fit
- signage     : sign makers/digital signage cos — regular panel demand, strong fit
- end-user    : venues/retail/churches buying for themselves — one-off, medium
- unknown     : no signal found

Scoring: base score per matched category (weights below) + small bonus per extra
distinct keyword hit (capped). Text matching is case-insensitive substring — the
input is jina-fetched page markdown.
"""
import re

# category -> (base_score, keywords). First matched category (by score desc) wins the label;
# keywords deliberately include common Spanish/Portuguese variants for LatAm sites.
_CATEGORIES: dict[str, tuple[int, tuple[str, ...]]] = {
    "rental": (90, (
        "rental", "staging", "event production", "stage rental", "av rental",
        "concert", "festival", "touring",
        # es/pt: alquiler(ES) / renta(MX) / arriendo(CL) / locação(BR)
        "alquiler", "renta de pantallas", "arriendo", "locação", "locacao", "eventos",
        # ko: 렌탈/대여/임대 = rental/lease. 무대(stage), 행사(event) and 공연(performance)
        # were tried and taken back out: they describe a project, not a business model,
        # and an integrator's case studies are full of them. 공연 alone was enough to file
        # winmedi.co.kr — a 통합배선/통합제어 house — as a rental company.
        "렌탈", "대여", "임대",
    )),
    "integrator": (85, (
        "av integrat", "system integrat", "audiovisual integrat", "integration services",
        "installation services", "audio visual solutions", "av solutions", "integrador",
        "instalación de pantallas", "instalacion de pantallas", "instalação de painéis",
        # ko: this category had no Korean at all, which is why Korean integrators — the
        # 시공/통합제어 companies — all came back unknown. 시공 = installation work,
        # 통합제어 = integrated control, 통합배선 = structured cabling, 영상시스템 = video system.
        "시공", "통합제어", "통합배선", "영상시스템", "음향영상",
    )),
    "reseller": (80, (
        "distributor", "wholesale", "reseller", "supplier of led", "led screen supplier",
        "we supply", "dealer", "distribuidor", "mayorista", "atacado",
        "venta de pantallas", "venda de painéis", "venda de paineis",
        # ko: 대리점=dealer, 유통=distribution, 총판=general distributor, 납품=supply.
        # 제조/생산 (manufacture) stays out on purpose — that is a competitor, not a buyer.
        "대리점", "유통", "총판", "납품",
    )),
    "signage": (75, (
        "signage", "sign company", "sign shop", "billboard", "custom signs",
        "digital sign", "led sign", "letreros", "rotulos", "comunicação visual",
        "publicidad exterior", "painel de led", "painéis de led",
        # ko: 전광판 = LED sign board (the dominant Korean term), 옥외광고 = outdoor
        # advertising, 미디어월 = media wall
        "전광판", "사이니지", "옥외광고", "미디어월",
    )),
    "end-user": (50, (
        "our venue", "our church", "our stadium", "our store", "retail chain",
        "shopping mall", "casino", "house of worship",
    )),
}

_BONUS_PER_HIT = 2
_BONUS_CAP = 10

_LABELS = {"rental": "租赁公司", "integrator": "AV集成商", "reseller": "经销商",
           "signage": "标识/广告牌", "end-user": "终端用户", "unknown": "未知"}


def classify_text(text: str) -> dict:
    """Return {icp_type, fit_score, hits} for a page text."""
    low = (text or "").lower()
    best_type, best_score, best_hits = "unknown", 0, []
    for cat, (base, keywords) in _CATEGORIES.items():
        hits = [k for k in keywords if k in low]
        if not hits:
            continue
        score = min(100, base + min(_BONUS_CAP, _BONUS_PER_HIT * (len(hits) - 1)))
        if score > best_score:
            best_type, best_score, best_hits = cat, score, hits
    return {"icp_type": best_type, "fit_score": best_score, "hits": best_hits}


def label(icp_type: str) -> str:
    return _LABELS.get(icp_type, icp_type)


_TAG_RE = re.compile(r"^icp:", re.I)

# docs/112 R2. 这门生意写在纸上的样子。库里关于一家公司的全部文字里一个都没出现过，
# 就是「我们手里没有任何一句话说这家跟屏有关」—— 那不是「不是客户」的证明，
# 是「不知道是不是客户」的证明。
#
# 三个词故意不在表里：
#   `av`   —— 葡语/西语地址里的 "Av. Paulista" 就是它，一条街名会让农产品出口商变成同行；
#   `sign` —— 网页上的 "Sign up" 到处都是；只收 signage / sign company 这类真说明行当的；
#   `stage`—— 保留，因为一家搭台的公司确实在这门生意的边上（docs/112 R5 的 Amos）。
_TRADE_WORDS = (
    r"led|display|displays|screen|screens|panel|panels|video ?wall|videowall|"
    r"signage|sign (?:company|shop|maker)|signboard|billboard|marquee|scoreboard|"
    r"projector|projection|kiosk|rental|rentals|renting|staging|stage|"
    r"event|events|concert|festival|touring|exhibition|expo|booth|"
    r"audio ?visual|integrator|integration|broadcast|dooh"
)
TRADE_RE = re.compile(
    rf"\b(?:{_TRADE_WORDS})\b|"
    r"pantalla|pantallas|painel|pain[eé]is|letrero|letreros|r[oó]tulo|alquiler|loca[cç][aã]o|"
    r"evento|eventos|palco|"
    r"전광판|디스플레이|사이니지|렌탈|대여|무대|행사|"
    r"显示屏|大屏|屏幕|广告牌|舞台|租赁|标识",
    re.I)

# 客户类别本身也是证据：判成「租赁公司 (90)」的公司，它的类别标签里就写着这一行。
_EVIDENCE_FIELDS = ("company_en", "company_local", "brief", "hook", "business",
                    "website", "tags", "target_fit")


def evidence_text(lead) -> str:
    """这家公司在库里的全部文字，接成一段。"""
    def read(key):
        try:
            return lead[key]
        except (KeyError, IndexError, TypeError):
            return None
    return " ".join(str(read(k) or "") for k in _EVIDENCE_FIELDS)


def has_buyer_category(lead) -> bool:
    """分级已经把这家归进了某个买家类别 —— 那是读整个官网得出的结论，比一个词硬。

    「经销商 (80)」这类标签里没有一个显示屏的词，但它恰恰是最强的证据：
    Thinksign 和 Look DS 的简介只写着 wholesale / reseller，差点因此被判成外行。
    而 `wholesale` 本身不能进词表 —— EKM 就是个农产品批发出口商。
    """
    try:
        fit = str(lead["target_fit"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return False
    return any(fit.startswith(label(t)) for t in _CATEGORIES)


def has_trade_evidence(lead) -> bool:
    """库里有没有任何一句话说这家跟显示屏这一行有关（docs/112 R2）。"""
    return has_buyer_category(lead) or bool(TRADE_RE.search(evidence_text(lead)))


# 判之前得先有话可判。一家刚采集进来、官网还没读过的公司，库里本来就没有几个字 ——
# 那是「还没看过」，不是「看过了看不出」，把两者混成一个结论正是 R1 要修的毛病。
# EKM 那条有 115 个字（一句官网原话 + 两封邮件的往来记录），够判了。
MIN_JUDGEABLE_CHARS = 40
_DESCRIBING_FIELDS = ("brief", "hook", "business")


def is_off_trade(lead) -> bool:
    """我们手里有关于这家的实质描述，而其中没有一个字跟这门生意有关（docs/112 R2）。"""
    def read(key):
        try:
            return lead[key]
        except (KeyError, IndexError, TypeError):
            return None
    described = " ".join(str(read(k) or "") for k in _DESCRIBING_FIELDS).strip()
    if len(described) < MIN_JUDGEABLE_CHARS:
        return False
    return not has_trade_evidence(lead)


def apply_to_lead(conn, lead_no: int, icp: dict) -> None:
    """Store classification: target_fit = '类型 (score)', tags get an icp:<type> tag.

    docs/112 R1. 「看不出是这一行的」也是一个结论，以前它在这里被扔掉：unknown 直接
    返回，于是「读过官网看不出来」和「从没分过级」在库里都是一个空的 target_fit，
    谁也没法拿它做事 —— EKM Exports 那家农产品出口商就是这样一路发到 FB 私信的。
    """
    fit = f"{label(icp['icp_type'])} ({icp['fit_score']})"
    row = conn.execute("SELECT tags, types_edited_at FROM leads WHERE no=?",
                       (lead_no,)).fetchone()
    if row is None:
        return
    from app import customer_types

    tags = [t.strip() for t in (row["tags"] or "").split(",") if t.strip()]
    tags = [t for t in tags if not _TAG_RE.match(t)]  # replace any previous icp tag
    tags.append(f"icp:{icp['icp_type']}")
    # The classifier already decided what this company does; leaving the customer type
    # blank means the answer lives only in a machine tag nobody reads (docs/64 R3).
    derived = customer_types.derive(",".join(tags), row["types_edited_at"])
    if derived:
        tags.insert(0, derived)
    conn.execute("UPDATE leads SET target_fit=?, tags=? WHERE no=?",
                 (fit, ",".join(tags), lead_no))
    conn.commit()
