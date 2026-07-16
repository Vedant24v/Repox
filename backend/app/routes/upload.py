"""
upload.py — POST /api/projects

Accepts a repository ZIP file plus optional metadata, extracts it to disk,
inserts a project row into SQLite, runs the full analysis pipeline, and
returns the project_id with status.

Analysis pipeline (all synchronous, run in a thread-pool via asyncio):
  Stage 1 — extraction + inventory (happens inline)
  Stage 2 — tech_detect
  Stage 3 — important_files
  Stage 4 — relationships
  Stage 5 — secrets scan
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sqlite3
import zipfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse

from app.services.inventory import build_inventory, SKIP_DIRS
from app.services.tech_detect import detect_tech_stack
from app.services.important_files import select_important_files
from app.services.relationships import extract_relationships
from app.services.secrets import scan_repo_for_secrets

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
DB_PATH = STORAGE_DIR / "db.sqlite"
PROJECTS_DIR = STORAGE_DIR / "projects"

router = APIRouter(tags=["projects"])


# ---------------------------------------------------------------------------
# Enums / helpers
# ---------------------------------------------------------------------------
class TechnicalLevel(str, Enum):
    beginner = "beginner"
    product = "product"
    developer = "developer"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _detect_repo_root(extraction_dir: Path) -> Path:
    """
    If the ZIP contained a single top-level folder, treat that as the repo
    root so paths are clean.  Otherwise use the extraction dir itself.
    """
    try:
        children = [
            p for p in extraction_dir.iterdir() if p.name not in SKIP_DIRS
        ]
    except StopIteration:
        return extraction_dir

    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extraction_dir


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


def _save_json(analysis_dir: Path, filename: str, data: object) -> None:
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / filename).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _run_analysis(project_id: str, repo_root: Path, inventory: list[dict]) -> None:
    """
    Synchronous analysis pipeline — intended to be run in a thread-pool.

    Writes JSON artefacts to:
        storage/projects/{project_id}/analysis/
            tech.json
            important_files.json
            relationships.json
            secrets_report.json
    """
    analysis_dir = PROJECTS_DIR / project_id / "analysis"

    # ── Stage 3: tech detection ───────────────────────────────────────────
    _set_status(project_id, "analyzing:tech")
    tech = detect_tech_stack(repo_root)
    _save_json(analysis_dir, "tech.json", tech)

    # ── Stage 4: important files ──────────────────────────────────────────
    _set_status(project_id, "analyzing:important_files")
    important = select_important_files(inventory)
    _save_json(analysis_dir, "important_files.json", important)

    # ── Stage 5a: relationships ───────────────────────────────────────────
    _set_status(project_id, "analyzing:relationships")
    rels = extract_relationships(repo_root)

    # Extract external API targets to enrich tech summary
    external_apis = list({
        r["target"]
        for r in rels
        if r["relationship"] == "calls_api"
        and r["target"].startswith(("http://", "https://", "/api/"))
    })
    tech["external_apis_detected"] = external_apis[:50]
    _save_json(analysis_dir, "tech.json", tech)       # re-save with APIs
    _save_json(analysis_dir, "relationships.json", rels)

    # ── Stage 5b: secrets scan ────────────────────────────────────────────
    _set_status(project_id, "analyzing:secrets")
    secrets_report = scan_repo_for_secrets(repo_root)
    _save_json(analysis_dir, "secrets_report.json", secrets_report)

    # ── Done ──────────────────────────────────────────────────────────────
    _set_status(project_id, "analyzed")


# ---------------------------------------------------------------------------
# Route — POST /api/projects
# ---------------------------------------------------------------------------
@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def upload_project(
    file: UploadFile = File(..., description="Repository ZIP archive"),
    product_description: Optional[str] = Form(None),
    important_features: Optional[str] = Form(None),
    technical_level: Optional[TechnicalLevel] = Form(TechnicalLevel.beginner),
):
    # ---- 1. Basic content-type sanity check --------------------------------
    if file.content_type not in (
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
        "application/x-zip",
    ) and not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_file_type",
                "message": "Only ZIP archives are accepted.",
            },
        )

    # ---- 2. Read the upload into memory ------------------------------------
    contents = await file.read()

    # ---- 3. Validate it's a real ZIP ----------------------------------------
    try:
        zf = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "bad_zip_file",
                "message": "The uploaded file is not a valid ZIP archive.",
            },
        )

    # ---- 4. Create project directories -------------------------------------
    project_id = str(uuid4())
    raw_dir = PROJECTS_DIR / project_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # ---- 5. Extract — skipping unwanted directories ------------------------
    extracted_count = 0
    for member in zf.infolist():
        member_path = Path(member.filename.replace("\\", "/"))

        if any(part in SKIP_DIRS for part in member_path.parts):
            continue

        dest = raw_dir / member_path
        try:
            dest.resolve().relative_to(raw_dir.resolve())
        except ValueError:
            continue  # path traversal detected — skip

        if member.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member.filename))
            extracted_count += 1

    zf.close()

    # ---- 6. Detect repo root -----------------------------------------------
    repo_root = _detect_repo_root(raw_dir)

    # ---- 7. Build file inventory ------------------------------------------
    inventory = build_inventory(repo_root)
    file_count = len(inventory)

    # ---- 8. Persist to SQLite ----------------------------------------------
    created_at = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        conn.execute(
            """
            INSERT INTO projects
                (id, status, created_at, product_description,
                 important_features, technical_level, repo_root_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                "extracted",
                created_at,
                product_description,
                important_features,
                technical_level.value if technical_level else None,
                str(repo_root),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # ---- 9. Run analysis pipeline in background thread --------------------
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        None,
        _run_analysis,
        project_id,
        repo_root,
        inventory,
    )

    # ---- 10. Return response -----------------------------------------------
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "project_id": project_id,
            "status": "extracted",
            "file_count": file_count,
            "repo_root": str(repo_root),
        },
    )
