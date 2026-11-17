"""Guardrails that run in code, between the LLM's decision to call a tool and the tool running.

Why not just a prompt rule? The system prompt already says "never make up a value", yet in the
evaluation the 3B model invented a hospital bill for a question that gave none, and confidently
told the customer what insurance would pay. Prompt rules are requests; code checks are guarantees.
"""

import json
import re

from langchain_core.messages import HumanMessage, ToolMessage

# Amount arguments the user must have stated themselves before estimate_claim may run.
USER_SUPPLIED_AMOUNTS = {"estimate_claim": ("total_bill", "room_rent_per_day")}

_MULTIPLIERS = {"lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "k": 1_000, "thousand": 1_000}
_NUMBER = re.compile(r"(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|k|thousand)?\b", re.IGNORECASE)


def numbers_in(text: str) -> set[int]:
    """Every amount a person could mean in this text: "Rs 1,50,000", "1.5 lakh", "80k", "4500"."""
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    found = set()
    for value, unit in _NUMBER.findall(text):
        amount = float(value) * _MULTIPLIERS.get(unit.lower(), 1) if unit else float(value)
        found.add(round(amount))
    return found


def ungrounded_amounts(tool_name: str, args: dict, user_texts: list[str]) -> list[str]:
    """Names of amount arguments whose values never appear in anything the user wrote."""
    stated = set().union(*(numbers_in(t) for t in user_texts)) if user_texts else set()
    missing = []
    for arg in USER_SUPPLIED_AMOUNTS.get(tool_name, ()):
        try:
            value = round(float(args.get(arg)))
        except (TypeError, ValueError):
            missing.append(arg)
            continue
        if value not in stated:
            missing.append(arg)
    return missing


async def require_user_supplied_amounts(request, execute):
    """LangGraph ToolNode interceptor: block estimate_claim when the amounts were not given by the user."""
    call = request.tool_call
    messages = request.state["messages"] if isinstance(request.state, dict) else request.state.messages
    user_texts = [m.content for m in messages if isinstance(m, HumanMessage) and isinstance(m.content, str)]
    missing = ungrounded_amounts(call["name"], call["args"], user_texts)
    if not missing:
        return await execute(request)
    return ToolMessage(
        tool_call_id=call["id"],
        name=call["name"],
        status="error",
        content=json.dumps({
            "error": "BLOCKED by guardrail: " + ", ".join(f"{m}={call['args'].get(m)}" for m in missing)
                     + " was not stated by the user. Do not invent amounts. Ask the user for: "
                     + ", ".join(missing) + ".",
        }),
    )
