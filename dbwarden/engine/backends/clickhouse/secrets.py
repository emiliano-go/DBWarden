from __future__ import annotations

_REDACTED = "[HIDDEN]"


def _secret_values(spec: dict) -> list[str]:
    return [v for v in spec.values() if isinstance(v, str)]


def has_visible_secrets(spec: dict) -> bool:
    return not any(v == _REDACTED for v in _secret_values(spec))


def strip_secret_values(spec: dict, secret_keys: frozenset[str]) -> dict:
    out = dict(spec)
    for k in secret_keys & out.keys():
        out[k] = _REDACTED
    return out
