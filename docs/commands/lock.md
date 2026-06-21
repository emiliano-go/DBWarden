---
seo:
  title: lock-status and unlock - DBWarden Documentation
  description: Inspect and recover migration lock state.
  canonical: https://emiliano-go.github.io/DBWarden/commands/lock/
  robots: index,follow
  og:
    type: website
    title: lock-status and unlock - DBWarden Documentation
    description: Inspect and recover migration lock state.
    url: https://emiliano-go.github.io/DBWarden/commands/lock/
    image: https://emiliano-go.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: lock-status and unlock - DBWarden Documentation
    description: Inspect and recover migration lock state.
    image: https://emiliano-go.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: lock-status and unlock - DBWarden Documentation
    url: https://emiliano-go.github.io/DBWarden/commands/lock/
    description: Inspect and recover migration lock state.
    image: https://emiliano-go.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `lock-status` and `unlock`

Inspect and recover migration lock state.

## Usage

```bash
$ dbwarden lock-status --database primary
$ dbwarden unlock --database primary
```

## Options

- `--database`, `-d`

## Notes

- use `lock-status` to inspect lock state
- use `unlock` only when lock is stale and no migration is running

See also: [Migration Locking](../advanced/migration-locking.md)
