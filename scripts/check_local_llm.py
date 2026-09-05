import sys
from pathlib import Path as _Path
_ROOT_FOR_IMPORT = _Path(__file__).resolve().parents[1]
if str(_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_ROOT_FOR_IMPORT))

import asyncio
import json
from app.providers.ollama import OllamaProvider


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


async def main() -> int:
    try:
        provider = OllamaProvider()
        health = await provider.health()
        emit({
            "ok": bool(health.get("ok")),
            "provider": health.get("provider", provider.name),
            "base_url": health.get("base_url", provider.base_url),
            "ollama_reachable": bool(health.get("ollama_reachable")),
            "configured_model": health.get("configured_model"),
            "model_available": bool(health.get("model_available")),
            "model_digest": health.get("model_digest"),
            "configured_model_info": health.get("configured_model_info"),
        })
        if not health.get("ok") or not health.get("model_available"):
            raise RuntimeError(
                f"Configured local model is unavailable: {provider.model}"
            )

        # Use the same contract the M0 pipeline relies on: non-streaming,
        # think=false, JSON-formatted output for a structured answerer marker.
        result = await provider.generate(
            system="VANILLA_RAG_ANSWERER. Return JSON only.",
            user='Return exactly this JSON object: {"status":"ok","message":"local llm working"}',
        )
        parsed = json.loads(result.text)
        if not isinstance(parsed, dict) or parsed.get("status") != "ok" or parsed.get("message") != "local llm working":
            raise RuntimeError(f"Unexpected structured output: {parsed!r}")

        emit({
            "ok": True,
            "provider": provider.name,
            "model": result.model,
            "json_mode": True,
            "think_disabled": True,
            "text": result.text,
            "tokens": result.usage.total_tokens,
        })
        return 0
    except Exception as exc:
        emit({"ok": False, "error_type": type(exc).__name__, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
