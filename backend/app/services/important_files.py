"""
important_files.py — Score and select the ~10-20 most structurally important
files in a repository using path/name heuristics.

Each file gets a numeric score; we return the top N with a human-readable
reason explaining why it was selected.
"""
from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Scoring rules
# Each rule is (score, reason_template, match_fn)
# match_fn(rel_path: Path) -> bool
# ---------------------------------------------------------------------------

def _name(p: Path) -> str:
    return p.name.lower()


def _stem(p: Path) -> str:
    return p.stem.lower()


def _parts(p: Path) -> list[str]:
    return [part.lower() for part in p.parts]


def _ext(p: Path) -> str:
    return p.suffix.lower()


_RULES: list[tuple[int, str, object]] = [
    # ── Entry points ─────────────────────────────────────────────────────
    (100, "Application entry point",
     lambda p: _name(p) in {"main.py", "app.py", "server.py", "index.py", "run.py",
                             "manage.py", "wsgi.py", "asgi.py"}),
    (100, "Application entry point",
     lambda p: _name(p) in {"index.js", "index.ts", "server.js", "server.ts",
                             "app.js", "app.ts", "main.js", "main.ts"}),
    (90, "Next.js / framework layout root",
     lambda p: _name(p) in {"layout.tsx", "layout.ts", "layout.jsx", "layout.js",
                             "_app.tsx", "_app.js", "_document.tsx"}),

    # ── Routes / controllers ──────────────────────────────────────────────
    (85, "Route definitions file",
     lambda p: any(s in _parts(p) for s in ("routes", "router", "routers"))
     and _ext(p) in {".py", ".ts", ".js", ".tsx"}),
    (80, "Controller file",
     lambda p: any(s in _parts(p) for s in ("controllers", "controller"))
     and _ext(p) in {".py", ".ts", ".js"}),
    (80, "API handler or route file",
     lambda p: any(s in _parts(p) for s in ("api", "handlers", "handler"))
     and _ext(p) in {".py", ".ts", ".js", ".tsx"}),

    # ── Services / business logic ─────────────────────────────────────────
    (75, "Service / business logic file",
     lambda p: any(s in _parts(p) for s in ("services", "service", "usecases", "use_cases"))
     and _ext(p) in {".py", ".ts", ".js"}),

    # ── Models / schemas ─────────────────────────────────────────────────
    (70, "Data model or schema definition",
     lambda p: any(s in _parts(p) for s in ("models", "model", "schemas", "schema",
                                              "entities", "entity"))
     and _ext(p) in {".py", ".ts", ".js", ".prisma"}),
    (70, "Prisma schema",
     lambda p: _name(p) == "schema.prisma"),

    # ── Frontend pages / components ───────────────────────────────────────
    (65, "Frontend page component",
     lambda p: any(s in _parts(p) for s in ("pages", "page")) and _ext(p) in {".tsx", ".jsx"}),
    (60, "Shared UI component",
     lambda p: any(s in _parts(p) for s in ("components", "component")) and _ext(p) in {".tsx", ".jsx"}),

    # ── Auth ──────────────────────────────────────────────────────────────
    (85, "Authentication logic",
     lambda p: "auth" in _stem(p) or "auth" in _parts(p)[:-1]),

    # ── Prompts / AI ─────────────────────────────────────────────────────
    (80, "AI prompt definitions",
     lambda p: any(s in _parts(p) for s in ("prompts", "prompt")) or "prompt" in _stem(p)),
    (75, "LLM / AI agent code",
     lambda p: any(s in _stem(p) for s in ("agent", "llm", "ai", "chain", "graph"))),

    # ── Config ────────────────────────────────────────────────────────────
    (65, "Environment variable template",
     lambda p: _name(p) in {".env.example", ".env.template", ".env.sample", ".env.local.example"}),
    (60, "Docker Compose configuration",
     lambda p: _name(p) in {"docker-compose.yml", "docker-compose.yaml",
                             "docker-compose.dev.yml", "docker-compose.prod.yml"}),
    (55, "Dockerfile",
     lambda p: "dockerfile" in _name(p)),
    (55, "Core config file",
     lambda p: _name(p) in {"next.config.ts", "next.config.js", "vite.config.ts",
                             "vite.config.js", "webpack.config.js", "tailwind.config.ts",
                             "pyproject.toml", "setup.py", "setup.cfg"}),

    # ── Docs ─────────────────────────────────────────────────────────────
    (50, "Project README / documentation",
     lambda p: _stem(p).startswith("readme") and _ext(p) in {".md", ".rst", ".txt", ""}),

    # ── Middleware ────────────────────────────────────────────────────────
    (60, "Middleware definition",
     lambda p: "middleware" in _name(p) and _ext(p) in {".py", ".ts", ".js"}),

    # ── Database migrations ───────────────────────────────────────────────
    (55, "Database migration file",
     lambda p: any(s in _parts(p) for s in ("migrations", "migration", "alembic"))
     and _ext(p) in {".py", ".sql", ".ts", ".js"}),
]

_MAX_FILES = 20
_MIN_SCORE = 50


def score_file(rel_path: Path) -> tuple[int, str]:
    """Return (total_score, primary_reason) for a relative file path."""
    total = 0
    primary_reason = "Matched heuristic"
    for score, reason, fn in _RULES:
        try:
            if fn(rel_path):
                if score > total:
                    primary_reason = reason
                total += score
        except Exception:
            pass
    return total, primary_reason


def select_important_files(
    inventory: list[dict],
    max_files: int = _MAX_FILES,
    min_score: int = _MIN_SCORE,
) -> list[dict]:
    """
    Given the output of build_inventory(), return the top important files.

    Returns:
        list of {path, reason_important, score}
    """
    scored = []
    for entry in inventory:
        if not entry.get("included", True):
            continue
        rel = Path(entry["path"])
        score, reason = score_file(rel)
        if score >= min_score:
            scored.append(
                {
                    "path": entry["path"],
                    "reason_important": reason,
                    "score": score,
                    "language": entry.get("language", ""),
                    "category": entry.get("category", "other"),
                }
            )

    # Sort by score descending; break ties alphabetically for determinism
    scored.sort(key=lambda x: (-x["score"], x["path"]))

    # Deduplicate by path (shouldn't happen but be safe)
    seen: set[str] = set()
    result = []
    for item in scored:
        if item["path"] not in seen:
            seen.add(item["path"])
            result.append(item)
        if len(result) >= max_files:
            break

    return result
