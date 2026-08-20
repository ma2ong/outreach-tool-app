"""Screen out candidates that are never buyers: Chinese peers, B2B directories, and
markets Allen doesn't sell into.

A keyword search for "LED display" mostly surfaces our own competitors (Shenzhen
factories) and sourcing portals. They pollute the candidate list and waste enrich
time, so we flag them with a reason instead of importing them.

Detection signals, strongest first:
  1. phone country code  (+86 -> China)   -- most reliable
  2. domain TLD          (.cn / .in ...)
  3. email domain TLD    (sales@x.cn)
  4. known B2B directory / marketplace host
Nothing else is guessed: an unknown country is left blank rather than assumed.
"""
import re

# Calling code -> country. Longest prefix wins, so 1-digit codes can't shadow 3-digit ones.
_CALLING_CODES = {
    "86": "China", "852": "Hong Kong", "886": "Taiwan",
    "91": "India", "92": "Pakistan", "94": "Sri Lanka", "880": "Bangladesh",
    "977": "Nepal", "95": "Myanmar", "855": "Cambodia", "856": "Laos",
    "234": "Nigeria", "233": "Ghana", "254": "Kenya", "256": "Uganda",
    "1": "USA/Canada", "44": "UK", "49": "Germany", "33": "France", "34": "Spain",
    "39": "Italy", "31": "Netherlands", "48": "Poland", "351": "Portugal",
    "52": "Mexico", "55": "Brazil", "56": "Chile", "54": "Argentina", "57": "Colombia",
    "51": "Peru", "971": "UAE", "966": "Saudi Arabia", "82": "South Korea",
    "81": "Japan", "61": "Australia", "64": "New Zealand", "27": "South Africa",
    "65": "Singapore", "60": "Malaysia", "66": "Thailand", "84": "Vietnam",
    "62": "Indonesia", "63": "Philippines", "90": "Turkey", "972": "Israel",
}
_CODES_BY_LEN = sorted(_CALLING_CODES, key=len, reverse=True)

_TLD_COUNTRY = {
    "cn": "China", "hk": "Hong Kong", "tw": "Taiwan",
    "in": "India", "pk": "Pakistan", "lk": "Sri Lanka", "bd": "Bangladesh",
    "ng": "Nigeria", "ke": "Kenya", "np": "Nepal",
    "us": "USA/Canada", "ca": "USA/Canada", "uk": "UK", "de": "Germany", "fr": "France",
    "es": "Spain", "it": "Italy", "nl": "Netherlands", "pl": "Poland", "pt": "Portugal",
    "mx": "Mexico", "br": "Brazil", "cl": "Chile", "ar": "Argentina", "co": "Colombia",
    "pe": "Peru", "ae": "UAE", "sa": "Saudi Arabia", "kr": "South Korea", "jp": "Japan",
    "au": "Australia", "nz": "New Zealand", "za": "South Africa", "sg": "Singapore",
    "my": "Malaysia", "th": "Thailand", "vn": "Vietnam", "id": "Indonesia",
    "ph": "Philippines", "tr": "Turkey", "il": "Israel",
}

# Sourcing portals / lead-scraper sites: never a prospect, always noise.
_DIRECTORY_HOSTS = (
    "alibaba.com", "made-in-china.com", "globalsources.com", "ec21.com",
    "tradekey.com", "tradeindia.com", "indiamart.com", "exportersindia.com",
    "justdial.com", "kompass.com", "listcompany.org", "aeroleads.com",
    "europages.com", "yellowpages.com", "manta.com", "dnb.com", "zoominfo.com",
    "thomasnet.com", "go4worldbusiness.com", "hktdc.com", "1688.com", "taobao.com",
)

# Countries whose companies are our competitors, not our customers.
PEER_COUNTRIES = ("China", "Hong Kong", "Taiwan")

# Chinese LED makers that sell abroad under .com/.ca/.com.br domains and answer a local
# phone. None of the signals above catch them: the TLD is Western and the number has no
# +86. They are the single most common way a competitor reaches the lead base, so the
# brands are named. Matching is on the registrable name anywhere in the host, because
# every one of them runs regional fronts (chipshowledusa.com, absen.com.br).
PEER_BRANDS = (
    "absen", "unilumin", "leyard", "liantronics", "chipshow", "ledman", "sansi",
    "esdlumen", "gloshine", "infiled", "roe-visual", "roevisual", "linsn", "novastar",
    "colorlight", "dicolor", "sharingled", "doitvision", "unit-led", "canbest",
    "highmight", "yaham", "retop", "lightlink", "kingaurora", "shenzhen", "szled",
    "hikvision", "gtek", "ledsino", "vision-led", "reissdisplay", "mrled",
)

# What a Chinese factory says about itself in English. Either signal alone is innocent —
# a US integrator writes "manufacturer" too, and a customer may mention Shenzhen — so
# both must appear before a candidate is called a peer.
_CN_ORIGIN = re.compile(
    r"shenzhen|shen\s?zhen|guangzhou|dongguan|guangdong|zhongshan|foshan|"
    r"深圳|广州|东莞", re.I)
_MAKER = re.compile(r"manufactur|factory|oem|odm|工厂|厂家", re.I)


def is_peer_brand(domain: str | None) -> str | None:
    """The brand name matched, or None. Substring on the host: absen.com.br counts."""
    host = (domain or "").lower()
    if not host:
        return None
    return next((b for b in PEER_BRANDS if b in host), None)


def reads_as_chinese_maker(cand: dict) -> bool:
    """Says both where it is and that it makes the panels."""
    text = " ".join(str(cand.get(k) or "") for k in ("title", "business", "brief",
                                                     "company_en", "description"))
    return bool(_CN_ORIGIN.search(text) and _MAKER.search(text))


def _country_from_phone(phone: str | None) -> str | None:
    """Country from a phone number — ONLY if written in international form.

    A local-format number carries no country: US toll-free '(866) 738-3580' starts
    with 866 and would read as +86 China, wrongly screening out a real US customer.
    So we require a leading + or 00, which every enriched number has.
    """
    raw = (phone or "").strip()
    if not raw.startswith("+") and not raw.startswith("00"):
        return None
    digits = "".join(ch for ch in raw if ch.isdigit()).removeprefix("00")
    for code in _CODES_BY_LEN:
        if digits.startswith(code):
            return _CALLING_CODES[code]
    return None


def _country_from_host(host: str | None) -> str | None:
    if not host or "." not in host:
        return None
    parts = host.lower().rstrip(".").split(".")
    tld = parts[-1]
    # co.uk / com.cn style: the ccTLD is last either way
    return _TLD_COUNTRY.get(tld)


def detect_country(cand: dict) -> str | None:
    """Best-effort origin of a candidate from phone, then domain, then email domain."""
    phone_country = _country_from_phone(cand.get("phone"))
    if phone_country:
        return phone_country
    host_country = _country_from_host(cand.get("domain"))
    if host_country:
        return host_country
    email = cand.get("email") or ""
    if "@" in email:
        return _country_from_host(email.split("@", 1)[1])
    return None


def is_directory(domain: str | None) -> bool:
    d = (domain or "").lower()
    return any(d == h or d.endswith("." + h) for h in _DIRECTORY_HOSTS)


def screen(cand: dict, exclude_countries: list[str] | None = None,
           exclude_peers: bool = True) -> dict:
    """Return {country, excluded, exclude_reason} for one candidate."""
    country = detect_country(cand)
    if is_directory(cand.get("domain")):
        return {"country": country, "excluded": True, "exclude_reason": "B2B 目录站/平台"}
    if exclude_peers and country in PEER_COUNTRIES:
        return {"country": country, "excluded": True, "exclude_reason": f"同行/供应商（{country}）"}
    if exclude_peers:
        brand = is_peer_brand(cand.get("domain"))
        if brand:
            return {"country": country, "excluded": True,
                    "exclude_reason": f"国内同行品牌（{brand}）"}
        if reads_as_chinese_maker(cand):
            return {"country": country, "excluded": True,
                    "exclude_reason": "自称中国厂家（产地+制造字样同时出现）"}
    wanted_out = {c.strip() for c in (exclude_countries or []) if c.strip()}
    if country and country in wanted_out:
        return {"country": country, "excluded": True, "exclude_reason": f"排除国家（{country}）"}
    return {"country": country, "excluded": False, "exclude_reason": None}
