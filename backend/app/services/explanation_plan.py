"""
explanation_plan.py — Generate a single unified explanation plan via one LLM call.

The returned plan dict is passed to every subsequent tutorial-generation
call so all sections stay internally consistent.
"""
from __future__ import annotations

import json
import logging

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a senior technical architect who creates clear, structured plans for explaining complex software repositories to non-experts.

Given structured analysis of a repository, produce a comprehensive JSON plan.

Return ONLY valid JSON — no markdown fences, no prose outside the JSON.

Required keys (do not add extras):
  "major_modules"              : array of {name, description, files: [str]}
  "explanation_order"          : array of {step: int, component: str, reason: str} — ordered by importance for understanding
  "main_user_flow_target"      : string — the single most important user-facing journey to trace
  "required_diagrams"          : array of strings — diagram types that would most aid understanding
  "concepts_needing_analogies" : array of strings — technical concepts that need real-world analogies
  "uncertain_areas"            : array of strings — gaps, ambiguities, or missing evidence in the analysis
"""


def _compact_summaries(file_summaries: list[dict], max_items: int = 20) -> str:
    """Compact representation for the plan prompt (stays within token budget)."""
    lines: list[str] = []
    for s in file_summaries[:max_items]:
        syms = ", ".join(str(x) for x in s.get("important_symbols", [])[:5])
        conns = ", ".join(str(x) for x in s.get("connections", [])[:4])
        lines.append(
            f"• {s['path']}\n"
            f"  Responsibility: {s.get('responsibility', '')}\n"
            f"  Symbols: {syms or 'none'} | Connects to: {conns or 'none'}"
        )
    return "\n".join(lines)


def _compact_routes(relationships: list[dict], limit: int = 30) -> str:
    routes = [r for r in relationships if r.get("relationship") == "declares_route"]
    return "\n".join(
        f"• {r['source']}: {r['target']}"
        for r in routes[:limit]
    ) or "No routes detected."


# ── Public API ────────────────────────────────────────────────────────────────

def generate_explanation_plan(
    tech: dict,
    file_summaries: list[dict],
    relationships: list[dict],
    product_description: str | None,
    important_features: str | None,
) -> dict:
    """
    Generate a structured explanation plan.

    Returns a dict matching the schema in _SYSTEM_PROMPT.
    Returns a minimal valid fallback dict if the LLM call fails.
    """
    parts: list[str] = []

    if product_description:
        parts.append(
            f"## Product Description (user-provided)\n{product_description}"
        )
    if important_features:
        parts.append(
            f"## Key Features (user-provided)\n{important_features}"
        )

    # Compact tech summary
    tech_lines = []
    for k, v in tech.items():
        if isinstance(v, list) and v:
            tech_lines.append(f"  {k}: {', '.join(str(x) for x in v)}")
        elif isinstance(v, bool) and v:
            tech_lines.append(f"  {k}: yes")
    parts.append("## Technology Stack\n" + "\n".join(tech_lines))

    parts.append(
        f"## Important Files (with LLM summaries)\n{_compact_summaries(file_summaries)}"
    )
    parts.append(
        f"## Declared API Routes\n{_compact_routes(relationships)}"
    )

    user_prompt = "\n\n".join(parts)

    try:
        raw = call_llm(_SYSTEM_PROMPT, user_prompt, json_mode=True)
        plan = json.loads(raw)
        logger.info("Explanation plan generated successfully.")
        return plan
    except Exception as exc:
        logger.error("Failed to generate explanation plan: %s", exc)
        return {
            "major_modules": [],
            "explanation_order": [],
            "main_user_flow_target": "primary user flow",
            "required_diagrams": ["architecture overview", "data flow"],
            "concepts_needing_analogies": [],
            "uncertain_areas": [f"Plan generation failed: {exc}"],
        }
