"""
secrets.py — Detect and redact secrets / credentials in repository files.

IMPORTANT: This module NEVER returns matched secret values.
Only secret types/categories are reported; matched values are replaced
with [REDACTED] in the masked output.
"""
from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Regex patterns: (category_label, compiled_pattern)
# Each pattern's group(0) is the full match to redact.
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    # OpenAI / similar sk- keys
    (
        "OpenAI API Key",
        re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    ),
    # Google API keys (AIza...)
    (
        "Google API Key",
        re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b"),
    ),
    # GitHub personal access tokens
    (
        "GitHub Token",
        re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    ),
    # GitHub OAuth tokens
    (
        "GitHub OAuth Token",
        re.compile(r"\bgho_[A-Za-z0-9]{36}\b"),
    ),
    # GitHub Actions tokens
    (
        "GitHub Actions Token",
        re.compile(r"\bghs_[A-Za-z0-9]{36}\b"),
    ),
    # GitHub refresh tokens
    (
        "GitHub Refresh Token",
        re.compile(r"\bghr_[A-Za-z0-9]{36}\b"),
    ),
    # AWS Access Key ID
    (
        "AWS Access Key ID",
        re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    ),
    # AWS Secret Access Key (heuristic: 40 base64 chars after known labels)
    (
        "AWS Secret Key",
        re.compile(
            r"(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9/+]{40})['\"]?",
            re.IGNORECASE,
        ),
    ),
    # Stripe keys
    (
        "Stripe API Key",
        re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b"),
    ),
    # Anthropic keys
    (
        "Anthropic API Key",
        re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
    ),
    # Generic KEY= / TOKEN= / PASSWORD= / SECRET= assignments in env-like files
    (
        "Generic Secret Assignment",
        re.compile(
            r"(?:^|[\s;,])(?:API_KEY|SECRET_KEY|PRIVATE_KEY|AUTH_TOKEN|ACCESS_TOKEN|"
            r"REFRESH_TOKEN|PASSWORD|PASSWD|DB_PASSWORD|DATABASE_PASSWORD|SECRET|"
            r"TOKEN|APP_SECRET)\s*[=:]\s*['\"]?([A-Za-z0-9!@#$%^&*()\-_=+[\]{};:,.<>?/|`~]{8,})['\"]?",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    # Database URLs with embedded credentials
    (
        "Database URL with Credentials",
        re.compile(
            r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|mssql|sqlite)"
            r"://[^:@\s]+:[^@\s]+@[^\s'\"]{4,}",
            re.IGNORECASE,
        ),
    ),
    # PEM private keys
    (
        "Private Key (PEM)",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
    # Bearer tokens inline in code
    (
        "Bearer Token",
        re.compile(
            r"""(?:Authorization|Authorization[- ]header)\s*[=:]\s*['"]?Bearer\s+([A-Za-z0-9\-._~+/]{20,})['"]?""",
            re.IGNORECASE,
        ),
    ),
    # Slack tokens
    (
        "Slack Token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    ),
    # Twilio keys
    (
        "Twilio Key",
        re.compile(r"\bSK[a-f0-9]{32}\b"),
    ),
    # SendGrid API keys
    (
        "SendGrid API Key",
        re.compile(r"\bSG\.[A-Za-z0-9_\-]{22,}\.[A-Za-z0-9_\-]{43}\b"),
    ),
    # Firebase / GCP service account JSON credential hint
    (
        "Service Account Private Key",
        re.compile(r'"private_key"\s*:\s*"-----BEGIN'),
    ),
    # Hardcoded JWT-looking strings (3 base64url segments)
    (
        "JWT Token",
        re.compile(
            r"""(?:=\s*|:\s*|['"])[eE][yY][A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"""
        ),
    ),
]

# Files that are typically secret containers (scan all text, not just source)
_ENV_EXTENSIONS: set[str] = {".env", ".envrc", ""}  # '' = no extension
_ENV_FILENAMES: set[str] = {
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.development", ".envrc", "credentials", "secrets",
    ".netrc", "auth.json",
}

# Directories to skip
_SKIP_DIRS: set[str] = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    "venv", ".venv", ".next", "coverage",
}

# Source-code extensions to scan
_SCAN_EXTS: set[str] = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs",
    ".env", ".json", ".yaml", ".yml", ".toml", ".sh",
    ".tf", ".hcl", ".ini", ".cfg",
}


# ---------------------------------------------------------------------------
# Core masking function
# ---------------------------------------------------------------------------

def mask_secrets(text: str) -> tuple[str, list[str]]:
    """
    Scan *text* for secrets, replace matched values with [REDACTED].

    Returns:
        (masked_text, list_of_detected_secret_types)

    The actual matched value is NEVER returned — only the category label.
    """
    detected_types: list[str] = []
    masked = text

    for category, pattern in _SECRET_PATTERNS:
        def _replacer(m: re.Match, cat: str = category) -> str:
            if cat not in detected_types:
                detected_types.append(cat)
            full = m.group(0)
            # If the pattern has a capturing group, only redact that group
            if m.lastindex and m.lastindex >= 1:
                captured = m.group(1)
                return full.replace(captured, "[REDACTED]")
            return "[REDACTED]"

        masked = pattern.sub(_replacer, masked)

    return masked, detected_types


# ---------------------------------------------------------------------------
# Repository-level scan
# ---------------------------------------------------------------------------

def scan_repo_for_secrets(repo_root: Path) -> dict:
    """
    Walk *repo_root* and produce a secrets report.

    Returns:
        {
            "total_files_scanned": int,
            "files_with_secrets": int,
            "secret_types_found": list[str],   # unique, across all files
            "findings": [                       # one per file that had hits
                {
                    "file": str,                # relative path
                    "secret_types": list[str],  # types found in this file
                }
            ],
            "high_risk_files": list[str],       # .env / credential files present
        }
    """
    total_scanned = 0
    files_with_secrets = 0
    all_types: list[str] = []
    findings: list[dict] = []
    high_risk_files: list[str] = []

    for path in sorted(repo_root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue

        rel = path.relative_to(repo_root).as_posix()

        # Flag .env and similar files as high-risk
        name_lower = path.name.lower()
        if name_lower in _ENV_FILENAMES or path.suffix.lower() == ".env":
            high_risk_files.append(rel)

        # Decide whether to scan this file
        should_scan = (
            path.suffix.lower() in _SCAN_EXTS
            or name_lower in _ENV_FILENAMES
            or path.suffix.lower() == ".env"
        )
        if not should_scan:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        total_scanned += 1
        _, detected = mask_secrets(text)

        if detected:
            files_with_secrets += 1
            findings.append({"file": rel, "secret_types": detected})
            for t in detected:
                if t not in all_types:
                    all_types.append(t)

    return {
        "total_files_scanned": total_scanned,
        "files_with_secrets": files_with_secrets,
        "secret_types_found": all_types,
        "findings": findings,
        "high_risk_files": high_risk_files,
    }
