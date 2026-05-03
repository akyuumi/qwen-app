from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "agent.sqlite3"
STATIC_DIR = BASE_DIR / "web"

DEFAULT_MODEL = "qwen2.5-coder"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_SYSTEM_PROMPT = (
    "You are a local AI agent. Treat generated code as untrusted. "
    "When Python execution is needed, respond only with JSON in this shape: "
    '{"tool":"run_python","arguments":{"code":"print(\'hello\')"}}. '
    "Otherwise answer normally in Japanese."
)
