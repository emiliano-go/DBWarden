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
from urllib.parse import urlparse

import yaml
from seoslug import SEOConfig, URLPolicy, SEOEntity, build_seo_payload

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SITE_URL = "https://dbwarden.emiliano-go.com"
SITE_NAME = "DBWarden Documentation"

# Extract base path from SITE_URL (e.g. "/DBWarden") for canonical URL construction.
# seoslug's normalize_public_url uses canonical_host (host-only), so it misses
# the base path. We fix canonical URLs post-generation.
_SITE_PARSE = urlparse(SITE_URL)
SITE_BASE_PATH = _SITE_PARSE.path.rstrip("/")

SEO_CONFIG = SEOConfig(
    canonical_host="emiliano-go.github.io",
    public_base_url=SITE_URL,
    url_policy=URLPolicy(
        enforce_https=True,
        lowercase_paths=True,
        trailing_slash="never",
    ),
    site_name=SITE_NAME,
    default_og_image=f"{SITE_URL}/assets/icon.png",
    publisher_name="Emiliano Gandini Outeda",
    title_template="{title} - DBWarden Documentation",
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


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return text


def extract_excerpt(body: str, max_chars: int = 160) -> str:
    # Strip the first heading (page title) since it's redundant in descriptions
    body = re.sub(r"^#\s+.*\n?", "", body, count=1).strip()
    # Take the first paragraph
    para = re.split(r"\n\s*\n", body, maxsplit=1)[0].strip()
    # Clean markdown syntax
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
            body = text[match.end() :].lstrip("\n")
    return meta, body


def build_seo_frontmatter(
    meta: dict, body: str, route_path: str
) -> dict | None:
    title = meta.get("title") or first_heading(body) or "Untitled"
    description = meta.get("description") or extract_excerpt(body)
    entity_type = "home" if route_path == "/" else "page"

    entity = SEOEntity(
        entity_type=entity_type,
        title=title,
        excerpt=description or None,
        status="published",
    )
    payload = build_seo_payload(entity, route_path, SEO_CONFIG)
    if not isinstance(payload, dict):
        return None

    # Fix canonical URL: seoslug's normalize_public_url only uses the host
    # from canonical_host, ignoring any base path in public_base_url.
    # The correct canonical needs the /DBWarden base path prepended.
    correct_canonical = f"https://{SEO_CONFIG.canonical_host}{SITE_BASE_PATH}{route_path}"
    if route_path == "/":
        correct_canonical = correct_canonical.rstrip("/") + "/"

    payload["canonical"] = correct_canonical
    if isinstance(payload.get("og"), dict):
        payload["og"]["url"] = correct_canonical
    if isinstance(payload.get("schema_jsonld"), dict):
        payload["schema_jsonld"]["url"] = correct_canonical
    elif isinstance(payload.get("schema_jsonld"), list):
        for item in payload["schema_jsonld"]:
            if isinstance(item, dict):
                item["url"] = correct_canonical

    return payload


def main() -> int:
    changed = 0
    skipped = 0
    errors = 0

    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        rel_path = md_file.relative_to(PROJECT_ROOT)
        meta, body = read_meta_and_body(md_file)
        route = route_path_from_file(md_file)
        new_seo = build_seo_frontmatter(meta, body, route)

        if new_seo is None:
            print(f"  SKIP  {rel_path}  (no payload generated)")
            skipped += 1
            continue

        existing_seo = meta.get("seo", {})
        new_dumped = yaml.dump(new_seo, sort_keys=True)
        existing_dumped = yaml.dump(existing_seo, sort_keys=True)

        if new_dumped == existing_dumped:
            skipped += 1
            continue

        meta["seo"] = new_seo
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
