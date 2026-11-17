import asyncio

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from claims_agent import mcp_server as s
from claims_agent.guardrails import numbers_in, require_user_supplied_amounts, ungrounded_amounts


def test_numbers_in_understands_indian_formats():
    assert numbers_in("Bill Rs 1,50,000 and room Rs 6,000/day") >= {150000, 6000}
    assert numbers_in("about 1.5 lakh, room 4.5k") >= {150000, 4500}


def test_amounts_must_come_from_the_user():
    args = {"total_bill": 150000, "room_rent_per_day": 6000}
    assert ungrounded_amounts("estimate_claim", args, ["Bill Rs 1,50,000, room Rs 6,000 per day"]) == []
    # Regression: the model invented a bill for a question that never mentioned one
    assert ungrounded_amounts("estimate_claim", args, ["How much for Rahul's cataract surgery? ID M1003"]) == [
        "total_bill", "room_rent_per_day"]
    # Amounts given in an earlier turn of the conversation count
    assert ungrounded_amounts("estimate_claim", args, ["Cataract for M1003", "bill 1.5 lakh, room 6000"]) == []
    # Other tools are not checked
    assert ungrounded_amounts("get_member", {"member_id": "M1003"}, []) == []


class _Request:
    def __init__(self, user_text, args):
        self.tool_call = {"name": "estimate_claim", "args": args, "id": "call-1"}
        self.state = {"messages": [HumanMessage(user_text), AIMessage("")]}


async def _executed(request):
    return ToolMessage(content="ran", tool_call_id=request.tool_call["id"])


def test_interceptor_blocks_or_runs():
    args = {"member_id": "M1003", "procedure_code": "PR-102", "hospital_id": "H01",
            "admission_date": "2026-12-01", "total_bill": 150000, "room_rent_per_day": 6000}
    blocked = asyncio.run(require_user_supplied_amounts(_Request("Cataract cover for M1003?", args), _executed))
    assert blocked.status == "error" and "BLOCKED" in blocked.content
    allowed = asyncio.run(require_user_supplied_amounts(
        _Request("Cataract for M1003, bill Rs 1,50,000, room Rs 6,000", args), _executed))
    assert allowed.content == "ran"


def test_rare_words_win_procedure_search():
    # Regression: "surgery" appears in five procedures and crowded out the fracture procedure
    assert s.search_procedures("fracture surgery")["matches"][0]["code"] == "PR-107"
    assert s.search_procedures("cataract surgery")["matches"][0]["code"] == "PR-102"
