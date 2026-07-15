from __future__ import annotations

from typing import Any


def _format_meta_value(value: Any, indent: str = "        ") -> list[str]:
    if isinstance(value, str):
        return [f"{indent}{value!r}"]
    if isinstance(value, list):
        if not value:
            return [f"{indent}[]"]
        lines = [f"{indent}["]
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{indent}    {item!r},")
            else:
                lines.append(f"{indent}    {item!r},")
        lines.append(f"{indent}]")
        return lines
    return [f"{indent}{value!r}"]
