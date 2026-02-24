from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import log_event, log_summary


class RelayLLMClient:
    def __init__(self) -> None:
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def chat_json(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        force_json_object: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        if not self.is_enabled():
            raise RuntimeError("LLM relay is not configured")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if force_json_object:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = None
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=timeout_s or 20.0) as client:
            for endpoint in self._candidate_endpoints():
                try:
                    log_event(
                        "llm.request.start",
                        mode="async",
                        model=model,
                        endpoint=endpoint,
                        force_json_object=force_json_object,
                        timeout_s=timeout_s or 20.0,
                        request_payload=payload,
                    )
                    log_summary("llm.request.start", model=model, endpoint=endpoint, mode="async")
                    resp = await client.post(endpoint, headers=headers, json=payload)
                    resp.raise_for_status()
                    log_event(
                        "llm.request.response",
                        mode="async",
                        model=model,
                        endpoint=endpoint,
                        status_code=resp.status_code,
                        content_type=resp.headers.get("content-type"),
                        response_body=resp.text,
                    )
                    data = self._parse_response_json(resp)
                    log_event("llm.request.success", mode="async", model=model, endpoint=endpoint)
                    content = data["choices"][0]["message"]["content"]
                    log_summary(
                        "llm.response",
                        model=model,
                        endpoint=endpoint,
                        mode="async",
                        status_code=resp.status_code,
                        llm_content=content,
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    log_event("llm.request.error", mode="async", model=model, endpoint=endpoint, error=str(exc))
                    log_summary("llm.request.error", model=model, endpoint=endpoint, mode="async", error=str(exc))
            if data is None:
                raise RuntimeError(f"LLM relay request failed: {last_error}")

        content = data["choices"][0]["message"]["content"]
        return self._coerce_json(content)

    def chat_json_sync(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        force_json_object: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        if not self.is_enabled():
            raise RuntimeError("LLM relay is not configured")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if force_json_object:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = None
        last_error: Exception | None = None
        with httpx.Client(timeout=timeout_s or 12.0) as client:
            for endpoint in self._candidate_endpoints():
                try:
                    log_event(
                        "llm.request.start",
                        mode="sync",
                        model=model,
                        endpoint=endpoint,
                        force_json_object=force_json_object,
                        timeout_s=timeout_s or 12.0,
                        request_payload=payload,
                    )
                    log_summary("llm.request.start", model=model, endpoint=endpoint, mode="sync")
                    resp = client.post(endpoint, headers=headers, json=payload)
                    resp.raise_for_status()
                    log_event(
                        "llm.request.response",
                        mode="sync",
                        model=model,
                        endpoint=endpoint,
                        status_code=resp.status_code,
                        content_type=resp.headers.get("content-type"),
                        response_body=resp.text,
                    )
                    data = self._parse_response_json(resp)
                    log_event("llm.request.success", mode="sync", model=model, endpoint=endpoint)
                    content = data["choices"][0]["message"]["content"]
                    log_summary(
                        "llm.response",
                        model=model,
                        endpoint=endpoint,
                        mode="sync",
                        status_code=resp.status_code,
                        llm_content=content,
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    log_event("llm.request.error", mode="sync", model=model, endpoint=endpoint, error=str(exc))
                    log_summary("llm.request.error", model=model, endpoint=endpoint, mode="sync", error=str(exc))
            if data is None:
                raise RuntimeError(f"LLM relay request failed: {last_error}")

        content = data["choices"][0]["message"]["content"]
        return self._coerce_json(content)

    @staticmethod
    def _coerce_json(content: Any) -> dict[str, Any]:
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise ValueError("LLM response is not a JSON object")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end > start:
                return json.loads(content[start : end + 1])
            raise

    def _candidate_endpoints(self) -> list[str]:
        base = (self.base_url or "").rstrip("/")
        if not base:
            return []
        endpoints = [f"{base}/chat/completions"]
        if not base.endswith("/v1"):
            endpoints.append(f"{base}/v1/chat/completions")
        return endpoints

    @staticmethod
    def _parse_response_json(resp: httpx.Response) -> dict[str, Any]:
        content_type = (resp.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            return resp.json()
        text = resp.text.strip()
        if text.startswith("{") or text.startswith("["):
            return json.loads(text)
        raise ValueError(f"non-json response ({content_type}): {text[:120]}")

    @staticmethod
    def _preview(text: str, max_len: int = 500) -> str:
        return text[:max_len]
