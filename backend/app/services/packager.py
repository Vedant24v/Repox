"""
packager.py — Stage 11 packaging.
Assembles the final output folder, creates the README index, and packages everything in a ZIP file.
"""
from __future__ import annotations

import json
import logging
import os
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
PROJECTS_DIR = STORAGE_DIR / "projects"

def package_output(
    project_id: str,
    tech: dict,
    plan: dict,
    validation_report: dict
) -> Path:
    """
    Assembles all sections, diagrams, tech summary, validation report, and README.md
    into the final output ZIP file.
    Returns the Path to the generated ZIP archive.
    """
    project_dir = PROJECTS_DIR / project_id
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Create tech_summary.json
    tech_summary = {
        "languages": tech.get("languages", []),
        "frontend_frameworks": tech.get("frontend_frameworks", []),
        "backend_frameworks": tech.get("backend_frameworks", []),
        "databases": tech.get("databases", []),
        "css_frameworks": tech.get("css_frameworks", []),
        "test_frameworks": tech.get("test_frameworks", []),
        "build_tools": tech.get("build_tools", []),
        "package_managers": tech.get("package_managers", []),
        "cloud_platforms": tech.get("cloud_platforms", []),
        "containerization": tech.get("containerization", []),
        "llm_providers": tech.get("llm_providers", []),
        "ai_frameworks": tech.get("ai_frameworks", []),
        "cache_stores": tech.get("cache_stores", []),
        "message_queues": tech.get("message_queues", []),
        "external_apis_detected": tech.get("external_apis_detected", [])
    }
    
    # Clean up empty list values
    tech_summary = {k: v for k, v in tech_summary.items() if v}
    
    try:
        (output_dir / "tech_summary.json").write_text(json.dumps(tech_summary, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error writing tech_summary.json: {e}")
        
    # 2. Write validation_report.json
    try:
        (output_dir / "validation_report.json").write_text(json.dumps(validation_report, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error writing validation_report.json: {e}")

    # 3. Create top-level README.md
    readme_content = f"""# Repox Explanation Report

Welcome to the Repox generated documentation for Project `{project_id}`.

This documentation folder contains comprehensive, structured explanations of the repository's codebase, architecture, components, and workflows.

## Recommended Reading Order

1. **[Start Here](sections/01_start_here.md)**: Introduction and orientation to the repository. Learn what this project does and get an overview of the guide.
2. **[Product Overview](sections/02_product_overview.md)**: High-level product definition, user roles, core capabilities, and business data flow. Factual claims are labeled for clarity.
3. **[Tech Stack Explanation](sections/03_tech_stack.md)**: Narrative explanation of the technologies used, their responsibilities, locations, and dependencies.
4. **[Architecture Guide](sections/04_architecture.md)**: Codebase architectural design pattern, structure, data-flow boundaries, and patterns.
5. **[Component Guide](sections/05_component_guide.md)**: Exhaustive breakdown of major components, input/output structures, and connection networks with confidence levels.
6. **[Main User Flow](sections/06_main_user_flow.md)**: End-to-end numbered tracing of the main user journey with file and code evidence citations.
7. **[Repository Navigation Map](sections/07_repo_guide.md)**: Directory-by-directory breakdown and list of the most important files.
8. **[How to Run & Setup](sections/08_how_to_run.md)**: Detailed step-by-step instructions derived from repo evidence for running and building the application.
9. **[Unknowns & Risks](sections/09_unknowns_and_risks.md)**: Transparency report on open questions, security patterns, and inferred areas.

## Visual Diagrams (Mermaid Format)

Diagrams are provided in standard Mermaid markdown format and can be rendered directly in GitHub, Markdown editors, or Mermaid live editor:

- **[System Architecture](diagrams/system_architecture.mmd)**: Flowchart of user, frontend, backend, database, and AI connections.
- **[Main User Flow](diagrams/main_user_flow.mmd)**: Tracing the main sequence of interactions.
- **[Repository Folder Map](diagrams/repository_map.mmd)**: A graph of major directory structures.
"""
    
    # Check if ERD diagram exists to append to README
    if (output_dir / "diagrams" / "database_erd.mmd").exists():
        readme_content += "- **[Database ERD](diagrams/database_erd.mmd)**: Relationship graph of detected data models.\n"
        
    try:
        (output_dir / "README.md").write_text(readme_content, encoding="utf-8")
    except Exception as e:
        logger.error(f"Error writing README.md: {e}")

    # 4. Zip the entire output/ folder into repotutor_output.zip inside the project directory
    zip_path = project_dir / "repotutor_output.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for path in output_dir.rglob("*"):
                if path.is_file():
                    arcname = path.relative_to(output_dir)
                    zip_file.write(path, arcname)
        logger.info(f"Successfully created ZIP file at {zip_path}")
    except Exception as e:
        logger.error(f"Error creating ZIP file: {e}")
        raise e
        
    return zip_path

def build_results_payload(project_id: str) -> dict:
    """
    Returns all section markdown + diagram mermaid strings as JSON.
    """
    project_dir = PROJECTS_DIR / project_id
    output_dir = project_dir / "output"
    
    payload = {
        "project_id": project_id,
        "sections": {},
        "diagrams": {},
        "tech_summary": {},
        "validation_report": {},
        "readme": ""
    }
    
    # 1. Load sections
    sections_dir = output_dir / "sections"
    if sections_dir.exists():
        for path in sections_dir.glob("*.md"):
            try:
                payload["sections"][path.stem] = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.error(f"Error reading section {path.name}: {e}")
                
    # 2. Load diagrams
    diagrams_dir = output_dir / "diagrams"
    if diagrams_dir.exists():
        for path in diagrams_dir.glob("*.mmd"):
            try:
                payload["diagrams"][path.name] = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.error(f"Error reading diagram {path.name}: {e}")
                
    # 3. Load JSON metadata
    try:
        tech_summary_file = output_dir / "tech_summary.json"
        if tech_summary_file.exists():
            payload["tech_summary"] = json.loads(tech_summary_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Error loading tech_summary.json: {e}")
        
    try:
        validation_file = output_dir / "validation_report.json"
        if validation_file.exists():
            payload["validation_report"] = json.loads(validation_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Error loading validation_report.json: {e}")
        
    # 4. Load README.md
    try:
        readme_file = output_dir / "README.md"
        if readme_file.exists():
            payload["readme"] = readme_file.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Error loading README.md: {e}")
        
    return payload
