"""
llm_client.py — Thin wrapper around Groq chat completions.

Uses llama-3.3-70b-versatile with:
  • Automatic retry (2 attempts) on rate-limit / transient API errors
  • Input truncation guard: user_prompt is capped at ~6000 tokens (~24 000 chars)
"""
from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Groq's llama-3.3 tokenises at roughly 4 chars / token
_CHARS_PER_TOKEN: int = 4
_MAX_USER_TOKENS: int = 2_500
_MAX_USER_CHARS: int = _MAX_USER_TOKENS * _CHARS_PER_TOKEN  # ≈ 10 000 chars
_TRUNCATION_NOTE: str = (
    "\n\n[… content truncated to fit the context window; "
    "some details may be absent …]\n"
)

# ── Lazy singleton client ────────────────────────────────────────────────────
_client = None  # type: ignore[assignment]


def _get_client():
    global _client
    if _client is None:
        try:
            from groq import Groq  # deferred so tests can mock easily
        except ImportError as exc:
            raise RuntimeError(
                "groq package is not installed. Run: pip install groq"
            ) from exc

        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Add it to backend/.env"
            )
        _client = Groq(api_key=api_key)
    return _client


# ── Helpers ──────────────────────────────────────────────────────────────────

def _truncate(text: str, max_chars: int = _MAX_USER_CHARS) -> str:
    """Trim *text* to *max_chars* and append a truncation note if needed."""
    if len(text) <= max_chars:
        return text
    logger.info(
        "Truncating user prompt from %d → %d chars.", len(text), max_chars
    )
    return text[:max_chars] + _TRUNCATION_NOTE


def estimate_tokens(text: str) -> int:
    """Rough token-count estimate (4 chars ≈ 1 token)."""
    return len(text) // _CHARS_PER_TOKEN


# ── Public API ───────────────────────────────────────────────────────────────

def call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    max_retries: int = 5,
) -> str:
    """
    Call the Groq API with retry and truncation protection.

    Parameters
    ----------
    system_prompt : str
        Instruction / context for the model.
    user_prompt : str
        The user message — automatically truncated if it exceeds ~6 000 tokens.
    json_mode : bool
        If True, sets response_format to json_object so the model returns
        valid JSON without markdown fences.
    max_retries : int
        Number of retry attempts on rate-limit / transient errors.

    Returns
    -------
    str
        The model's text (or JSON string when json_mode=True).

    Raises
    ------
    RuntimeError
        When all retry attempts are exhausted.
    """
    try:
        from groq import APIError, RateLimitError  # type: ignore
    except ImportError as exc:
        raise RuntimeError("groq package not installed.") from exc

    user_prompt = _truncate(user_prompt)

    client = _get_client()
    kwargs: dict = dict(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.25,
        max_tokens=2048,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or ""
            return content
        except RateLimitError as exc:
            wait = (attempt + 1) * 10  # 10s, 20s, 30s, 40s, 50s
            logger.warning(
                "Groq rate-limit (attempt %d/%d) — waiting %ds. %s",
                attempt + 1, max_retries, wait, exc,
            )
            time.sleep(wait)
            last_err = exc
        except APIError as exc:
            wait = 2 ** attempt * 3  # 3 s, 6 s
            logger.warning(
                "Groq API error (attempt %d/%d) — waiting %ds. %s",
                attempt + 1, max_retries, wait, exc,
            )
            time.sleep(wait)
            last_err = exc

    raise RuntimeError(
        f"LLM call failed after {max_retries} attempt(s): {last_err}"
    )
