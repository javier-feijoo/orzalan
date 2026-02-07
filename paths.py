from __future__ import annotations

import sys
from pathlib import Path


PORTABLE_DIRS = [
    "data",
    "imports",
    "exports",
    "backups",
]


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def ensure_portable_dirs() -> dict[str, Path]:
    base_dir = get_base_dir()
    paths: dict[str, Path] = {}
    for name in PORTABLE_DIRS:
        p = base_dir / name
        p.mkdir(parents=True, exist_ok=True)
        paths[name] = p
    return paths


def get_portable_dir(name: str) -> Path:
    if name not in PORTABLE_DIRS:
        raise ValueError(f"Unknown portable dir: {name}")
    base_dir = get_base_dir()
    p = base_dir / name
    p.mkdir(parents=True, exist_ok=True)
    return p
