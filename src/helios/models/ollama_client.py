"""Cliente de Ollama para texto y visión. No llama a ninguna API de pago."""

from __future__ import annotations

import base64
import json

import requests

from helios.config import Settings
from helios.models.errors import ModelUnavailable


class OllamaClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def healthy(self) -> bool:
        try:
            response = requests.get(f"{self.settings.ollama_host}/api/tags", timeout=0.6)
            return response.ok
        except requests.RequestException:
            return False

    def model_names(self) -> list[str]:
        if not self.healthy():
            return []
        response = requests.get(f"{self.settings.ollama_host}/api/tags", timeout=5)
        response.raise_for_status()
        return [item.get("name", "") for item in response.json().get("models", [])]

    def resolve(self, preferred: str, fallbacks: tuple[str, ...] = ()) -> str | None:
        available = self.model_names()
        for wanted in (preferred, *fallbacks):
            found = _match(available, wanted)
            if found:
                return found
        return None

    def chat(
        self,
        model: str,
        prompt: str,
        images: list[bytes] | None = None,
        timeout: int = 300,
        json_mode: bool = False,
        system: str | None = None,
    ) -> str:
        if not self.healthy():
            raise ModelUnavailable(f"Ollama no responde en {self.settings.ollama_host}.")
        message: dict[str, object] = {"role": "user", "content": prompt}
        if images:
            message["images"] = [base64.b64encode(blob).decode("ascii") for blob in images]
        messages: list[dict[str, object]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append(message)
        payload: dict[str, object] = {"model": model, "messages": messages, "stream": False}
        if json_mode:
            payload["format"] = "json"
        try:
            response = requests.post(
                f"{self.settings.ollama_host}/api/chat",
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ModelUnavailable(f"Fallo al hablar con {model}: {exc}") from exc
        content = response.json().get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        return str(content).strip()

    def pull(self, name: str) -> None:
        if not self.healthy():
            raise ModelUnavailable(f"Ollama no responde en {self.settings.ollama_host}.")
        try:
            response = requests.post(
                f"{self.settings.ollama_host}/api/pull",
                json={"name": name, "stream": True},
                stream=True,
                timeout=None,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ModelUnavailable(f"No se pudo descargar {name}: {exc}") from exc
        for line in response.iter_lines():
            if not line:
                continue
            payload = json.loads(line.decode("utf-8"))
            if payload.get("error"):
                raise ModelUnavailable(str(payload["error"]))
            status = payload.get("status", "")
            total = payload.get("total") or 0
            completed = payload.get("completed") or 0
            if total and status:
                print(f"  {name}: {status} {100 * completed / total:.0f}%", flush=True)
            elif status:
                print(f"  {name}: {status}", flush=True)


def _match(available: list[str], wanted: str) -> str | None:
    wanted_base, _, wanted_tag = wanted.partition(":")
    for name in available:
        clean = name.strip()
        if clean == wanted:
            return clean
        base, _, _tag = clean.partition(":")
        if not wanted_tag and base == wanted_base:
            return clean
    return None
