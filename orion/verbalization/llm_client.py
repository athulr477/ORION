"""Ollama LLM client — wraps HTTP calls to local Ollama for verbalization.

Uses temperature=0.0 for fully deterministic phrasing.  Graceful fallback:
if Ollama is unavailable, callers receive an indication to use the evidence
tuple's built-in fallback sentence instead.

IMPORTANT: This is the ONLY module that touches an LLM.  The LLM is used
solely for phrasing audit summaries, never for scoring or classification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import ollama as ollama_sdk
from ollama import ResponseError

from orion.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from the LLM client."""

    text: str
    model: str
    success: bool
    error: str | None = None


class OllamaClient:
    """Thin wrapper around the Ollama Python SDK for evidence verbalization.

    Configuration is pulled from orion.config.settings:
        - ollama_base_url: Ollama server URL (default: http://localhost:11434)
        - ollama_model: Model to use (default: llama3.1:8b)

    Temperature is fixed at 0.0 — deterministic output only.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature

        # Initialize the Ollama client
        self._client = ollama_sdk.Client(host=self.base_url)

        logger.info(
            "OllamaClient initialized: model=%s, base_url=%s, temperature=%s",
            self.model,
            self.base_url,
            self.temperature,
        )

    def is_available(self) -> bool:
        """Check whether the Ollama server is reachable and the model is loaded.

        Returns:
            True if the server responds and the model exists.
        """
        try:
            # List available models to verify connectivity
            models_response = self._client.list()
            available_models = [
                m.model for m in models_response.models
            ]
            if self.model in available_models:
                return True
            # Also check without tag (e.g. "llama3.1" matches "llama3.1:8b")
            base_model = self.model.split(":")[0]
            for m in available_models:
                if m.startswith(base_model):
                    return True
            logger.warning(
                "Ollama server is up but model '%s' not found. Available: %s",
                self.model,
                available_models,
            )
            return False
        except Exception as e:
            logger.warning("Ollama server not available at %s: %s", self.base_url, e)
            return False

    def generate(self, prompt: str) -> LLMResponse:
        """Generate a single response from the LLM.

        Uses the Ollama chat API with temperature=0.0 for deterministic output.
        No streaming — waits for the full response.

        Args:
            prompt: The full prompt text to send to the LLM.

        Returns:
            LLMResponse with the generated text, or an error message.
        """
        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a requirements traceability auditor. "
                            "Write exactly one concise sentence based ONLY on the evidence provided. "
                            "Do not invent any claims not present in the evidence."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                options={
                    "temperature": self.temperature,
                    "num_predict": 200,  # Cap output length — one sentence only
                },
            )

            text = response.message.content.strip()

            logger.info(
                "LLM generated %d chars for prompt (%d chars)",
                len(text),
                len(prompt),
            )

            return LLMResponse(
                text=text,
                model=self.model,
                success=True,
            )

        except ResponseError as e:
            logger.error("Ollama API error: %s", e)
            return LLMResponse(
                text="",
                model=self.model,
                success=False,
                error=f"Ollama API error: {e}",
            )
        except Exception as e:
            logger.error("Ollama client error: %s", e)
            return LLMResponse(
                text="",
                model=self.model,
                success=False,
                error=f"Ollama connection error: {e}",
            )
