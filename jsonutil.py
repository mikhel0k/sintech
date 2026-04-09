"""Загрузка JSON для CLI: понятная ошибка, если файла нет."""

import json
from pathlib import Path
from typing import Any, Optional


def load_json(path: Path, *, hint: Optional[str] = None) -> Any:
    p = Path(path)
    if not p.is_file():
        msg = f"Файл не найден: {p.resolve()}"
        if hint:
            msg += f"\n{hint}"
        raise FileNotFoundError(msg)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
