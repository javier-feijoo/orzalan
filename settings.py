from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paths import get_portable_dir


SETTINGS_FILE = "empresa.json"


@dataclass
class Settings:
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Settings":
        data_dir = get_portable_dir("data")
        path = data_dir / SETTINGS_FILE
        defaults = {
            "theme": "light",
            "mostrar_costes": True,
            "idioma": "es",
            "logo_path": "",
            "company_name": "",
            "company_tax_id": "",
            "company_address": "",
            "company_phone": "",
            "company_email": "",
            "company_web": "",
            "default_vat": "",
            "default_margin": "",
            "quote_prefix": "PRES-",
        }
        if not path.exists():
            data = dict(defaults)
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return cls(data=data)
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = dict(defaults)
        except Exception:
            data = dict(defaults)
        
        # Ensure defaults
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        return cls(data=data)

    def save(self) -> None:
        data_dir = get_portable_dir("data")
        path = data_dir / SETTINGS_FILE
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
