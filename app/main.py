from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import run_agent_turn
from .config import STATIC_DIR
from .database import get_settings, init_db, list_executions, update_settings
from .execution_manager import execute_python


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str
    tool_result: dict | None = None


class PythonExecutionRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20_000)


class ProfileUpdateRequest(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=100)
    ollama_base_url: str | None = Field(default=None, min_length=1, max_length=300)
    system_prompt: str | None = Field(default=None, min_length=1, max_length=4000)


app = FastAPI(title="Qwen Local Agent", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> dict:
    return run_agent_turn(request.text, get_settings())


@app.post("/api/run-python")
def run_python(request: PythonExecutionRequest) -> dict:
    return execute_python(request.code)


@app.get("/api/executions")
def executions(limit: int = 20) -> list[dict]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return list_executions(limit)


@app.get("/api/profile")
def get_profile() -> dict[str, str]:
    return get_settings()


@app.put("/api/profile")
def update_profile(request: ProfileUpdateRequest) -> dict[str, str]:
    values = request.model_dump(exclude_none=True)
    return update_settings(values)
