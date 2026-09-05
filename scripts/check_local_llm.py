import sys
from pathlib import Path as _Path
_ROOT_FOR_IMPORT = _Path(__file__).resolve().parents[1]
if str(_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_ROOT_FOR_IMPORT))

import asyncio
import json
from app.providers.ollama import OllamaProvider


async def main():
    provider = OllamaProvider()
    try:
        health = await provider.health()
        print({
            "ok": bool(health.get("ok")),
            "configured_model": health.get("configured_model"),
            "configured_model_info": health.get("configured_model_info"),
        })

        # Use the same contract the M0 pipeline relies on: non-streaming,
        # think=false, JSON-formatted output for a structured answerer marker.
        result = await provider.generate(
            system="VANILLA_RAG_ANSWERER. Return JSON only.",
            user='Return exactly this JSON object: {"status":"ok","message":"local llm working"}',
        )
        parsed = json.loads(result.text)
        if parsed.get("status") != "ok" or parsed.get("message") != "local llm working":
            raise RuntimeError(f"Unexpected structured output: {parsed!r}")

        print({
            "ok": True,
            "model": result.model,
            "json_mode": True,
            "think_disabled": True,
            "text": result.text,
            "tokens": result.usage.total_tokens,
        })
    except Exception as exc:
        print({"ok": False, "error": str(exc)})
        raise SystemExit(1)


asyncio.run(main())
