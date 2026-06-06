# FastAPI Integration

DBWarden provides FastAPI integration for database sessions, health checks,
migration management, Prometheus metrics, and distributed migration locking.

One configuration source serves both migrations and runtime.

## Resources

- [FastAPI integration home](index.md) - landing page with overview
- [Tutorial](tutorial/first-steps.md) - step-by-step guides
- [Concepts](concepts.md) - how it works
- [Advanced guides](advanced/multi-database.md) - advanced patterns
- [API Reference](reference.md) - complete function signatures

## Migration guide

| Old page | New location |
|----------|-------------|
| `overview.md` (this page) | [index.md](index.md) |
| `get-session.md` | [tutorial/session-dependency.md](tutorial/session-dependency.md) |
| `migration-context.md` | [tutorial/startup-checks.md](tutorial/startup-checks.md) |
| `health-router.md` | [tutorial/health-endpoints.md](tutorial/health-endpoints.md) |
| `full-example.md` | [tutorial/complete-application.md](tutorial/complete-application.md) |
