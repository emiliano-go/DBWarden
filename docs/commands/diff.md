# `diff`

Show structural diff helpers (models/migrations/database).

## Usage

```bash
dbwarden diff all --database primary
dbwarden diff models --database primary
dbwarden diff migrations --database primary
```

## Arguments and options

- positional `diff_type`: `all`, `models`, or `migrations`
- `--database`, `-d`
- `--verbose`, `-v`

## Notes

- intended for schema comparison workflows
- model path configuration affects model-based diffs

See also: [Configuration](../configuration.md)
