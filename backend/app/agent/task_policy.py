"""Ownership rules for work that the autonomous operator can safely do itself.

A CRM activity is not automatically human work just because it is visible in the task
ledger. Account Brain uses activities as durable checkpoints. Routine public research
and bounded no-reply email follow-up belong to the Agent; commercial commitments and
ambiguous judgement stay with the user.
"""
from __future__ import annotations

WORK_OWNERS = ("human", "agent")

# Structured Account Brain rules the Worker can complete without inventing facts or
# commercial terms. `schedule_followup` only reconnects an already-emailed lead to the
# approved 3-step email sequence; it does not create copy or bypass autosend controls.
AGENT_EXECUTABLE_ACCOUNT_KEYS = frozenset({
    "refresh_icp",
    "find_decision_maker",
    "replace_invalid_channel",
    "verify_company",
    "schedule_followup",
})


def owner_for_completion_rule(rule: object) -> str:
    """Return who owns a generated task without guessing from its title."""
    if not isinstance(rule, dict):
        return "human"
    if rule.get("type") != "account_brain":
        return "human"
    return "agent" if rule.get("next_action_key") in AGENT_EXECUTABLE_ACCOUNT_KEYS else "human"


def owner_for_proposal(proposal: dict | None) -> str:
    proposal = proposal or {}
    # Decision Maker Radar already did the live public research before creating this
    # review checkpoint. Its stable dedupe namespace is exact internal provenance, not
    # a title heuristic. Weak candidates stay in the candidate pool for later rescans;
    # they should not become a human Sales Task by default.
    if str(proposal.get("dedupe_key") or "").startswith("decision-maker-"):
        return "agent"
    payload = proposal.get("payload") or {}
    return owner_for_completion_rule(payload.get("completion_rule"))
