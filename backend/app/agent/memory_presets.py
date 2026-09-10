"""The five things Allen keeps writing by hand, as buttons that also change the state.

Every hand-written memory in the book said one of five things, and six of the eight said
a version of "we are already talking to them, stop the cold emails, find a way to make
them (re)order". Typing that sentence again for the next customer is the small cost. The
large one is that the sentence went into `lead_memory_items`, which only ever reaches a
prompt — the send path never read it, so the cold sequence kept its place in the queue
(docs/122).

So a preset is two things at once: the sentence, and the flag that actually stops the
letter. They are defined here, in one place, because a phrase that is a memory *and* a
state *and* eventually a filter cannot afford two definitions.
"""
from __future__ import annotations

# key -> what it writes, and what it changes.
#   memory:  the sentence filed under this lead, in Allen's own words
#   patch:   lead fields to set (repository.update_lead)
#   effect:  what the drawer tells him it did — never a silent switch (docs/122 R4)
PRESETS: dict[str, dict] = {
    "reorder": {
        "label": "成交客户，很久没下单",
        "memory": "成交客户，已经很久没有下单了。不要再发冷邮件或冷私信，"
                  "想办法让他重新下单。",
        "patch": {"no_cold_outreach": 1, "stage": "won"},
        "effect": "已停冷发，阶段推进到「已成交」",
    },
    "in_touch": {
        "label": "已经建立联系了",
        "memory": "与客户已经建立联系，后续不发冷邮件或冷私信，走人对人的跟进。",
        "patch": {"no_cold_outreach": 1},
        "effect": "已停冷发",
    },
    "quoted": {
        "label": "报过价，还没成交",
        "memory": "已经给对方报过价，还没有成交。不要再发冷消息，想办法推动这一单成交。",
        "patch": {"no_cold_outreach": 1},
        "effect": "已停冷发",
    },
    "peer": {
        "label": "同行 / 竞争对手",
        "memory": "这家是同行，不是客户。",
        "patch": {"do_not_contact": 1},
        "effect": "已标为不再联系（所有渠道都不再发）",
    },
    "not_decider": {
        "label": "实际决策人另有其人",
        "memory": "现在这位对接人不是拍板的人，真正做决定的是另一位。",
        "patch": {},
        "effect": "已记住",
    },
}


def options() -> list[dict]:
    """What the drawer draws. The sentence goes along so he can see what it will file."""
    return [{"key": key, "label": p["label"], "memory": p["memory"], "effect": p["effect"]}
            for key, p in PRESETS.items()]


def apply(conn, lead_no: int, key: str) -> dict:
    """File the sentence and make the change. Raises KeyError on an unknown preset."""
    from app import repository
    from app.agent import memory

    preset = PRESETS[key]
    memory.write_explicit(conn, lead_no, preset["memory"], "profile")
    if preset["patch"]:
        repository.update_lead(conn, lead_no, dict(preset["patch"]))
    return {"key": key, "memory": preset["memory"], "effect": preset["effect"]}
