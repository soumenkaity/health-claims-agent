"""The agent: an LLM in a LangGraph loop that calls MCP tools until it can answer.

    START -> agent --(LLM asked for tools?)--> tools -> agent -> ... -> END
                   \--(no tool calls: final answer)--> END
"""

import sys
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .config import Settings
from .guardrails import require_user_supplied_amounts

SYSTEM_PROMPT = """You are a claims support assistant for Northwind Health Insurance in India. Today is {today}.

Rules:
1. Get every fact from the tools. Never invent member details, procedure codes, hospital details, rules or amounts.
2. Never calculate money yourself. For any question about how much will be paid or covered, call estimate_claim
   and report its insurer_pays and member_pays numbers exactly, with the main reasons from its steps.
3. estimate_claim needs: member ID, procedure, hospital, admission date, total bill and room rent per day.
   Always look up procedure codes with search_procedures and hospital IDs with search_hospitals; never guess an ID.
   If the user has not given some of these facts, ask for all of the missing ones in one message.
   Never assume, estimate or make up a value the user did not give.
4. If a tool returns an error, such as a member that does not exist, tell the user plainly and stop. Do not
   continue with made-up data.
5. If a claim is not covered, explain why using reasons_not_covered.
6. Write amounts in rupees, e.g. Rs 67,500. Be concise and friendly."""


def make_llm(settings: Settings) -> BaseChatModel:
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.chat_model, base_url=settings.ollama_url, temperature=0,
                          num_ctx=settings.num_ctx)
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.chat_model, base_url=settings.openai_base_url,
                          api_key=settings.openai_api_key, temperature=0)
    raise ValueError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'")


def build_graph(llm: BaseChatModel, tools: list, today: str, checkpointer=None):
    llm_with_tools = llm.bind_tools(tools)
    system = SystemMessage(SYSTEM_PROMPT.format(today=today))

    async def agent(state: MessagesState) -> dict:
        reply = await llm_with_tools.ainvoke([system, *state["messages"]])
        return {"messages": [reply]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    # Every tool call passes through the guardrail before it runs.
    graph.add_node("tools", ToolNode(tools, awrap_tool_call=require_user_supplied_amounts))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # tool calls -> "tools", otherwise -> END
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)


@dataclass
class ToolCall:
    name: str
    args: dict
    result: str


@dataclass
class TurnResult:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    llm_calls: int = 0
    latency_ms: int = 0


class ClaimsAgent:
    def __init__(self, graph, settings: Settings):
        self.graph = graph
        self.settings = settings

    async def ask(self, question: str, thread_id: str | None = None) -> TurnResult:
        """Run one user turn. Pass the same thread_id to continue a conversation."""
        config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())},
                  "recursion_limit": self.settings.max_steps * 2}
        before = 0
        if thread_id:
            snapshot = await self.graph.aget_state(config)
            before = len(snapshot.values.get("messages", [])) if snapshot.values else 0

        start = time.perf_counter()
        state = await self.graph.ainvoke({"messages": [HumanMessage(question)]}, config)
        latency = int((time.perf_counter() - start) * 1000)

        new = state["messages"][before:]
        results = {m.tool_call_id: m.content for m in new if isinstance(m, ToolMessage)}
        calls = [
            ToolCall(tc["name"], tc["args"], _text(results.get(tc["id"], "")))
            for m in new if isinstance(m, AIMessage) for tc in m.tool_calls
        ]
        llm_calls = sum(isinstance(m, AIMessage) for m in new)
        return TurnResult(_text(state["messages"][-1].content), calls, llm_calls, latency)


def _text(content) -> str:
    """Tool and model content can be a string or a list of content blocks."""
    if isinstance(content, str):
        return content
    return "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)


@asynccontextmanager
async def open_agent(settings: Settings | None = None):
    """Start the MCP server as a subprocess, load its tools, and yield a ready agent."""
    settings = settings or Settings()
    client = MultiServerMCPClient({
        "claims": {"command": sys.executable, "args": ["-m", "claims_agent.mcp_server"], "transport": "stdio"},
    })
    async with client.session("claims") as session:
        tools = await load_mcp_tools(session)
        graph = build_graph(make_llm(settings), tools, settings.today, checkpointer=InMemorySaver())
        yield ClaimsAgent(graph, settings)
