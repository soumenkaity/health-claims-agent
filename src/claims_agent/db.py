"""Read-only data access over an in-memory SQLite database loaded from data/seed.json.

In a real insurer this module would talk to the policy-admin and claims systems; the agent never
sees SQL, only the tool functions built on top of this module.
"""

import json
import math
import re
import sqlite3
from pathlib import Path

SEED = Path(__file__).resolve().parents[2] / "data" / "seed.json"

SCHEMA = """
CREATE TABLE plans (code TEXT PRIMARY KEY, sum_insured INTEGER, room_rent_limit_per_day INTEGER,
                    copay_pct INTEGER, ped_wait_months INTEGER);
CREATE TABLE members (member_id TEXT PRIMARY KEY, name TEXT, plan TEXT REFERENCES plans(code),
                      policy_start TEXT, status TEXT, sum_insured_used INTEGER, pre_existing TEXT);
CREATE TABLE hospitals (hospital_id TEXT PRIMARY KEY, name TEXT, city TEXT, network INTEGER);
CREATE TABLE procedures (code TEXT PRIMARY KEY, name TEXT, keywords TEXT, specific_wait_months INTEGER,
                         related_condition TEXT, accident INTEGER, excluded INTEGER);
CREATE TABLE claims (claim_id TEXT PRIMARY KEY, member_id TEXT, hospital_id TEXT, procedure_code TEXT,
                     submitted_on TEXT, billed_amount INTEGER, status TEXT, approved_amount INTEGER, remarks TEXT);
"""


def connect(seed_path: Path = SEED) -> sqlite3.Connection:
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for table, rows in data.items():
        for row in rows:
            row = {k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()}
            cols = ", ".join(row)
            conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({', '.join('?' * len(row))})", list(row.values()))
    return conn


def _row(r: sqlite3.Row | None) -> dict | None:
    return dict(r) if r else None


def get_member(conn, member_id: str) -> dict | None:
    m = _row(conn.execute("SELECT * FROM members WHERE member_id = ?", (member_id.strip().upper(),)).fetchone())
    if m:
        m["pre_existing"] = json.loads(m["pre_existing"])
    return m


def get_plan(conn, code: str) -> dict | None:
    return _row(conn.execute("SELECT * FROM plans WHERE code = ?", (code,)).fetchone())


def get_hospital(conn, hospital_id: str) -> dict | None:
    h = _row(conn.execute("SELECT * FROM hospitals WHERE hospital_id = ?", (hospital_id.strip().upper(),)).fetchone())
    if h:
        h["network"] = bool(h["network"])
    return h


def get_procedure(conn, code: str) -> dict | None:
    p = _row(conn.execute("SELECT * FROM procedures WHERE code = ?", (code.strip().upper(),)).fetchone())
    if p:
        p["accident"], p["excluded"] = bool(p["accident"]), bool(p["excluded"])
    return p


def get_claim(conn, claim_id: str) -> dict | None:
    return _row(conn.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id.strip().upper(),)).fetchone())


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _search(rows: list[dict], query: str, fields: list[str], limit: int = 3) -> list[dict]:
    """Return the best-matching rows (ties included, up to `limit`).

    Each matched word scores its inverse document frequency, log(N / rows containing it), so rare,
    specific words count more than common ones: in "fracture surgery", "fracture" (1 procedure)
    outweighs "surgery" (5 procedures). Weaker matches are dropped on purpose: when "Lakeview
    Clinic Kolkata" also returned every other Kolkata hospital, the agent sometimes picked the wrong one.
    """
    docs = [_words(" ".join(str(row[f]) for f in fields)) for row in rows]
    idf = {w: math.log(len(docs) / sum(w in d for d in docs)) + 1e-6 for w in _words(query) if any(w in d for d in docs)}
    scored = [(round(sum(idf[w] for w in idf if w in d), 9), row) for d, row in zip(docs, rows)]
    best = max((score for score, _ in scored), default=0)
    if best <= 0:
        return []
    return [row for score, row in scored if score == best][:limit]


def search_procedures(conn, query: str) -> list[dict]:
    rows = [get_procedure(conn, r["code"]) for r in conn.execute("SELECT code FROM procedures")]
    return _search(rows, query, ["name", "keywords", "code"])


def search_hospitals(conn, query: str) -> list[dict]:
    rows = [get_hospital(conn, r["hospital_id"]) for r in conn.execute("SELECT hospital_id FROM hospitals")]
    return _search(rows, query, ["name", "city", "hospital_id"])
