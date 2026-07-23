---
description: Inspect discovered DBWarden plugins and registered hooks.
---

# Plugin List And Info

## List Plugins

```bash
dbwarden plugin list
```

The Rich table shows every discovered distribution with its version, tier, trust state, load state, the hooks and object handlers it registered, and its lockfile verification status.

```text
                                     DBWarden Plugins
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Distribution           ┃ Version ┃ Tier      ┃ Trusted ┃ State   ┃ Hooks           ┃ Objects      ┃ Lock       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ dbwarden-fastapi       │ 0.1.0   │ official  │ yes     │ loaded  │ health_routes,  │ -            │ provenance │
│                        │         │           │         │         │ session_factory │              │            │
│ dbwarden-pgsql-exten…  │ 0.3.0   │ official  │ yes     │ loaded  │ -               │ pg_extension │ provenance │
│ dbwarden-acme          │ 1.0.0   │ community │ no      │ skipped │ -               │ -            │ -          │
└────────────────────────┴─────────┴───────────┴─────────┴─────────┴─────────────────┴──────────────┴────────────┘
```

Column meanings:

- **Trusted**: `yes` if the plugin is allowed to load (official, approved-and-current, or consented community).
- **State**: `loaded`, `skipped` (untrusted community), `failed` (raised during `setup`), or `discovered`.
- **Hooks / Objects**: the value hooks and object handler types the plugin registered. A discovered-but-skipped plugin registers nothing, so these stay empty.
- **Lock**: the lockfile `verified` value (e.g. `provenance`) for provenance-locked installs.

### JSON Output

For CI or scripting, use `--format json`:

```bash
dbwarden plugin list --format json
```

```json
[
  {
    "distribution": "dbwarden-fastapi",
    "version": "0.1.0",
    "tier": "official",
    "trusted": true,
    "state": "loaded",
    "hooks": ["health_routes", "session_factory"],
    "object_handlers": [],
    "error": null,
    "lock": {"verified": "provenance", "identity": "https://github.com/dbwarden-org/dbwarden-fastapi", "...": "..."}
  }
]
```

## Plugin Details

```bash
dbwarden plugin info dbwarden-fastapi
```

```text
Plugin Info
  Distribution       dbwarden-fastapi
  Version            0.1.0
  Entry point        fastapi = dbwarden_fastapi:setup
  Tier               official
  Trusted            yes
  State              loaded
  Hooks              health_routes, session_factory
  Object handlers    -
  Error
  Repository         https://github.com/dbwarden-org/dbwarden-fastapi
  Approved minimum
  Lock verified      provenance
  Lock identity      https://github.com/dbwarden-org/dbwarden-fastapi
```

- For **Official** plugins, details include the repository and lockfile provenance fields.
- For **Approved** plugins, the **Approved minimum** row shows the version floor.
- For **Community** plugins, trust reflects consent state; `Repository` and `Approved minimum` are empty.

`plugin info` also supports `--format json`.

## Checking Registered Hooks

Both `plugin list` and `plugin info` report the hooks and object handlers registered **after load**. If a plugin is discovered but skipped (untrusted) or failed during `setup`, those columns are empty and, for failures, the **Error** row explains why.
