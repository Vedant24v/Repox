"""
diagrams.py — Generate Mermaid definitions from structured analysis.
Runs Stage 9 of the Repox explanation pipeline.
All diagrams are generated using deterministic templates/logic to ensure syntax correctness.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
PROJECTS_DIR = STORAGE_DIR / "projects"

def generate_system_architecture(tech: dict) -> str:
    """
    Generates a flowchart representing the system architecture.
    """
    lines = ["flowchart TD", "    User([User])"]
    
    # Extract components
    frontend_list = tech.get("frontend_frameworks", [])
    backend_list = tech.get("backend_frameworks", [])
    db_list = tech.get("databases", [])
    cloud_list = tech.get("cloud_platforms", [])
    container_list = tech.get("containerization", [])
    ai_list = tech.get("llm_providers", []) or tech.get("ai_frameworks", [])
    apis = tech.get("external_apis_detected", [])
    
    fe_label = f"Frontend\\n({', '.join(frontend_list)})" if frontend_list else "Frontend"
    be_label = f"Backend\\n({', '.join(backend_list)})" if backend_list else "Backend"
    db_label = f"Database\\n({', '.join(db_list)})" if db_list else "Database"
    
    lines.append(f'    Frontend["{fe_label}"]')
    lines.append(f'    Backend["{be_label}"]')
    lines.append(f'    Database[(" {db_label} ")]')
    
    lines.append("    User --> Frontend")
    lines.append("    Frontend --> Backend")
    lines.append("    Backend --> Database")
    
    if ai_list:
        ai_label = f"AI / LLM Services\\n({', '.join(ai_list)})"
        lines.append(f'    AIService["{ai_label}"]')
        lines.append("    Backend --> AIService")
        
    if apis:
        api_names = [a.split("//")[-1].split("/")[0] for a in apis if "//" in a]
        api_names = list(set(api_names))[:3]  # keep top 3
        if not api_names:
            api_names = ["External APIs"]
        api_label = f"External Services\\n({', '.join(api_names)})"
        lines.append(f'    ExtAPI["{api_label}"]')
        lines.append("    Backend --> ExtAPI")
        
    if container_list:
        lines.append(f'    %% Containerized with {", ".join(container_list)}')
        
    return "\n".join(lines)

def generate_main_user_flow(flow_markdown: str) -> str:
    """
    Parses steps from the main_user_flow markdown and builds a sequenceDiagram.
    """
    # Find steps like "Step 1 — Action" or "Step 1: Action" or "**Step 1 — Action**"
    step_pattern = re.compile(r"\*?\*?Step\s*(\d+)\s*[-—:]\s*(.*?)\*?\*?", re.IGNORECASE)
    file_pattern = re.compile(r"-\s*\*\*File\*\*\s*:\s*`?([a-zA-Z0-9_\-\./\\:]+)`?", re.IGNORECASE)
    
    steps = []
    current_step_num = None
    current_action = None
    
    lines = flow_markdown.split("\n")
    for line in lines:
        step_match = step_pattern.search(line)
        if step_match:
            current_step_num = step_match.group(1)
            current_action = step_match.group(2).strip().replace("`", "").replace("'", "").replace('"', "")
            continue
            
        file_match = file_pattern.search(line)
        if file_match and current_step_num is not None:
            file_path = file_match.group(1)
            steps.append({
                "num": current_step_num,
                "action": current_action,
                "file": file_path
            })
            current_step_num = None
            current_action = None

    if not steps:
        # Fallback if no step format was matched
        return (
            "sequenceDiagram\n"
            "    actor User\n"
            "    participant Frontend\n"
            "    participant Backend\n"
            "    participant Database\n"
            "    User->>Frontend: Access Application\n"
            "    Frontend->>Backend: Request Data\n"
            "    Backend->>Database: Query Database\n"
            "    Database-->>Backend: Query Results\n"
            "    Backend-->>Frontend: Response Data\n"
            "    Frontend-->>User: Display View\n"
        )
        
    # Helper to classify file path to participant
    def get_participant(fp: str) -> str:
        fp_lower = fp.lower()
        if any(x in fp_lower for x in ["component", "pages", "app/pages", "view", "client", "frontend", ".tsx", ".jsx", ".vue", ".svelte", "css"]):
            return "Frontend"
        if any(x in fp_lower for x in ["service", "logic", "usecase", "use_case"]):
            return "Service"
        if any(x in fp_lower for x in ["model", "schema", "db", "database", "repository", "migration", "prisma"]):
            return "Database"
        if any(x in fp_lower for x in ["external", "api_client", "thirdparty", "integration"]):
            return "ExternalAPI"
        return "Backend"

    participants = ["User"]
    diagram_steps = []
    
    last_participant = "User"
    for step in steps:
        p = get_participant(step["file"])
        if p not in participants:
            participants.append(p)
        
        action = f"Step {step['num']}: {step['action']}"
        # Truncate action for clean rendering
        if len(action) > 40:
            action = action[:37] + "..."
            
        diagram_steps.append(f"    {last_participant}->>{p}: {action}")
        last_participant = p
        
    # Link back to User at the end if we ended elsewhere
    if last_participant != "User":
        diagram_steps.append(f"    {last_participant}-->>User: Completed Flow")
        
    diagram_lines = ["sequenceDiagram"]
    for p in participants:
        if p == "User":
            diagram_lines.append(f"    actor {p}")
        else:
            diagram_lines.append(f"    participant {p}")
            
    diagram_lines.extend(diagram_steps)
    return "\n".join(diagram_lines)

def generate_repository_map(inventory: list[dict]) -> str:
    """
    Flowchart showing top-level and major subfolders of the repository.
    """
    folders = set()
    for item in inventory:
        path_parts = Path(item["path"]).parts
        if len(path_parts) > 1:
            # Add top level folder
            folders.add(path_parts[0])
            # Add second level folder if present
            if len(path_parts) > 2:
                folders.add(f"{path_parts[0]}/{path_parts[1]}")
                
    sorted_folders = sorted(list(folders))
    
    lines = ["flowchart TD", '    root["Repository Root"]']
    
    # To avoid rendering too many nodes, cap second-level nodes at 15
    rendered_folders = sorted_folders[:25]
    
    for folder in rendered_folders:
        node_id = folder.replace("/", "_").replace(".", "_").replace("-", "_")
        folder_name = folder.split("/")[-1]
        
        lines.append(f'    {node_id}["📁 {folder_name}"]')
        
        if "/" in folder:
            parent = folder.split("/")[0].replace("/", "_").replace(".", "_").replace("-", "_")
            lines.append(f"    {parent} --> {node_id}")
        else:
            lines.append(f"    root --> {node_id}")
            
    return "\n".join(lines)

def generate_database_erd(important_files: list[dict], repo_root: Path) -> str | None:
    """
    Generates a Mermaid ERD diagram if models or schemas are detected.
    """
    has_models = False
    model_files = []
    
    for f in important_files:
        path_str = f.get("path", "")
        path_lower = path_str.lower()
        if "model.py" in path_lower or "models/" in path_lower or "schema.prisma" in path_lower or "migrations/" in path_lower:
            has_models = True
            model_files.append(path_str)
            
    if not has_models:
        return None
        
    # Extract entities
    entities = []
    # Regular expressions to find entity names
    prisma_re = re.compile(r"^model\s+(\w+)\s*\{", re.MULTILINE)
    django_sqlalchemy_re = re.compile(r"^class\s+(\w+)\s*\(.*Model.*\)\s*:", re.MULTILINE)
    sqlalchemy_base_re = re.compile(r"^class\s+(\w+)\s*\(.*Base.*\)\s*:", re.MULTILINE)
    
    for file_path in model_files:
        abs_path = repo_root / file_path
        if not abs_path.exists():
            continue
        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
            # Prisma
            for match in prisma_re.finditer(content):
                entities.append(match.group(1))
            # Django/SQLAlchemy
            for match in django_sqlalchemy_re.finditer(content):
                entities.append(match.group(1))
            for match in sqlalchemy_base_re.finditer(content):
                entities.append(match.group(1))
        except Exception as e:
            logger.warning(f"Error parsing model file {file_path}: {e}")
            
    entities = list(set(entities))
    if not entities:
        # Fallback entity list
        entities = ["User", "Session"]
        
    lines = ["erDiagram"]
    for entity in entities[:10]:  # Limit to 10 entities for clean diagram
        lines.append(f"    {entity} {{")
        lines.append("        string id PK")
        lines.append("        string name")
        lines.append("    }")
        
    # Create simple relationships for entities
    if len(entities) > 1:
        for i in range(len(entities[:10]) - 1):
            lines.append(f"    {entities[i]} ||--o{{ {entities[i+1]} : relates")
            
    return "\n".join(lines)

def generate_all_diagrams(
    project_id: str,
    tech: dict,
    important_files: list[dict],
    relationships: list[dict],
    inventory: list[dict],
    sections_markdown: dict[str, str],
    repo_root: Path,
) -> dict[str, str]:
    """
    Generates all required Mermaid diagrams, saves them to the output directory, and returns them in a dict.
    """
    output_dir = PROJECTS_DIR / project_id / "output" / "diagrams"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    diagrams = {}
    
    # 1. System Architecture
    try:
        sys_arch = generate_system_architecture(tech)
        (output_dir / "system_architecture.mmd").write_text(sys_arch, encoding="utf-8")
        diagrams["system_architecture.mmd"] = sys_arch
    except Exception as e:
        logger.error(f"Error generating system_architecture.mmd: {e}")
        
    # 2. Main User Flow
    try:
        # Get flow markdown from sections_markdown
        flow_md = ""
        for key, val in sections_markdown.items():
            if "user_flow" in key or "06_" in key:
                flow_md = val
                break
        
        user_flow = generate_main_user_flow(flow_md)
        (output_dir / "main_user_flow.mmd").write_text(user_flow, encoding="utf-8")
        diagrams["main_user_flow.mmd"] = user_flow
    except Exception as e:
        logger.error(f"Error generating main_user_flow.mmd: {e}")
        
    # 3. Repository Map
    try:
        repo_map = generate_repository_map(inventory)
        (output_dir / "repository_map.mmd").write_text(repo_map, encoding="utf-8")
        diagrams["repository_map.mmd"] = repo_map
    except Exception as e:
        logger.error(f"Error generating repository_map.mmd: {e}")
        
    # 4. Database ERD (Optional)
    try:
        erd = generate_database_erd(important_files, repo_root)
        if erd:
            (output_dir / "database_erd.mmd").write_text(erd, encoding="utf-8")
            diagrams["database_erd.mmd"] = erd
    except Exception as e:
        logger.error(f"Error generating database_erd.mmd: {e}")
        
    return diagrams
