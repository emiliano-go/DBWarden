---
seo:
  title: '`status` - DBWarden Documentation'
  description: status Show migration status applied vs pending. Usage bash dbwarden
    status database primary dbwarden status all Options database, d all, a Notes run
    before and after migration execution supports...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/status/
  robots: index,follow
  og:
    type: website
    title: '`status` - DBWarden Documentation'
    description: status Show migration status applied vs pending. Usage bash dbwarden
      status database primary dbwarden status all Options database, d all, a Notes
      run before and after migration execution supports...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/status/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: '`status` - DBWarden Documentation'
    description: status Show migration status applied vs pending. Usage bash dbwarden
      status database primary dbwarden status all Options database, d all, a Notes
      run before and after migration execution supports...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: '`status` - DBWarden Documentation'
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/status/
    description: status Show migration status applied vs pending. Usage bash dbwarden
      status database primary dbwarden status all Options database, d all, a Notes
      run before and after migration execution supports...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `status`

Show migration status (applied vs pending).

## Usage

```bash
dbwarden status --database primary
dbwarden status --all
```

## Options

- `--database`, `-d`
- `--all`, `-a`

## Notes

- run before and after migration execution
- supports multi-database status with `--all`

See also: [Checking Status](../tutorial/checking-status.md)
