"""Runtime configuration.

Loads from environment variables (prefix `FORLAS_`) and `.env`, with sensible
defaults suited for both `uvicorn` dev runs and Tauri sidecar embedding.
"""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    """User-scoped data directory, OS-appropriate.

    Tauri sets `FORLAS_DATA_DIR` explicitly; without it we fall back to standard
    per-user locations so dev installs and bundled installs share conventions.
    """
    if env := os.environ.get("FORLAS_DATA_DIR"):
        return Path(env)
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "FORLAS" / "CRQ"
    if os.uname().sysname == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "FORLAS" / "CRQ"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "forlas-crq"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FORLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Identity / branding
    app_name: str = "FORLAS CRQ"
    app_version: str = "0.2.0"

    # Data layout
    data_dir: Path = Field(default_factory=_default_data_dir)
    database_filename: str = "forlas_crq.db"

    # Network
    host: str = "127.0.0.1"
    port: int = 8765
    cors_origins: list[str] = Field(
        # Vite dev + both Tauri WebView origin schemes (v2 uses http://tauri.localhost
        # on Windows, tauri://localhost on macOS/Linux).
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "tauri://localhost",
            "http://tauri.localhost",
            "https://tauri.localhost",
        ]
    )

    # Security
    #
    # Left as None by default so we can distinguish "operator supplied a key via
    # FORLAS_SECRET_KEY" from "no key given, load-or-create a persistent one".
    # A random per-process key would silently invalidate every session on
    # restart, so we never do that.
    secret_key: str | None = None
    secret_key_filename: str = "secret.key"
    session_cookie_name: str = "forlas_session"
    session_ttl_hours: int = 12
    argon2_time_cost: int = 3
    argon2_memory_cost_kib: int = 65536
    argon2_parallelism: int = 2

    # Simulation defaults
    default_iterations: int = 100_000
    default_seed: int = 42
    # Capped so a single run stays sub-second on SMB hardware and never ties up
    # a worker for tens of seconds. Raise deliberately if you add a background
    # job runner (the synchronous path is not meant for multi-million runs).
    max_iterations: int = 1_000_000
    # Runs at or below this execute synchronously in the request. Above it we
    # reject rather than block — kept as a single knob for a future async path.
    sync_iteration_ceiling: int = 1_000_000

    # First-run bootstrap
    seed_demo_scenarios: bool = True
    bootstrap_owner_email: str = "owner@local"
    bootstrap_owner_name: str = "Local Owner"
    # If unset, a random password is generated and printed to stdout on first run.
    bootstrap_owner_password: str | None = None

    # Reporting
    reports_dir_name: str = "reports"
    backups_dir_name: str = "backups"

    # Misc
    debug: bool = False

    # ------------------------------------------------------------------ validators

    @model_validator(mode="after")
    def _resolve_secret_key(self) -> Settings:
        """Load or create a persistent signing key.

        Precedence: explicit `FORLAS_SECRET_KEY` env/`.env` value wins. Otherwise
        read `<data_dir>/secret.key`, creating it (0600 where the OS supports it)
        on first run. This keeps sessions valid across restarts and across
        multiple uvicorn workers.
        """
        if self.secret_key:
            return self
        self.data_dir.mkdir(parents=True, exist_ok=True)
        key_path = self.data_dir / self.secret_key_filename
        if key_path.exists():
            self.secret_key = key_path.read_text(encoding="utf-8").strip()
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(48)
            key_path.write_text(self.secret_key, encoding="utf-8")
            try:
                key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            except (OSError, NotImplementedError):
                # Windows / restricted FS — best effort, not fatal.
                pass
        return self

    # ------------------------------------------------------------------ derived

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_filename

    @property
    def database_url(self) -> str:
        # SQLAlchemy sqlite URL; use absolute path so Alembic + Tauri agree.
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / self.reports_dir_name

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / self.backups_dir_name

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.reports_dir, self.backups_dir):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
