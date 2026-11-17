"""Calculator tests. Every expected amount is worked out by hand in the comment next to it."""

from datetime import date

import pytest

from claims_agent import calculator, db

conn = db.connect()


def est(member_id, procedure, hospital, admitted, bill, room):
    m = db.get_member(conn, member_id)
    return calculator.estimate(m, db.get_plan(conn, m["plan"]), db.get_procedure(conn, procedure),
                               db.get_hospital(conn, hospital), date.fromisoformat(admitted), bill, room)


def test_room_rent_proportional_deduction_and_copay():
    # SILVER: limit 3000, co-pay 10%. 150000 * 3000/6000 = 75000; * 0.9 = 67500
    e = est("M1003", "PR-103", "H02", "2026-12-01", 150000, 6000)
    assert (e.covered, e.insurer_pays, e.member_pays, e.claim_type) == (True, 67500, 82500, "cashless")


def test_proportional_deduction_rounds_half_up_to_rupees():
    # GOLD: limit 5000, no co-pay. 100000 * 5000/5500 = 90909.09 -> 90909
    e = est("M1001", "PR-103", "H02", "2026-12-15", 100000, 5500)
    assert (e.insurer_pays, e.member_pays) == (90909, 9091)


def test_room_within_limit_pays_full_bill():
    e = est("M1007", "PR-103", "H01", "2026-12-05", 120000, 4500)
    assert e.insurer_pays == 120000


def test_non_network_hospital_adds_ten_percent_copay():
    # GOLD at a non-network hospital: 60000 * 0.9 = 54000, paid as reimbursement
    e = est("M1001", "PR-106", "H03", "2026-12-01", 60000, 3000)
    assert (e.insurer_pays, e.claim_type) == (54000, "reimbursement")


def test_capped_at_sum_insured_remaining():
    # SENIOR: co-pay 20% -> 250000 * 0.8 = 200000, but only 500000 - 410000 = 90000 remains
    e = est("M1005", "PR-104", "H04", "2026-12-01", 250000, 4000)
    assert e.insurer_pays == 90000


def test_platinum_has_no_room_rent_limit():
    e = est("M1008", "PR-103", "H01", "2026-12-01", 200000, 20000)
    assert e.insurer_pays == 200000


def test_initial_waiting_period_blocks_illness_claims():
    # Policy started 2026-10-25; 16 days later is inside the 30-day initial waiting period
    e = est("M1002", "PR-106", "H01", "2026-11-10", 60000, 2500)
    assert not e.covered and e.insurer_pays == 0 and "Initial waiting period" in e.reasons_not_covered[0]


def test_accidents_skip_the_initial_waiting_period():
    # SILVER co-pay 10%: 90000 * 0.9 = 81000
    e = est("M1002", "PR-107", "H01", "2026-11-10", 90000, 2500)
    assert e.covered and e.insurer_pays == 81000


def test_specific_disease_waiting_period():
    # Knee replacement needs 24 months; 2025-02-01 -> 2026-12-10 is 22 months
    e = est("M1007", "PR-101", "H01", "2026-12-10", 300000, 4000)
    assert not e.covered and "Specific-disease" in e.reasons_not_covered[0]


def test_pre_existing_disease_waiting_period():
    # Rohan declared diabetes; GOLD covers it after 24 months; 2025-09-01 -> 2026-12-01 is 15 months
    assert not est("M1009", "PR-108", "H01", "2026-12-01", 80000, 3000).covered
    # Aarav also declared diabetes but has held the policy since 2023-04-01 (44 months)
    assert est("M1001", "PR-108", "H01", "2026-12-01", 80000, 3000).insurer_pays == 80000


def test_lapsed_policy_and_excluded_procedure():
    assert not est("M1006", "PR-103", "H01", "2026-12-01", 80000, 3000).covered
    assert not est("M1008", "PR-109", "H01", "2026-12-01", 80000, 3000).covered


@pytest.mark.parametrize("start,end,months", [
    ("2025-01-15", "2025-02-15", 1),
    ("2025-01-31", "2025-02-28", 0),
    ("2025-02-01", "2026-12-10", 22),
])
def test_months_between(start, end, months):
    assert calculator.months_between(date.fromisoformat(start), date.fromisoformat(end)) == months


def test_rejects_invalid_amounts():
    with pytest.raises(ValueError):
        est("M1003", "PR-103", "H02", "2026-12-01", 0, 6000)
