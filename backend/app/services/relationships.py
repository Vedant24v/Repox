"""
relationships.py — Extract file-level relationships using regex (no AST).

Detects:
  - imports / from-imports (JS/TS and Python)
  - HTTP API calls: axios, fetch, requests
  - Route declarations: Express, FastAPI, Flask

Output is a list of:
    {
        "source": "<relative file path>",
        "relationship": "imports" | "calls_api" | "declares_route" | "uses_model",
        "target": "<module, URL, or route pattern>",
        "evidence": "<matched line truncated to 200 chars>"
    }
"""
from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_SKIP_DIRS: set[str] = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    "venv", ".venv", ".next", "coverage",
}

_SOURCE_EXTS: set[str] = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}

_EVIDENCE_MAX = 200


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# JS/TS imports
_JS_IMPORT = re.compile(
    r"""(?:import\s+.*?from\s+['"]([^'"]+)['"]|"""
    r"""(?:require)\s*\(\s*['"]([^'"]+)['"]\s*\))""",
    re.MULTILINE,
)

# JS/TS dynamic import
_JS_DYN_IMPORT = re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""")

# Axios / fetch calls — capture the URL string (static only)
_JS_HTTP_CALL = re.compile(
    r"""(?:axios|fetch)\s*\.?\s*(?:get|post|put|patch|delete|request)?\s*\(\s*['"`]([^'"`]+)['"`]""",
    re.IGNORECASE | re.MULTILINE,
)

# Express route declarations: app.get('/path', ...) | router.get('/path', ...)
_JS_ROUTE = re.compile(
    r"""(?:app|router)\s*\.\s*(get|post|put|patch|delete|all|use)\s*\(\s*['"`]([^'"`]+)['"`]""",
    re.IGNORECASE | re.MULTILINE,
)

# Python imports
_PY_IMPORT = re.compile(
    r"""^(?:import\s+([\w.,\s]+)|from\s+([\w.]+)\s+import\s+.*)""",
    re.MULTILINE,
)

# Python HTTP calls (requests library)
_PY_HTTP_CALL = re.compile(
    r"""requests\s*\.\s*(get|post|put|patch|delete|head|options)\s*\(\s*['"f]([^'")\n]{3,120})""",
    re.IGNORECASE | re.MULTILINE,
)

# httpx calls
_PY_HTTPX_CALL = re.compile(
    r"""httpx\s*\.\s*(get|post|put|patch|delete)\s*\(\s*['"]([^'")\n]{3,120})['"]""",
    re.IGNORECASE | re.MULTILINE,
)

# FastAPI route decorators
_PY_FASTAPI_ROUTE = re.compile(
    r"""@(?:app|router)\s*\.\s*(get|post|put|patch|delete)\s*\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE | re.MULTILINE,
)

# Flask route decorators
_PY_FLASK_ROUTE = re.compile(
    r"""@(?:app|bp|blueprint)\s*\.route\s*\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE | re.MULTILINE,
)

# Django URL patterns (urlpatterns / path / re_path)
_PY_DJANGO_URL = re.compile(
    r"""(?:path|re_path|url)\s*\(\s*r?['"]([^'"]+)['"]""",
    re.MULTILINE,
)

# SQLAlchemy / ORM model usage hints
_PY_MODEL_USE = re.compile(
    r"""(?:session\.(?:add|query|get|execute|merge)\(|db\.session\.|Base\.metadata)""",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evidence(line: str) -> str:
    return line.strip()[:_EVIDENCE_MAX]


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _line_for_match(text: str, match: re.Match) -> str:
    """Return the full source line that contains the regex match."""
    start = text.rfind("\n", 0, match.start()) + 1
    end = text.find("\n", match.end())
    return text[start:end if end != -1 else len(text)]


# ---------------------------------------------------------------------------
# Per-language extractors
# ---------------------------------------------------------------------------

def _extract_js(source_rel: str, text: str) -> list[dict]:
    rels: list[dict] = []

    # Imports
    for m in _JS_IMPORT.finditer(text):
        target = m.group(1) or m.group(2)
        if target:
            rels.append({
                "source": source_rel,
                "relationship": "imports",
                "target": target,
                "evidence": _evidence(_line_for_match(text, m)),
            })

    # Dynamic imports
    for m in _JS_DYN_IMPORT.finditer(text):
        rels.append({
            "source": source_rel,
            "relationship": "imports",
            "target": m.group(1),
            "evidence": _evidence(_line_for_match(text, m)),
        })

    # HTTP calls
    for m in _JS_HTTP_CALL.finditer(text):
        rels.append({
            "source": source_rel,
            "relationship": "calls_api",
            "target": m.group(1),
            "evidence": _evidence(_line_for_match(text, m)),
        })

    # Route declarations
    for m in _JS_ROUTE.finditer(text):
        method, route = m.group(1).upper(), m.group(2)
        rels.append({
            "source": source_rel,
            "relationship": "declares_route",
            "target": f"{method} {route}",
            "evidence": _evidence(_line_for_match(text, m)),
        })

    return rels


def _extract_py(source_rel: str, text: str) -> list[dict]:
    rels: list[dict] = []

    # Imports
    for m in _PY_IMPORT.finditer(text):
        if m.group(1):
            # plain `import a, b, c`
            for mod in re.split(r",\s*", m.group(1)):
                mod = mod.strip().split(" as ")[0].strip()
                if mod:
                    rels.append({
                        "source": source_rel,
                        "relationship": "imports",
                        "target": mod,
                        "evidence": _evidence(_line_for_match(text, m)),
                    })
        elif m.group(2):
            # `from x import ...`
            rels.append({
                "source": source_rel,
                "relationship": "imports",
                "target": m.group(2),
                "evidence": _evidence(_line_for_match(text, m)),
            })

    # HTTP calls
    for m in _PY_HTTP_CALL.finditer(text):
        rels.append({
            "source": source_rel,
            "relationship": "calls_api",
            "target": m.group(2).strip(),
            "evidence": _evidence(_line_for_match(text, m)),
        })

    for m in _PY_HTTPX_CALL.finditer(text):
        rels.append({
            "source": source_rel,
            "relationship": "calls_api",
            "target": m.group(2).strip(),
            "evidence": _evidence(_line_for_match(text, m)),
        })

    # FastAPI / Starlette routes
    for m in _PY_FASTAPI_ROUTE.finditer(text):
        method, route = m.group(1).upper(), m.group(2)
        rels.append({
            "source": source_rel,
            "relationship": "declares_route",
            "target": f"{method} {route}",
            "evidence": _evidence(_line_for_match(text, m)),
        })

    # Flask routes
    for m in _PY_FLASK_ROUTE.finditer(text):
        rels.append({
            "source": source_rel,
            "relationship": "declares_route",
            "target": f"ROUTE {m.group(1)}",
            "evidence": _evidence(_line_for_match(text, m)),
        })

    # Django URL patterns
    for m in _PY_DJANGO_URL.finditer(text):
        rels.append({
            "source": source_rel,
            "relationship": "declares_route",
            "target": f"URL {m.group(1)}",
            "evidence": _evidence(_line_for_match(text, m)),
        })

    # ORM / model usage
    for m in _PY_MODEL_USE.finditer(text):
        rels.append({
            "source": source_rel,
            "relationship": "uses_model",
            "target": m.group(0).rstrip("("),
            "evidence": _evidence(_line_for_match(text, m)),
        })

    return rels


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_relationships(repo_root: Path) -> list[dict]:
    """
    Walk *repo_root* and return a flat list of relationship dicts.

    Each dict: {source, relationship, target, evidence}
    """
    results: list[dict] = []

    for path in sorted(repo_root.rglob("*")):
        if path.is_dir():
            continue
        # Skip unwanted directories
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in _SOURCE_EXTS:
            continue

        text = _read(path)
        if not text:
            continue

        rel = _rel(path, repo_root)

        if path.suffix.lower() == ".py":
            results.extend(_extract_py(rel, text))
        else:
            results.extend(_extract_js(rel, text))

    # Deduplicate: same (source, relationship, target) triple
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for r in results:
        key = (r["source"], r["relationship"], r["target"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped
