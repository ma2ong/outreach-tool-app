"""One spelling per country, applied at the moment a lead is written.

The book had 130 leads in "Korea", 14 in "South Korea" and 1 in "韩国" — three bars on
the dashboard for one market, and three different filter results for the same question.
Nothing was wrong with any of the writers; they simply never agreed, because the
collector, the discovery import and the quick-add box each set the field themselves.

So the agreement lives here, at the single point every one of them passes through
(`repository.insert_lead` / `update_lead`) rather than in each of their heads.

The canonical spellings deliberately match whatever the book already uses most — "USA",
not "United States" — so adding this rule needed no migration of the existing rows and
cannot silently re-label them later.

Anything not in the table passes through unchanged apart from trimming. A country we
have never seen is not a mistake, and guessing at its canonical form (title-casing
"UAE" into "Uae") would be one.
"""

# alias (lowercased, trimmed) -> canonical spelling
_ALIASES = {
    "korea": "South Korea", "kr": "South Korea", "kor": "South Korea",
    "korea, south": "South Korea", "republic of korea": "South Korea",
    "south korea": "South Korea", "韩国": "South Korea", "대한민국": "South Korea",
    "한국": "South Korea",

    "us": "USA", "u.s.": "USA", "u.s.a.": "USA", "usa": "USA",
    "united states": "USA", "united states of america": "USA", "america": "USA",
    "美国": "USA",

    "uk": "UK", "gb": "UK", "united kingdom": "UK", "great britain": "UK",
    "england": "UK", "英国": "UK",

    "brazil": "Brazil", "brasil": "Brazil", "br": "Brazil", "巴西": "Brazil",
    "mexico": "Mexico", "méxico": "Mexico", "mx": "Mexico", "墨西哥": "Mexico",
    "chile": "Chile", "cl": "Chile", "智利": "Chile",
    "argentina": "Argentina", "ar": "Argentina", "阿根廷": "Argentina",
    "colombia": "Colombia", "co": "Colombia", "哥伦比亚": "Colombia",
    "peru": "Peru", "perú": "Peru", "pe": "Peru", "秘鲁": "Peru",
    "canada": "Canada", "ca": "Canada", "加拿大": "Canada",

    # The two-letter codes that were already sitting in the book. A filter list reading
    # "AT · AU · BE · DE · ES" tells nobody which markets those are, and the row itself
    # is no better. "USA" and "UK" stay as they are: those read as country names, which
    # is the whole test.
    "at": "Austria", "austria": "Austria",
    "au": "Australia", "australia": "Australia",
    "be": "Belgium", "belgium": "Belgium",
    "de": "Germany", "germany": "Germany", "deutschland": "Germany",
    "es": "Spain", "spain": "Spain", "españa": "Spain",
    "fi": "Finland", "finland": "Finland",
    "fr": "France", "france": "France",
    "gr": "Greece", "greece": "Greece",
    "id": "Indonesia", "indonesia": "Indonesia",
    "in": "India", "india": "India",
    "it": "Italy", "italy": "Italy", "italia": "Italy",
    "my": "Malaysia", "malaysia": "Malaysia",
    "nz": "New Zealand", "new zealand": "New Zealand",
    "pl": "Poland", "poland": "Poland",
    "ru": "Russia", "russia": "Russia",
    "se": "Sweden", "sweden": "Sweden",
    "tr": "Turkey", "turkey": "Turkey", "türkiye": "Turkey",
    "tn": "Tunisia", "tunisia": "Tunisia",
    "ve": "Venezuela", "venezuela": "Venezuela",
    "vn": "Vietnam", "vietnam": "Vietnam", "viet nam": "Vietnam",
    "ph": "Philippines", "philippines": "Philippines",
    "pg": "Papua New Guinea",
    "ge": "Georgia", "kz": "Kazakhstan",
    "ae": "UAE", "uae": "UAE", "united arab emirates": "UAE",
    "sa": "Saudi Arabia", "saudi arabia": "Saudi Arabia",
    "za": "South Africa", "south africa": "South Africa",
    "eg": "Egypt", "egypt": "Egypt",
    "ng": "Nigeria", "nigeria": "Nigeria",
    "ke": "Kenya", "kenya": "Kenya",
    "il": "Israel", "israel": "Israel",
    "jp": "Japan", "japan": "Japan", "日本": "Japan",
    "cn": "China", "china": "China", "中国": "China",
    "sg": "Singapore", "singapore": "Singapore",
    "th": "Thailand", "thailand": "Thailand",
    "nl": "Netherlands", "netherlands": "Netherlands",
    "pt": "Portugal", "portugal": "Portugal",
    "ie": "Ireland", "ireland": "Ireland",
    "no": "Norway", "norway": "Norway",
    "dk": "Denmark", "denmark": "Denmark",
    "ua": "Ukraine", "ukraine": "Ukraine",
    "gt": "Guatemala", "guatemala": "Guatemala",
    "ec": "Ecuador", "ecuador": "Ecuador",
    "uy": "Uruguay", "uruguay": "Uruguay",
    "py": "Paraguay", "paraguay": "Paraguay",
    "bo": "Bolivia", "bolivia": "Bolivia",
    "cr": "Costa Rica", "costa rica": "Costa Rica",
    "pa": "Panama", "panama": "Panama",
    "do": "Dominican Republic", "dominican republic": "Dominican Republic",

    # 他手工维护的那张客户资料表用中文写国名（docs/118 R7）。写在这里而不是写在导入器
    # 里，是因为这张表还会再导，而第四种拼法只要出现一次就再也收不回来。
    "澳大利亚": "Australia", "新加坡": "Singapore", "马来西亚": "Malaysia",
    "菲律宾": "Philippines", "泰国": "Thailand", "印度": "India", "印度尼西亚": "Indonesia",
    "越南": "Vietnam", "伊拉克": "Iraq", "以色列": "Israel", "沙特阿拉伯": "Saudi Arabia",
    "阿联酋": "UAE", "迪拜": "UAE",  # 迪拜是城市，但表里它出现在国家栏
    "法国": "France", "意大利": "Italy", "西班牙": "Spain", "德国": "Germany",
    "匈牙利": "Hungary", "波兰": "Poland", "荷兰": "Netherlands", "葡萄牙": "Portugal",
    "俄罗斯": "Russia", "乌克兰": "Ukraine", "土耳其": "Turkey", "格鲁吉亚": "Georgia",
    "巴拿马": "Panama", "危地马拉": "Guatemala", "厄瓜多尔": "Ecuador", "玻利维亚": "Bolivia",
    "乌拉圭": "Uruguay", "巴拉圭": "Paraguay", "哥斯达黎加": "Costa Rica",
    "多米尼加": "Dominican Republic", "委内瑞拉": "Venezuela",
    "南非": "South Africa", "埃及": "Egypt", "尼日利亚": "Nigeria", "肯尼亚": "Kenya",
    "加拿大": "Canada", "新西兰": "New Zealand", "瑞典": "Sweden", "挪威": "Norway",
    "丹麦": "Denmark", "芬兰": "Finland", "爱尔兰": "Ireland", "奥地利": "Austria",
    "比利时": "Belgium", "希腊": "Greece", "哈萨克斯坦": "Kazakhstan",
}


def normalize(value: str | None) -> str | None:
    """Canonical spelling for a country as written by any of the capture paths."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        # An empty string and NULL mean the same thing — "we do not know" — and keeping
        # both produces a blank row in the filter that selects a third of nothing.
        return None
    return _ALIASES.get(cleaned.lower(), cleaned)
