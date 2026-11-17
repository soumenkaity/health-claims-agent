"""Tool-level tests: call the MCP tool functions directly, plus check what the server advertises."""

import asyncio

from claims_agent import mcp_server as s


def test_server_advertises_all_tools():
    tools = asyncio.run(s.mcp.list_tools())
    assert {t.name for t in tools} == {
        "get_member", "search_procedures", "search_hospitals", "estimate_claim", "get_claim_status"}
    estimate = next(t for t in tools if t.name == "estimate_claim")
    assert set(estimate.inputSchema["required"]) == {
        "member_id", "procedure_code", "hospital_id", "admission_date", "total_bill", "room_rent_per_day"}


def test_get_member_includes_plan_rules():
    m = s.get_member("m1003")
    assert m["name"] == "Rahul Verma"
    assert m["plan_rules"]["sum_insured_remaining"] == 180000
    assert m["plan_rules"]["room_rent_limit_per_day"] == 3000


def test_unknown_ids_return_errors_not_exceptions():
    assert "error" in s.get_member("M9999")
    assert "error" in s.get_claim_status("C0000")
    assert "error" in s.estimate_claim("M1003", "PR-999", "H01", "2026-12-01", 1000, 100)
    assert "error" in s.estimate_claim("M1003", "PR-103", "H01", "01/12/2026", 1000, 100)


def test_search_matches_everyday_words():
    assert s.search_procedures("appendix removal")["matches"][0]["code"] == "PR-103"
    assert s.search_procedures("broken bone")["matches"][0]["code"] == "PR-107"
    assert s.search_hospitals("Green Valley Pune")["matches"][0]["hospital_id"] == "H05"


def test_search_returns_only_the_best_matches():
    # Regression: City Care Hospital (also in Kolkata) used to be returned too, and the agent picked it
    assert [h["hospital_id"] for h in s.search_hospitals("Lakeview Clinic Kolkata")["matches"]] == ["H03"]
    # A city-only search still lists every hospital in that city
    assert {h["hospital_id"] for h in s.search_hospitals("Kolkata")["matches"]} == {"H01", "H03"}
    assert "error" in s.search_procedures("teleportation")


def test_errors_tell_the_agent_how_to_recover():
    assert "search_hospitals" in s.estimate_claim("M1003", "PR-103", "HC02", "2026-12-01", 1000, 100)["error"]


def test_estimate_claim_tool_returns_breakdown():
    r = s.estimate_claim("M1003", "PR-103", "H02", "2026-12-01", 150000, 6000)
    assert r["insurer_pays"] == 67500
    assert any("proportionally" in step for step in r["steps"])
