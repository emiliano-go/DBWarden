---
seo:
  title: Event Triggers - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers
  robots: index,follow
  og:
    type: website
    title: Event Triggers - DBWarden Documentation
    description: 'Handler: EventTriggerHandler PREAMBLE phase, config-driven'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Event Triggers - DBWarden Documentation
    description: 'Handler: EventTriggerHandler PREAMBLE phase, config-driven'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Handler: EventTriggerHandler PREAMBLE phase, config-driven'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Event Triggers - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers
    description: 'Handler: EventTriggerHandler PREAMBLE phase, config-driven'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
      logo: https://dbwarden.emiliano-go.com/assets/images/og-image.png
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Databases
      item: https://dbwarden.emiliano-go.com/databases
    - '@type': ListItem
      position: 2
      name: PostgreSQL
      item: https://dbwarden.emiliano-go.com/databases/postgresql
    - '@type': ListItem
      position: 3
      name: Event Triggers
      item: https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers
seo_html: "<title>Event Triggers - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Handler: EventTriggerHandler PREAMBLE phase, config-driven\">\n<link\
  \ rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Event Triggers - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Handler: EventTriggerHandler PREAMBLE\
  \ phase, config-driven\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Event Triggers - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Handler: EventTriggerHandler PREAMBLE\
  \ phase, config-driven\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Event Triggers - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers\"\
  ,\n    \"description\": \"Handler: EventTriggerHandler PREAMBLE phase, config-driven\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Event Triggers\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/event-triggers\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Event Triggers

**Handler**: `EventTriggerHandler` (PREAMBLE phase, config-driven)

Event triggers fire on database-level DDL events. They are scoped to the entire database cluster (not per-schema).

```python
pg_event_triggers=[
    {
        "name": "trg_ddl_audit",
        "event": "ddl_command_start",
        "function": "audit_ddl",
        "tags": ["CREATE TABLE", "ALTER TABLE"],
    },
]
```

## Events

| Event | Fires On |
|-------|----------|
| `ddl_command_start` | Before any DDL statement |
| `ddl_command_end` | After any DDL statement |
| `sql_drop` | When objects are dropped |
| `table_rewrite` | When `ALTER TABLE` rewrites a table |

## DDL Command Tags

Available tags for `WHEN TAG IN` filtering (selected common tags):

| Tag Category | Tags |
|--------------|------|
| DDL | `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `CREATE INDEX`, `ALTER INDEX`, `DROP INDEX` |
| Schema | `CREATE SCHEMA`, `ALTER SCHEMA`, `DROP SCHEMA` |
| Type | `CREATE TYPE`, `ALTER TYPE`, `DROP TYPE` |
| Function | `CREATE FUNCTION`, `ALTER FUNCTION`, `DROP FUNCTION` |
| Trigger | `CREATE TRIGGER`, `ALTER TRIGGER`, `DROP TRIGGER` |
| View | `CREATE VIEW`, `ALTER VIEW`, `DROP VIEW` |
| Sequence | `CREATE SEQUENCE`, `ALTER SEQUENCE`, `DROP SEQUENCE` |
| Extension | `CREATE EXTENSION`, `ALTER EXTENSION`, `DROP EXTENSION` |

The full list of supported tags is available in the PostgreSQL documentation under "Server Event Trigger Command Tags".

## Function Context Variables

Event trigger functions access DDL context through special session variables:

| Variable | Type | Description |
|----------|------|-------------|
| `TG_EVENT` | `text` | Event name: `ddl_command_start`, `ddl_command_end`, `sql_drop`, `table_rewrite` |
| `TG_TAG` | `text` | Command tag: `CREATE TABLE`, `ALTER TABLE`, etc. |
| `TG_TABLE_SCHEMA` | `text` | Schema of the target object (when applicable) |
| `TG_TABLE_NAME` | `text` | Name of the target object (when applicable) |

Example function using context variables:

```sql
CREATE FUNCTION audit_ddl()
RETURNS event_trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO ddl_audit_log (event, tag, schema, object, occurred_at)
    VALUES (TG_EVENT, TG_TAG, TG_TABLE_SCHEMA, TG_TABLE_NAME, NOW());
END;
$$;
```

## Function Signature Requirements

Event trigger functions must:
- Take **no arguments**
- Return type `event_trigger`
- Be created before the event trigger that references them

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE EVENT TRIGGER name ON event WHEN TAG IN ('tag1', 'tag2') EXECUTE FUNCTION func();` |
| Alter | `ALTER EVENT TRIGGER name DISABLE;` / `ALTER EVENT TRIGGER name ENABLE;` / `ALTER EVENT TRIGGER name RENAME TO new_name;` |
| Drop | `DROP EVENT TRIGGER IF EXISTS name;` |

## Enabled State

| Value | Meaning |
|-------|---------|
| `O` | Enabled (default) |
| `D` | Disabled |
| `R` | Enabled in replica mode |
| `A` | Always enabled |

## Notes

- Event triggers require a superuser to create
- The backing function must be created first (see [Functions & Triggers](functions-and-triggers.md))
- `DROP EVENT TRIGGER` does not auto-drop the backing function
- Tags filter which DDL commands fire the trigger; absent tags means all DDL commands
- If an event trigger function raises an exception, the DDL command is aborted and rolled back
- Use `sql_drop` with care: objects have already been removed from catalogs, so `TG_TABLE_SCHEMA` and `TG_TABLE_NAME` may be NULL for dropped objects; use `pg_event_trigger_dropped_objects()` to get the list
