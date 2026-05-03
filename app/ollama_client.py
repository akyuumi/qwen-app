from __future__ import annotations

import json
import urllib.error
import urllib.request


def chat_with_ollama(
    *,
    base_url: str,
    model: str,
    system_prompt: str,
    user_text: str,
    timeout: int = 120,
) -> str:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }
    url = base_url.rstrip("/") + "/api/chat"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.reason
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            detail = error_body.get("error", detail)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        raise ConnectionError(f"Ollama request failed: {detail}") from exc
    except TimeoutError as exc:
        raise ConnectionError(f"Ollama request timed out after {timeout} seconds") from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(f"Ollama request failed: {exc.reason}") from exc

    message = data.get("message", {})
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("Ollama response did not contain message.content")
    return content
