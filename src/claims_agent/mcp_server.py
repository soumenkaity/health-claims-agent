"""MCP server exposing the claims tools.

MCP (Model Context Protocol) is an open standard for giving AI applications tools and data. This
server can be used by the LangGraph agent in this repo or by any other MCP-compatible client.

    uv run claims-mcp          # starts the server on stdio
"""

from datetime import date

from mcp.server.fastmcp import FastMCP

from . import calculator, db

mcp = FastMCP("northwind-health-claims", log_level="WARNING")
conn = db.connect()


_HOW_TO_FIND = {
    "procedure": "Use search_procedures with the procedure name to get its code.",
    "hospital": "Use search_hospitals with the hospital name to get its ID.",
    "member": "Ask the user to check their member ID.",
    "claim": "Ask the user to check the claim ID.",
}


def _not_found(kind: str, value: str) -> dict:
    # Error messages are written for the agent: they say how to recover, not just what failed.
    return {"error": f"No {kind} found with ID '{value}'. {_HOW_TO_FIND[kind]}"}


@mcp.tool()
def get_member(member_id: str) -> dict:
    """Look up a policy member by member ID (for example "M1003").

    Returns the member's name, policy status, policy start date, declared pre-existing diseases,
    and their plan rules: sum insured, sum insured remaining this year, room-rent limit per day,
    co-pay percentage and pre-existing-disease waiting period.
    """
    member = db.get_member(conn, member_id)
    if not member:
        return _not_found("member", member_id)
    plan = db.get_plan(conn, member["plan"])
    return {
        **member,
        "plan_rules": {
            **plan,
            "sum_insured_remaining": plan["sum_insured"] - member["sum_insured_used"],
            "room_rent_limit_per_day": plan["room_rent_limit_per_day"] or "no limit",
            "initial_waiting_days": calculator.INITIAL_WAIT_DAYS,
            "extra_copay_pct_at_non_network_hospital": calculator.NON_NETWORK_EXTRA_COPAY_PCT,
        },
    }


@mcp.tool()
def search_procedures(query: str) -> dict:
    """Find medical procedures by name or description (for example "knee replacement" or "appendix").

    Returns {"matches": [...]}: the best matches, each with its procedure code (needed by
    estimate_claim), waiting period in months, related pre-existing condition, whether it is an
    accident, and whether it is excluded from cover.
    """
    matches = db.search_procedures(conn, query)
    return {"matches": matches} if matches else {"error": f"No procedure matches '{query}'. Try other words."}


@mcp.tool()
def search_hospitals(query: str) -> dict:
    """Find hospitals by name and/or city. Returns {"matches": [...]}: the best matches, each with its
    hospital ID (needed by estimate_claim), city, and whether it is a network hospital (network =
    cashless claims). Use the ID of the hospital whose name the user gave."""
    matches = db.search_hospitals(conn, query)
    return {"matches": matches} if matches else {"error": f"No hospital matches '{query}'. Try the hospital name."}


@mcp.tool()
def estimate_claim(member_id: str, procedure_code: str, hospital_id: str, admission_date: str,
                   total_bill: int, room_rent_per_day: int) -> dict:
    """Calculate how much the insurer will pay for a hospitalisation, and how much the member pays.

    Always use this tool for any amount question; it applies waiting periods, room-rent proportional
    deduction, co-pay and the remaining sum insured.

    Args:
        member_id: e.g. "M1003"
        procedure_code: code from search_procedures, e.g. "PR-103"
        hospital_id: ID from search_hospitals, e.g. "H01"
        admission_date: YYYY-MM-DD
        total_bill: total hospital bill in rupees, a whole number such as 150000
        room_rent_per_day: room rent per day in rupees, e.g. 4500
    """
    member = db.get_member(conn, member_id)
    procedure = db.get_procedure(conn, procedure_code)
    hospital = db.get_hospital(conn, hospital_id)
    for kind, value, found in (("member", member_id, member), ("procedure", procedure_code, procedure),
                               ("hospital", hospital_id, hospital)):
        if not found:
            return _not_found(kind, value)
    try:
        admitted = date.fromisoformat(admission_date)
    except ValueError:
        return {"error": f"admission_date '{admission_date}' must be in YYYY-MM-DD format."}
    try:
        result = calculator.estimate(member, db.get_plan(conn, member["plan"]), procedure, hospital,
                                     admitted, int(total_bill), int(room_rent_per_day))
    except ValueError as e:
        return {"error": str(e)}
    return {"member": member["name"], "procedure": procedure["name"], "hospital": hospital["name"],
            **result.to_dict()}


@mcp.tool()
def get_claim_status(claim_id: str) -> dict:
    """Get the status of an existing claim by claim ID (for example "C9002"): status, billed and
    approved amounts, and remarks explaining the decision or what is pending."""
    claim = db.get_claim(conn, claim_id)
    return claim or _not_found("claim", claim_id)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
