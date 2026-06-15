from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        return cls(
            host=require_env("BDP_DB_HOST"),
            port=int(os.getenv("BDP_DB_PORT", "3306")),
            database=require_env("BDP_DB_NAME"),
            user=require_env("BDP_DB_USER"),
            password=require_env("BDP_DB_PASSWORD"),
        )


@dataclass(frozen=True)
class QnhSettings:
    mtgsig_service_url: str

    @classmethod
    def from_env(cls) -> "QnhSettings":
        return cls(
            mtgsig_service_url=require_env("QNH_MTGSIG_SERVICE_URL"),
        )


@dataclass(frozen=True)
class RuntimeSettings:
    config: dict[str, Any]
    database: DatabaseSettings
    qnh: QnhSettings

    @classmethod
    def load(cls, config_path: Path, env_path: Optional[Path] = None) -> "RuntimeSettings":
        if env_path:
            load_dotenv(env_path)
        return cls(
            config=read_yaml(config_path),
            database=DatabaseSettings.from_env(),
            qnh=QnhSettings.from_env(),
        )
