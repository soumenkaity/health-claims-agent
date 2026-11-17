"""REST API + chat page.  Run:  uv run uvicorn claims_agent.api:app"""

from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import open_agent

STATIC = Path(__file__).parent / "static"
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        state["agent"] = await stack.enter_async_context(open_agent())
        yield


app = FastAPI(title="Northwind Health Claims Agent", version="0.1.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    thread_id: str = Field(min_length=1, max_length=100, description="Same ID = same conversation")


class ToolCallOut(BaseModel):
    name: str
    args: dict
    result: str


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCallOut]
    llm_calls: int
    latency_ms: int


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        r = await state["agent"].ask(req.message, req.thread_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Agent failed: {e}") from e
    return ChatResponse(answer=r.answer, llm_calls=r.llm_calls, latency_ms=r.latency_ms,
                        tool_calls=[ToolCallOut(name=c.name, args=c.args, result=c.result) for c in r.tool_calls])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": state["agent"].settings.chat_model}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
