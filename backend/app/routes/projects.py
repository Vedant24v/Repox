"""
projects.py — Project query routes.

GET /api/projects/{project_id}/status
    Returns the current stage + status of a project (for frontend polling).

GET /api/projects/{project_id}/analysis/{artifact}
    Returns one of the analysis JSON artefacts (tech, important_files,
    relationships, secrets_report) — once analysis is complete.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
DB_PATH = STORAGE_DIR / "db.sqlite"
PROJECTS_DIR = STORAGE_DIR / "projects"

router = APIRouter(tags=["projects"])

_VALID_ARTIFACTS = {"tech", "important_files", "relationships", "secrets_report"}

# Map status values to a human-readable stage name + progress percentage
_STATUS_META: dict[str, dict] = {
    # ── Phase 2: analysis ─────────────────────────────────────────────────────
    "extracted":                  {"stage": "Extraction complete",           "progress": 10},
    "analyzing:tech":             {"stage": "Detecting tech stack",          "progress": 30},
    "analyzing:important_files":  {"stage": "Scoring important files",       "progress": 50},
    "analyzing:relationships":    {"stage": "Mapping relationships",         "progress": 70},
    "analyzing:secrets":          {"stage": "Scanning for secrets",          "progress": 85},
    "analyzed":                   {"stage": "Analysis complete",             "progress": 100},
    # ── Phase 3: generation ───────────────────────────────────────────────────
    "reading_files":                    {"stage": "Reading repository files",       "progress": 5},
    "detecting_tech":                   {"stage": "Confirming tech stack",          "progress": 10},
    "finding_components":               {"stage": "Identifying components",         "progress": 15},
    "mapping_relationships":            {"stage": "Mapping relationships",          "progress": 20},
    "identifying_flow":                 {"stage": "Summarising files with LLM",     "progress": 30},
    "generating_explanations (0/9)":    {"stage": "Planning explanation",           "progress": 35},
    "generating_explanations (1/9)":    {"stage": "Writing: Start Here",            "progress": 42},
    "generating_explanations (2/9)":    {"stage": "Writing: Product Overview",      "progress": 50},
    "generating_explanations (3/9)":    {"stage": "Writing: Tech Stack",            "progress": 57},
    "generating_explanations (4/9)":    {"stage": "Writing: Architecture",          "progress": 64},
    "generating_explanations (5/9)":    {"stage": "Writing: Component Guide",       "progress": 71},
    "generating_explanations (6/9)":    {"stage": "Writing: Main User Flow",        "progress": 78},
    "generating_explanations (7/9)":    {"stage": "Writing: Repo Guide",            "progress": 85},
    "generating_explanations (8/9)":    {"stage": "Writing: How to Run",            "progress": 92},
    "generating_explanations (9/9)":    {"stage": "Writing: Unknowns & Risks",      "progress": 97},
    "generated":                        {"stage": "Tutorial ready",                 "progress": 100},
    "complete":                         {"stage": "Generation complete",            "progress": 100},
    # ── Errors ────────────────────────────────────────────────────────────────
    "error":                      {"stage": "Pipeline failed",              "progress": 0},
}


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """
    Poll this endpoint to track analysis progress.

    Returns:
        {
            "project_id": str,
            "status": str,          # raw DB value
            "stage": str,           # human-readable label
            "progress": int,        # 0-100
            "is_complete": bool,
            "is_error": bool,
        }
    """
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT id, status, created_at FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Project {project_id!r} not found."},
        )

    db_status: str = row["status"]
    meta = _STATUS_META.get(db_status, {"stage": db_status, "progress": 0})

    return JSONResponse(
        content={
            "project_id": project_id,
            "status": db_status,
            "stage": meta["stage"],
            "progress": meta["progress"],
            "is_complete": db_status in {"analyzed", "generated", "complete"},
            "is_error": db_status == "error",
            "created_at": row["created_at"],
        }
    )


@router.get("/projects/{project_id}/analysis/{artifact}")
async def get_analysis_artifact(project_id: str, artifact: str):
    """
    Retrieve one of the analysis JSON artefacts.

    artifact must be one of: tech | important_files | relationships | secrets_report
    """
    if artifact not in _VALID_ARTIFACTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_artifact",
                "message": f"artifact must be one of: {', '.join(sorted(_VALID_ARTIFACTS))}",
            },
        )

    # Verify project exists
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT status FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Project {project_id!r} not found."},
        )

    artifact_path = PROJECTS_DIR / project_id / "analysis" / f"{artifact}.json"
    if not artifact_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "artifact_not_ready",
                "message": f"Artifact '{artifact}' is not available yet. "
                           f"Current status: {row['status']}",
            },
        )

    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "artifact_read_error", "message": str(exc)},
        )

    return JSONResponse(content=data)
