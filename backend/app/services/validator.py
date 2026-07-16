"""
validator.py — Stage 10 validation checks.
Checks generated markdown for valid file paths, diagram components, and scans for any leaked secrets.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from app.services.secrets import mask_secrets

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
PROJECTS_DIR = STORAGE_DIR / "projects"

def validate_output(
    project_id: str,
    inventory: list[dict],
    important_files: list[dict],
    relationships: list[dict],
    sections_markdown: dict[str, str],
    diagrams_mmd: dict[str, str]
) -> dict:
    """
    Runs validation checks on generated sections and diagrams.
    Saves a report to output_dir / "validation_report.json".
    """
    output_dir = PROJECTS_DIR / project_id / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report = {
        "project_id": project_id,
        "unresolved_file_paths": [],
        "unresolved_diagram_components": [],
        "leaked_secrets_detected": []
    }
    
    # Create sets for fast lookup
    inventory_paths = {item["path"] for item in inventory}
    inventory_basenames = {Path(item["path"]).name for item in inventory}
    
    important_paths = {item["path"] for item in important_files}
    important_basenames = {Path(item["path"]).name for item in important_files}
    
    relationship_targets = {item.get("target", "") for item in relationships}
    relationship_sources = {item.get("source", "") for item in relationships}
    
    known_components = important_paths.union(important_basenames).union(relationship_targets).union(relationship_sources)
    known_components = {str(c).lower() for c in known_components}
    
    # 1. Check file paths in generated markdown
    sections_dir = output_dir / "sections"
    
    # Fallback to validating sections_markdown dict if files don't exist yet on disk
    for name, content in sections_markdown.items():
        try:
            # Check for secrets as a safety pass
            masked_content, detected_secrets = mask_secrets(content)
            if detected_secrets:
                report["leaked_secrets_detected"].append({
                    "file": f"{name}.md",
                    "secret_types": detected_secrets
                })
                # Overwrite file with masked content if it exists
                md_file = sections_dir / f"{name}.md"
                if md_file.exists():
                    md_file.write_text(masked_content, encoding="utf-8")
                content = masked_content
            
            # Extract paths
            # Match potential file paths: e.g. path/to/file.ext or file.ext (minimum one dot and extension)
            path_regex = re.compile(r"\b(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9_]{1,10}\b")
            matches = path_regex.findall(content)
            for path_str in matches:
                if path_str.startswith("http") or path_str.startswith("www."):
                    continue
                if re.match(r"^\d+\.\d+$", path_str):
                    continue
                    
                normalized_path = path_str.replace("\\", "/")
                if normalized_path not in inventory_paths and Path(normalized_path).name not in inventory_basenames:
                    report["unresolved_file_paths"].append({
                        "section": f"{name}.md",
                        "path": path_str
                    })
        except Exception as e:
            logger.error(f"Error validating file paths in section {name}: {e}")

    # 2. Check components in diagrams
    for name, content in diagrams_mmd.items():
        try:
            # Simple extraction of components from Mermaid
            labels = []
            bracket_labels = re.findall(r"\[\"([^\"]+)\"\]|\[([^\]]+)\]|\(([^)]+)\)", content)
            for match in bracket_labels:
                for group in match:
                    if group:
                        labels.append(group.strip())
                        
            actor_labels = re.findall(r"(?:actor|participant)\s+([a-zA-Z0-9_\-\.]+)", content)
            labels.extend(actor_labels)
            
            for label in set(labels):
                label_lower = label.lower()
                if label_lower in ["user", "frontend", "backend", "database", "service", "externalapi", "external api", "external services", "repository root"]:
                    continue
                
                matched = False
                for comp in known_components:
                    if label_lower in comp or comp in label_lower:
                        matched = True
                        break
                        
                if not matched:
                    report["unresolved_diagram_components"].append({
                        "diagram": name,
                        "component": label
                    })
        except Exception as e:
            logger.error(f"Error validating diagram {name}: {e}")

    # Deduplicate lists
    report["unresolved_file_paths"] = list({(item["section"], item["path"]): item for item in report["unresolved_file_paths"]}.values())
    report["unresolved_diagram_components"] = list({(item["diagram"], item["component"]): item for item in report["unresolved_diagram_components"]}.values())

    # Write report
    report_file = output_dir / "validation_report.json"
    try:
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error writing validation report: {e}")
        
    return report
