# Health Claims Agent: a LangGraph tool-calling agent over an MCP server

A support agent for a health insurer that answers questions such as *"Member M1003 is having an
appendectomy at Sunrise Multispeciality Hospital on 1 December. The bill is Rs 1,50,000 and the room
is Rs 6,000 a day. How much will insurance pay?"*

To answer, the LLM decides which tools to call: look up the procedure, find the hospital, then run
the claim calculation. It then explains the result in plain language. **The LLM never does the
money maths**: a deterministic, unit-tested calculator does, and the agent only orchestrates.

Everything runs locally and for free with [Ollama](https://ollama.com). Any OpenAI-compatible API
can be swapped in with an environment variable.

> The insurer ("Northwind Health"), members, hospitals and claims are fictional. The rules are
> simplified versions of common Indian health-insurance terms.

## Architecture

```
 user ──► FastAPI /chat ──► LangGraph agent ─────────────┐
                              │  ▲                       │ tool calls
                              ▼  │ tool results          ▼
                         LLM (Ollama /           MCP client ══ stdio ══► MCP server
                         OpenAI-compatible)                               ├─ get_member
                                                                          ├─ search_procedures
              conversation memory:                                        ├─ search_hospitals
              LangGraph checkpointer (thread_id)                          ├─ estimate_claim ─► calculator.py
                                                                          └─ get_claim_status      │
                                                                                 SQLite ◄─────────┘
```

The agent loop is a LangGraph state graph:

```
START ─► agent ──(LLM requested tools?)──► tools ─► agent ─► … ─► END
                 └──(no: final answer)──────────────────────────► END
```

| Piece | Choice | Why |
|---|---|---|
| Agent loop | LangGraph `StateGraph` with `ToolNode` | explicit, inspectable control flow; step limit; conversation memory via a checkpointer |
| Tools | MCP server (`FastMCP`, stdio) | standard protocol: the same tools work with any MCP-compatible client, not just this agent |
| Tool loading | `langchain-mcp-adapters` | turns MCP tools into LangChain tools with no glue code |
| Money | `calculator.py` with `Decimal`, rounded half-up | LLMs are unreliable at arithmetic; money must be exact and testable |
| Data | in-memory SQLite seeded from `data/seed.json` | stands in for policy-admin and claims systems |
| LLM | `qwen2.5:7b` via Ollama (default) | free, local, good tool calling; `LLM_PROVIDER=openai` for hosted models |
| Guardrail | `ToolNode(awrap_tool_call=...)` interceptor | blocks a tool call in code when its amounts were never given by the user |
| API | FastAPI `/chat` returning the answer **and every tool call** | answers can be audited: you see exactly which data the agent used |

### Claim rules implemented by the calculator

1. Policy must be active and the procedure not permanently excluded.
2. 30-day initial waiting period (accidents exempt).
3. Specific-disease waiting periods (e.g. 24 months for knee replacement or cataract).
4. Pre-existing-disease waiting period, set per plan.
5. Room-rent cap with **proportional deduction**: a room above the plan's limit scales down the whole bill.
6. Co-pay per plan, plus 10% at a non-network hospital (reimbursement instead of cashless).
7. Capped at the sum insured remaining for the year.

## Results

18 labelled support scenarios ([`evals/scenarios.jsonl`](evals/scenarios.jsonl)): claim status,
plan lookups, payout estimates, claims that are not covered (waiting periods, lapsed policy,
exclusion), and safety cases (unknown member; a question with no bill amount). A scenario passes only
if the answer contains the exact expected facts (e.g. "Rs 67,500"), the agent called the required
tools, and it called no forbidden tool. Full reports: [7B](evals/results-qwen2.5-7b.md),
[3B](evals/results-qwen2.5-3b.md), [first 7B run](evals/results-qwen2.5-7b-before-tool-fixes.md).

| Model (local, RTX 3050 4 GB) | Passed | Estimates exact | Not-covered explained | Mean tool calls | Median latency |
|---|---|---|---|---|---|
| **`qwen2.5:7b`** | **17/18 (94%)** | **6/6** | **5/5** | 2.6 | 81 s |
| `qwen2.5:3b` | 15/18 (83%) | 5/6 | 4/5 | 1.6 | 19 s |

The one 7B "failure" (s18) is the safety case with no bill amount: the model still *tried* to call
`estimate_claim` with an invented bill. The guardrail blocked the call, and the agent then asked the
customer for the bill and room rent, which is the correct outcome. The eval counts the attempt as a
failure anyway, because the model's own behaviour isn't safe; only the guardrail made it safe.

### How it got there

| Version | 7B | 3B | What changed |
|---|---|---|---|
| 1. First build | 15/18 | – | |
| 2. Tool output fixes | 16/18 | 15/18 | search returns only the best matches, as one JSON object; errors say how to recover |
| 3. Search ranking + guardrail | **17/18** | 15/18 | rare words weigh more in search; code check that amounts came from the user |

Version 1 ran with an 8k-token context window; versions 2–3 use 4k to fit in laptop memory.

### What I learned building it

1. **Keep arithmetic out of the LLM.** Every rupee amount comes from `calculator.py` (Decimal,
   unit-tested with hand-worked examples). The agent picks the inputs and explains the result.
2. **Tools are designed for a model, not a human.** In version 1, searching "Lakeview Clinic
   Kolkata" also returned another Kolkata hospital; the agent used the wrong one and told the
   customer their bill was fully covered, missing the 10% non-network co-pay. Returning only the
   best matches fixed it. Error messages now say how to recover ("use search_hospitals to get the ID")
   instead of only what failed, after the agent guessed a hospital ID that didn't exist.
3. **Search ranking matters inside tools too.** "fracture surgery" matched five procedures on the
   word "surgery", and the fracture procedure was cut from the results. Weighting rare words more
   (inverse document frequency, the idea behind BM25) fixed it.
4. **A prompt rule is a request; a code check is a guarantee.** The system prompt says "never make up
   a value", yet the 3B model invented a bill for a question that gave none and confidently said
   "insurance will pay Rs 90,000". [`guardrails.py`](src/claims_agent/guardrails.py) now intercepts
   every tool call (LangGraph `awrap_tool_call`) and blocks `estimate_claim` unless the bill and room
   rent appear in the user's messages (understanding "Rs 1,50,000", "1.5 lakh" and "80k").
5. **Smaller models skip steps.** The 3B model averages 1.6 tool calls against 2.6 for the 7B: it
   often calls `estimate_claim` directly with a guessed procedure code instead of searching first. It
   is 4× faster, but wrong more often. A second guardrail (IDs must come from an earlier tool result)
   is a possible next step.
6. **Agents multiply latency.** Each step is a full LLM call, so 3–4 calls at about 20 s each on a
   4 GB GPU adds up to over a minute. A hosted model would bring this to a few seconds.

## Run it

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com).

```bash
ollama pull qwen2.5:7b
uv sync

uv run claims-agent "What is the status of claim C9002?"    # one question
uv run claims-agent                                           # interactive chat
uv run uvicorn claims_agent.api:app                           # web UI at http://localhost:8000
```

```bash
uv run pytest                                                 # calculator + tool tests (no LLM needed)
uv run python evals/run_eval.py --out results.md              # agent evaluation
```

The MCP server also runs on its own (`uv run claims-mcp`) and can be added to any MCP-compatible
desktop client or IDE as a stdio server.

Settings are environment variables; see [`.env.example`](.env.example).

## Project layout

```
data/seed.json              plans, members, hospitals, procedures, claims
src/claims_agent/
  calculator.py             claim rules and money maths (pure functions)
  db.py                     SQLite data access and search
  mcp_server.py             the five MCP tools
  guardrails.py             blocks tool calls that use amounts the user never gave
  agent.py                  LangGraph agent, system prompt, MCP connection
  cli.py, api.py, static/   terminal chat, REST API, web chat with tool trace
evals/
  scenarios.jsonl           18 labelled support scenarios
  run_eval.py               scoring and report
tests/                      calculator, tool, search and guardrail tests (run in CI)
```

## Next steps

- A guardrail that IDs (procedure, hospital) must come from an earlier tool result, for smaller models
- Human approval before any write action (e.g. filing a claim) using LangGraph interrupts
- Tracing with Langfuse or LangSmith
- LLM-as-judge scoring for tone and completeness alongside the exact-fact checks
- Streaming responses in the web UI
