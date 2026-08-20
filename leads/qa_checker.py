"""
QA Checker: 发送前合规检查，任一项不通过则阻止发送
用法: from qa_checker import QAChecker
"""
import sys, os, json
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from datetime import datetime, date
from pathlib import Path

BASE = Path(__file__).parent
PIPELINE = BASE / "pipeline"

# 每日平台限额
DAILY_LIMITS = {
    "instagram": 8,
    "facebook":  5,
    "whatsapp":  5,
}

# 最小发送间隔（分钟）
MIN_INTERVAL_MINUTES = {
    "instagram": 20,
    "facebook":  30,
    "whatsapp":  40,
}

# 禁止词汇（全小写匹配）
BANNED_PHRASES = [
    "i hope this message finds you well",
    "leading manufacturer",
    "best price",
    "factory direct",
    "factory price",
    "wholesale",
    "competitive price",
    "dear sir",
    "dear friend",
    "we are a",
    "our company",
    "please contact us",
    "contact us for",
    "check out our",
    "visit our website",
]

TIMEZONE_WINDOWS = {
    "Korea":     (2, 10),   # UTC+9, 10:00-16:00 KST = 01:00-07:00 UTC
    "USA":       (-5, -9),  # 多时区，取东部 UTC-5
    "Brazil":    (-3, -3),
    "Canada":    (-5, -5),
    "Chile":     (-4, -4),
    "Argentina": (-3, -3),
    "Colombia":  (-5, -5),
    "Peru":      (-5, -5),
    "Mexico":    (-6, -6),
}


class QAResult:
    def __init__(self):
        self.passed = True
        self.failures = []

    def fail(self, reason: str):
        self.passed = False
        self.failures.append(reason)

    def __repr__(self):
        if self.passed:
            return "QA PASSED"
        return f"QA FAILED: {'; '.join(self.failures)}"


def load_json(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


class QAChecker:
    def __init__(self, platform: str, today: str = None):
        self.platform = platform
        self.today = today or date.today().isoformat()
        self.platform_dir = PIPELINE / platform

        self.blacklist = {e.get("username", "") for e in load_json(PIPELINE / "blacklist.json")}
        self.messaged = load_json(self.platform_dir / "messaged.json")
        self.log = self._load_daily_log()

    def _load_daily_log(self) -> list:
        log_path = PIPELINE / f"daily_log_{self.today}.json"
        return load_json(log_path)

    def _messages_sent_today(self) -> list:
        return [e for e in self.log if e.get("platform") == self.platform and e.get("action") == "dm_sent"]

    def _last_send_time(self) -> datetime | None:
        sends = sorted(self._messages_sent_today(), key=lambda x: x.get("time", ""))
        if not sends:
            return None
        try:
            return datetime.fromisoformat(sends[-1]["time"])
        except Exception:
            return None

    def _message_similarity(self, msg: str, past_messages: list) -> float:
        """简单词袋相似度检测，返回最高相似度 0-1"""
        words_a = set(msg.lower().split())
        if not words_a:
            return 0.0
        max_sim = 0.0
        for past in past_messages:
            words_b = set(past.lower().split())
            if not words_b:
                continue
            intersection = words_a & words_b
            union = words_a | words_b
            sim = len(intersection) / len(union)
            max_sim = max(max_sim, sim)
        return max_sim

    def check(self, prospect: dict, message: str) -> QAResult:
        result = QAResult()
        username = prospect.get("username", "")
        country = prospect.get("country", "")

        # 1. 专属信息检查（消息不是通用模板）
        # 用公司名、城市、国家或业务关键词至少出现1个
        company = (prospect.get("company_en") or "").lower()
        city = (prospect.get("city") or "").split(",")[0].strip().lower()
        msg_lower = message.lower()
        specificity_hints = [company, city, country.lower()]
        business_words = (prospect.get("business") or "").lower().split()[:8]
        specificity_hints += [w for w in business_words if len(w) > 4]
        has_specific = any(h and h in msg_lower for h in specificity_hints)
        if not has_specific:
            result.fail("消息缺乏专属信息，疑似通用模板")

        # 2. 当日平台发送限额
        sent_today = len(self._messages_sent_today())
        limit = DAILY_LIMITS[self.platform]
        if sent_today >= limit:
            result.fail(f"今日 {self.platform} 已发 {sent_today} 条，已达上限 {limit}")

        # 3. 时区工作时间窗口（Mon-Fri 10:00-16:00 当地时间）
        now_utc = datetime.utcnow()
        if now_utc.weekday() not in (0, 1, 2, 3, 4):  # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4
            result.fail(f"当前为 UTC 周{now_utc.weekday()+1}，发送窗口仅 Mon-Fri")
        else:
            tz_offset = TIMEZONE_WINDOWS.get(country, (-5, -5))[0]
            local_hour = (now_utc.hour + tz_offset) % 24
            if not (10 <= local_hour < 16):
                result.fail(f"{country} 当地时间约 {local_hour}:00，发送窗口 10:00-16:00")

        # 4. 重复度检测（与过去7天消息 >30% 相似则阻止）
        recent_7d_messages = [
            e.get("message", "")
            for e in self.log[-200:]  # 最近200条日志
            if e.get("platform") == self.platform and e.get("action") == "dm_sent"
        ]
        if recent_7d_messages:
            sim = self._message_similarity(message, recent_7d_messages)
            if sim > 0.30:
                result.fail(f"消息与历史发送重复度 {sim:.0%}，超过30%阈值")

        # 5. blacklist 检查
        if username in self.blacklist:
            result.fail(f"@{username} 在 blacklist 中，不可触达")

        # 6. 发送间隔检查
        last_time = self._last_send_time()
        if last_time:
            elapsed = (datetime.utcnow() - last_time).total_seconds() / 60
            min_interval = MIN_INTERVAL_MINUTES[self.platform]
            if elapsed < min_interval:
                result.fail(f"距上次发送仅 {elapsed:.1f} 分钟，需间隔 {min_interval} 分钟")

        # 7. 消息长度检查
        word_count = len(message.split())
        limits = {"instagram": (40, 60), "facebook": (50, 80), "whatsapp": (30, 50)}
        min_w, max_w = limits.get(self.platform, (30, 80))
        if word_count < min_w:
            result.fail(f"消息 {word_count} 词，低于 {self.platform} 最低 {min_w} 词")
        if word_count > max_w + 10:  # +10 容错
            result.fail(f"消息 {word_count} 词，超过 {self.platform} 最高 {max_w} 词")

        # 8. 禁止词汇检查
        for phrase in BANNED_PHRASES:
            if phrase in msg_lower:
                result.fail(f"消息含禁止词汇: \"{phrase}\"")

        # 9. 中国供应商/博主检查（用词边界匹配，避免误判含 factory/manufacturer 品牌名）
        import re as _re
        business_lower = (prospect.get("business") or "").lower()
        phone_lower = (prospect.get("phone_whatsapp") or "").lower()
        china_signals = ["shenzhen", "guangzhou", "china", "chinese", "manufacturer", "factory", "+86"]
        if any(_re.search(r'\b' + _re.escape(s) + r'\b', business_lower) or s in phone_lower for s in china_signals):
            result.fail("疑似中国供应商账号，排除")

        # 10. 触达次数上限（最多2次）
        if prospect.get("touch_count", 0) >= 2:
            result.fail("已触达2次，不可再发")

        return result


def log_send(platform: str, prospect: dict, message: str, today: str = None):
    """记录发送事件到 daily_log"""
    today = today or date.today().isoformat()
    log_path = PIPELINE / f"daily_log_{today}.json"
    log = load_json(log_path)
    log.append({
        "time": datetime.utcnow().isoformat(),
        "platform": platform,
        "action": "dm_sent",
        "username": prospect.get("username"),
        "country": prospect.get("country"),
        "company": prospect.get("company_en"),
        "message": message,
    })
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    # 快速自测
    checker = QAChecker("instagram")
    test_prospect = {
        "username": "ledwave",
        "company_en": "LedWave",
        "city": "São Paulo",
        "country": "Brazil",
        "business": "LED panel sales, rental, OOH media",
        "touch_count": 0,
    }
    test_msg_good = "LedWave caught my attention — your OOH media portfolio in São Paulo is extensive. Are most of your rental panels running fixed installations or temporary event setups?"
    test_msg_bad = "I hope this message finds you well. We are a leading manufacturer of LED displays. Best price, factory direct. Please contact us."

    print("=== Good message ===")
    print(checker.check(test_prospect, test_msg_good))
    print("\n=== Bad message ===")
    r = checker.check(test_prospect, test_msg_bad)
    print(r)
    for f in r.failures:
        print(f"  - {f}")
