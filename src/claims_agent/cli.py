"""Chat with the agent in the terminal.

    uv run claims-agent "What is the status of claim C9002?"
    uv run claims-agent            # interactive conversation
"""

import asyncio
import json
import sys
import uuid

from .agent import open_agent


def _show(result) -> None:
    for call in result.tool_calls:
        print(f"  -> {call.name}({json.dumps(call.args)})")
    print(f"\n{result.answer}\n  [{result.llm_calls} LLM calls, {result.latency_ms / 1000:.1f}s]\n")


async def _run(question: str | None) -> None:
    async with open_agent() as agent:
        if question:
            _show(await agent.ask(question))
            return
        thread = str(uuid.uuid4())
        print("Northwind Health claims assistant. Type 'exit' to quit.\n")
        while (line := input("you> ").strip()).lower() not in {"exit", "quit"}:
            if line:
                _show(await agent.ask(line, thread))


def main() -> None:
    asyncio.run(_run(" ".join(sys.argv[1:]) or None))


if __name__ == "__main__":
    main()
