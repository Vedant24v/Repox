"""
personalization.py — Map technical_level → generation config dict.

These configs are injected verbatim into every tutorial-generation system
prompt to calibrate the output tone, depth, and style.

Spec reference: Section 11 — Personalization.
"""
from __future__ import annotations

# ── Level config definitions (spec Section 11) ───────────────────────────────

_CONFIGS: dict[str, dict] = {
    "beginner": {
        "tone": "friendly, encouraging, and simple — assume no prior coding background",
        "use_analogies": True,
        "explain_jargon": True,
        "include_code_details": False,
        "explain_step_by_step": True,
        "max_technical_depth": "high-level concepts only; skip implementation internals",
    },
    "product": {
        "tone": "professional and product-focused — explain what the system does, not how it's built",
        "use_analogies": True,
        "explain_jargon": False,
        "include_code_details": False,
        "explain_step_by_step": True,
        "max_technical_depth": "business logic, data flows, and user-facing capabilities",
    },
    "developer": {
        "tone": "technical, precise, and peer-to-peer — assume strong programming background",
        "use_analogies": False,
        "explain_jargon": False,
        "include_code_details": True,
        "explain_step_by_step": False,
        "max_technical_depth": "full implementation details, architectural patterns, and trade-offs",
    },
}

_DEFAULT_LEVEL = "beginner"


def get_level_config(technical_level: str | None) -> dict:
    """
    Return the personalization config dict for *technical_level*.

    Falls back to 'beginner' for unknown or None values.
    """
    return dict(
        _CONFIGS.get(technical_level or _DEFAULT_LEVEL, _CONFIGS[_DEFAULT_LEVEL])
    )


def level_config_to_system_prompt_block(config: dict) -> str:
    """
    Render *config* as a compact block suitable for embedding in system prompts.
    """
    lines = [
        "## Audience & Writing Style",
        f"- **Tone**: {config['tone']}",
        f"- **Depth**: {config['max_technical_depth']}",
    ]

    if config["use_analogies"]:
        lines.append("- Use real-world analogies to explain abstract concepts.")
    else:
        lines.append("- Do NOT use analogies — the reader is comfortable with technical language.")

    if config["explain_jargon"]:
        lines.append("- Define every piece of technical jargon the first time it appears.")
    else:
        lines.append("- Technical terms may be used without definition.")

    if config["include_code_details"]:
        lines.append("- Include relevant code snippets and implementation details where they add clarity.")
    else:
        lines.append("- Keep explanations high-level; omit code snippets unless absolutely essential.")

    if config["explain_step_by_step"]:
        lines.append("- Break every process into numbered steps.")
    else:
        lines.append("- Be concise; the reader can infer intermediate steps.")

    return "\n".join(lines)
