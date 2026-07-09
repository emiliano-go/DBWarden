# Logging Audit

## Source of Truth Summary

`dbwarden/logging.py` is the central logging facade. It wraps stdlib `logging`, keeps normal severity semantics (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`), and adds a second `Verbosity` axis intended only for user-facing `INFO` variants. `debug_enabled=True` raises the underlying logger level to `DEBUG`; otherwise it stays at `INFO` ([dbwarden/logging.py:306-321](/home/ahmet/DBWarden/dbwarden/logging.py:306), [dbwarden/logging.py:648-684](/home/ahmet/DBWarden/dbwarden/logging.py:648)).

The facade is a mutable singleton returned by `get_logger()`. Later calls can overwrite shared `debug_enabled`, `verbosity`, `db_name`, and `db_type` state on that singleton ([dbwarden/logging.py:676-683](/home/ahmet/DBWarden/dbwarden/logging.py:676)). Plain-text output goes to stdout with ANSI coloring when `sys.stdout.isatty()` is true; JSON output is selected only at logger construction time when `DBWARDEN_LOG_JSON` is truthy ([dbwarden/logging.py:74-83](/home/ahmet/DBWarden/dbwarden/logging.py:74), [dbwarden/logging.py:210-243](/home/ahmet/DBWarden/dbwarden/logging.py:210)).

The current implementation only partially realizes the intended verbosity model. `_log_best_candidate()` can choose between `DEBUG` and `INFO` candidates gated by `Verbosity`, but all existing helper-backed `INFO` messages are tagged `Verbosity.NORMAL`, and many command paths still use plain `logger.info(...)` directly ([dbwarden/logging.py:371-415](/home/ahmet/DBWarden/dbwarden/logging.py:371), [dbwarden/logging.py:417-641](/home/ahmet/DBWarden/dbwarden/logging.py:417)).

## High-Priority Issues

### [High] Query tracing docs describe structured per-query logs, but the implementation emits lossy per-request summaries

- **Category:** `outdated-doc`
- **Locations:**
  - [dbwarden/fastapi/observability.py:9-18](/home/ahmet/DBWarden/dbwarden/fastapi/observability.py:9)
  - [dbwarden/fastapi/observability.py:50-62](/home/ahmet/DBWarden/dbwarden/fastapi/observability.py:50)
  - [dbwarden/logging.py:216-235](/home/ahmet/DBWarden/dbwarden/logging.py:216)
  - [docs/fastapi/reference.md:681-693](/home/ahmet/DBWarden/docs/fastapi/reference.md:681)
  - [docs/cookbook/11-observability.md:121-125](/home/ahmet/DBWarden/docs/cookbook/11-observability.md:121)
  - [docs/cookbook/11-observability.md:206-207](/home/ahmet/DBWarden/docs/cookbook/11-observability.md:206)
  - [examples/observability/README.md:39-43](/home/ahmet/DBWarden/examples/observability/README.md:39)
- **Current behavior:** `QueryTracingMiddleware` logs one summary message per request via the child logger `dbwarden.tracing`. It attaches request/query metrics through `extra`, but `JSONFormatter` serializes only `timestamp`, `level`, `logger`, `message`, `db_name`, `db_type`, and `exception`.
- **Why this may be stale or risky:** The docs currently promise "every SQL query with duration" and list fields like `path`, `query_count`, and `slow_queries`. In practice, the middleware does not log each query, and the default JSON formatter drops those extra fields entirely.
- **Suggested fix:** Either extend `JSONFormatter` to include arbitrary safe extras and revise middleware docs to describe per-request summaries, or change the middleware to emit the per-query events the docs currently describe.

### [High] Query tracing counters are captured by value, so logged counts/timings can remain zero

- **Category:** `edge-case`
- **Locations:**
  - [dbwarden/fastapi/observability.py:39-44](/home/ahmet/DBWarden/dbwarden/fastapi/observability.py:39)
  - [dbwarden/fastapi/observability.py:124-145](/home/ahmet/DBWarden/dbwarden/fastapi/observability.py:124)
  - [tests/test_fastapi_lifespan.py:6-29](/home/ahmet/DBWarden/tests/test_fastapi_lifespan.py:6)
- **Current behavior:** `__call__()` passes primitive counters into `_patch_engine_for_tracing(qc, tqt, sqt, sq, ...)`. The wrapper mutates `_patch_engine_for_tracing`'s local variables, not the `__call__()` locals used for the final log payload.
- **Why this may be stale or risky:** The log record can claim zero queries and zero query time even after database work occurred. Existing tests only assert that the middleware can be mounted and does not inspect the emitted log payload.
- **Suggested fix:** Store mutable state in a dict/object/closure owned by `__call__()`, and add log-payload tests that assert non-zero counters after a request that performs queries.

### [High] The mutable singleton can cross-contaminate log context in concurrent or nested workflows

- **Category:** `edge-case`
- **Locations:**
  - [dbwarden/logging.py:648-684](/home/ahmet/DBWarden/dbwarden/logging.py:648)
  - [dbwarden/database/connection.py:160-163](/home/ahmet/DBWarden/dbwarden/database/connection.py:160)
  - [dbwarden/fastapi/context.py:53](/home/ahmet/DBWarden/dbwarden/fastapi/context.py:53)
  - [dbwarden/fastapi/context.py:84](/home/ahmet/DBWarden/dbwarden/fastapi/context.py:84)
  - [dbwarden/fastapi/context.py:131](/home/ahmet/DBWarden/dbwarden/fastapi/context.py:131)
- **Current behavior:** `get_logger()` returns one shared `DBWardenLogger` and mutates its `db_name`, `db_type`, `verbosity`, and `debug_enabled` on subsequent calls. `get_db_connection()` mutates that shared logger every time a connection is opened.
- **Why this may be stale or risky:** In CLI flows this is mostly sequential, but in FastAPI or other embedded multi-database usage, one request/workflow can overwrite another's logging context mid-flight. That can mislabel database prefixes and unpredictably alter verbosity/debug state.
- **Suggested fix:** Needs maintainer decision. Either make the facade explicitly CLI-only, or stop mutating shared contextual state globally and instead use per-call `extra`, child loggers, or `contextvars`.

## Medium-Priority Issues

### [Medium] `Verbosity` is defined, but there is no real project-level path to configure or exercise it

- **Category:** `design-gap`
- **Locations:**
  - [dbwarden/logging.py:15](/home/ahmet/DBWarden/dbwarden/logging.py:15)
  - [dbwarden/logging.py:648-684](/home/ahmet/DBWarden/dbwarden/logging.py:648)
  - [dbwarden/cli/main.py:39](/home/ahmet/DBWarden/dbwarden/cli/main.py:39)
  - [tests/test_config.py:628-693](/home/ahmet/DBWarden/tests/test_config.py:628)
- **Current behavior:** `Verbosity` exists in the facade, but no CLI option, env var, config loader, or command entry point passes a non-default `verbosity`. `debug_enabled` is also never passed outside tests.
- **Why this may be stale or risky:** The source comment says verbosity may be configured from constructor arguments, config files, env vars, or CLI options, but only direct Python callers can currently do that, and the normal CLI cannot reach `QUIET`, `VERBOSE`, or debug-only helper output.
- **Suggested fix:** Add a real configuration surface for `verbosity` and `debug_enabled`, or reduce the docs/comments to match the current callable-only reality.

### [Medium] `QUIET` and `VERBOSE` do not behave like the module docstring says

- **Category:** `design-gap`
- **Locations:**
  - [dbwarden/logging.py:8-15](/home/ahmet/DBWarden/dbwarden/logging.py:8)
  - [dbwarden/logging.py:396-415](/home/ahmet/DBWarden/dbwarden/logging.py:396)
  - [dbwarden/logging.py:417-641](/home/ahmet/DBWarden/dbwarden/logging.py:417)
- **Current behavior:** All helper-backed `INFO` candidates are tagged `Verbosity.NORMAL`. At `QUIET`, helper-based `INFO` logs disappear entirely. At `VERBOSE`, helper output is usually identical to `NORMAL`. Direct `logger.info(...)` calls bypass verbosity gating altogether.
- **Why this may be stale or risky:** The top-level documentation says `QUIET` should still emit essential `INFO` output and `VERBOSE` should emit additional informational detail. The current behavior is closer to "suppress all helper INFO" for `QUIET` and "same as NORMAL" for `VERBOSE`.
- **Suggested fix:** Add actual `QUIET` and `VERBOSE` variants for helper-backed messages, and minimize direct `logger.info(...)` calls for user-facing progress.

### [Medium] The old `verbose` flag is still passed everywhere and documented as meaningful, but `get_logger(verbose=...)` ignores it

- **Category:** `stale-call-site`
- **Locations:**
  - [dbwarden/logging.py:275-293](/home/ahmet/DBWarden/dbwarden/logging.py:275)
  - [dbwarden/logging.py:668-674](/home/ahmet/DBWarden/dbwarden/logging.py:668)
  - [dbwarden/commands/migrate.py:180-182](/home/ahmet/DBWarden/dbwarden/commands/migrate.py:180)
  - [dbwarden/commands/rollback.py:36-38](/home/ahmet/DBWarden/dbwarden/commands/rollback.py:36)
  - [dbwarden/commands/downgrade.py:27-29](/home/ahmet/DBWarden/dbwarden/commands/downgrade.py:27)
  - [dbwarden/commands/seeds.py:32](/home/ahmet/DBWarden/dbwarden/commands/seeds.py:32)
  - [dbwarden/fastapi/context.py:53](/home/ahmet/DBWarden/dbwarden/fastapi/context.py:53)
- **Current behavior:** Many workflows still call `get_logger(verbose=verbose, ...)`, but `get_logger()` never forwards `verbose` into `DBWardenLogger(...)`, and nothing in the facade consults `self.verbose`.
- **Why this may be stale or risky:** Callers and docs still imply that `--verbose` materially changes logger output, but the argument is effectively ignored by the central facade.
- **Suggested fix:** Either wire `verbose` into a defined behavior, or stop advertising it as a logging control and migrate callers/docs to `verbosity`.

### [Medium] Rollback and downgrade paths still bypass the structured helper API

- **Category:** `stale-call-site`
- **Locations:**
  - [dbwarden/commands/rollback.py:89-100](/home/ahmet/DBWarden/dbwarden/commands/rollback.py:89)
  - [dbwarden/commands/downgrade.py:83-101](/home/ahmet/DBWarden/dbwarden/commands/downgrade.py:83)
- **Current behavior:** These workflows use plain `logger.info(...)` strings for start/end/skip messages instead of the helper-backed rollback methods already defined in the facade.
- **Why this may be stale or risky:** These messages are not verbosity-aware, do not match the styled helper output used by `migrate`, and increase the direct-API surface that already mismatches stdlib semantics.
- **Suggested fix:** Reuse `log_rollback_start()` / `log_rollback_end()` where possible, or add explicit downgrade helpers backed by `_log_best_candidate()`.

### [Medium] Several entry points know the database context but initialize the logger without it

- **Category:** `stale-call-site`
- **Locations:**
  - [dbwarden/commands/make_migrations.py:461-489](/home/ahmet/DBWarden/dbwarden/commands/make_migrations.py:461)
  - [dbwarden/commands/status.py:15-18](/home/ahmet/DBWarden/dbwarden/commands/status.py:15)
  - [dbwarden/commands/history.py:11-13](/home/ahmet/DBWarden/dbwarden/commands/history.py:11)
  - [dbwarden/commands/seeds.py:32-35](/home/ahmet/DBWarden/dbwarden/commands/seeds.py:32)
- **Current behavior:** These commands create or use a logger before resolving `db_name`/`db_type`, or never attach the context at all.
- **Why this may be stale or risky:** Helper prefixes and JSON `db_name`/`db_type` fields are unavailable or incomplete even when the command already knows which database it is operating on.
- **Suggested fix:** Resolve database context first, then initialize the logger with `db_name` and `db_type`.

### [Medium] `seed apply` reuses `-v` for both `--version` and `--verbose`

- **File:** [dbwarden/cli/main.py](/home/ahmet/DBWarden/dbwarden/cli/main.py:540)
- **Line(s):** `540-552`
- **Category:** `stale-call-site`
- **Current behavior:** `seed apply` binds `-v` to `--version` and again to `--verbose`.
- **Why this may be stale or risky:** The command-line surface is ambiguous and the verbose flag is not reliably usable on this subcommand.
- **Suggested fix:** Move one of the short options, preferably keeping `--verbose` on `-v` and dropping the short alias from `--version`.

### [Medium] JSON formatter drops database context for most helper-based messages

- **Category:** `design-gap`
- **Locations:**
  - [dbwarden/logging.py:216-235](/home/ahmet/DBWarden/dbwarden/logging.py:216)
  - [dbwarden/logging.py:357-369](/home/ahmet/DBWarden/dbwarden/logging.py:357)
  - [dbwarden/logging.py:371-415](/home/ahmet/DBWarden/dbwarden/logging.py:371)
- **Current behavior:** The helper path prefixes `db_name`/`db_type` into the message string via `_prefixed()`, then logs plain text. The JSON formatter only emits structured `db_name`/`db_type` when those fields are present on the `LogRecord`.
- **Why this may be stale or risky:** Human-readable output contains the context, but JSON output often does not. Docs that imply structured database fields "when applicable" are overstating current behavior.
- **Suggested fix:** Attach `db_name` and `db_type` as structured fields on helper emissions in addition to or instead of prefixing them into the message text.

### [Medium] Toggling `DBWARDEN_LOG_JSON` after logger creation has no effect

- **Category:** `edge-case`
- **Locations:**
  - [dbwarden/logging.py:306-321](/home/ahmet/DBWarden/dbwarden/logging.py:306)
  - [dbwarden/logging.py:667-684](/home/ahmet/DBWarden/dbwarden/logging.py:667)
  - [tests/test_observability.py:339-357](/home/ahmet/DBWarden/tests/test_observability.py:339)
- **Current behavior:** Formatter selection happens only inside `_setup_logger()` during construction. Later `get_logger()` calls update state on the singleton but do not rebuild handlers/formatters.
- **Why this may be stale or risky:** Embedded users or tests that change `DBWARDEN_LOG_JSON` after the first logger initialization will keep the old formatter unexpectedly.
- **Suggested fix:** Document that formatter mode is fixed after first logger creation, or re-run handler setup when JSON mode changes.

## Low-Priority / Cleanup Issues

### [Low] Several logger-related imports or variables are now unused

- **Category:** `stale-call-site`
- **Locations:**
  - [dbwarden/commands/export_seeds.py:15](/home/ahmet/DBWarden/dbwarden/commands/export_seeds.py:15)
  - [dbwarden/commands/generate_models.py:10](/home/ahmet/DBWarden/dbwarden/commands/generate_models.py:10)
  - [dbwarden/cli/main.py:34](/home/ahmet/DBWarden/dbwarden/cli/main.py:34)
  - [dbwarden/commands/check_db.py:20](/home/ahmet/DBWarden/dbwarden/commands/check_db.py:20)
- **Current behavior:** `get_logger` is imported but unused in several files, and `check_db_cmd()` creates a logger variable that is never used.
- **Why this may be stale or risky:** This is mostly cleanup, but it makes it harder to see which workflows actually participate in the central logging facade.
- **Suggested fix:** Remove unused imports/variables or start using the facade meaningfully in those paths.

### [Low] Logging tests are mostly smoke tests and do not assert emitted behavior

- **Category:** `test-gap`
- **Locations:**
  - [tests/test_config.py:645-680](/home/ahmet/DBWarden/tests/test_config.py:645)
- **Current behavior:** Many logger tests merely call methods and assert that no exception was raised.
- **Why this may be stale or risky:** Breaking changes in message selection, verbosity gating, JSON structure, or helper context can slip through while the tests still pass.
- **Suggested fix:** Replace smoke tests with assertions on captured output or `LogRecord` contents.

## Edge Cases Reviewed

- Reviewed stdlib compatibility of facade methods. Found real incompatibilities with `exception()`, positional formatting args, and `exc_info`.
- Reviewed JSON formatter activation. It works at construction time, but changing `DBWARDEN_LOG_JSON` later does not rebuild handlers.
- Reviewed ANSI path. `supports_color()` cleanly disables ANSI output when stdout is not a TTY; no direct issue found there.
- Reviewed duplicate-handler risk. `_setup_logger()` removes existing handlers before adding a new one, so repeated construction does not accumulate duplicates.
- Reviewed direct child stdlib loggers such as `dbwarden.lock`, `dbwarden.snapshot`, and `dbwarden.tracing`. They are not automatically wrong, but they rely on the `dbwarden` parent logger/formatter and can diverge from facade semantics.
- Reviewed FastAPI query tracing. Found documentation mismatches, dropped extra fields, and likely-zero counters.
- Reviewed singleton mutation across CLI and FastAPI paths. Sequential CLI use is mostly fine; concurrent server/library use is risky.

## Outdated Docs / Comments / Examples

### [High] CLI help and command docs still describe `--verbose` as if it meaningfully increases logging detail

- **Category:** `outdated-doc`
- **Locations:**
  - [dbwarden/cli/main.py:37-39](/home/ahmet/DBWarden/dbwarden/cli/main.py:37)
  - [docs/cli-reference.md:71-83](/home/ahmet/DBWarden/docs/cli-reference.md:71)
  - [docs/commands/make-migrations.md:45-65](/home/ahmet/DBWarden/docs/commands/make-migrations.md:45)
  - [docs/commands/migrate.md:52-58](/home/ahmet/DBWarden/docs/commands/migrate.md:52)
  - [docs/commands/rollback.md:45-48](/home/ahmet/DBWarden/docs/commands/rollback.md:45)
  - [docs/commands/downgrade.md:43-45](/home/ahmet/DBWarden/docs/commands/downgrade.md:43)
  - [docs/commands/diff.md:49-52](/home/ahmet/DBWarden/docs/commands/diff.md:49)
  - [docs/commands/seed.md:58-60](/home/ahmet/DBWarden/docs/commands/seed.md:58)
  - [docs/commands/seed.md:79-83](/home/ahmet/DBWarden/docs/commands/seed.md:79)
  - [docs/commands/seed.md:101-104](/home/ahmet/DBWarden/docs/commands/seed.md:101)
  - [docs/commands/seed.md:122-126](/home/ahmet/DBWarden/docs/commands/seed.md:122)
  - [docs/fastapi/reference.md:150-152](/home/ahmet/DBWarden/docs/fastapi/reference.md:150)
  - [docs/fastapi/reference.md:760](/home/ahmet/DBWarden/docs/fastapi/reference.md:760)
- **Current behavior:** The docs repeatedly describe `--verbose` as "verbose output", "detailed logging", or "verbose migration output".
- **Why this may be stale or risky:** The current central facade does not use the old `verbose` argument to materially change output density.
- **Suggested fix:** Rewrite these docs to describe the current compatibility-only status of `verbose`, or implement the intended behavior before keeping the wording.

### [Medium] `logging.py` module docs overstate current configurability of `Verbosity`

- **File:** [dbwarden/logging.py](/home/ahmet/DBWarden/dbwarden/logging.py:15)
- **Line(s):** `15`
- **Category:** `outdated-doc`
- **Current behavior:** The module docstring says verbosity may be configured from constructor args, config files, env vars, or CLI options.
- **Why this may be stale or risky:** Only direct constructor / `get_logger(..., verbosity=...)` callers can do that today.
- **Suggested fix:** Narrow the comment to the current reality or wire the missing config surfaces.

### [Medium] Troubleshooting docs show an invalid global `--verbose` invocation

- **File:** [docs/configuration/troubleshooting.md](/home/ahmet/DBWarden/docs/configuration/troubleshooting.md:581)
- **Line(s):** `581-584`
- **Category:** `outdated-doc`
- **Current behavior:** The docs suggest `dbwarden --verbose migrate`.
- **Why this may be stale or risky:** `--verbose` is defined on individual commands, not as a global app callback option.
- **Suggested fix:** Change the example to `dbwarden migrate --verbose`.

### [Medium] Observability docs show JSON event shapes the current formatter does not emit

- **Category:** `outdated-doc`
- **Locations:**
  - [docs/observability.md:124-141](/home/ahmet/DBWarden/docs/observability.md:124)
  - [docs/cookbook/11-observability.md:105-109](/home/ahmet/DBWarden/docs/cookbook/11-observability.md:105)
- **Current behavior:** The docs show JSON examples with structured event fields such as `event`, `database`, `duration_ms`, `version`, and reliably present `db_name` / `db_type`.
- **Why this may be stale or risky:** The default formatter only serializes a small fixed field set, and helper-based DB context usually stays embedded inside the message string.
- **Suggested fix:** Update the examples to match the actual schema, or extend the formatter to include arbitrary structured extras and helper context.

## Test Coverage Gaps

- No tests cover stdlib-compatible facade behavior for `logger.exception(...)`, positional formatting args, or `exc_info`.
- No tests assert `QUIET`, `NORMAL`, and `VERBOSE` message selection behavior.
- No tests verify that direct `logger.info(...)` calls bypass verbosity while helper-backed `INFO` calls are gated.
- No tests assert JSON timestamp format, so the literal `%f` bug is currently invisible.
- No tests cover formatter behavior when `DBWARDEN_LOG_JSON` changes after singleton initialization.
- No tests cover singleton context mutation across multiple `get_logger()` calls with different `db_name` / `db_type`.
- No tests verify that FastAPI query tracing logs include the documented fields, correct severity, or non-zero counters.
- No tests exercise the broken `seed apply` `-v` option collision.

## Recommended Follow-Up Work

1. Fix the facade API mismatch first: add stdlib-compatible method signatures, support `exception()`, and repair `exc_info` / `%s` formatting behavior.
2. Fix JSON formatting correctness: render timestamps correctly and decide whether arbitrary `extra` fields should be serialized.
3. Decide whether the singleton logger is CLI-only or must be safe for embedded/concurrent FastAPI usage; then align implementation with that decision.
4. Wire a real configuration path for `verbosity` and `debug_enabled`, or scale back docs/comments that currently promise those controls.
5. Standardize stale command call sites, starting with rollback/downgrade and other paths that know database context but skip helper-backed logging.
6. Correct user-facing docs/examples: `--verbose` semantics, JSON log schema, query tracing behavior, and the invalid `dbwarden --verbose migrate` example.
7. Add focused tests for the logging contract instead of smoke tests: facade compatibility, verbosity behavior, JSON mode, singleton mutation, and tracing payloads.
