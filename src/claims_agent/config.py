import os
from dataclasses import dataclass, field
from datetime import date


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    # "ollama" (local, free) or "openai" (any OpenAI-compatible API: OpenAI, Groq, Together...)
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "ollama"))
    chat_model: str = field(default_factory=lambda: _env("CHAT_MODEL", "qwen2.5:7b"))
    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://localhost:11434"))
    # Context window for Ollama models; larger needs more memory. 4096 fits these conversations.
    num_ctx: int = field(default_factory=lambda: int(_env("OLLAMA_NUM_CTX", "4096")))
    openai_base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))
    # Fixed "today" makes evals reproducible; defaults to the real date.
    today: str = field(default_factory=lambda: _env("AGENT_TODAY", date.today().isoformat()))
    max_steps: int = field(default_factory=lambda: int(_env("AGENT_MAX_STEPS", "12")))
