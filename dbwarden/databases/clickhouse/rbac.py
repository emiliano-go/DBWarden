from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChRoleSpec:
    name: str
    settings: dict[str, str] | None = None


@dataclass(frozen=True)
class ChUserSpec:
    name: str
    auth: str = "no_password"
    roles: tuple[str, ...] = ()
    default_roles: tuple[str, ...] = ()
    host: str = "ANY"
    settings_profile: str | None = None


@dataclass(frozen=True)
class ChRowPolicySpec:
    name: str
    table: str
    using: str
    to_roles: tuple[str, ...] = ("ALL",)
    permissive: bool = True


@dataclass(frozen=True)
class ChQuotaSpec:
    name: str
    interval: str
    limits: dict[str, int]
    to_roles: tuple[str, ...] = ("ALL",)


@dataclass(frozen=True)
class ChSettingsProfileSpec:
    name: str
    settings: dict[str, str]
    to_roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChGrantSpec:
    privileges: tuple[str, ...]
    on: str
    to: str
    with_grant_option: bool = False
