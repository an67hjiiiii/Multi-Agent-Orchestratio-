from __future__ import annotations

import math
import os
import uuid
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.types import ProviderResult, Usage
from app.providers.base import Provider


DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:4b"
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_HEALTH_TIMEOUT_SECONDS = 5.0
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_OUTPUT_TOKENS = 700
MIN_OUTPUT_TOKENS = 64
STRUCTURED_OUTPUT_CONFIG_VERSION = "ollama-json-schema-v1"

_LOCAL_HOSTNAMES = frozenset({"localhost"})
_MODEL_FIELDS = ("name", "model", "digest", "size", "modified_at")
_STRUCTURED_MARKERS = ("VANILLA_RAG_ANSWERER", "TASK_DECOMPOSER", "WORKER")


class OllamaConfigurationError(ValueError):
    """Raised when local Ollama configuration violates the provider boundary."""


class OllamaProtocolError(RuntimeError):
    """Raised when Ollama returns a response outside the adapter contract."""


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ):
        model_value = model if model is not None else os.getenv("LOCAL_LLM_MODEL", DEFAULT_MODEL)
        base_url_value = base_url if base_url is not None else os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        timeout_value = timeout if timeout is not None else os.getenv(
            "LOCAL_LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)
        )

        self.model = self._validate_model(model_value)
        self.base_url = self._validate_base_url(base_url_value)
        self.timeout = self._positive_float(timeout_value, "LOCAL_LLM_TIMEOUT_SECONDS")

        temperature = os.getenv("LOCAL_LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE))
        self.temperature = self._non_negative_float(temperature, "LOCAL_LLM_TEMPERATURE")

        max_output_tokens = os.getenv("MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS))
        self.max_output_tokens = max(
            MIN_OUTPUT_TOKENS,
            self._positive_int(max_output_tokens, "MAX_OUTPUT_TOKENS"),
        )

    async def generate(
        self,
        *,
        system: str,
        user: str,
        format: dict[str, Any] | str | None = None,
        temperature: float | None = None,
    ) -> ProviderResult:
        marker = system.upper()
        payload = {
            "model": self.model,
            "stream": False,
            # Qwen3 and other reasoning-capable Ollama models may emit a thinking
            # channel unless this is disabled explicitly. Research pipelines
            # need clean machine-readable outputs and comparable token/latency.
            "think": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_predict": self.max_output_tokens,
            },
        }
        if format is not None:
            payload["format"] = format
        elif any(value in marker for value in _STRUCTURED_MARKERS):
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, dict):
            raise OllamaProtocolError("Ollama chat response must be a JSON object")
        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaProtocolError("Ollama chat response is missing message.content")

        input_tokens = self._response_count(data, "prompt_eval_count")
        output_tokens = self._response_count(data, "eval_count")
        return ProviderResult(
            text=message["content"],
            usage=Usage(input_tokens, output_tokens),
            request_id="ollama_" + uuid.uuid4().hex[:10],
            model=self.model,
        )

    async def health(self) -> dict:
        """Return safe, reproducible metadata for the configured local model."""

        async with httpx.AsyncClient(timeout=DEFAULT_HEALTH_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, dict):
            raise OllamaProtocolError("Ollama tags response must be a JSON object")
        raw_models = data.get("models", [])
        if not isinstance(raw_models, list):
            raise OllamaProtocolError("Ollama tags response models must be a list")

        models = [self._model_info(item) for item in raw_models]
        configured = next(
            (
                item
                for item in models
                if item.get("name") == self.model or item.get("model") == self.model
            ),
            None,
        )
        model_available = configured is not None
        return {
            # `ok` means ready for the configured M0 local model, not merely
            # that an Ollama process answered /api/tags.
            "ok": model_available,
            "provider": self.name,
            "base_url": self.base_url,
            "ollama_reachable": True,
            "status": "READY" if model_available else "MODEL_NOT_FOUND",
            "configured_model": self.model,
            "model_available": model_available,
            "model_digest": configured.get("digest") if configured else None,
            "configured_model_info": configured,
            "models": models,
            "generation_contract": {
                "stream": False,
                "think": False,
                "structured_format": "json",
                "structured_output_config_version": STRUCTURED_OUTPUT_CONFIG_VERSION,
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            },
        }

    @staticmethod
    def _validate_model(value: object) -> str:
        if not isinstance(value, str):
            raise OllamaConfigurationError("LOCAL_LLM_MODEL must be a non-empty string")
        model = value.strip()
        if not model or any(character.isspace() for character in model):
            raise OllamaConfigurationError("LOCAL_LLM_MODEL must be a non-empty model tag")
        return model

    @staticmethod
    def _validate_base_url(value: object) -> str:
        if not isinstance(value, str):
            raise OllamaConfigurationError("OLLAMA_BASE_URL must be a local HTTP(S) URL")
        raw_url = value.strip()
        if not raw_url or any(character.isspace() for character in raw_url):
            raise OllamaConfigurationError("OLLAMA_BASE_URL must be a local HTTP(S) URL")

        try:
            parsed = urlsplit(raw_url)
            hostname = parsed.hostname
            parsed.port  # Force malformed/out-of-range ports to fail here.
        except ValueError as exc:
            raise OllamaConfigurationError("OLLAMA_BASE_URL has an invalid host or port") from exc

        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise OllamaConfigurationError("OLLAMA_BASE_URL must use HTTP(S) on loopback")
        if parsed.username is not None or parsed.password is not None:
            raise OllamaConfigurationError("OLLAMA_BASE_URL must not contain credentials")
        if parsed.query or parsed.fragment:
            raise OllamaConfigurationError("OLLAMA_BASE_URL must not contain a query or fragment")
        if not OllamaProvider._is_loopback_host(hostname):
            raise OllamaConfigurationError(
                "OLLAMA_BASE_URL must point to the local Ollama service on loopback"
            )
        return raw_url.rstrip("/")

    @staticmethod
    def _is_loopback_host(hostname: str | None) -> bool:
        if not hostname:
            return False
        normalized = hostname.casefold().rstrip(".")
        if normalized in _LOCAL_HOSTNAMES:
            return True
        try:
            return ip_address(normalized).is_loopback
        except ValueError:
            return False

    @staticmethod
    def _positive_float(value: object, name: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise OllamaConfigurationError(f"{name} must be a positive number") from exc
        if not math.isfinite(parsed) or parsed <= 0:
            raise OllamaConfigurationError(f"{name} must be a positive number")
        return parsed

    @staticmethod
    def _non_negative_float(value: object, name: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise OllamaConfigurationError(f"{name} must be a non-negative number") from exc
        if not math.isfinite(parsed) or parsed < 0:
            raise OllamaConfigurationError(f"{name} must be a non-negative number")
        return parsed

    @staticmethod
    def _positive_int(value: object, name: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise OllamaConfigurationError(f"{name} must be a positive integer") from exc
        if parsed <= 0:
            raise OllamaConfigurationError(f"{name} must be a positive integer")
        return parsed

    @staticmethod
    def _response_count(data: dict, key: str) -> int:
        value = data.get(key)
        if value is None:
            return 0
        if isinstance(value, bool):
            raise OllamaProtocolError(f"Ollama response field {key} must be a non-negative integer")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise OllamaProtocolError(
                f"Ollama response field {key} must be a non-negative integer"
            ) from exc
        if parsed < 0:
            raise OllamaProtocolError(f"Ollama response field {key} must be a non-negative integer")
        return parsed

    @staticmethod
    def _model_info(value: object) -> dict:
        if not isinstance(value, dict):
            raise OllamaProtocolError("Ollama model metadata must be an object")
        return {field: value.get(field) for field in _MODEL_FIELDS}
