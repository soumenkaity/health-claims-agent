"""Deterministic claim estimate. The LLM never does this arithmetic: it calls this code through a tool.

Rules (simplified versions of common Indian health-insurance terms):
  1. The policy must be ACTIVE and the procedure must not be excluded.
  2. Initial waiting period: no cover in the first 30 days of the policy, except accidents.
  3. Specific-disease waiting period: some procedures are covered only after N months.
  4. Pre-existing disease (PED) waiting period: if the procedure treats a condition the member
     declared at purchase, it is covered only after the plan's PED waiting period.
  5. Room-rent cap with proportional deduction: if the room costs more per day than the plan
     allows, the whole bill is scaled by (limit / actual room rent).
  6. Co-pay: the member pays the plan's co-pay %, plus 10% extra at a non-network hospital.
  7. The insurer pays at most the sum insured remaining for the policy year.
Money uses Decimal, rounded half-up to whole rupees.
"""

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

INITIAL_WAIT_DAYS = 30
NON_NETWORK_EXTRA_COPAY_PCT = 10


@dataclass
class Estimate:
    covered: bool
    total_bill: int
    insurer_pays: int
    member_pays: int
    claim_type: str  # "cashless" at network hospitals, "reimbursement" elsewhere
    steps: list[str] = field(default_factory=list)
    reasons_not_covered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def months_between(start: date, end: date) -> int:
    """Completed months from start to end."""
    return (end.year - start.year) * 12 + (end.month - start.month) - (1 if end.day < start.day else 0)


def _rupees(x: Decimal) -> int:
    return int(x.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def estimate(member: dict, plan: dict, procedure: dict, hospital: dict,
             admission_date: date, total_bill: int, room_rent_per_day: int) -> Estimate:
    if total_bill <= 0 or room_rent_per_day < 0:
        raise ValueError("total_bill must be positive and room_rent_per_day cannot be negative")

    claim_type = "cashless" if hospital["network"] else "reimbursement"
    start = date.fromisoformat(member["policy_start"])
    reasons = []

    if member["status"] != "ACTIVE":
        reasons.append(f"The policy status is {member['status']}, so no claim is payable.")
    if procedure["excluded"]:
        reasons.append(f"{procedure['name']} is a permanent exclusion under the policy.")
    if admission_date < start:
        reasons.append("The admission date is before the policy start date.")
    else:
        days = (admission_date - start).days
        months = months_between(start, admission_date)
        if days < INITIAL_WAIT_DAYS and not procedure["accident"]:
            reasons.append(
                f"Initial waiting period: only {days} days since the policy started on {start}; "
                f"non-accident claims need {INITIAL_WAIT_DAYS} days."
            )
        if months < procedure["specific_wait_months"]:
            reasons.append(
                f"Specific-disease waiting period: {procedure['name']} is covered after "
                f"{procedure['specific_wait_months']} months; the policy is {months} months old."
            )
        if procedure["related_condition"] in member["pre_existing"] and months < plan["ped_wait_months"]:
            reasons.append(
                f"Pre-existing disease waiting period: {procedure['related_condition']} was declared at purchase; "
                f"the {plan['code']} plan covers it after {plan['ped_wait_months']} months; the policy is {months} months old."
            )

    if reasons:
        return Estimate(False, total_bill, 0, total_bill, claim_type, [], reasons)

    steps = [f"Total bill: Rs {total_bill}."]
    eligible = Decimal(total_bill)

    limit = plan["room_rent_limit_per_day"]
    if limit is not None and room_rent_per_day > limit:
        eligible = eligible * Decimal(limit) / Decimal(room_rent_per_day)
        steps.append(
            f"Room rent Rs {room_rent_per_day}/day is above the {plan['code']} limit of Rs {limit}/day, "
            f"so the bill is reduced proportionally ({limit}/{room_rent_per_day}) to Rs {_rupees(eligible)}."
        )
    else:
        steps.append("Room rent is within the plan limit, so no proportional deduction applies.")

    copay = plan["copay_pct"] + (0 if hospital["network"] else NON_NETWORK_EXTRA_COPAY_PCT)
    if copay:
        eligible = eligible * (Decimal(100 - copay) / Decimal(100))
        why = f"{plan['copay_pct']}% plan co-pay" if plan["copay_pct"] else ""
        if not hospital["network"]:
            why = (why + " + " if why else "") + f"{NON_NETWORK_EXTRA_COPAY_PCT}% non-network co-pay"
        steps.append(f"Co-pay of {copay}% ({why}) leaves Rs {_rupees(eligible)}.")

    remaining = plan["sum_insured"] - member["sum_insured_used"]
    if eligible > remaining:
        eligible = Decimal(remaining)
        steps.append(f"Capped at the sum insured remaining for this policy year: Rs {remaining}.")

    insurer = _rupees(eligible)
    steps.append(f"Insurer pays Rs {insurer}; member pays Rs {total_bill - insurer}.")
    return Estimate(True, total_bill, insurer, total_bill - insurer, claim_type, steps, [])
