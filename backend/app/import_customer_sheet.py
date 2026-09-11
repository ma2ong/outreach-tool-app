"""Bring in the customer sheet Allen keeps by hand.

`客户资料表.xlsx` is not a CRM export. `import_customers` (docs/54) reads 小满's export,
where every row is a customer he already worked, and it marks the lot as contacted. Most
rows in *this* sheet are the opposite: companies he researched and has never written to.
Running them through that importer would lock 236 leads out of the cold queue for good,
so this is a second reader with the opposite default (docs/118).

What the sheet says, it says in Chinese prose in a 备注 column — including the two
instructions that must never be got wrong: 只入库不联系, and "write from my own gmail and
do not name the company". Both end in `do_not_contact=1`; the second one also lands in the
import report, because the thing it asks for is something the sender cannot do.

The headers are advice, not fact: a phone sits in the name cell, an email in the phone
cell, an Instagram link where the website goes. Every person cell is read by what is in
it (docs/118 R9), and a stored value that cannot be what its field says it is counts as
blank on the next run (R10), so re-importing repairs what the first pass filed wrong.

Run:  python -m app.import_customer_sheet "客户资料表 .xlsx"           # preview only
      python -m app.import_customer_sheet "客户资料表 .xlsx" --apply   # write
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

from app import blocklist, contacts as contacts_mod, repository as repo
from app.db import connect
from app.dedupe import normalize_website

DB = "outreach.db"

# His own mailbox appears in the 备注 of five rows as an instruction about how to write to
# them. It is never a customer address (docs/118 R2).
ALLEN_MAILBOX = "allenma2ong@gmail.com"

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}")
_HANGUL = re.compile(r"[가-힣]")
_CHINESE = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[A-Za-z]")
_URL = re.compile(r"(?:https?://|www\.|(?:instagram|facebook|linkedin)\.com/)"
                  r"[^\s,，、;；)（）'\"]+")
# A run of digits with the separators people type between them. Whitespace only joins
# when a digit follows, so two numbers on two lines stay two numbers.
_PHONE = re.compile(r"\(?\+?\s?\d(?:[\d\-–().]|\s+(?=[\d\-–(]))*\d")
_PAREN = re.compile(r"[（(][^()（）]*[)）]")
_CJK_ASIDE = re.compile(r"[一-鿿][一-鿿A-Za-z0-9：:]*")
# Words written next to a number to say what kind of number it is. Not a name.
_NOISE = re.compile(r"(?i)\b(?:whatsapp|watapps|wa|call|tel|fax|mobile|phone|blog|email|e-mail"
                    r"|facebook|instagram|twitter|linkedin|viber|wechat|kakao|kakaotalk|skype"
                    r"|telegram|line|sales|enquiry|enquiries|inquiry|support|marketing|info"
                    r"|office|hotline|mob|hp|cell)\b|이메일|메일|대표번호|휴대폰|전화|카톡|카카오톡")
# Longest first, so 대표이사 is one title and not 대표 + 이사; and not followed by more
# Hangul, so 영상실장최기민 is left alone rather than cut into 영상 + 최기민.
_TITLES = sorted(("대표이사", "대표자", "부대표", "이사장", "회장", "부회장", "부사장", "본부장", "대표", "이사",
                  "상무", "전무", "사장", "부장", "차장", "과장", "팀장", "실장", "소장", "국장",
                  "대리", "사원", "주임", "프로", "경리", "담당자", "담당", "매니저", "총괄", "관리"),
                 key=len, reverse=True)
_TITLE = re.compile("(?:" + "|".join(_TITLES) + r")(?:님)?(?![가-힣])")
_SEGMENT = re.compile(r"[\n,，;；|]|或者")
_SOCIAL_HOSTS = ("instagram.com", "facebook.com", "linkedin.com")
# Labels an earlier import filed where a person's name goes.
_NOT_A_NAME = {"公司邮箱", "会社邮箱", "회사메일", "公司", "邮箱", "同上", "대표메일"}

# The instruction words, read in this order: a row that says 继续联系 means it, even when
# the same sentence also says 成交客户 (docs/118 R1).
_KEEP_CONTACTING = ("继续联系",)
_DO_NOT_CONTACT = ("只入库不联系", "成交客户", "我的合作客户", "合作客户")

_SHEET = "《客户资料表》"
_NOTE_HEAD = f"从{_SHEET}导入（"

# Cells that hold people and ways to reach them, in the order a value found in one of them
# is believed. The header says what the cell should hold; the content says what it does.
_PERSON_CELLS = ("联系人昵称", "联系人邮箱", "联系人电话", "联系人备注", "公司简称", "座机",
                 "Facebook", "instagram", "LinkedIn", "备注")
# Where the company's own account is written — read before any link next to a person.
_COMPANY_ACCOUNT_CELLS = ("instagram", "Facebook", "LinkedIn", "公司网址")
# Cells whose whole text already goes into the note, so their leftovers need not.
_NOTE_CELLS = ("联系人备注", "备注")


def _text(value) -> str:
    return "" if value is None else re.sub(r"[﻿​]", "", str(value)).strip()


def read_sheet(path: str) -> list[dict]:
    """Rows of the first sheet, keyed by header. Unlabelled columns keep their position."""
    from openpyxl import load_workbook

    book = load_workbook(Path(path), read_only=True, data_only=True)
    rows = book.worksheets[0].iter_rows(values_only=True)
    headers = [_text(h) or f"col{i}" for i, h in enumerate(next(rows, []))]
    out = []
    for values in rows:
        row = {headers[i]: _text(v) for i, v in enumerate(values) if i < len(headers)}
        if any(row.values()):
            out.append(row)
    return out


def _emails(text: str) -> list[str]:
    seen: list[str] = []
    for hit in _EMAIL.findall(text or ""):
        address = hit.strip(" '\"<>.,;").lower()
        if address != ALLEN_MAILBOX and address not in seen:
            seen.append(address)
    return seen


def _phone(raw: str) -> str:
    """The number as typed, or '' when the digits could not be a phone number."""
    if not 8 <= len(re.sub(r"\D", "", raw)) <= 15:
        return ""
    raw = raw.strip(" '‘’\"-–")
    if raw.count("(") != raw.count(")"):
        raw = re.sub(r"[()]", "", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _handle(cell: str, text: str) -> str:
    """`Instagram：leesungsik` in the instagram column is a handle without a link."""
    if cell not in ("instagram", "Facebook") or "://" in text:
        return ""
    handle = text.split("：")[-1].split(":")[-1].strip()
    return handle if re.fullmatch(r"[A-Za-z0-9._]+", handle) else ""


def _social(url: str) -> dict:
    """{'instagram': handle} / {'facebook': …} / {'linkedin': …} / {'website': host} / {}."""
    from app.quick_add import BadUrl, parse_url

    try:
        fields = parse_url(url)
    except BadUrl:
        return {}
    if fields.get("facebook") == "profile.php":
        ident = re.search(r"[?&]id=(\d+)", url)
        fields["facebook"] = f"profile.php?id={ident.group(1)}" if ident else ""
    return {k: v for k, v in fields.items() if v}


def _person(segment: str) -> dict:
    """One comma/newline-separated piece of a cell as {name, title, phone, remark}.

    `이채원 이사님010-4482-0017` is a name, a title and a phone. What is left after those
    are taken out and does not look like a name — a Chinese aside in brackets, a channel
    word, a bare domain — is remark text for the note.
    """
    phones = [p for p in map(_phone, _PHONE.findall(segment)) if p]
    rest = _PHONE.sub(lambda m: " " if _phone(m.group()) else m.group(), segment)
    remarks = [m.group().strip("()（） ") for m in _PAREN.finditer(rest)]
    rest = _PAREN.sub(" ", rest)
    titles = list(dict.fromkeys(t.rstrip("님") for t in _TITLE.findall(rest)))
    rest = _NOISE.sub(" ", _TITLE.sub(" ", rest))
    if _HANGUL.search(rest):
        # 유준수팀장已加微信 — the Chinese aside was written straight onto the Korean name.
        remarks.extend(m.group() for m in _CJK_ASIDE.finditer(rest))
        rest = _CJK_ASIDE.sub(" ", rest)
    name = re.sub(r"\s+", " ", re.sub(r"[:：'‘’\"\-–/()（）]+", " ", rest)).strip()
    if _HANGUL.search(name):
        name = name.replace(" ", "")
        # 이 과장님 is a surname and a title; that much is still a person.
        looks_like_name = bool(re.fullmatch(r"[가-힣]{2,5}", name)) or \
            bool(titles and re.fullmatch(r"[가-힣]", name))
    else:
        looks_like_name = bool(re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'\-]+", name)) \
            and len(name.split()) <= 4 and not re.search(r"\w\.\w", name)
    if name and not looks_like_name:
        remarks.append(name)
        name = ""
    return {"name": name, "title": "/".join(titles), "phone": phones[0] if phones else "",
            "extra_phones": phones[1:], "remark": " ".join(r for r in remarks if r.strip())}


def _instruction(*texts: str) -> tuple[bool, str]:
    """(do_not_contact, the sentence that says so) — 继续联系 wins over every other word."""
    joined = " ".join(t for t in texts if t)
    if any(word in joined for word in _KEEP_CONTACTING):
        return False, ""
    if ALLEN_MAILBOX in joined:
        return True, "备注要求用 Allen 私人邮箱、且不署公司名 —— 自动发送做不到，留给手工处理"
    for word in _DO_NOT_CONTACT:
        if word in joined:
            return True, f"备注写着「{word}」"
    return False, ""


def _names(company: str, short: str) -> tuple[str, str | None]:
    """(company_en, company_local). Korean names live in company_local (docs/118 R5)."""
    # 「(주)컴텔싸인_成交客户」 — the instruction was written into the name. Strip it, or the
    # Korean letter opens by calling them 成交客户.
    company = re.sub(r"[（(_\s]*成交客户[)）]*\s*$", "", company).strip(" _")
    short = "" if ("@" in short or _phone(short)) else short
    if _HANGUL.search(company):
        english = short if _LATIN.search(short) else ""
        return (english or company), company
    return company, (short if _HANGUL.search(short) else None)


def _people(row: dict) -> tuple[list[str], list[dict], list[str]]:
    """(links, people, leftovers) read out of every person cell by content (R9). A person
    is one segment: name, title, phone and the addresses written in the same breath."""
    links: list[str] = []
    people: list[dict] = []
    leftovers: list[str] = []
    seen: set[str] = set()
    for cell in _PERSON_CELLS:
        text = _text(row.get(cell))
        if not text or (cell == "座机" and "商" in text):
            continue
        handle = _handle(cell, text)
        if handle:
            links.append(f"https://{cell.lower()}.com/{handle}")
            continue
        links.extend(_URL.findall(text))
        for segment in _SEGMENT.split(_URL.sub(" ", text)):
            if not segment.strip():
                continue
            emails = [a for a in _emails(segment) if a not in seen]
            seen.update(emails)
            person = {**_person(_EMAIL.sub(" ", segment)), "emails": emails, "cell": cell}
            # Only the name cell is trusted to hold a bare name. Elsewhere a name counts
            # when a title, a number or (in the email cell) an address stands next to it;
            # 公司简称 holds no people at all.
            reached = person["title"] or person["phone"] or (cell == "联系人邮箱" and emails)
            if person["name"] and (cell == "公司简称" or (cell != "联系人昵称" and not reached)):
                if cell != "公司简称":
                    leftovers.append(person["name"])
                person["name"] = ""
            if person["name"] or person["phone"] or person["emails"]:
                people.append(person)
            # 公司简称 is a company name; only a Chinese aside there (与KLDC是同一个客户) is news.
            if person["remark"] and cell not in _NOTE_CELLS and (
                    cell != "公司简称" or _CHINESE.search(person["remark"])):
                leftovers.append(person["remark"])
    return links, people, leftovers


def _contacts(people: list[dict]) -> tuple[list[dict], list[str]]:
    """(contacts, phones nobody is named next to). The primary is the person in the name
    cell, else the first named one; a different name next to a phone is a second contact
    (R11); every address nobody is named next to is a person of its own (R6)."""
    primary = next((p for p in people if p["cell"] == "联系人昵称" and p["name"]), None) \
        or next((p for p in people if p["name"]), None) \
        or {"name": "", "title": "", "phone": "", "emails": []}
    out = [{"name": primary["name"], "title": primary["title"], "phone": primary["phone"],
            "email": ""}]
    loose: list[str] = list(primary["emails"])
    for person in people:
        same = person is primary or not person["name"] or person["name"] == primary["name"]
        if same:
            if not out[0]["phone"] and person["phone"]:
                out[0]["phone"] = person["phone"]
            if not out[0]["title"] and person["title"]:
                out[0]["title"] = person["title"]
            if person is not primary:
                loose.extend(person["emails"])
        elif not any(c["name"] == person["name"] for c in out):
            out.append({"name": person["name"], "title": person["title"],
                        "phone": person["phone"],
                        "email": person["emails"][0] if person["emails"] else ""})
            loose.extend(person["emails"][1:])
    if loose:
        out[0]["email"] = loose.pop(0)
    out.extend({"name": "", "title": "", "phone": "", "email": a} for a in loose)
    used = {c["phone"] for c in out}
    spare = [p for person in people for p in [person["phone"], *person["extra_phones"]]
             if p and p not in used]
    return out, list(dict.fromkeys(spare))


def parse_row(row: dict) -> dict | None:
    """One sheet row as a lead-shaped record, or None when there is nothing to file."""
    company = _text(row.get("公司名称"))
    short = _text(row.get("公司简称"))
    remark = _text(row.get("备注"))
    contact_remark = _text(row.get("联系人备注"))
    company_en, company_local = _names(company, short)

    links, people, leftovers = _people(row)
    contacts, spare_phones = _contacts(people)
    emails = [c["email"] for c in contacts if c["email"]]
    if not company_en and not emails:
        return None

    # Company accounts before personal ones: the `instagram` column is the company's, the
    # link next to a person's name is theirs. Whatever has no field goes to the note.
    company_cells = [_text(row.get(c)) for c in _COMPANY_ACCOUNT_CELLS]
    website = _text(row.get("公司网址"))
    name_cell = _text(row.get("联系人昵称"))
    links = _URL.findall(website) + links
    ordered = sorted(dict.fromkeys(links), key=lambda u: (
        0 if any(u in c for c in company_cells) else 2 if u in name_cell else 1))
    social: dict[str, str] = {}
    extra_links: list[str] = []
    for url in ordered:
        fields = _social(url)
        key = next((k for k in ("instagram", "facebook", "linkedin") if k in fields), None)
        if key and key not in social:
            social[key] = fields[key]
        elif not (key is None and url == website):
            extra_links.append(url)
    if any(host in website for host in _SOCIAL_HOSTS) or (website and malformed("website", website)):
        website = ""

    blocked, reason = _instruction(remark, contact_remark, company)
    country_cell = _text(row.get("国家地区"))
    tags = _text(row.get("标签")) or ("" if "商" not in _text(row.get("座机")) else _text(row.get("座机")))

    # Everything the sheet says that no field can hold. Guessing a Korean street address
    # into `city` would be inventing structure; the note keeps it readable (docs/118 R6).
    lines = []
    for label, value in (("备注", remark), ("联系人备注", contact_remark),
                         ("联系人原文", " | ".join(dict.fromkeys(leftovers))),
                         ("其他电话", "、".join(spare_phones)),
                         ("其他链接", " ".join(extra_links)),
                         ("地址", _text(row.get("col18")) or _text(row.get("详细地址"))),
                         ("小满", _text(row.get("col16"))),
                         ("是否取得联系", _text(row.get("是否取得联系"))),
                         ("原国家地区", country_cell if "/" in country_cell else "")):
        if value:
            lines.append(f"{label}：{value}")

    return {
        "company_en": company_en or emails[0],
        "company_local": company_local,
        "country": country_cell.split("/")[0],
        "website": website,
        "email": contacts[0]["email"],
        "emails": emails,
        "phone": contacts[0]["phone"],
        "contact_name": contacts[0]["name"],
        "title": contacts[0]["title"],
        "contacts": contacts,
        "tags": tags.replace("，", ",").replace(" ", ""),
        "instagram": social.get("instagram", ""),
        "facebook": social.get("facebook", ""),
        "linkedin": social.get("linkedin", ""),
        # 是 and 否 both mean he already wrote to them; 否 is "wrote, never got through"
        # (docs/118 R3). Only an empty cell is a stranger.
        "contacted": bool(_text(row.get("是否取得联系"))),
        "do_not_contact": blocked,
        "block_reason": reason,
        "note": "\n".join(lines),
    }


def _match(conn, record: dict) -> int | None:
    """The lead this row is about: by email, then website, then company name."""
    for address in record["emails"]:
        hit = conn.execute("SELECT no FROM leads WHERE lower(email)=?", (address,)).fetchone()
        if hit:
            return hit["no"]
        hit = conn.execute("SELECT lead_no FROM contacts WHERE lower(email)=?",
                           (address,)).fetchone()
        if hit:
            return hit["lead_no"]
    site = normalize_website(record["website"])
    if site:
        hit = conn.execute(
            "SELECT no FROM leads WHERE lower(replace(replace(website,'https://',''),"
            "'http://','')) LIKE ?", (f"{site}%",)).fetchone()
        if hit:
            return hit["no"]
    if record["instagram"]:
        hit = conn.execute("SELECT no FROM leads WHERE lower(instagram)=?"
                           " OR lower(website)=?", (record["instagram"].lower(),
                                                    f"instagram.com/{record['instagram'].lower()}")).fetchone()
        if hit:
            return hit["no"]
    for name in (record["company_en"], record["company_local"]):
        if name:
            hit = conn.execute(
                "SELECT no FROM leads WHERE lower(company_en)=? OR lower(company_local)=?",
                (name.lower(), name.lower())).fetchone()
            if hit:
                return hit["no"]
    return None


def malformed(field: str, value) -> bool:
    """A value that cannot be what its field says it is — an email in `phone`, an Instagram
    link in `website`, a phone number in a person's name. It counts as blank (R10)."""
    value = _text(value)
    if not value:
        return True
    if field == "phone":
        return bool(re.search(r"[A-Za-z가-힣一-鿿@]", value)) \
            or len(re.sub(r"\D", "", value)) < 7
    if field == "website":
        return any(host in value for host in _SOCIAL_HOSTS) \
            or not re.fullmatch(r"[a-z0-9.\-]+\.[a-z]{2,}(/.*)?", _site(value))
    if field in ("instagram", "facebook"):
        return not re.fullmatch(r"[A-Za-z0-9._\-]+|profile\.php\?id=\d+", value)
    if field == "linkedin":
        return "@" in value or " " in value or "://" in value
    if field == "name":
        return "@" in value or "://" in value or bool(re.search(r"\d{3}", value)) \
            or value in _NOT_A_NAME \
            or bool(_HANGUL.search(value) and (_CHINESE.search(value) or _TITLE.search(value)))
    return False


_SHEET_WINS = ("company_en", "company_local", "country", "website", "instagram", "facebook",
               "linkedin", "tags")
_OVERRIDE_HEAD = f"{_SHEET}覆盖前库里的值（"


def _site(url: str) -> str:
    """Stored form of a website: no scheme, no www., no query string."""
    return (normalize_website(url) or "").split("?")[0].rstrip("/")


def _same(field: str, a, b) -> bool:
    """Two spellings of one value are not a disagreement: +82 010-4482-0017 is
    010-4482-0017, http://www.jdkat.com/?_main=1 is jdkat.com."""
    a, b = _text(a), _text(b)
    if field == "phone":
        return re.sub(r"\D", "", a)[-8:] == re.sub(r"\D", "", b)[-8:]
    if field == "website":
        return _site(a).split("/")[0] == _site(b).split("/")[0]
    if field == "country":
        from app import countries
        return countries.normalize(a) == countries.normalize(b)
    if field == "tags":
        return set(a.split(",")) == set(b.split(","))
    if field in ("email", "instagram", "facebook", "linkedin"):
        return a.lower() == b.lower()
    return a == b


def _tags(sheet: str, current: str) -> str:
    """His labels replace his labels; the classifier's icp:* labels are not his to lose."""
    kept = [t for t in (current or "").split(",") if t.startswith("icp:")]
    return ",".join(dict.fromkeys(t for t in (*sheet.split(","), *kept) if t))


def _take_sheet(conn, no: int, record: dict, *, first_row: bool = True) -> dict:
    """Where the sheet and the book disagree, the sheet wins (R4). Returns what the book
    used to say, so the note can keep it."""
    current = conn.execute("SELECT * FROM leads WHERE no=?", (no,)).fetchone()
    patch: dict = {}
    replaced: dict = {}
    # A company written twice in the sheet: the first row speaks for it, the second only
    # adds people and may still say 只入库不联系.
    for field in _SHEET_WINS if first_row else ():
        new = record.get(field) or ""
        if field == "tags" and new:
            new = _tags(new, current["tags"])
        if field == "website":
            new = _site(new)
        if new and malformed(field, new):
            new = ""
        # 公司简称 is a nickname he types (sysmate, kioskkorea), not the company's English
        # name: it fills a blank but does not replace `Kiosk Korea`. A Latin 公司名称 does.
        if field == "company_en" and record["company_local"] and current[field]:
            continue
        if not new:
            if current[field] and malformed(field, current[field]):
                patch[field] = None
            continue
        if _same(field, current[field], new):
            continue
        if current[field] and not malformed(field, current[field]):
            replaced[field] = current[field]
        patch[field] = new
    if record["do_not_contact"] and not current["do_not_contact"]:
        patch["do_not_contact"] = 1
    if patch:
        repo.update_lead(conn, no, patch)
    return replaced


def _keep_replaced(conn, no: int, replaced: dict, today: dt.date) -> None:
    """The old value survives only here: once the field is overwritten nothing can tell it
    was, so it is written down once, and never rewritten."""
    if not replaced:
        return
    body = " ".join(f"{k}={v}" for k, v in replaced.items())
    if conn.execute("SELECT 1 FROM notes WHERE lead_no=? AND text LIKE ? AND text LIKE ?",
                    (no, f"{_OVERRIDE_HEAD}%", f"%{body}%")).fetchone():
        return
    repo.add_note(conn, no, f"{_OVERRIDE_HEAD}{today.isoformat()}）：{body}")


def _add_note(conn, no: int, text: str) -> bool:
    """One sheet note per company, refreshed in place: the sheet gets re-imported, and a
    second note per run is manual cleanup (R8, R11)."""
    if not text:
        return False
    existing = conn.execute(
        "SELECT id, text FROM notes WHERE lead_no=? AND text LIKE ? ORDER BY id",
        (no, f"{_NOTE_HEAD}%")).fetchall()
    if not existing:
        repo.add_note(conn, no, text)
        return True
    # The first pass left one note per row; the sheet's rows about this company are now
    # one note, so the extras go.
    for extra in existing[1:]:
        conn.execute("DELETE FROM notes WHERE id=?", (extra["id"],))
    if existing[0]["text"].split("\n", 1)[1:] == text.split("\n", 1)[1:]:
        return bool(existing[1:])
    conn.execute("UPDATE notes SET text=? WHERE id=?", (text, existing[0]["id"]))
    return True


def _find_person(conn, no: int, person: dict):
    """The contact this sheet person already is: same address, else same number, else the
    same name. None when they are new to the book."""
    if person["email"]:
        hit = conn.execute("SELECT * FROM contacts WHERE lead_no=? AND lower(email)=?",
                           (no, person["email"])).fetchone()
        if hit:
            return hit
    if person["phone"]:
        for row in conn.execute("SELECT * FROM contacts WHERE lead_no=? AND phone!=''",
                                (no,)).fetchall():
            if _same("phone", row["phone"], person["phone"]):
                return row
    if person["name"]:
        return conn.execute("SELECT * FROM contacts WHERE lead_no=? AND name=?",
                            (no, person["name"])).fetchone()
    return None


def _file_contacts(conn, no: int, record: dict, *, first_row: bool = True) -> tuple[int, dict]:
    """Every address is a person, and so is every name next to a phone. The sheet's first
    person is the primary — whoever the book had before steps down to secondary, and
    stays (R4). Secondaries are never written to by the daily send on their own
    (docs/114). Returns (contacts added, what the primary used to say).

    When the sheet has two rows about one company, the first row names the primary; the
    second row's people are all secondaries."""
    contacts_mod.migrate_lead(conn, no)
    added = 0
    replaced: dict = {}
    first, *others = record["contacts"]
    if not first_row:
        others = [first, *others]
        first = {"name": "", "title": "", "phone": "", "email": ""}
    primary = conn.execute("SELECT * FROM contacts WHERE lead_no=? AND is_primary=1",
                           (no,)).fetchone()
    # Updating the primary copies its fields back onto the lead, and the two have drifted
    # (a phone normalised on the lead, a LinkedIn only the lead has). Read the lead first,
    # so a blank on the contact never erases what the lead shows.
    lead = conn.execute("SELECT contact_name AS name, title, email, phone, linkedin"
                        " FROM leads WHERE no=?", (no,)).fetchone()
    # An address is an identity; a name or a number alone is not. A sheet person with an
    # email is the primary (found or created). Without one, the sheet is describing the
    # primary the book already has — replacing them with a name-only person would leave
    # the company with nobody to email.
    if first["email"]:
        target = _find_person(conn, no, first)
    else:
        target = primary
    if target is None and not any(first.values()):
        pass
    elif target is None:
        contacts_mod.create(conn, no, {k: v or None for k, v in first.items()},
                            is_primary=True, source="manual")
        added += 1
        if primary is not None:
            replaced["主联系人"] = " / ".join(v for v in (primary["name"], primary["email"],
                                                       primary["phone"]) if v)
    else:
        if not target["is_primary"]:
            contacts_mod.set_primary(conn, target["id"])
            replaced["主联系人"] = " / ".join(v for v in (primary["name"], primary["email"],
                                                       primary["phone"]) if v)
        # 임정재 부장(已加微信) is still 임정재: when the sheet gives no name, the name inside
        # the dirty one is kept and the aside moves to the contact's note.
        patch: dict = {}
        was_primary = primary is not None and target["id"] == primary["id"]
        current = {k: target[k] or (lead[k] if was_primary else None)
                   for k in ("name", "title", "phone", "email")}
        # LinkedIn on a lead is the company page, whoever the primary is. Promoting a
        # contact without one must not wipe it.
        current["linkedin"] = target["linkedin"] or lead["linkedin"]
        dirty = current["name"] if current["name"] and malformed("name", current["name"]) else ""
        if dirty:
            head, *tail = [t.strip() for t in _SEGMENT.split(dirty) if t.strip()]
            inside = _person(head)
            current = {**current, "name": inside["name"] or None,
                       "title": current["title"] or inside["title"] or None,
                       "phone": current["phone"] or inside["phone"] or None}
            aside = " | ".join(t for t in (inside["remark"], *tail) if t)
            if aside and aside not in (target["note"] or ""):
                patch["note"] = "\n".join(t for t in (target["note"], aside) if t)
        for k in ("name", "title", "phone", "email", "linkedin"):
            new = first.get(k) or ""
            if new and not _same(k, current[k], new):
                if current[k] and not malformed(k, current[k]):
                    replaced[k] = current[k]
                patch[k] = new
            elif malformed(k, current[k]):
                patch[k] = None if current[k] else patch.get(k)
            elif (current[k] or "") != (target[k] or ""):
                patch[k] = current[k]
        patch = {k: v for k, v in patch.items() if (v or None) != (target[k] or None)
                 or k == "note"}
        if patch.get("email") and conn.execute(
                "SELECT 1 FROM contacts WHERE lead_no=? AND lower(email)=? AND id!=?",
                (no, patch["email"], target["id"])).fetchone():
            del patch["email"]
        if patch:
            contacts_mod.update(conn, target["id"], patch)
    # A secondary whose phone is an email or a link got it from the first pass. The
    # addresses inside are filed as people of their own below.
    for row in conn.execute("SELECT id, phone FROM contacts WHERE lead_no=? AND is_primary=0",
                            (no,)).fetchall():
        if row["phone"] and malformed("phone", row["phone"]):
            contacts_mod.update(conn, row["id"], {"phone": None})
    for person in others:
        if not (person["email"] or person["phone"]) or _find_person(conn, no, person):
            continue
        try:
            contacts_mod.create(conn, no, {k: v or None for k, v in person.items()},
                                source="manual")
            added += 1
        except (contacts_mod.ContactValidation, contacts_mod.ContactAddressTaken):
            continue
    return added, replaced


def _mark_contacted(conn, no: int, record: dict, today: dt.date) -> None:
    """Already written to means no first cold email, whichever channel it went out on."""
    for channel, address in (("email", record["email"]), ("whatsapp", record["phone"])):
        if not address:
            continue
        conn.execute(
            "INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)"
            " VALUES (?, ?, 'messaged', 1, ?)"
            " ON CONFLICT(lead_no, channel) DO UPDATE SET"
            "   status=CASE WHEN outreach.status IN ('prospect','') THEN 'messaged'"
            "               ELSE outreach.status END",
            (no, channel, today.isoformat()))


def plan(conn, records: list[dict]) -> dict:
    """What an import would do, without doing any of it."""
    contacts_mod.ensure_schema(conn)
    created = merged = 0
    for record in records:
        if _match(conn, record) is None:
            created += 1
        else:
            merged += 1
    return {
        "total": len(records), "created": created, "merged": merged,
        "do_not_contact": sum(1 for r in records if r["do_not_contact"]),
        "already_contacted": sum(1 for r in records if r["contacted"]),
        "manual_only": [r["company_en"] for r in records if ALLEN_MAILBOX in r["note"]],
    }


def apply(conn, records: list[dict], today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    contacts_mod.ensure_schema(conn)
    result = {"created": 0, "merged": 0, "blocked": 0, "notes": 0, "contacts": 0,
              "do_not_contact": 0, "skipped_domains": []}
    # Two rows about one company (sysmate twice, 현선디스플레이 and hyunsundisplay) share
    # its one note; otherwise the second row overwrites the first and a rerun flips them.
    bodies: dict[int, list[str]] = {}
    for record in records:
        no = _match(conn, record)
        first_row = no not in bodies
        if no is None:
            try:
                no = repo.insert_lead(conn, {
                    "company_en": record["company_en"],
                    "company_local": record["company_local"],
                    "country": record["country"], "website": record["website"],
                    "instagram": record["instagram"], "facebook": record["facebook"],
                    "linkedin": record["linkedin"],
                })
            except blocklist.BlockedLead:
                # The domain is on the never-collect-again list. Someone put it there on
                # purpose; a spreadsheet is not a reason to overrule that.
                result["blocked"] += 1
                result["skipped_domains"].append(record["company_en"])
                continue
            repo.update_lead(conn, no, {
                "tags": record["tags"],
                "do_not_contact": 1 if record["do_not_contact"] else 0,
                "stage": "contacted" if record["contacted"] else "new",
            })
            result["created"] += 1
            replaced: dict = {}
        else:
            replaced = _take_sheet(conn, no, record, first_row=no not in bodies)
            result["merged"] += 1
        if record["do_not_contact"]:
            result["do_not_contact"] += 1
        added, was = _file_contacts(conn, no, record, first_row=first_row)
        result["contacts"] += added
        _keep_replaced(conn, no, {**replaced, **was}, today)
        if record["contacted"]:
            _mark_contacted(conn, no, record, today)
        head = f"{_NOTE_HEAD}{today.isoformat()}）"
        if record["block_reason"]:
            head += f"，只入库不联系：{record['block_reason']}"
        bodies.setdefault(no, []).append(head + ("\n" + record["note"] if record["note"] else ""))
    for no, parts in bodies.items():
        if _add_note(conn, no, "\n\n".join(parts)):
            result["notes"] += 1
    conn.commit()
    return result


def main(path: str, apply_it: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = read_sheet(path)
    records = [r for r in (parse_row(row) for row in rows) if r]
    conn = connect(DB)
    summary = plan(conn, records)
    print(f"读到 {len(rows)} 行，可用 {summary['total']} 条：新建 {summary['created']}，"
          f"补充已有 {summary['merged']}")
    print(f"其中 标为不再联系 {summary['do_not_contact']} 条，"
          f"已开发过（不再发首封）{summary['already_contacted']} 条")
    if summary["manual_only"]:
        print("\n以下备注要求用你的私人邮箱、且不暴露公司名 —— 系统做不到，已标为不联系，请手工处理：")
        for name in summary["manual_only"]:
            print(f"  · {name}")
    if not apply_it:
        print("\n预览模式，未写入。加 --apply 执行")
        return
    done = apply(conn, records)
    print(f"\n写入完成：新建 {done['created']}，补充 {done['merged']}，"
          f"新增联系人 {done['contacts']}，写备注 {done['notes']}，"
          f"标为不再联系 {done['do_not_contact']}")
    if done["blocked"]:
        print(f"跳过 {done['blocked']} 条（域名在永不再收录名单里）："
              + "、".join(done["skipped_domains"]))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--apply"]
    if not args:
        print("用法：python -m app.import_customer_sheet <客户资料表.xlsx> [--apply]")
        raise SystemExit(2)
    main(args[0], "--apply" in sys.argv)
