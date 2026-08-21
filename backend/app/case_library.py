"""Human-approved case knowledge for safe customer-facing sales replies.

Quotes and orders are private commercial history, not permission to name a customer or
present a project as a public reference. Cases therefore live in an explicit library.
Rows are private by default. Only a row Allen marks shareable, with a public label and
public summary, can enter an automatic customer reply.
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3

from app.agent import led_playbook


MIN_CUSTOMER_MATCH_SCORE = 45

SCHEMA = """
CREATE TABLE IF NOT EXISTS approved_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_name TEXT NOT NULL,
    public_label TEXT,
    country TEXT,
    application TEXT,
    indoor_outdoor TEXT,
    pixel_pitch TEXT,
    width_m REAL,
    height_m REAL,
    product_model TEXT,
    public_summary TEXT,
    source_url TEXT,
    shareable INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cases_shareable ON approved_cases(shareable, id);
CREATE INDEX IF NOT EXISTS idx_cases_application ON approved_cases(application, indoor_outdoor);
"""

TEXT_FIELDS = (
    "internal_name", "public_label", "country", "application", "indoor_outdoor",
    "pixel_pitch", "product_model", "public_summary", "source_url",
)
SAFE_FIELDS = (
    "id", "public_label", "country", "application", "indoor_outdoor", "pixel_pitch",
    "width_m", "height_m", "product_model", "public_summary", "source_url",
)


class CaseValidation(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _text(value) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _environment(value) -> str | None:
    raw = (_text(value) or "").lower()
    if not raw:
        return None
    if "out" in raw or "户外" in raw or "室外" in raw:
        return "Outdoor"
    if "in" in raw or "室内" in raw:
        return "Indoor"
    return None


def _numbers(value) -> list[float]:
    out = []
    for raw in re.findall(r"\d+(?:\.\d+)?", _text(value) or ""):
        try:
            out.append(float(raw))
        except ValueError:
            pass
    return out


def _range(value) -> tuple[float, float] | None:
    values = _numbers(value)
    if not values:
        return None
    if len(values) == 1:
        return values[0], values[0]
    return min(values[0], values[1]), max(values[0], values[1])


def _clean(data: dict, *, partial: bool = False) -> dict:
    clean = {k: v for k, v in data.items() if k in (*TEXT_FIELDS, "width_m", "height_m", "shareable")}
    for field in TEXT_FIELDS:
        if field in clean:
            limit = 4000 if field == "public_summary" else 1200
            clean[field] = (_text(clean[field]) or "")[:limit] or None
    if not partial and not clean.get("internal_name"):
        raise CaseValidation("内部案例名称不能为空")
    if "internal_name" in clean and not clean["internal_name"]:
        raise CaseValidation("内部案例名称不能为空")
    if "indoor_outdoor" in clean and clean["indoor_outdoor"]:
        env = _environment(clean["indoor_outdoor"])
        if env is None:
            raise CaseValidation("室内/户外只能填写 Indoor 或 Outdoor")
        clean["indoor_outdoor"] = env
    for field, label in (("width_m", "宽度"), ("height_m", "高度")):
        if field in clean:
            if clean[field] in (None, ""):
                clean[field] = None
            else:
                try:
                    number = float(clean[field])
                except (TypeError, ValueError) as exc:
                    raise CaseValidation(f"{label}必须是数字") from exc
                if number <= 0:
                    raise CaseValidation(f"{label}必须大于 0")
                clean[field] = number
    if "shareable" in clean:
        clean["shareable"] = int(bool(clean["shareable"]))
    return clean


def _validate_shareable(row: dict) -> None:
    if not bool(row.get("shareable")):
        return
    if not _text(row.get("public_label")) or not _text(row.get("public_summary")):
        raise CaseValidation("允许 Agent 对外引用前，必须填写公开标签和可公开摘要")


def create(conn: sqlite3.Connection, data: dict) -> dict:
    ensure_schema(conn)
    clean = _clean(data)
    clean.setdefault("shareable", 0)
    _validate_shareable(clean)
    now = _now()
    fields = [*clean.keys(), "created_at", "updated_at"]
    values = [*clean.values(), now, now]
    cur = conn.execute(
        f"INSERT INTO approved_cases({','.join(fields)}) VALUES ({','.join('?' * len(fields))})",
        values,
    )
    conn.commit()
    return get(conn, cur.lastrowid)


def get(conn: sqlite3.Connection, case_id: int) -> dict | None:
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM approved_cases WHERE id=?", (case_id,)).fetchone()
    return dict(row) if row else None


def update(conn: sqlite3.Connection, case_id: int, data: dict) -> dict | None:
    ensure_schema(conn)
    existing = get(conn, case_id)
    if existing is None:
        return None
    clean = _clean(data, partial=True)
    merged = {**existing, **clean}
    _validate_shareable(merged)
    if clean:
        clean["updated_at"] = _now()
        conn.execute(
            f"UPDATE approved_cases SET {', '.join(f'{k}=?' for k in clean)} WHERE id=?",
            [*clean.values(), case_id],
        )
        conn.commit()
    return get(conn, case_id)


def delete(conn: sqlite3.Connection, case_id: int) -> bool:
    ensure_schema(conn)
    cur = conn.execute("DELETE FROM approved_cases WHERE id=?", (case_id,))
    conn.commit()
    return cur.rowcount == 1


def list_all(conn: sqlite3.Connection, *, shareable: bool | None = None,
             limit: int = 100) -> list[dict]:
    ensure_schema(conn)
    sql = "SELECT * FROM approved_cases"
    params: list = []
    if shareable is not None:
        sql += " WHERE shareable=?"
        params.append(int(shareable))
    sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 500)))
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def match(conn: sqlite3.Connection, opportunity: dict, *, limit: int = 3,
          shareable_only: bool = True) -> list[dict]:
    """Rank similar cases. Explicit environment/pitch conflicts are excluded."""
    rows = list_all(conn, shareable=True if shareable_only else None, limit=300)
    wanted_app = led_playbook.normalize_use_case(opportunity.get("use_case"))
    wanted_env = _environment(opportunity.get("indoor_outdoor"))
    wanted_pitch_range = _range(opportunity.get("pixel_pitch"))
    wanted_pitch = wanted_pitch_range[0] if wanted_pitch_range else None
    ranked = []
    for case in rows:
        score = 10
        reasons: list[str] = []
        case_app = led_playbook.normalize_use_case(case.get("application"))
        if wanted_app and case_app:
            if wanted_app == case_app:
                score += 35
                reasons.append(f"应用匹配：{wanted_app}")
            else:
                score -= 10
        case_env = _environment(case.get("indoor_outdoor"))
        if wanted_env and case_env:
            if wanted_env != case_env:
                continue
            score += 25
            reasons.append(f"环境匹配：{wanted_env}")
        case_pitch = _range(case.get("pixel_pitch"))
        if wanted_pitch is not None and case_pitch:
            if not (case_pitch[0] - 1e-6 <= wanted_pitch <= case_pitch[1] + 1e-6):
                continue
            score += 30
            reasons.append(f"点间距匹配：P{wanted_pitch:g}")
        item = dict(case)
        item["match_score"] = max(0, min(100, score))
        item["match_reasons"] = reasons
        ranked.append(item)
    ranked.sort(key=lambda r: (-r["match_score"], -r["id"]))
    return ranked[:max(1, min(int(limit), 20))]


def customer_safe_matches(conn: sqlite3.Connection, opportunity: dict,
                          *, limit: int = 2) -> list[dict]:
    """Return only externally approved *and relevant* reference facts.

    Shareable means permission, not relevance. A case must also cross a deterministic
    similarity threshold before it can enter an automatic reply. Internal names are
    deliberately omitted even from the returned dict.
    """
    safe = []
    # Fetch a wider internal candidate set before applying the customer-facing relevance
    # gate so a low-scoring recent case cannot crowd out a better older one.
    for row in match(conn, opportunity, limit=max(10, limit * 5), shareable_only=True):
        if not row.get("shareable") or int(row.get("match_score") or 0) < MIN_CUSTOMER_MATCH_SCORE:
            continue
        safe.append({field: row.get(field) for field in SAFE_FIELDS
                     if field != "id" and row.get(field) not in (None, "", 0)})
        if len(safe) >= max(1, min(int(limit), 20)):
            break
    return safe
