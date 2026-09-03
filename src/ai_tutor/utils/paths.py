from __future__ import annotations
from pathlib import Path
from typing import Union
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def project_path(value: Union[str, Path]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path

def load_config(*names: str) -> dict:
    """Load default config and recursively overlay method configs."""
    def merge(base: dict, extra: dict) -> dict:
        for key, value in extra.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                merge(base[key], value)
            else:
                base[key] = value
        return base
    result: dict = {}
    for name in ("default", *names):
        path = project_path("configs") / f"{name}.yaml"
        with path.open(encoding="utf-8") as handle:
            merge(result, yaml.safe_load(handle) or {})
    return result
