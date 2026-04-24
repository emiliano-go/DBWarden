# Checksum Integrity

DBWarden stores checksums for executed migrations.

Checksums are used to:

- detect changed migration content
- support repeatable migration behavior (`RA__`, `ROC__`)
- avoid accidental re-application of equivalent SQL

Best practice: do not edit already-applied versioned migration files.

## Navigation

- Previous: [Migration Locking](migration-locking.md)
- Next: [Squashing Migrations](squashing-migrations.md)
