from __future__ import annotations

import json

from .execution_manager import execute_python
from .ollama_client import chat_with_ollama


def run_agent_turn(text: str, settings: dict[str, str]) -> dict:
    try:
        first_response = chat_with_ollama(
            base_url=settings["ollama_base_url"],
            model=settings["model"],
            system_prompt=settings["system_prompt"],
            user_text=text,
        )
    except (ConnectionError, ValueError) as exc:
        return {
            "response": f"Ollamaに接続できませんでした: {exc}",
            "tool_result": None,
        }

    tool_call = _parse_tool_call(first_response)
    if tool_call is None:
        return {"response": first_response, "tool_result": None}

    if tool_call.get("tool") != "run_python":
        return {
            "response": "未対応のツール呼び出しです。",
            "tool_result": None,
        }

    code = tool_call.get("arguments", {}).get("code", "")
    result = execute_python(code)
    follow_up_text = (
        "次のPython実行結果を踏まえて、ユーザーに最終回答を返してください。\n\n"
        f"ユーザー入力:\n{text}\n\n"
        f"stdout:\n{result['stdout']}\n\n"
        f"stderr:\n{result['stderr']}\n\n"
        f"exit_code: {result['exit_code']}"
    )
    try:
        final_response = chat_with_ollama(
            base_url=settings["ollama_base_url"],
            model=settings["model"],
            system_prompt=settings["system_prompt"],
            user_text=follow_up_text,
        )
    except (ConnectionError, ValueError):
        final_response = (
            "Pythonを実行しましたが、最終回答の生成に失敗しました。"
            "実行結果を確認してください。"
        )

    return {"response": final_response, "tool_result": result}


def _parse_tool_call(content: str) -> dict | None:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and "tool" in parsed:
        return parsed
    return None
