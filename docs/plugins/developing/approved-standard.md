---
description: Approved plugin test standard and review process.
---

# Approved Plugin Standard

The **Approved** tier earns a plugin the **Verified** badge: it loads without per-user consent once its installed version meets the approved minimum. To qualify, the plugin must pass a focused, automatable conformance suite that proves it respects the DBWarden contract, does not compromise the user's environment, and (for object plugins) integrates correctly with the diff pipeline.

The suite is deliberately minimal. It does **not** review business logic, performance, or security; it ensures the plugin is a well-behaved citizen.

!!! warning "Approval is not a security audit"
    The Verified badge is a statement of contract adherence, not fitness for purpose. It says the plugin respects DBWarden's rules, will not break core, and will not execute code before you consent. It does **not** certify the plugin is free of vulnerabilities or malicious behavior, and it grants no sandboxing. A loaded plugin runs with full process privileges. Vet the source yourself for anything sensitive.

## The Conformance Harness

DBWarden ships the checks as `dbwarden.plugin_conformance`, so verification is reproducible rather than a one-time manual event. Each function raises `ConformanceError` with an explanation on failure. The [plugin template](publishing.md#starting-from-the-template) already wires them into `tests/test_conformance.py`; copy that file and adjust the distribution/package names.

## Required Tests

| # | Test | Harness call | Protects against |
|---|------|--------------|------------------|
| 1 | `test_entry_point_is_declared` | `assert_entry_point_declared(dist)` | Misconfigured packaging, missing/unresolvable entry point, a plugin that can never be discovered. |
| 2 | `test_import_has_no_side_effects` | `assert_import_has_no_side_effects(pkg)` | The #1 security-model violation: registering at import time bypasses the consent gate. Enforces classify-before-load. |
| 3 | `test_setup_registers_hooks` | `assert_setup_registers(setup, value_hooks=...)` | A broken `setup()` (wrong signature, swallowed exception, forgot to register) that installs but does nothing. |
| 4 | `test_hook_signature_compliance` | `assert_hook_signatures(setup)` | Runtime `TypeError` when core calls a hook with the documented arguments; caught at build time instead of migration time. |
| 5 | `test_no_core_internals_imported` | `assert_no_core_internals_imported(pkg)` | Dependence on implementation details that break on core upgrades, and a plugin reaching into `dbwarden.engine.*` to manipulate the pipeline. |
| 6 | `test_object_handler_conformance` (object plugins) | `assert_object_handler_conformance(handler, config=...)` | Handlers that crash the diff pipeline or emit malformed statements: `extract`/`canonicalize`/`diff`/`emit` must return the right types. |
| 7 | `test_ordering_constraint_satisfiable` (object plugins) | `assert_ordering_constraint_satisfiable(handler)` | Ordering constraints that can never be satisfied (impossible anchor pair, unknown/cyclic object references) and crash generation. |
| 8 | `test_idempotent_setup` (recommended) | `assert_idempotent_setup(setup)` | Double-loading in reloads/tests/interactive sessions: calling `setup()` twice must not raise or add new registrations. |

Tests 1–5 apply to every plugin. Tests 6–7 apply to object plugins; value-only plugins mark them not applicable and say so. Test 8 is recommended and may become required.

### What the harness allows for test 5

The public API surface is `dbwarden.plugin`, `dbwarden.exceptions`, and `dbwarden.engine.core` (the public object-handler types). Any other import under `dbwarden.<subpackage>` is treated as an internal and fails the check: `dbwarden.engine.*` other than `dbwarden.engine.core`, `dbwarden.database*`, `dbwarden.commands.*`, `dbwarden.repositories.*`, and so on. Official plugins are exempt: they are trusted by provenance, not by this suite, and legitimately extract behavior from core.

## What This Does Not Cover

- **Business logic**: whether the emitted SQL does what the user wants (their own tests).
- **Performance**: no benchmark required.
- **Security audit**: no static analysis for malicious code beyond the import restriction.
- **Inter-plugin interaction**: the resolver's job.

## Submit For Approval

Open an issue in the DBWarden repository using the **Plugin Approval** template with:

```markdown
### Plugin repository
https://github.com/<you>/dbwarden-<name>

### Package name & requested approved version
dbwarden-<name>, minimum 0.2.0

### What it provides
Value hooks: ...
Object handlers: ...

### Checklist evidence
Link to a green CI run of tests/test_conformance.py (all required tests passing).

### Compatibility
Tested against dbwarden>=0.15.0
```

## CI Enforcement

To be Verified, the plugin must run the conformance suite in public CI (GitHub Actions or similar) on every push, with a visible status badge. The template's `.github/workflows/test.yml` does this. The reviewer confirms CI is green and that `tests/test_conformance.py` matches the standard, then does a quick sanity pass for obviously unsafe behavior (malware, core monkey-patching, network exfiltration). On approval, the distribution name and minimum version are added to `dbwarden/_approved.py` and ship in the next DBWarden release.

## Version Re-Approval

The approved minimum is a **floor**: patch and minor releases above it load automatically. A **new major version** (or any release that changes hooks, signatures, or object semantics) must request re-approval, and the floor in `dbwarden/_approved.py` is updated accordingly. Until then, a version below the recorded floor is treated as **Community** and requires consent.
