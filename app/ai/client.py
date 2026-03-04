"""Reusable Vertex AI (Gemini) client.

Initialises the SDK once, then exposes thin helpers to call Gemini Flash
(high-volume, cheap) and Gemini Pro (deeper strategic analysis).

Environment variables
---------------------
GOOGLE_APPLICATION_CREDENTIALS : path to service-account JSON
GOOGLE_CLOUD_PROJECT           : GCP project ID
VERTEX_REGION                  : region (default us-central1)
"""
from __future__ import annotations

import json
import os
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────────

_DEFAULT_REGION = "us-central1"

# Model identifiers — keep in one place for easy upgrade.
MODEL_FLASH = "gemini-2.0-flash"
MODEL_PRO = "gemini-2.0-pro"

# Safety / generation defaults
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_MAX_TOKENS = 4096


# ── Client class ─────────────────────────────────────────────────────────────

class VertexAIClient:
    """Thin wrapper around the Vertex AI Generative Model API.

    Lazy-initialises: ``import vertexai`` happens on first call, not at
    module load, so the rest of the system works fine without GCP creds.
    """

    def __init__(
        self,
        project: str | None = None,
        region: str | None = None,
    ) -> None:
        self.project = project or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self.region = region or os.environ.get("VERTEX_REGION", _DEFAULT_REGION)
        self._initialised = False
        self._flash_model: Any = None
        self._pro_model: Any = None

    # ── Lazy init ─────────────────────────────────────────────────────

    def _ensure_init(self) -> None:
        """Initialise Vertex AI SDK on first use."""
        if self._initialised:
            return

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project, location=self.region)

            self._flash_model = GenerativeModel(MODEL_FLASH)
            self._pro_model = GenerativeModel(MODEL_PRO)
            self._initialised = True
            logger.info(
                "vertex_ai_initialised",
                project=self.project,
                region=self.region,
            )
        except Exception as exc:
            logger.error("vertex_ai_init_failed", error=str(exc))
            raise RuntimeError(
                f"Vertex AI initialisation failed: {exc}.  "
                "Ensure GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT "
                "and VERTEX_REGION are set."
            ) from exc

    @property
    def available(self) -> bool:
        """Return True when SDK + credentials look usable."""
        if self._initialised:
            return True
        try:
            self._ensure_init()
            return True
        except Exception:
            return False

    # ── Core generation helpers ───────────────────────────────────────

    def generate_flash(
        self,
        prompt: str,
        *,
        temperature: float = _DEFAULT_TEMPERATURE,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> str:
        """Call Gemini Flash (fast, cheap, high-volume tasks)."""
        self._ensure_init()
        config = self._make_config(temperature, max_tokens)
        response = self._flash_model.generate_content(prompt, generation_config=config)
        return response.text

    def generate_pro(
        self,
        prompt: str,
        *,
        temperature: float = _DEFAULT_TEMPERATURE,
        max_tokens: int = 8192,
    ) -> str:
        """Call Gemini Pro (deeper strategic analysis)."""
        self._ensure_init()
        config = self._make_config(temperature, max_tokens)
        response = self._pro_model.generate_content(prompt, generation_config=config)
        return response.text

    def _make_config(self, temperature: float, max_tokens: int) -> Any:
        """Build a GenerationConfig (imported lazily)."""
        from vertexai.generative_models import GenerationConfig
        return GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    def generate_json(
        self,
        prompt: str,
        *,
        use_pro: bool = False,
        temperature: float = 0.4,
        max_tokens: int = 8192,
    ) -> dict[str, Any] | list[Any] | None:
        """Generate content and parse the response as JSON.

        Appends an instruction to return valid JSON and strips
        markdown fences before parsing.
        """
        full_prompt = (
            prompt
            + "\n\nIMPORTANT: Return ONLY valid JSON. "
            "No markdown fences, no commentary."
        )
        raw = (
            self.generate_pro(full_prompt, temperature=temperature, max_tokens=max_tokens)
            if use_pro
            else self.generate_flash(full_prompt, temperature=temperature, max_tokens=max_tokens)
        )
        return _parse_json_response(raw)


# ── Singleton ────────────────────────────────────────────────────────────────

_client: VertexAIClient | None = None


def get_ai_client() -> VertexAIClient:
    """Return (or create) the global VertexAIClient singleton."""
    global _client
    if _client is None:
        _client = VertexAIClient()
    return _client


# ── JSON helpers ─────────────────────────────────────────────────────────────

def _parse_json_response(raw: str) -> dict[str, Any] | list[Any] | None:
    """Strip markdown fences and parse JSON from an LLM response.

    Returns None if the text cannot be parsed as valid JSON.
    """
    text = raw.strip()
    # Remove ```json … ``` fences
    if text.startswith("```"):
        lines = text.split("\n")
        # drop first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("json_parse_failed", preview=text[:120])
        return None
