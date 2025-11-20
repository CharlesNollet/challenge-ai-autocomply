"""
Thin wrapper around the AutoComply /ask endpoint that enforces the prompt contract.
"""

from __future__ import annotations

import json
from threading import Lock
from typing import Dict, List

import requests

from solution.config import API_KEY, API_URL, CLASSIFICATION_PROMPT, DEFAULT_MODEL


class LLMClientError(RuntimeError):
    """Raised when the LLM client cannot return predictions."""


class LLMClient:
    """Handles prompt construction, HTTP requests and JSON parsing."""

    def __init__(
        self,
        api_url: str = API_URL,
        api_key: str = API_KEY,
        model: str = DEFAULT_MODEL,
        timeout: int = 120,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.request_count = 0
        self._request_lock = Lock()

        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def classify_block(self, block_payload: Dict) -> List[Dict]:
        """Send one block to the LLM and return parsed predictions."""
        instructions = f"{CLASSIFICATION_PROMPT}\n\nJSON INPUT:\n{json.dumps(block_payload, ensure_ascii=False)}"
        body = {
            "query": instructions,
            "model": self.model,
        }

        try:
            response = requests.post(
                f"{self.api_url}/ask",
                headers=self._headers,
                json=body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise LLMClientError(f"LLM request failed: {exc}") from exc
        except ValueError as exc:  # json decoding error on response
            raise LLMClientError("LLM response is not valid JSON") from exc

        with self._request_lock:
            self.request_count += 1
        raw_result = data.get("result", "")
        predictions = self._parse_predictions(raw_result)
        return predictions

    def _parse_predictions(self, raw_text: str) -> List[Dict]:
        json_payload = self._extract_json(raw_text)
        try:
            parsed = json.loads(json_payload)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"Unable to decode LLM JSON: {exc}") from exc

        predictions = parsed.get("pagePredictions")
        if not isinstance(predictions, list):
            raise LLMClientError("LLM response missing pagePredictions array")
        return predictions

    @staticmethod
    def _extract_json(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMClientError("LLM response did not include a JSON object")
        return text[start : end + 1]


