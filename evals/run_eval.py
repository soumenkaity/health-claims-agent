"""Run the agent on labelled support scenarios and score it.

    uv run python evals/run_eval.py --out results-qwen2.5-7b.md
    CHAT_MODEL=qwen2.5:3b uv run python evals/run_eval.py --out results-qwen2.5-3b.md

A scenario passes only if all three hold:
  * the final answer contains every required fact (e.g. the exact rupee amount),
  * the agent called every required tool (e.g. estimate_claim for money questions),
  * the agent called no forbidden tool (e.g. estimate_claim when the bill amount is unknown).
"""

import argparse
import asyncio
import json
import os
import re
import statistics
from pathlib import Path

from claims_agent.agent import open_agent
from claims_agent.config import Settings

HERE = Path(__file__).parent
EVAL_TODAY = "2026-11-17"  # scenarios are written relative to this date


def normalize(text: str) -> str:
    text = text.lower().replace("₹", "rs ")
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    return re.sub(r"\s+", " ", text)


def contains_facts(answer: str, groups: list[list[str]]) -> bool:
    norm = normalize(answer)
    return all(any(alt.lower() in norm for alt in group) for group in groups)


async def run(out: str) -> None:
    os.environ.setdefault("AGENT_TODAY", EVAL_TODAY)
    settings = Settings()
    scenarios = [json.loads(l) for l in (HERE / "scenarios.jsonl").read_text(encoding="utf-8").splitlines() if l]
    rows, latencies, tool_counts, llm_counts = [], [], [], []
    by_category: dict[str, list[bool]] = {}

    async with open_agent(settings) as agent:
        for s in scenarios:
            try:
                r = await agent.ask(s["question"])
                answer, called = r.answer, [c.name for c in r.tool_calls]
                latencies.append(r.latency_ms)
                tool_counts.append(len(called))
                llm_counts.append(r.llm_calls)
            except Exception as e:  # a crashed run is a failed scenario, not a crashed eval
                answer, called = f"ERROR: {type(e).__name__}: {e}", []
            facts_ok = contains_facts(answer, s["must_include"])
            tools_ok = set(s["required_tools"]) <= set(called)
            safe_ok = not (set(s["forbidden_tools"]) & set(called))
            ok = facts_ok and tools_ok and safe_ok
            problems = [p for p, good in (("missing facts", facts_ok), ("missing tool", tools_ok),
                                          ("forbidden tool", safe_ok)) if not good]
            by_category.setdefault(s["category"], []).append(ok)
            rows.append((s, ok, called, answer, problems))
            print(f"{s['id']} {'PASS' if ok else 'FAIL ' + ', '.join(problems)}  tools={called}")

    passed = sum(ok for _, ok, *_ in rows)
    lines = [
        "# Agent evaluation results\n",
        f"Chat model `{settings.chat_model}` ({settings.llm_provider}), scenario date {settings.today}.\n",
        "| Metric | Value |", "|---|---|",
        f"| Scenarios passed | {passed}/{len(rows)} ({100 * passed / len(rows):.0f}%) |",
        f"| Required tools called | {sum(set(s['required_tools']) <= set(c) for s, _, c, *_ in rows)}/{len(rows)} |",
        f"| Forbidden tool calls | {sum(bool(set(s['forbidden_tools']) & set(c)) for s, _, c, *_ in rows)} |",
        f"| Mean tool calls per scenario | {statistics.mean(tool_counts or [0]):.1f} |",
        f"| Mean LLM calls per scenario | {statistics.mean(llm_counts or [0]):.1f} |",
        f"| Median latency | {statistics.median(latencies or [0]) / 1000:.1f} s |",
        "",
        "| Category | Passed |", "|---|---|",
        *[f"| {c} | {sum(v)}/{len(v)} |" for c, v in by_category.items()],
        "",
        "## Per-scenario results\n",
        "| ID | Category | Pass | Tools called | Answer |", "|---|---|---|---|---|",
    ]
    for s, ok, called, answer, problems in rows:
        flat = answer.replace("|", "/").replace("\n", " ")
        verdict = "✅" if ok else "❌ " + ", ".join(problems)
        lines.append(f"| {s['id']} | {s['category']} | {verdict} | {', '.join(called) or '-'} | {flat} |")
    (HERE / out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{passed}/{len(rows)} passed. Wrote {HERE / out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results.md")
    asyncio.run(run(parser.parse_args().out))


if __name__ == "__main__":
    main()
