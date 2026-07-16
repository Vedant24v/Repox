"""
inventory.py — Walk a repository root and build a structured file inventory.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Extension → language mapping
# ---------------------------------------------------------------------------
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    # Web / JS ecosystem
    ".ts": "TypeScript",
    ".tsx": "TypeScript (JSX)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (JSX)",
    ".mjs": "JavaScript (ESM)",
    ".cjs": "JavaScript (CJS)",
    ".vue": "Vue",
    ".svelte": "Svelte",
    # Python
    ".py": "Python",
    ".pyi": "Python (stub)",
    # Rust
    ".rs": "Rust",
    # Go
    ".go": "Go",
    # Java / JVM
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin Script",
    ".scala": "Scala",
    ".groovy": "Groovy",
    # C / C++
    ".c": "C",
    ".h": "C Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++ Header",
    # C#
    ".cs": "C#",
    # Ruby
    ".rb": "Ruby",
    # PHP
    ".php": "PHP",
    # Swift
    ".swift": "Swift",
    # Dart / Flutter
    ".dart": "Dart",
    # Shell
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".fish": "Fish",
    ".ps1": "PowerShell",
    # Markup / data
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".xml": "XML",
    ".json": "JSON",
    ".jsonc": "JSON (with comments)",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".env": "Env",
    # Docs
    ".md": "Markdown",
    ".mdx": "MDX",
    ".rst": "reStructuredText",
    ".txt": "Plain Text",
    # SQL
    ".sql": "SQL",
    # GraphQL
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    # Terraform / infra
    ".tf": "Terraform",
    ".hcl": "HCL",
    # Docker
    "dockerfile": "Dockerfile",
    ".dockerfile": "Dockerfile",
    # Other config
    ".lock": "Lock File",
    ".gitignore": "Git Config",
    ".editorconfig": "EditorConfig",
}

Category = Literal[
    "frontend_component",
    "backend_route",
    "model",
    "config",
    "test",
    "doc",
    "other",
]

# Directories to skip entirely when walking the repo
SKIP_DIRS: set[str] = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    "venv",
    ".venv",
    ".next",
    "target",
    ".idea",
    ".vscode",
    "coverage",
}


def _detect_language(path: Path) -> str:
    """Return a human-readable language name for a given file path."""
    name_lower = path.name.lower()
    # Exact filename matches (e.g. Dockerfile, .gitignore)
    if name_lower in EXTENSION_LANGUAGE_MAP:
        return EXTENSION_LANGUAGE_MAP[name_lower]
    ext = path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")


def _categorize(path: Path) -> Category:
    """Heuristically assign a category to a file based on name / path parts."""
    parts_lower = [p.lower() for p in path.parts]
    name_lower = path.name.lower()
    stem_lower = path.stem.lower()
    ext_lower = path.suffix.lower()

    # --- Tests ---
    if any(
        kw in name_lower
        for kw in ("test", "spec", ".test.", ".spec.", "_test", "_spec")
    ):
        return "test"
    if any(p in ("tests", "test", "__tests__", "spec", "specs") for p in parts_lower):
        return "test"

    # --- Docs ---
    if ext_lower in (".md", ".mdx", ".rst", ".txt"):
        return "doc"
    if any(p in ("docs", "doc", "documentation") for p in parts_lower):
        return "doc"

    # --- Config ---
    config_names = {
        "package.json",
        "tsconfig.json",
        "next.config.ts",
        "next.config.js",
        "vite.config.ts",
        "vite.config.js",
        "tailwind.config.ts",
        "tailwind.config.js",
        "webpack.config.js",
        "rollup.config.js",
        "babel.config.js",
        ".babelrc",
        "jest.config.ts",
        "jest.config.js",
        "vitest.config.ts",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".env",
        ".env.local",
        ".env.example",
        ".gitignore",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.json",
        ".prettierrc",
        ".editorconfig",
    }
    if name_lower in config_names:
        return "config"
    if ext_lower in (".toml", ".ini", ".yaml", ".yml", ".lock", ".env", ".cfg"):
        return "config"

    # --- Models / schemas ---
    model_keywords = ("model", "schema", "entity", "type", "interface", "dto", "orm")
    if any(kw in stem_lower for kw in model_keywords):
        return "model"
    if any(p in ("models", "schemas", "entities", "types") for p in parts_lower):
        return "model"

    # --- Backend routes / controllers / services ---
    backend_keywords = (
        "route",
        "router",
        "controller",
        "handler",
        "service",
        "api",
        "endpoint",
        "view",
        "server",
    )
    if any(kw in stem_lower for kw in backend_keywords):
        return "backend_route"
    if any(
        p in ("routes", "controllers", "handlers", "services", "api", "views")
        for p in parts_lower
    ):
        return "backend_route"

    # --- Frontend components ---
    frontend_exts = {".tsx", ".jsx", ".vue", ".svelte"}
    if ext_lower in frontend_exts:
        return "frontend_component"
    frontend_dirs = (
        "components",
        "pages",
        "app",
        "views",
        "layouts",
        "ui",
        "screens",
    )
    if any(p in frontend_dirs for p in parts_lower) and ext_lower in (
        ".ts",
        ".js",
        ".css",
        ".scss",
    ):
        return "frontend_component"

    return "other"


def build_inventory(repo_root: Path) -> list[dict]:
    """
    Walk *repo_root* and return a list of file descriptor dicts.

    Each dict contains:
        path        — relative path from repo_root (POSIX string)
        extension   — file extension (lower-case, including dot)
        language    — human-readable language name
        size        — file size in bytes
        category    — one of Category literals
        included    — True by default (reserved for future filtering)
    """
    inventory: list[dict] = []

    for dirpath, dirnames, filenames in os.walk(repo_root):
        # Prune skip-dirs in-place so os.walk won't descend into them
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            abs_path = Path(dirpath) / filename
            try:
                size = abs_path.stat().st_size
            except OSError:
                size = 0

            rel_path = abs_path.relative_to(repo_root)
            ext = abs_path.suffix.lower()

            inventory.append(
                {
                    "path": rel_path.as_posix(),
                    "extension": ext,
                    "language": _detect_language(abs_path),
                    "size": size,
                    "category": _categorize(rel_path),
                    "included": True,
                }
            )

    return inventory
