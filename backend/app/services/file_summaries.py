"""
file_summaries.py — LLM-powered per-file summaries for "important" files.

Only files selected by important_files.py are sent to the LLM.
File content is capped at 3 000 chars to stay within token budgets.

Concurrency is limited to 3 simultaneous Groq calls (asyncio + Semaphore)
to respect Groq free-tier rate limits (~30 RPM).
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

_MAX_FILE_CHARS: int = 3_000
_SEMAPHORE_LIMIT: int = 1
# Small inter-call courtesy delay to stay inside Groq's RPM window
_INTER_CALL_SLEEP: float = 6.0

_SYSTEM_PROMPT = """You are a senior software engineer analysing a source file from a repository.

Return ONLY a valid JSON object — no markdown fences, no explanation, nothing else.
The JSON must have exactly these 6 keys (no extras):
  "responsibility"     : one or two sentences describing what this file is responsible for
  "important_symbols"  : array of up to 8 key function / class / variable names (strings)
  "inputs"             : what data, arguments, or events does this file receive?
  "outputs"            : what does it produce, return, export, or expose?
  "connections"        : array of other modules, files, or external services it talks to
  "evidence_snippet"   : the single most revealing 1-3 lines of code from this file (as a string)
"""


# ── File I/O ─────────────────────────────────────────────────────────────────

def _read_file(abs_path: Path, max_chars: int = _MAX_FILE_CHARS) -> str:
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + "\n… [file truncated at 3000 chars]"
        return text
    except OSError:
        return "(file could not be read)"


def _build_prompt(path: str, reason: str, language: str, content: str) -> str:
    return (
        f"File path   : {path}\n"
        f"Language    : {language}\n"
        f"Why notable : {reason}\n\n"
        f"--- FILE CONTENT ---\n{content}\n--- END ---"
    )


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _parse(raw: str, fallback_path: str) -> dict:
    """Parse the LLM JSON response, with a safe fallback."""
    try:
        data = json.loads(raw)
        return {
            "path": fallback_path,
            "responsibility": str(data.get("responsibility", "")),
            "important_symbols": list(data.get("important_symbols", [])),
            "inputs": str(data.get("inputs", "")),
            "outputs": str(data.get("outputs", "")),
            "connections": list(data.get("connections", [])),
            "evidence_snippet": str(data.get("evidence_snippet", "")),
        }
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning("Could not parse JSON summary for %s — using raw text.", fallback_path)
        return {
            "path": fallback_path,
            "responsibility": raw.strip()[:500] if raw else "Summarisation failed.",
            "important_symbols": [],
            "inputs": "",
            "outputs": "",
            "connections": [],
            "evidence_snippet": "",
        }


# ── Per-file async worker ─────────────────────────────────────────────────────

async def _summarize_one(
    entry: dict,
    repo_root: Path,
    semaphore: asyncio.Semaphore,
    loop: asyncio.AbstractEventLoop,
) -> dict:
    """Summarise a single file, honouring the concurrency semaphore."""
    async with semaphore:
        rel_path: str = entry["path"]
        abs_path = repo_root / rel_path
        content = _read_file(abs_path)
        user_prompt = _build_prompt(
            path=rel_path,
            reason=entry.get("reason_important", "selected as important"),
            language=entry.get("language", "unknown"),
            content=content,
        )
        try:
            raw = await loop.run_in_executor(
                None,
                lambda: call_llm(_SYSTEM_PROMPT, user_prompt, json_mode=True),
            )
            result = _parse(raw, rel_path)
            logger.info("Summarised %s", rel_path)
        except Exception as exc:
            logger.error("Failed to summarise %s: %s", rel_path, exc)
            result = {
                "path": rel_path,
                "responsibility": f"Summarisation error: {exc}",
                "important_symbols": [],
                "inputs": "",
                "outputs": "",
                "connections": [],
                "evidence_snippet": "",
            }
        # Small courtesy pause between calls
        await asyncio.sleep(_INTER_CALL_SLEEP)
        return result


# ── Public API ────────────────────────────────────────────────────────────────

async def summarize_important_files(
    repo_root: Path,
    important_files: list[dict],
) -> list[dict]:
    """
    Concurrently summarise each file in *important_files* using the LLM.

    At most *_SEMAPHORE_LIMIT* (3) calls run simultaneously.
    Returns a list of summary dicts in the same order as *important_files*.
    """
    if not important_files:
        return []

    semaphore = asyncio.Semaphore(_SEMAPHORE_LIMIT)
    loop = asyncio.get_event_loop()

    tasks = [
        _summarize_one(entry, repo_root, semaphore, loop)
        for entry in important_files
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)
