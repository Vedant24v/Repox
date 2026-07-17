"""
tutorial_generator.py — Generate each tutorial section as a separate LLM call.

9 generators, each producing one Markdown section:
  1. start_here         — orientation / quick-start overview
  2. product_overview   — what the product does (labelled evidence)
  3. tech_stack         — each technology: what / why / where / depends-on
  4. architecture       — system architecture narrative
  5. component_guide    — 5-10 components with confidence labels
  6. main_user_flow     — numbered steps with File + Evidence citations
  7. repo_guide         — folder-by-folder + 10-20 key files
  8. how_to_run         — evidence-only commands; gaps stated explicitly
  9. unknowns_and_risks — open questions, security gaps, inferred areas

Each function:
  • Builds a system prompt (with the level_config block embedded)
  • Calls call_llm (sync, wrapped in run_in_executor for async contexts)
  • Writes output to: storage/projects/{project_id}/output/sections/{name}.md
  • Returns the markdown string

Public API:
  generate_all_sections(project_id, repo_root, ...)  — orchestrates all 9
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Callable

from app.services.llm_client import call_llm
from app.services.personalization import level_config_to_system_prompt_block

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
PROJECTS_DIR = STORAGE_DIR / "projects"

# ── Helpers ──────────────────────────────────────────────────────────────────

def _sections_dir(project_id: str) -> Path:
    d = PROJECTS_DIR / project_id / "output" / "sections"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_section(project_id: str, name: str, content: str) -> Path:
    path = _sections_dir(project_id) / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote section %s (%d chars)", name, len(content))
    return path


def _compact_summaries(summaries: list[dict], max_items: int = 15) -> str:
    lines: list[str] = []
    for s in summaries[:max_items]:
        syms = ", ".join(str(x) for x in s.get("important_symbols", [])[:6])
        conns = ", ".join(str(x) for x in s.get("connections", [])[:4])
        snippet = s.get("evidence_snippet", "").replace("\n", " ")[:120]
        lines.append(
            f"### {s['path']}\n"
            f"**Responsibility**: {s.get('responsibility', '')}\n"
            f"**Inputs**: {s.get('inputs', 'unknown')} | "
            f"**Outputs**: {s.get('outputs', 'unknown')}\n"
            f"**Symbols**: {syms or 'none'} | **Connects to**: {conns or 'none'}\n"
            f"**Snippet**: `{snippet}`"
        )
    return "\n\n".join(lines)


def _compact_relationships(relationships: list[dict], limit: int = 40) -> str:
    lines: list[str] = []
    for r in relationships[:limit]:
        lines.append(
            f"• [{r.get('relationship', '?')}] {r.get('source', '')} → "
            f"{r.get('target', '')}  "
            f"(evidence: {str(r.get('evidence', ''))[:80]})"
        )
    return "\n".join(lines) or "No relationships detected."


def _compact_tech(tech: dict) -> str:
    lines: list[str] = []
    for k, v in tech.items():
        if isinstance(v, list) and v:
            lines.append(f"- **{k}**: {', '.join(str(x) for x in v[:10])}")
        elif isinstance(v, bool) and v:
            lines.append(f"- **{k}**: yes")
        elif isinstance(v, str) and v:
            lines.append(f"- **{k}**: {v}")
    return "\n".join(lines) or "No tech data."


async def _llm_async(system_prompt: str, user_prompt: str) -> str:
    """Run sync call_llm inside the default thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: call_llm(system_prompt, user_prompt, json_mode=False),
    )


# ── Section 1: Start Here ────────────────────────────────────────────────────

async def generate_start_here(
    plan: dict,
    tech: dict,
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior developer writing the opening section of a repository tutorial.

{style}

## Your task
Write a "Start Here" section in Markdown. This is the very first thing a reader sees.
It should:
1. Explain what this repository is and what it does in 2-3 sentences.
2. Tell the reader what they will learn from this tutorial (based on the plan).
3. Recommend which sections to read first given their background.
4. Keep it concise — no more than 300 words.

Return only Markdown text. Start with a level-1 heading: # Start Here"""

    modules = json.dumps(plan.get("major_modules", []), indent=2)
    order = json.dumps(plan.get("explanation_order", [])[:5], indent=2)
    flow_target = plan.get("main_user_flow_target", "primary user journey")

    user = (
        f"## Tech Stack\n{_compact_tech(tech)}\n\n"
        f"## Major Modules\n{modules}\n\n"
        f"## Suggested Reading Order (first 5 steps)\n{order}\n\n"
        f"## Main User Flow This Tutorial Will Trace\n{flow_target}"
    )

    content = await _llm_async(system, user)
    _write_section(project_id, "01_start_here", content)
    return content


# ── Section 2: Product Overview ──────────────────────────────────────────────

async def generate_product_overview(
    product_description: str | None,
    tech: dict,
    file_summaries: list[dict],
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior developer writing the product overview section of a repository tutorial.

{style}

## Your task
Write a "Product Overview" section in Markdown. Label EVERY factual claim with one of:
  [User-Provided] — information from the product description the user supplied
  [Repository-Evidence] — inferred from actual files / code in the repository
  [Inferred] — reasonable inference with no direct file evidence (use sparingly)

The section should cover:
1. What this product is and who uses it.
2. Core capabilities / what problems it solves.
3. High-level data flow (inputs → processing → outputs).

Return only Markdown. Start with: # Product Overview"""

    user_parts: list[str] = []
    if product_description:
        user_parts.append(
            f"## User-Provided Product Description\n{product_description}"
        )
    else:
        user_parts.append("## User-Provided Product Description\n(none provided)")

    user_parts.append(f"## Tech Stack (from repository)\n{_compact_tech(tech)}")
    user_parts.append(
        f"## Important File Summaries (from repository)\n{_compact_summaries(file_summaries)}"
    )

    content = await _llm_async(system, "\n\n".join(user_parts))
    _write_section(project_id, "02_product_overview", content)
    return content


# ── Section 3: Tech Stack Explanation ────────────────────────────────────────

async def generate_tech_stack_explanation(
    tech: dict,
    file_summaries: list[dict],
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior developer explaining a project's technology stack.

{style}

## Your task
Write a "Tech Stack" section in Markdown. For EACH detected technology / framework / library:
  - **What it is** — one sentence explanation
  - **Why this project uses it** — the specific reason, with file evidence if available
  - **Where you'll see it** — which files or directories use it
  - **Depends on** — other technologies it works with in this repo

Do NOT produce a simple list. Every technology must have narrative prose.
Group related technologies together (e.g. "Backend Runtime", "Database", "Frontend Framework").

Return only Markdown. Start with: # Tech Stack"""

    user = (
        f"## Detected Tech Stack\n{_compact_tech(tech)}\n\n"
        f"## File Summaries for Context\n{_compact_summaries(file_summaries, max_items=10)}"
    )

    content = await _llm_async(system, user)
    _write_section(project_id, "03_tech_stack", content)
    return content


# ── Section 4: Architecture ───────────────────────────────────────────────────

async def generate_architecture(
    tech: dict,
    relationships: list[dict],
    file_summaries: list[dict],
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior software architect explaining a system's architecture.

{style}

## Your task
Write an "Architecture" section in Markdown. Cover:
1. The overall architectural pattern (e.g. MVC, microservices, monolith, client-server).
2. The major layers / tiers and how data flows between them.
3. Key integration points: databases, external APIs, message queues, etc.
4. Any notable design patterns observed (e.g. repository pattern, dependency injection).

Describe the architecture as a narrative — not just a list.
Where possible, cite specific file names as evidence.
If architectural details are unclear, say so explicitly rather than guessing.

Return only Markdown. Start with: # Architecture"""

    # Focus on route and import relationships
    routes = [r for r in relationships if r.get("relationship") == "declares_route"]
    imports = [r for r in relationships if r.get("relationship") == "imports"][:30]
    apis = [r for r in relationships if r.get("relationship") == "calls_api"][:20]

    user = (
        f"## Tech Stack\n{_compact_tech(tech)}\n\n"
        f"## Declared Routes ({len(routes)} total)\n"
        + _compact_relationships(routes, limit=30)
        + f"\n\n## Internal Imports (sample of {len(imports)})\n"
        + _compact_relationships(imports, limit=30)
        + f"\n\n## External API Calls ({len(apis)} total)\n"
        + _compact_relationships(apis, limit=20)
        + f"\n\n## File Summaries\n{_compact_summaries(file_summaries)}"
    )

    content = await _llm_async(system, user)
    _write_section(project_id, "04_architecture", content)
    return content


# ── Section 5: Component Guide ────────────────────────────────────────────────

async def generate_component_guide(
    file_summaries: list[dict],
    relationships: list[dict],
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior developer writing a component guide for a repository.

{style}

## Your task
Identify 5-10 logical components in this repository and describe each one.

For EACH component, produce exactly this structure (as a Markdown subsection):
### [Component Name]
- **Simple description**: one plain-English sentence about what this component does
- **Technical responsibility**: what it owns in the codebase
- **Input**: what data or events it receives
- **Output**: what it produces or exposes
- **Connected components**: which other components it talks to
- **Key files**: the most important files in this component
- **Confidence**: one of — Confirmed (files clearly show this), Inferred (reasonable inference), Unclear (limited evidence), Missing (component expected but not found)

Use exactly 5 to 10 components. Do not invent components without evidence.

Return only Markdown. Start with: # Component Guide"""

    user = (
        f"## File Summaries\n{_compact_summaries(file_summaries, max_items=20)}\n\n"
        f"## Relationships (sample)\n{_compact_relationships(relationships, limit=40)}"
    )

    content = await _llm_async(system, user)
    _write_section(project_id, "05_component_guide", content)
    return content


# ── Section 6: Main User Flow ─────────────────────────────────────────────────

async def generate_main_user_flow(
    important_features: str | None,
    relationships: list[dict],
    file_summaries: list[dict],
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior developer tracing the main user flow through a codebase.

{style}

## Your task
Trace the single most important user-facing journey through the repository as numbered steps.

For EACH step use exactly this format:
**Step N — [Action Name]**
- **What happens**: describe the action
- **File**: the file where this happens (with relative path)
- **Evidence**: the specific function name, route, or code pattern that proves this

## Critical rules:
- NEVER invent steps. If you cannot find evidence, say so.
- If the full flow cannot be traced, write a section called "## What We Found" and "## What Remains Unclear".
- Do not speculate about what "probably" happens — state it as inference and label it [Inferred].
- Cite at least one file + one piece of evidence per confirmed step.

Return only Markdown. Start with: # Main User Flow"""

    user_parts: list[str] = []
    if important_features:
        user_parts.append(f"## User-Provided Key Features\n{important_features}")
    else:
        user_parts.append("## User-Provided Key Features\n(none provided — infer the main flow from the code)")

    routes = [r for r in relationships if r.get("relationship") == "declares_route"]
    user_parts.append(
        f"## API Routes (potential flow entry points)\n{_compact_relationships(routes, limit=30)}"
    )
    user_parts.append(
        f"## File Summaries\n{_compact_summaries(file_summaries, max_items=15)}"
    )
    user_parts.append(
        f"## Imports / Dependencies\n{_compact_relationships([r for r in relationships if r.get('relationship') == 'imports'][:25], limit=25)}"
    )

    content = await _llm_async(system, "\n\n".join(user_parts))
    _write_section(project_id, "06_main_user_flow", content)
    return content


# ── Section 7: Repo Guide ─────────────────────────────────────────────────────

async def generate_repo_guide(
    inventory: list[dict],
    important_files: list[dict],
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior developer writing a repository navigation guide.

{style}

## Your task
Write a "Repo Guide" section in Markdown. Cover:
1. For each major top-level folder:
   - **Purpose**: what this folder contains
   - **File types**: main languages / file extensions inside
   - **Capability supported**: what feature area it serves
   - **Study order**: "Read now" (essential to understand the system) or "Read later" (secondary)
2. A list of the 10-20 most important individual files, each with:
   - File path
   - Why it matters (one sentence)

Return only Markdown. Start with: # Repo Guide"""

    # Summarise directory structure from inventory
    dirs: dict[str, list[str]] = {}
    for entry in inventory:
        parts = Path(entry["path"]).parts
        top = parts[0] if len(parts) > 1 else "(root)"
        dirs.setdefault(top, []).append(entry.get("language", "?"))

    dir_lines: list[str] = []
    for d, langs in sorted(dirs.items())[:20]:
        unique_langs = list(dict.fromkeys(langs))[:5]
        dir_lines.append(f"- **{d}/**: {len(langs)} files, langs: {', '.join(unique_langs)}")

    imp_lines: list[str] = []
    for f in important_files[:20]:
        imp_lines.append(f"- `{f['path']}` — {f.get('reason_important', 'important file')} (score: {f.get('score', '?')})")

    user = (
        f"## Top-Level Directory Summary\n" + "\n".join(dir_lines) +
        f"\n\n## Heuristically Important Files\n" + "\n".join(imp_lines) +
        f"\n\n## Total files in inventory: {len(inventory)}"
    )

    content = await _llm_async(system, user)
    _write_section(project_id, "07_repo_guide", content)
    return content


# ── Section 8: How to Run ─────────────────────────────────────────────────────

async def generate_how_to_run(
    readme_content: str | None,
    package_json: str | None,
    requirements_txt: str | None,
    dockerfiles: list[str],
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior developer writing a "How to Run" guide for a repository.

{style}

## Critical rule
Only include commands that have DIRECT evidence in the repository files below.
If a step cannot be confirmed, write:
  > ⚠️ The repository does not provide enough information to confirm this step.

## Your task
Write a "How to Run" section in Markdown. Cover:
1. Prerequisites (only if stated in the files)
2. Environment setup (env vars — only list keys, never values)
3. Install dependencies (with exact command from evidence)
4. Run the development server (with exact command from evidence)
5. Run tests (with exact command from evidence, or state not found)
6. Build for production (with exact command, or state not found)
7. Docker / container setup (if Dockerfiles present)

Return only Markdown. Start with: # How to Run"""

    parts: list[str] = []
    if readme_content:
        parts.append(f"## README.md content (first 3000 chars)\n{readme_content[:3000]}")
    else:
        parts.append("## README.md\n(not found)")

    if package_json:
        parts.append(f"## package.json (first 2000 chars)\n{package_json[:2000]}")

    if requirements_txt:
        parts.append(f"## requirements.txt\n{requirements_txt[:1000]}")

    if dockerfiles:
        parts.append(f"## Dockerfile content(s)\n" + "\n\n---\n\n".join(d[:800] for d in dockerfiles))

    content = await _llm_async(system, "\n\n".join(parts) if parts else "No setup files found in the repository.")
    _write_section(project_id, "08_how_to_run", content)
    return content


# ── Section 9: Unknowns & Risks ───────────────────────────────────────────────

async def generate_unknowns_and_risks(
    all_analysis_json: dict,
    secrets_report: dict,
    level_config: dict,
    project_id: str,
) -> str:
    style = level_config_to_system_prompt_block(level_config)
    system = f"""You are a senior software engineer writing a risk and unknowns section of a repository tutorial.

{style}

## Your task
Write an "Unknowns & Risks" section in Markdown. Cover:
1. **Inferred areas** — parts of the codebase where the tutorial had to guess due to missing evidence
2. **Missing documentation** — things you'd expect to find but didn't
3. **Security concerns** — secrets found, insecure patterns, missing auth
4. **Architectural risks** — single points of failure, tight coupling, hardcoded values
5. **Open questions** — things a developer would need to investigate directly

Be honest and specific. Do not downplay real issues.
For each item, state: what it is, why it matters, and how to investigate it.

Return only Markdown. Start with: # Unknowns & Risks"""

    plan_uncertain = all_analysis_json.get("plan", {}).get("uncertain_areas", [])
    secrets_findings = secrets_report.get("findings", [])[:10]
    high_risk = secrets_report.get("high_risk_files", [])

    user = (
        f"## Uncertain Areas (from explanation plan)\n"
        + (json.dumps(plan_uncertain, indent=2) if plan_uncertain else "None flagged.")
        + f"\n\n## Secrets Report\n"
        f"- Files scanned: {secrets_report.get('total_files_scanned', 0)}\n"
        f"- Files with secrets: {secrets_report.get('files_with_secrets', 0)}\n"
        f"- Secret types found: {', '.join(secrets_report.get('secret_types_found', [])) or 'none'}\n"
        f"- High-risk files: {', '.join(high_risk) or 'none'}\n\n"
        f"## Sample Secret Findings\n{json.dumps(secrets_findings, indent=2)}\n\n"
        f"## Tech Stack (for context)\n{_compact_tech(all_analysis_json.get('tech', {}))}"
    )

    content = await _llm_async(system, user)
    _write_section(project_id, "09_unknowns_and_risks", content)
    return content


# ── Helpers: read setup files from repo ───────────────────────────────────────

def _read_file_safe(path: Path, max_chars: int = 3000) -> str | None:
    try:
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + "\n… [truncated]"
        return text
    except OSError:
        return None


def _find_dockerfiles(repo_root: Path) -> list[str]:
    contents: list[str] = []
    for p in sorted(repo_root.rglob("*")):
        if p.is_dir():
            continue
        name = p.name.lower()
        if "dockerfile" in name:
            txt = _read_file_safe(p, max_chars=800)
            if txt:
                contents.append(f"--- {p.relative_to(repo_root).as_posix()} ---\n{txt}")
    return contents[:5]  # cap at 5 Dockerfiles


# ── Orchestrator ──────────────────────────────────────────────────────────────

SECTION_NAMES = [
    "01_start_here",
    "02_product_overview",
    "03_tech_stack",
    "04_architecture",
    "05_component_guide",
    "06_main_user_flow",
    "07_repo_guide",
    "08_how_to_run",
    "09_unknowns_and_risks",
]


async def generate_all_sections(
    project_id: str,
    repo_root: Path,
    plan: dict,
    tech: dict,
    important_files: list[dict],
    file_summaries: list[dict],
    relationships: list[dict],
    inventory: list[dict],
    secrets_report: dict,
    product_description: str | None,
    important_features: str | None,
    level_config: dict,
    stage_callback: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """
    Orchestrate all 9 section generators in parallel batches of 3.

    Parameters
    ----------
    stage_callback
        Optional callable(stage_label) called before each batch
        to update DB progress.

    Returns
    -------
    dict mapping section_name -> markdown_content
    """
    results: dict[str, str] = {}

    def _notify(idx: int, name: str) -> None:
        if stage_callback:
            stage_callback(f"generating_explanations ({idx}/9)")
        logger.info("Generating section %d/9: %s", idx, name)

    # Pre-read files needed by section 8 (how_to_run)
    readme = _read_file_safe(repo_root / "README.md") or _read_file_safe(repo_root / "readme.md")
    package_json = _read_file_safe(repo_root / "package.json")
    requirements = _read_file_safe(repo_root / "requirements.txt")
    dockerfiles = _find_dockerfiles(repo_root)

    # ── Batch 1: sections 1-3 (independent) ──────────────────────────────
    _notify(1, "start_here, product_overview, tech_stack")
    batch1 = await asyncio.gather(
        generate_start_here(plan=plan, tech=tech, level_config=level_config, project_id=project_id),
        generate_product_overview(product_description=product_description, tech=tech, file_summaries=file_summaries, level_config=level_config, project_id=project_id),
        generate_tech_stack_explanation(tech=tech, file_summaries=file_summaries, level_config=level_config, project_id=project_id),
    )
    results["01_start_here"] = batch1[0]
    results["02_product_overview"] = batch1[1]
    results["03_tech_stack"] = batch1[2]

    # ── Batch 2: sections 4-6 (independent) ──────────────────────────────
    _notify(4, "architecture, component_guide, main_user_flow")
    await asyncio.sleep(2)  # courtesy pause between batches
    batch2 = await asyncio.gather(
        generate_architecture(tech=tech, relationships=relationships, file_summaries=file_summaries, level_config=level_config, project_id=project_id),
        generate_component_guide(file_summaries=file_summaries, relationships=relationships, level_config=level_config, project_id=project_id),
        generate_main_user_flow(important_features=important_features, relationships=relationships, file_summaries=file_summaries, level_config=level_config, project_id=project_id),
    )
    results["04_architecture"] = batch2[0]
    results["05_component_guide"] = batch2[1]
    results["06_main_user_flow"] = batch2[2]

    # ── Batch 3: sections 7-9 (independent) ──────────────────────────────
    _notify(7, "repo_guide, how_to_run, unknowns_and_risks")
    await asyncio.sleep(2)  # courtesy pause between batches
    all_analysis = {"plan": plan, "tech": tech}
    batch3 = await asyncio.gather(
        generate_repo_guide(inventory=inventory, important_files=important_files, level_config=level_config, project_id=project_id),
        generate_how_to_run(readme_content=readme, package_json=package_json, requirements_txt=requirements, dockerfiles=dockerfiles, level_config=level_config, project_id=project_id),
        generate_unknowns_and_risks(all_analysis_json=all_analysis, secrets_report=secrets_report, level_config=level_config, project_id=project_id),
    )
    results["07_repo_guide"] = batch3[0]
    results["08_how_to_run"] = batch3[1]
    results["09_unknowns_and_risks"] = batch3[2]

    logger.info("All 9 sections generated for project %s", project_id)
    return results

