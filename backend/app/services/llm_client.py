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

import json
import urllib.request
import urllib.error

# ── Gemini Integration ────────────────────────────────────────────────────────

def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    max_retries: int = 5,
) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": user_prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 2048,
        }
    }
    
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [
                {
                    "text": system_prompt
                }
            ]
        }
        
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
        
    data = json.dumps(payload).encode("utf-8")
    
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                
                candidates = resp_data.get("candidates", [])
                if not candidates:
                    raise RuntimeError(f"Gemini API returned no candidates: {resp_data}")
                    
                content_obj = candidates[0].get("content", {})
                parts = content_obj.get("parts", [])
                if not parts:
                    raise RuntimeError(f"Gemini API candidate content has no parts: {resp_data}")
                    
                text = parts[0].get("text", "")
                return text
                
        except urllib.error.HTTPError as exc:
            # Code 429 = RESOURCE_EXHAUSTED
            if exc.code == 429:
                wait = (attempt + 1) * 5  # 5s, 10s, 15s, etc.
                logger.warning(
                    "Gemini rate-limit (attempt %d/%d) — waiting %ds. %s",
                    attempt + 1, max_retries, wait, exc,
                )
                time.sleep(wait)
            elif exc.code >= 500:
                wait = 2 ** attempt * 2  # 2s, 4s, 8s
                logger.warning(
                    "Gemini server error %d (attempt %d/%d) — waiting %ds. %s",
                    exc.code, attempt + 1, max_retries, wait, exc,
                )
                time.sleep(wait)
            else:
                try:
                    err_msg = exc.read().decode("utf-8")
                except Exception:
                    err_msg = str(exc)
                logger.error("Gemini API client error %d: %s", exc.code, err_msg)
                raise RuntimeError(f"Gemini API client error {exc.code}: {err_msg}") from exc
            last_err = exc
        except Exception as exc:
            wait = 2 ** attempt * 2
            logger.warning(
                "Gemini connection error (attempt %d/%d) — waiting %ds. %s",
                attempt + 1, max_retries, wait, exc,
            )
            time.sleep(wait)
            last_err = exc
            
    raise RuntimeError(
        f"Gemini LLM call failed after {max_retries} attempt(s): {last_err}"
    )


# ── Public API ───────────────────────────────────────────────────────────────

def call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    max_retries: int = 5,
) -> str:
    """
    Call either Gemini or Groq API (depending on configuration) with retry and truncation protection.
    """
    user_prompt = _truncate(user_prompt)

    # Automatically use Gemini if GEMINI_API_KEY is configured
    if os.getenv("GEMINI_API_KEY", "").strip():
        logger.info("Using Gemini API for LLM call.")
        return _call_gemini(system_prompt, user_prompt, json_mode=json_mode, max_retries=max_retries)

    logger.info("Using Groq API for LLM call.")
    try:
        from groq import APIError, RateLimitError  # type: ignore
    except ImportError as exc:
        raise RuntimeError("groq package not installed.") from exc

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
