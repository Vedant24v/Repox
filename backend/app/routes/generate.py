"""
generate.py — POST /api/projects/{project_id}/generate

Runs the Phase-3 LLM explanation pipeline end-to-end:

  Phase stages (written to `status` column as they progress):
    reading_files
    detecting_tech          (re-uses existing tech.json)
    finding_components      (re-uses existing important_files.json)
    mapping_relationships   (re-uses existing relationships.json)
    identifying_flow        (LLM file summarization)
    generating_explanations (1/9) … generating_explanations (9/9)
    generating_diagrams     (Stage 9  — deterministic Mermaid)
    validating              (Stage 10 — path/secret checks)
    packaging               (Stage 11 — ZIP + README index)
    complete                (final)

All Phase-2 artifacts are loaded from storage/projects/{project_id}/analysis/.

Output files:
  storage/projects/{project_id}/output/plan.json
  storage/projects/{project_id}/output/sections/*.md   (9 files)
  storage/projects/{project_id}/output/diagrams/*.mmd  (3-4 files)
  storage/projects/{project_id}/output/tech_summary.json
  storage/projects/{project_id}/output/validation_report.json
  storage/projects/{project_id}/output/README.md
  storage/projects/{project_id}/repotutor_output.zip
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse

from app.services.file_summaries import summarize_important_files
from app.services.explanation_plan import generate_explanation_plan
from app.services.personalization import get_level_config
from app.services.tutorial_generator import generate_all_sections, SECTION_NAMES
from app.services.diagrams import generate_all_diagrams
from app.services.validator import validate_output
from app.services.packager import package_output, build_results_payload

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
DB_PATH = STORAGE_DIR / "db.sqlite"
PROJECTS_DIR = STORAGE_DIR / "projects"

router = APIRouter(tags=["generate"])

# Statuses from which generation is allowed to start
_ALLOWED_STATUSES = {"analyzed", "generated", "complete", "error"}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_project(project_id: str) -> sqlite3.Row | None:
    conn = _get_db()
    try:
        return conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    finally:
        conn.close()


def _set_status(project_id: str, new_status: str) -> None:
    conn = _get_db()
    try:
        conn.execute(
            "UPDATE projects SET status = ? WHERE id = ?",
            (new_status, project_id),
        )
        conn.commit()
    finally:
        conn.close()


# ── Artifact helpers ──────────────────────────────────────────────────────────

def _load_json(analysis_dir: Path, filename: str) -> dict | list:
    path = analysis_dir / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return {}


def _save_output_json(project_id: str, filename: str, data: object) -> None:
    out_dir = PROJECTS_DIR / project_id / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Core pipeline (runs in thread-pool via asyncio) ───────────────────────────

async def _run_generation_pipeline(
    project_id: str,
    repo_root: Path,
    product_description: str | None,
    important_features: str | None,
    technical_level: str | None,
) -> None:
    """
    Full Phase-3 pipeline.  Runs asynchronously — all LLM calls are offloaded
    to the default thread-pool executor inside each generator.
    """
    analysis_dir = PROJECTS_DIR / project_id / "analysis"

    try:
        # ── Stage: reading_files ──────────────────────────────────────────────
        _set_status(project_id, "reading_files")
        logger.info("[%s] Stage: reading_files", project_id)

        tech: dict = _load_json(analysis_dir, "tech.json")  # type: ignore[assignment]
        important_files: list[dict] = _load_json(analysis_dir, "important_files.json")  # type: ignore[assignment]
        relationships: list[dict] = _load_json(analysis_dir, "relationships.json")  # type: ignore[assignment]
        secrets_report: dict = _load_json(analysis_dir, "secrets_report.json")  # type: ignore[assignment]

        # Re-build inventory from repo root (lightweight — no LLM)
        _set_status(project_id, "detecting_tech")
        logger.info("[%s] Stage: detecting_tech", project_id)
        from app.services.inventory import build_inventory
        inventory = build_inventory(repo_root)

        # ── Stage: finding_components ─────────────────────────────────────────
        _set_status(project_id, "finding_components")
        logger.info("[%s] Stage: finding_components", project_id)
        # important_files already loaded from analysis artifact

        # ── Stage: mapping_relationships ──────────────────────────────────────
        _set_status(project_id, "mapping_relationships")
        logger.info("[%s] Stage: mapping_relationships", project_id)
        # relationships already loaded from analysis artifact

        # ── Stage: identifying_flow (LLM file summarization) ──────────────────
        _set_status(project_id, "identifying_flow")
        logger.info("[%s] Stage: identifying_flow", project_id)
        file_summaries = await summarize_important_files(
            repo_root=repo_root,
            important_files=important_files,
        )

        # ── Explanation plan (one LLM call) ────────────────────────────────────
        _set_status(project_id, "generating_explanations (0/9)")
        logger.info("[%s] Generating explanation plan", project_id)
        loop = asyncio.get_event_loop()
        plan = await loop.run_in_executor(
            None,
            lambda: generate_explanation_plan(
                tech=tech,
                file_summaries=file_summaries,
                relationships=relationships,
                product_description=product_description,
                important_features=important_features,
            ),
        )
        _save_output_json(project_id, "plan.json", plan)

        # ── Level config ───────────────────────────────────────────────────────
        level_config = get_level_config(technical_level)

        # ── Stage: generating_explanations (1-9/9) ─────────────────────────────
        sections_markdown = await generate_all_sections(
            project_id=project_id,
            repo_root=repo_root,
            plan=plan,
            tech=tech,
            important_files=important_files,
            file_summaries=file_summaries,
            relationships=relationships,
            inventory=inventory,
            secrets_report=secrets_report,
            product_description=product_description,
            important_features=important_features,
            level_config=level_config,
            stage_callback=lambda stage: _set_status(project_id, stage),
        )


        # ── Stage 9: generating_diagrams ───────────────────────────────────
        _set_status(project_id, "generating_diagrams")
        logger.info("[%s] Stage: generating_diagrams", project_id)
        diagrams_mmd = generate_all_diagrams(
            project_id=project_id,
            tech=tech,
            important_files=important_files,
            relationships=relationships,
            inventory=inventory,
            sections_markdown=sections_markdown,
            repo_root=repo_root,
        )

        # ── Stage 10: validating ───────────────────────────────────────────
        _set_status(project_id, "validating")
        logger.info("[%s] Stage: validating", project_id)
        validation_report = validate_output(
            project_id=project_id,
            inventory=inventory,
            important_files=important_files,
            relationships=relationships,
            sections_markdown=sections_markdown,
            diagrams_mmd=diagrams_mmd,
        )

        # ── Stage 11: packaging ────────────────────────────────────────────
        _set_status(project_id, "packaging")
        logger.info("[%s] Stage: packaging", project_id)
        package_output(
            project_id=project_id,
            tech=tech,
            plan=plan,
            validation_report=validation_report,
        )

        # ── Done ───────────────────────────────────────────────────────────
        _set_status(project_id, "complete")
        logger.info("[%s] Pipeline complete.", project_id)

    except Exception as exc:
        logger.exception("[%s] Generation pipeline failed: %s", project_id, exc)
        _set_status(project_id, "error")
        raise


# ── Route — POST /api/projects/{project_id}/generate ─────────────────────────

@router.post("/projects/{project_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_tutorial(
    project_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Trigger Phase-3 LLM explanation pipeline for a previously analysed project.

    The project must be in `analyzed` (or `generated`/`error` to re-run) status.

    Returns immediately with 202; poll GET /api/projects/{project_id}/status
    to track progress through:
      reading_files → detecting_tech → finding_components →
      mapping_relationships → identifying_flow →
      generating_explanations (1/9) … (9/9) → generated
    """
    row = _get_project(project_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Project {project_id!r} does not exist.",
            },
        )

    current_status: str = row["status"]

    # Only allow generation if analysis is done (or re-run after generate/error)
    if current_status not in _ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "not_ready",
                "message": (
                    f"Project is currently in status '{current_status}'. "
                    f"Generation requires status to be one of: "
                    f"{', '.join(sorted(_ALLOWED_STATUSES))}."
                ),
            },
        )

    repo_root = Path(row["repo_root_path"])
    if not repo_root.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": "repo_not_found",
                "message": f"Repository files no longer exist at {repo_root}.",
            },
        )

    product_description: str | None = row["product_description"]
    important_features: str | None = row["important_features"]
    technical_level: str | None = row["technical_level"]

    # FastAPI BackgroundTasks run in a threadpool (sync context), so wrap the
    # async pipeline in a synchronous function that drives its own event loop.
    def _run_sync() -> None:
        asyncio.run(
            _run_generation_pipeline(
                project_id=project_id,
                repo_root=repo_root,
                product_description=product_description,
                important_features=important_features,
                technical_level=technical_level,
            )
        )

    background_tasks.add_task(_run_sync)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "project_id": project_id,
            "status": "reading_files",
            "message": (
                "Generation pipeline started. "
                "Poll GET /api/projects/{project_id}/status for progress."
            ),
            "sections_expected": len(SECTION_NAMES),
        },
    )


# ── Route — GET /api/projects/{project_id}/output/{section} ──────────────────

@router.get("/projects/{project_id}/output/{section}")
async def get_output_section(project_id: str, section: str):
    """
    Retrieve a generated tutorial section as plain Markdown text.

    `section` should be the filename without `.md` extension, e.g. `01_start_here`.
    """
    row = _get_project(project_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Project {project_id!r} not found."},
        )

    # Sanitise section name to prevent path traversal
    safe_section = Path(section).name
    section_path = PROJECTS_DIR / project_id / "output" / "sections" / f"{safe_section}.md"

    if not section_path.exists():
        # List what's available
        sections_dir = PROJECTS_DIR / project_id / "output" / "sections"
        available = []
        if sections_dir.exists():
            available = [p.stem for p in sorted(sections_dir.glob("*.md"))]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "section_not_found",
                "message": f"Section '{section}' has not been generated yet.",
                "available_sections": available,
                "current_status": row["status"],
            },
        )

    try:
        content = section_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "read_error", "message": str(exc)},
        )

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")


# ── Route — GET /api/projects/{project_id}/output ────────────────────────────

@router.get("/projects/{project_id}/output")
async def list_output_sections(project_id: str):
    """
    List all generated tutorial sections for a project.
    """
    row = _get_project(project_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Project {project_id!r} not found."},
        )

    sections_dir = PROJECTS_DIR / project_id / "output" / "sections"
    sections = []
    if sections_dir.exists():
        for p in sorted(sections_dir.glob("*.md")):
            sections.append({
                "name": p.stem,
                "filename": p.name,
                "size_bytes": p.stat().st_size,
                "url": f"/api/projects/{project_id}/output/{p.stem}",
            })

    plan_path = PROJECTS_DIR / project_id / "output" / "plan.json"

    return JSONResponse(content={
        "project_id": project_id,
        "status": row["status"],
        "sections_ready": len(sections),
        "sections_expected": len(SECTION_NAMES),
        "sections": sections,
        "plan_ready": plan_path.exists(),
    })


@router.get("/projects/{project_id}/download")
async def download_output_zip(project_id: str):
    """
    Returns the packaged ZIP file of the tutorial output.
    """
    row = _get_project(project_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Project {project_id!r} not found."},
        )

    zip_path = PROJECTS_DIR / project_id / "repotutor_output.zip"
    if not zip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_ready",
                "message": f"Tutorial package has not been generated or is not ready yet. Status: {row['status']}",
            },
        )

    return FileResponse(
        path=zip_path,
        filename="repotutor_output.zip",
        media_type="application/zip",
    )


@router.get("/projects/{project_id}/results")
async def get_generation_results(project_id: str):
    """
    Returns all section markdown + diagram mermaid strings as JSON for the frontend.
    """
    row = _get_project(project_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Project {project_id!r} not found."},
        )

    if row["status"] != "complete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "not_ready",
                "message": f"Tutorial results are not ready yet. Status: {row['status']}",
            },
        )

    try:
        payload = build_results_payload(project_id)
        return JSONResponse(content=payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "results_failed", "message": str(exc)},
        )

