import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import upload, projects, generate

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
DB_PATH = STORAGE_DIR / "db.sqlite"


def init_db() -> None:
    """Create the SQLite database and `projects` table if they don't exist."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id                  TEXT PRIMARY KEY,
            status              TEXT NOT NULL DEFAULT 'extracted',
            created_at          TEXT NOT NULL,
            product_description TEXT,
            important_features  TEXT,
            technical_level     TEXT,
            repo_root_path      TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Repox API",
    description="Backend for the Repox repository explanation tool.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and any future Vercel deployment
# ---------------------------------------------------------------------------
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
configured_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
origins = list(dict.fromkeys([*default_origins, *configured_origins]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(upload.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(generate.router, prefix="/api")


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
