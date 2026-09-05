from __future__ import annotations
import os
import uuid
import httpx
from app.core.types import ProviderResult, Usage
from app.providers.base import Provider

class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: float | None = None):
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "qwen3:4b")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout or float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "180"))
        self.temperature = float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.1"))
        self.max_output_tokens = max(64, int(os.getenv("MAX_OUTPUT_TOKENS", "700")))

    async def generate(self, *, system: str, user: str) -> ProviderResult:
        payload = {
            "model": self.model,
            "stream": False,
            # Qwen3 and other reasoning-capable Ollama models may emit a thinking
            # channel unless this is disabled explicitly. Research pipelines
            # need clean machine-readable outputs and comparable token/latency.
            "think": False,
            "messages": [
                {"role":"system","content":system},
                {"role":"user","content":user},
            ],
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_output_tokens,
            },
        }
        marker = system.upper()
        if any(x in marker for x in ("VANILLA_RAG_ANSWERER", "TASK_DECOMPOSER", "WORKER")):
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        text = (data.get("message") or {}).get("content", "")
        inp = int(data.get("prompt_eval_count") or 0)
        out = int(data.get("eval_count") or 0)
        return ProviderResult(text=text, usage=Usage(inp, out), request_id="ollama_"+uuid.uuid4().hex[:10], model=self.model)

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
        models = []
        for m in data.get("models", []):
            models.append({
                "name": m.get("name"),
                "model": m.get("model"),
                "digest": m.get("digest"),
                "size": m.get("size"),
                "modified_at": m.get("modified_at"),
            })
        configured = next((m for m in models if m.get("name") == self.model or m.get("model") == self.model), None)
        return {"ok": True, "models": models, "configured_model": self.model, "configured_model_info": configured}
