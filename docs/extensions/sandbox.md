---
seo:
  title: Sandbox - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/extensions/sandbox
  robots: index,follow
  og:
    type: website
    title: Sandbox - DBWarden Documentation
    description: DBWarden provides two sandbox mechanisms that protect your production
      data from unintended changes.
    url: https://dbwarden.emiliano-go.com/extensions/sandbox
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Sandbox - DBWarden Documentation
    description: DBWarden provides two sandbox mechanisms that protect your production
      data from unintended changes.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: DBWarden provides two sandbox mechanisms that protect your production
    data from unintended changes.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Sandbox - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/extensions/sandbox
    description: DBWarden provides two sandbox mechanisms that protect your production
      data from unintended changes.
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
      name: Extensions
      item: https://dbwarden.emiliano-go.com/extensions
    - '@type': ListItem
      position: 2
      name: Sandbox
      item: https://dbwarden.emiliano-go.com/extensions/sandbox
seo_html: "<title>Sandbox - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"DBWarden provides two sandbox mechanisms that protect your production\
  \ data from unintended changes.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/extensions/sandbox\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Sandbox - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"DBWarden provides two sandbox mechanisms\
  \ that protect your production data from unintended changes.\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/extensions/sandbox\">\n<meta\
  \ property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Sandbox - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"DBWarden provides two sandbox mechanisms\
  \ that protect your production data from unintended changes.\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Sandbox - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/extensions/sandbox\"\
  ,\n    \"description\": \"DBWarden provides two sandbox mechanisms that protect\
  \ your production data from unintended changes.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Extensions\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/extensions\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"Sandbox\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/extensions/sandbox\"\n \
  \     }\n    ]\n  }\n]\n</script>\n"
---

# Sandbox

DBWarden provides two sandbox mechanisms that protect your production data from unintended changes.

## Migration Sandbox

The `--sandbox` flag applies pending migrations to a temporary database and reports results without touching the real target.

```bash
dbwarden migrate --sandbox --database primary
```

When you run with `--sandbox`, DBWarden creates a fresh sandbox instance (SQLite by default, or a Docker-backed database when the `[sandbox]` extra is installed), applies all pending migrations, and reports success or failure. The sandbox is then torn down. Nothing touches the production database.

### Use Cases

**Validating generated SQL before real deployment.** After running `make-migrations`, validate the SQL against a temporary database to catch syntax errors, missing columns, or type mismatches.

```bash
dbwarden make-migrations "add reporting table"
dbwarden migrate --sandbox --database primary
```

**CI gates.** Run the sandbox check in pull request pipelines to ensure every migration compiles and applies cleanly.

```yaml
sandbox-check:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - run: uv add "dbwarden[sandbox]"
    - name: Apply migrations to sandbox
      run: dbwarden migrate --sandbox --database primary
```

The sandbox starts a fresh database, applies all pending migrations, reports results, and tears down. It never touches the real database.

**Combined with dry-run.** Chain `--dry-run` (preview SQL without any database access) before `--sandbox` for a two-phase validation.

```bash
dbwarden migrate --dry-run --database primary
dbwarden migrate --sandbox --database primary
```

### Behavior

- Sandbox migrations follow the same migration ordering and dependency resolution as real migrations.
- Schema snapshots and model state are not written during sandbox runs, preventing the temporary database schema from overwriting the production snapshot.
- The sandbox backend defaults to SQLite when the `[sandbox]` extra is not installed.
- With `uv add "dbwarden[sandbox]"`, the sandbox can spin up Docker containers matching your production database type.

## Config Security Sandbox

DBWarden applies import restrictions to config files loaded from isolated locations. This prevents accidental escalation of file-read access to arbitrary code execution.

### How It Works

Config files are loaded in one of two modes:

| Mode | Import behavior | Applies to |
|------|----------------|------------|
| Isolated | Sandboxed: only `dbwarden.*` imports allowed | Top-level `dbwarden.py`; any full-scan-discovered file at the project root |
| In-package | Normal Python import | Full-scan-discovered files inside subdirectories; `DBWARDEN_CONFIG_MODULE` modules |

An isolated config file runs in a sandbox where only `dbwarden` and its submodules can be imported. An in-package config file is imported as a normal Python module, with full access to project-level imports.

### Path Validation

Path traversal blocking applies to all file-based sources regardless of mode. DBWarden validates that config file paths stay within the project root.

### Debugging

To disable the sandbox for isolated files during development:

```bash
DBWARDEN_DISABLE_SANDBOX=1 dbwarden status
```

Disabling the sandbox removes import restrictions for isolated config files. Keep it enabled in production.
