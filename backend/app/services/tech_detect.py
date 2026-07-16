"""
tech_detect.py — Detect the technology stack used in a repository.

Parses known manifest files and source imports to produce a structured
tech summary. All detection is purely file-based — no network calls.
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constant sets
# ---------------------------------------------------------------------------

_FRONTEND_FRAMEWORKS = {
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "svelte": "Svelte",
    "sveltekit": "SvelteKit",
    "@sveltejs/kit": "SvelteKit",
    "angular": "Angular",
    "@angular/core": "Angular",
    "solid-js": "SolidJS",
    "preact": "Preact",
    "astro": "Astro",
    "remix": "Remix",
    "@remix-run/react": "Remix",
    "gatsby": "Gatsby",
    "qwik": "Qwik",
    "lit": "Lit",
}

_BACKEND_FRAMEWORKS = {
    # JS/TS
    "express": "Express",
    "fastify": "Fastify",
    "koa": "Koa",
    "hono": "Hono",
    "nestjs": "NestJS",
    "@nestjs/core": "NestJS",
    "hapi": "@hapi/hapi",
    "trpc": "tRPC",
    "@trpc/server": "tRPC",
    # Python
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "tornado": "Tornado",
    "starlette": "Starlette",
    "sanic": "Sanic",
    "litestar": "Litestar",
    "aiohttp": "aiohttp",
    # Ruby
    "rails": "Rails",
    # Go (detected by import path patterns in source)
    "gin-gonic/gin": "Gin",
    "echo": "Echo",
    "fiber": "Fiber",
    # Java
    "spring-boot": "Spring Boot",
    "spring-web": "Spring Web",
    "quarkus": "Quarkus",
    "micronaut": "Micronaut",
}

_DATABASES = {
    "mongoose": "MongoDB (Mongoose)",
    "mongodb": "MongoDB",
    "prisma": "@prisma/client",
    "@prisma/client": "Prisma",
    "typeorm": "TypeORM",
    "sequelize": "Sequelize",
    "drizzle-orm": "Drizzle ORM",
    "pg": "PostgreSQL (pg)",
    "postgres": "PostgreSQL",
    "mysql2": "MySQL",
    "mysql": "MySQL",
    "sqlite3": "SQLite",
    "better-sqlite3": "SQLite (better-sqlite3)",
    "redis": "Redis",
    "ioredis": "Redis (ioredis)",
    "dynamodb": "DynamoDB",
    # Python
    "sqlalchemy": "SQLAlchemy",
    "databases": "databases (async)",
    "motor": "MongoDB (Motor)",
    "pymongo": "PyMongo",
    "psycopg2": "PostgreSQL (psycopg2)",
    "psycopg": "PostgreSQL (psycopg3)",
    "aiomysql": "MySQL (aiomysql)",
    "aiosqlite": "SQLite (aiosqlite)",
    "tortoise": "Tortoise ORM",
    "beanie": "Beanie (MongoDB)",
    "pymysql": "MySQL (PyMySQL)",
}

_AUTH = {
    "next-auth": "NextAuth.js",
    "passport": "Passport.js",
    "jsonwebtoken": "JWT",
    "jose": "jose (JWT)",
    "clerk": "Clerk",
    "@clerk/nextjs": "Clerk",
    "supabase": "Supabase Auth",
    "@supabase/supabase-js": "Supabase",
    "auth0": "Auth0",
    "@auth0/nextjs-auth0": "Auth0",
    "firebase": "Firebase Auth",
    # Python
    "python-jose": "python-jose (JWT)",
    "pyjwt": "PyJWT",
    "authlib": "Authlib",
    "passlib": "passlib",
    "python-oauth2": "OAuth2",
    "fastapi-users": "FastAPI Users",
    "django-allauth": "django-allauth",
}

_AI_LLM = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "groq": "Groq",
    "transformers": "HuggingFace Transformers",
    "huggingface": "HuggingFace",
    "huggingface_hub": "HuggingFace Hub",
    "@anthropic-ai/sdk": "Anthropic",
    "llamaindex": "LlamaIndex",
    "llama-index": "LlamaIndex",
    "llama_index": "LlamaIndex",
    "google-generativeai": "Google Gemini",
    "google.generativeai": "Google Gemini",
    "vertexai": "Google Vertex AI",
    "cohere": "Cohere",
    "mistralai": "Mistral AI",
    "together": "Together AI",
    "replicate": "Replicate",
    "tiktoken": "tiktoken (OpenAI)",
    "sentence_transformers": "Sentence Transformers",
    "chromadb": "ChromaDB",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "qdrant": "Qdrant",
}

_CLOUD = {
    "aws-sdk": "AWS SDK",
    "@aws-sdk": "AWS SDK",
    "boto3": "AWS (boto3)",
    "botocore": "AWS (botocore)",
    "@google-cloud": "Google Cloud",
    "google-cloud": "Google Cloud",
    "azure": "Azure SDK",
    "@azure": "Azure SDK",
    "vercel": "Vercel",
    "netlify": "Netlify",
    "cloudflare": "Cloudflare",
    "fly.io": "Fly.io",
    "railway": "Railway",
}

_PACKAGE_MANAGERS = {
    "package-lock.json": "npm",
    "yarn.lock": "Yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "Bun",
    "requirements.txt": "pip",
    "Pipfile": "Pipenv",
    "Pipfile.lock": "Pipenv",
    "pyproject.toml": "pip/Poetry/uv",
    "poetry.lock": "Poetry",
    "uv.lock": "uv",
    "Cargo.toml": "Cargo",
    "go.mod": "Go modules",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle (Kotlin)",
    "Gemfile": "Bundler",
    "Gemfile.lock": "Bundler",
}

_TESTING = {
    # JS
    "jest": "Jest",
    "vitest": "Vitest",
    "mocha": "Mocha",
    "cypress": "Cypress",
    "playwright": "@playwright/test",
    "@playwright/test": "Playwright",
    "testing-library": "@testing-library",
    "@testing-library/react": "React Testing Library",
    # Python
    "pytest": "pytest",
    "unittest": "unittest",
    "hypothesis": "Hypothesis",
    "factory_boy": "factory_boy",
}

_AI_LLM_IMPORT_PATTERNS = [
    r"\bopenai\b",
    r"\banthropicai\b",
    r"\banthropicai/sdk\b",
    r"\banthropicai-sdk\b",
    r"\banthropic\b",
    r"\blangchain\b",
    r"\blanggraph\b",
    r"\bgroq\b",
    r"\btransformers\b",
    r"\bhuggingface\b",
    r"\bhuggingface_hub\b",
    r"\bllama_index\b",
    r"\bllamaindex\b",
    r"\bgoogle\.generativeai\b",
    r"\bvertexai\b",
    r"\bcohere\b",
    r"\bmistralai\b",
    r"\btogether\b",
    r"\breplicate\b",
    r"\bchromadb\b",
    r"\bpinecone\b",
    r"\bweaviate\b",
    r"\bqdrant_client\b",
    r"\bsentence_transformers\b",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _find_file(root: Path, name: str) -> Path | None:
    """Find the first file with this exact name (case-sensitive) in root."""
    for p in root.rglob(name):
        # Don't look inside skip dirs
        if any(
            part in {"node_modules", ".git", "venv", ".venv", "__pycache__"}
            for part in p.parts
        ):
            continue
        return p
    return None


def _match_deps(deps: dict[str, Any], lookup: dict[str, str]) -> list[str]:
    results = []
    for dep_key in deps:
        key_lower = dep_key.lower().lstrip("@").split("/")[0]
        # Try full key first
        if dep_key.lower() in lookup:
            val = lookup[dep_key.lower()]
            if val not in results:
                results.append(val)
        elif key_lower in lookup:
            val = lookup[key_lower]
            if val not in results:
                results.append(val)
    return results


def _unique(lst: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for x in lst:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_package_json(root: Path) -> dict:
    result: dict = {
        "languages": ["JavaScript"],
        "frontend_frameworks": [],
        "backend_frameworks": [],
        "databases": [],
        "auth_libraries": [],
        "ai_llm_libraries": [],
        "cloud_config": [],
        "testing_frameworks": [],
    }

    p = _find_file(root, "package.json")
    if not p:
        return result

    try:
        data = json.loads(p.read_bytes())
    except (json.JSONDecodeError, OSError):
        return result

    # Check for TypeScript
    all_deps = {
        **data.get("dependencies", {}),
        **data.get("devDependencies", {}),
        **data.get("peerDependencies", {}),
    }
    if "typescript" in all_deps or any(k.startswith("@types/") for k in all_deps):
        result["languages"].append("TypeScript")

    result["frontend_frameworks"] = _match_deps(all_deps, _FRONTEND_FRAMEWORKS)
    result["backend_frameworks"] = _match_deps(all_deps, _BACKEND_FRAMEWORKS)
    result["databases"] = _match_deps(all_deps, _DATABASES)
    result["auth_libraries"] = _match_deps(all_deps, _AUTH)
    result["ai_llm_libraries"] = _match_deps(all_deps, _AI_LLM)
    result["cloud_config"] = _match_deps(all_deps, _CLOUD)
    result["testing_frameworks"] = _match_deps(all_deps, _TESTING)
    return result


def _parse_requirements_txt(root: Path) -> dict:
    result: dict = {
        "languages": ["Python"],
        "backend_frameworks": [],
        "databases": [],
        "auth_libraries": [],
        "ai_llm_libraries": [],
        "cloud_config": [],
        "testing_frameworks": [],
    }

    p = _find_file(root, "requirements.txt")
    if not p:
        return result

    text = _read_text(p)
    # Normalise: lowercase, strip version specifiers
    deps = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[=<>!~\[;]", line)[0].strip().lower()
        deps[name] = "*"

    result["backend_frameworks"] = _match_deps(deps, _BACKEND_FRAMEWORKS)
    result["databases"] = _match_deps(deps, _DATABASES)
    result["auth_libraries"] = _match_deps(deps, _AUTH)
    result["ai_llm_libraries"] = _match_deps(deps, _AI_LLM)
    result["cloud_config"] = _match_deps(deps, _CLOUD)
    result["testing_frameworks"] = _match_deps(deps, _TESTING)
    return result


def _parse_pyproject_toml(root: Path) -> dict:
    result: dict = {
        "languages": ["Python"],
        "backend_frameworks": [],
        "databases": [],
        "auth_libraries": [],
        "ai_llm_libraries": [],
        "cloud_config": [],
        "testing_frameworks": [],
    }

    p = _find_file(root, "pyproject.toml")
    if not p:
        return result

    try:
        data = tomllib.loads(_read_text(p))
    except Exception:
        return result

    deps_list: list[str] = []
    # poetry style
    deps_list += list(data.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys())
    deps_list += list(
        data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {}).keys()
    )
    # PEP 621 style
    for dep in data.get("project", {}).get("dependencies", []):
        deps_list.append(re.split(r"[=<>!~\[;]", dep)[0].strip())

    deps = {d.lower(): "*" for d in deps_list}
    result["backend_frameworks"] = _match_deps(deps, _BACKEND_FRAMEWORKS)
    result["databases"] = _match_deps(deps, _DATABASES)
    result["auth_libraries"] = _match_deps(deps, _AUTH)
    result["ai_llm_libraries"] = _match_deps(deps, _AI_LLM)
    result["cloud_config"] = _match_deps(deps, _CLOUD)
    result["testing_frameworks"] = _match_deps(deps, _TESTING)
    return result


def _parse_pom_xml(root: Path) -> dict:
    result: dict = {"languages": ["Java"], "backend_frameworks": [], "databases": []}
    p = _find_file(root, "pom.xml")
    if not p:
        return result
    text = _read_text(p)
    # Simple artifact ID regex
    artifact_ids = re.findall(r"<artifactId>([^<]+)</artifactId>", text)
    for aid in artifact_ids:
        aid_lower = aid.lower()
        for key, label in _BACKEND_FRAMEWORKS.items():
            if key in aid_lower:
                result["backend_frameworks"].append(label)
        for key, label in _DATABASES.items():
            if key in aid_lower:
                result["databases"].append(label)
    result["backend_frameworks"] = _unique(result["backend_frameworks"])
    result["databases"] = _unique(result["databases"])
    return result


def _parse_gradle(root: Path) -> dict:
    result: dict = {"languages": ["Java/Kotlin"], "backend_frameworks": [], "databases": []}
    p = _find_file(root, "build.gradle") or _find_file(root, "build.gradle.kts")
    if not p:
        return result
    text = _read_text(p)
    for key, label in {**_BACKEND_FRAMEWORKS, **_DATABASES}.items():
        if key.lower() in text.lower():
            if label not in result["backend_frameworks"]:
                result["backend_frameworks"].append(label)
    return result


def _parse_dockerfile(root: Path) -> bool:
    return bool(_find_file(root, "Dockerfile") or _find_file(root, "Dockerfile.dev"))


def _parse_docker_compose(root: Path) -> dict:
    """Extract image names that hint at DB / service usage."""
    found: list[str] = []
    p = _find_file(root, "docker-compose.yml") or _find_file(root, "docker-compose.yaml")
    if not p:
        return {"docker_compose": False, "services": []}
    text = _read_text(p)
    images = re.findall(r"image:\s*([^\s\n]+)", text)
    for img in images:
        img_lower = img.lower().split(":")[0]
        for key, label in _DATABASES.items():
            if key in img_lower and label not in found:
                found.append(label)
    return {"docker_compose": True, "services": images[:20]}


def _grep_ai_imports(root: Path) -> list[str]:
    """Scan .py, .ts, .js, .tsx, .jsx files for AI/LLM import patterns."""
    found: list[str] = []
    extensions = {".py", ".ts", ".js", ".tsx", ".jsx", ".mjs"}
    skip = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}

    for path in root.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if path.suffix.lower() not in extensions:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in _AI_LLM_IMPORT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Map back to a friendly label
                key = re.sub(r"\\b|[\\^$(){}.*+?|]", "", pattern).strip()
                label = _AI_LLM.get(key) or key
                if label not in found:
                    found.append(label)
    return found


def _detect_languages(root: Path) -> list[str]:
    """Infer languages from file extensions (broad sweep)."""
    ext_map = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".cpp": "C++",
        ".c": "C",
        ".swift": "Swift",
        ".dart": "Dart",
        ".scala": "Scala",
    }
    skip = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}
    found: set[str] = set()
    for path in root.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        lang = ext_map.get(path.suffix.lower())
        if lang:
            found.add(lang)
    return sorted(found)


def _detect_package_managers(root: Path) -> list[str]:
    found = []
    for filename, pm in _PACKAGE_MANAGERS.items():
        if (root / filename).exists():
            if pm not in found:
                found.append(pm)
    return found


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_tech_stack(repo_root: Path) -> dict:
    """
    Parse the repo and return a structured technology summary.
    """
    pkg = _parse_package_json(repo_root)
    req = _parse_requirements_txt(repo_root)
    pyp = _parse_pyproject_toml(repo_root)
    pom = _parse_pom_xml(repo_root)
    grd = _parse_gradle(repo_root)
    docker_compose = _parse_docker_compose(repo_root)
    has_docker = _parse_dockerfile(repo_root) or docker_compose["docker_compose"]

    # AI/LLM: merge manifest results + grep over source
    ai_from_manifests = _unique(
        pkg.get("ai_llm_libraries", [])
        + req.get("ai_llm_libraries", [])
        + pyp.get("ai_llm_libraries", [])
    )
    ai_from_source = _grep_ai_imports(repo_root)
    ai_all = _unique(ai_from_manifests + ai_from_source)

    # Merge all detected databases (manifests + docker-compose images)
    databases = _unique(
        pkg.get("databases", [])
        + req.get("databases", [])
        + pyp.get("databases", [])
        + pom.get("databases", [])
        + grd.get("databases", [])
        + docker_compose["services"]  # raw image names as fallback hints
    )
    # Filter to only known DB names (remove raw docker image strings)
    databases = [d for d in databases if d in set(_DATABASES.values())]

    return {
        "languages": _unique(
            _detect_languages(repo_root)
            + pkg.get("languages", [])
            + req.get("languages", [])
            + pyp.get("languages", [])
            + pom.get("languages", [])
            + grd.get("languages", [])
        ),
        "frontend_frameworks": _unique(pkg.get("frontend_frameworks", [])),
        "backend_frameworks": _unique(
            pkg.get("backend_frameworks", [])
            + req.get("backend_frameworks", [])
            + pyp.get("backend_frameworks", [])
            + pom.get("backend_frameworks", [])
            + grd.get("backend_frameworks", [])
        ),
        "databases": databases,
        "auth_libraries": _unique(
            pkg.get("auth_libraries", [])
            + req.get("auth_libraries", [])
            + pyp.get("auth_libraries", [])
        ),
        "ai_llm_libraries": ai_all,
        "cloud_config": _unique(
            pkg.get("cloud_config", [])
            + req.get("cloud_config", [])
            + pyp.get("cloud_config", [])
        ),
        "docker": has_docker,
        "package_managers": _detect_package_managers(repo_root),
        "testing_frameworks": _unique(
            pkg.get("testing_frameworks", [])
            + req.get("testing_frameworks", [])
            + pyp.get("testing_frameworks", [])
        ),
        "external_apis_detected": [],  # populated by relationships.py
    }
