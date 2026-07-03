"""Pre-build script: generates SEO frontmatter for all docs pages via seoslug.

Run before `zensical build` to inject per-page SEO metadata (title,
description, canonical, Open Graph, Twitter Cards, JSON-LD) into each
Markdown file's YAML frontmatter.

Idempotent: skips writing if the computed payload matches what's already
in the file, so CI diffs stay clean.
"""

import os
import re
import sys
from pathlib import Path

import yaml
from seoslug import (
    SEOConfig,
    URLPolicy,
    SEOEntity,
    Breadcrumb,
    OGImage,
    Robots,
    build_seo_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SITE_URL = "https://dbwarden.emiliano-go.com"
SITE_NAME = "DBWarden Documentation"

SEO_CONFIG = SEOConfig(
    canonical_host="dbwarden.emiliano-go.com",
    public_base_url=SITE_URL,
    url_policy=URLPolicy(
        enforce_https=True,
        lowercase_paths=True,
        trailing_slash="never",
    ),
    site_name=SITE_NAME,
    default_og_image=OGImage(
        url=f"{SITE_URL}/assets/images/og-image.png",
        width=1376,
        height=768,
        alt="DBWarden documentation",
    ),
    publisher_name="Emiliano Gandini Outeda",
    publisher_logo=f"{SITE_URL}/assets/images/og-image.png",
    locale="en_US",
    twitter_site="@emiliano_go_",
    title_template="{title} - DBWarden Documentation",
    default_robots=Robots(index=True, follow=True),
    emit_warnings=True,
)

FM_RE = re.compile(
    r"^-{3}[ \r\t]*?\n(.*?\r?\n)(?:\.{3}|-{3})[ \r\t]*\n",
    re.UNICODE | re.DOTALL,
)


def route_path_from_file(filepath: Path) -> str:
    rel = filepath.relative_to(DOCS_DIR)
    parts = list(rel.parts)
    if parts[-1] == "index.md":
        parts.pop()
        if not parts:
            return "/"
        return "/" + "/".join(parts) + "/"
    stem = Path(*parts).with_suffix("")
    return "/" + str(stem) + "/"


def first_heading(text: str) -> str | None:
    match = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    if not match:
        return None
    title = match.group(1).strip()
    title = re.sub(r"[`*_]", "", title)
    return title


def extract_excerpt(body: str, max_chars: int = 160) -> str:
    body = re.sub(r"^#\s+.*\n?", "", body, count=1).strip()
    para = re.split(r"\n\s*\n", body, maxsplit=1)[0].strip()
    clean = re.sub(r"[`*_\[\]()>|#{}]", "", para)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return ""
    if len(clean) <= max_chars:
        return clean
    break_at = clean.rfind(" ", 0, max_chars)
    return clean[:break_at] + "..." if break_at > 0 else clean[:max_chars] + "..."


def read_meta_and_body(filepath: Path) -> tuple[dict, str]:
    text = filepath.read_text(encoding="utf-8")
    meta: dict = {}
    body = text
    if text.startswith("---"):
        match = FM_RE.match(text)
        if match:
            try:
                parsed = yaml.load(match.group(1), yaml.SafeLoader)
                if isinstance(parsed, dict):
                    meta = parsed
            except Exception:
                pass
            body = text[match.end():].lstrip("\n")
    return meta, body


def build_breadcrumbs(route_path: str) -> list[Breadcrumb] | None:
    parts = [p for p in route_path.strip("/").split("/") if p]
    if not parts:
        return None

    crumbs = []
    acc = ""

    label_map = {
        "getting-started": "Get Started",
        "first-migration": "Your First Migration",
        "first-steps": "First Steps",
        "developing-locally": "Developing Locally",
        "cookbook": "Cookbook & Examples",
        "configuration": "Configuration",
        "quick-start": "Quick Start",
        "connection-urls": "Connection URLs",
        "model-discovery": "Model Discovery",
        "multi-database": "Multi-Database",
        "dev-mode": "Dev Mode",
        "credentials": "Credentials and Secrets",
        "production-patterns": "Production Patterns",
        "troubleshooting": "Troubleshooting",
        "migration-files": "Migration File Format",
        "models": "SQLAlchemy Models Reference",
        "seeds": "Seed Management",
        "sql-translation": "SQL Translation",
        "observability": "Observability",
        "architecture-deep-dive": "Architecture",
        "databases": "Databases",
        "round-trip": "Round Trip Support",
        "sql-databases": "SQL Databases",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL & MariaDB",
        "clickhouse": "ClickHouse",
        "fastapi": "FastAPI Integration",
        "concepts": "Concepts",
        "tutorial": "Tutorial",
        "session-dependency": "Session Dependency",
        "startup-checks": "Startup Checks",
        "health-endpoints": "Health Endpoints",
        "complete-application": "Complete Application",
        "advanced": "Advanced",
        "engine-lifecycle": "Engine Lifecycle",
        "transaction-management": "Transaction Management",
        "testing": "Testing",
        "cli-reference": "CLI Reference",
        "commands": "Commands",
        "init": "init",
        "make-migrations": "make-migrations",
        "migrate": "migrate",
        "downgrade": "downgrade",
        "rollback": "rollback",
        "make-rollback": "make-rollback",
        "generate-models": "generate-models",
        "snapshot": "snapshot",
        "schema-snapshots": "Schema Snapshots",
        "status": "status",
        "check": "check",
        "check-db": "check-db",
        "diff": "diff",
        "history": "history",
        "new": "new",
        "lock": "lock-status/unlock",
        "seed": "seed",
        "settings": "settings",
        "database": "database",
        "version": "version",
        "migration-locking": "Migration Locking",
        "checksum-integrity": "Checksum Integrity",
        "safe-deployment": "Safe Deployment",
        "ci-cd-patterns": "CI/CD Patterns",
        "reference": "Reference",
        "configuration-api": "Configuration API Reference",
        "migrate-from-toml": "Migrate from TOML",
        "codebase": "Codebase Organization",
        "installation": "Installation",
        "features": "Features",
        "setup": "Setup",
        "modeling": "Modeling Guide",
        "workflows": "Workflows",
        "glossary": "Glossary",
    }

    for part in parts:
        acc += "/" + part
        label = label_map.get(part, part.replace("-", " ").title())
        crumbs.append(Breadcrumb(name=label, url=acc))

    return crumbs


def build_seo_frontmatter(
    meta: dict, body: str, route_path: str
) -> dict | None:
    title = meta.get("title") or first_heading(body) or SITE_NAME.replace(" Documentation", "")
    description = meta.get("description") or extract_excerpt(body)
    entity_type = "home" if route_path == "/" else "page"

    breadcrumbs = build_breadcrumbs(route_path)

    entity = SEOEntity(
        entity_type=entity_type,
        title=title,
        excerpt=description or None,
        status="published",
        breadcrumbs=breadcrumbs,
    )
    payload = build_seo_payload(entity, route_path, SEO_CONFIG)

    if payload is None:
        return None

    return {
        "seo_html": payload.render_html(),
        "seo": payload.to_dict(),
    }


def main() -> int:
    changed = 0
    skipped = 0
    errors = 0

    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        rel_path = md_file.relative_to(PROJECT_ROOT)
        meta, body = read_meta_and_body(md_file)
        route = route_path_from_file(md_file)
        result = build_seo_frontmatter(meta, body, route)

        if result is None:
            print(f"  SKIP  {rel_path}  (no payload generated)")
            skipped += 1
            continue

        new_seo = result["seo"]
        new_seo_html = result["seo_html"]

        existing_seo = meta.get("seo", {})
        existing_seo_html = meta.get("seo_html")

        new_dumped = yaml.dump(new_seo, sort_keys=True)
        existing_dumped = yaml.dump(existing_seo, sort_keys=True)

        if new_dumped == existing_dumped and new_seo_html == existing_seo_html:
            skipped += 1
            continue

        meta["seo"] = new_seo
        meta["seo_html"] = new_seo_html
        fm_dump = yaml.dump(
            meta,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        fm_text = f"---\n{fm_dump}---\n\n{body}"
        md_file.write_text(fm_text, encoding="utf-8")
        print(f"  WRITE {rel_path}")
        changed += 1

    print(f"\nDone: {changed} changed, {skipped} skipped, {errors} errors")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
