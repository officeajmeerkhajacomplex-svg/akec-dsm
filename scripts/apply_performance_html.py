#!/usr/bin/env python3
"""Apply responsive-image sizing and local deferred Bootstrap across all AKEC pages."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(".")
PAGES = [
    "index.html", "about.html", "admission.html", "contact.html",
    "dawa.html", "garden.html", "hifz.html", "madrassa.html",
]
BOOTSTRAP_JS = "/assets-optimized/bootstrap.bundle.min.js"
HERO_WIDTHS = [320, 480, 640, 800, 960, 1280]
GALLERY_WIDTHS = [320, 360, 400, 480, 640, 960, 1280]


def get_attr(tag: str, name: str) -> str | None:
    match = re.search(
        r'\s' + re.escape(name) + r'\s*=\s*(["\'])(.*?)\1',
        tag,
        re.I | re.S,
    )
    return match.group(2) if match else None


def set_attr(tag: str, name: str, value: str) -> str:
    pattern = re.compile(
        r'(\s)' + re.escape(name) + r'\s*=\s*(["\']).*?\2',
        re.I | re.S,
    )
    if pattern.search(tag):
        return pattern.sub(lambda match: f'{match.group(1)}{name}="{value}"', tag, count=1)
    return re.sub(r'\s*/?>$', lambda match: f' {name}="{value}"' + match.group(0), tag, count=1)


def replace_bootstrap_script(text: str, page: str) -> str:
    cdn_script = re.compile(
        r"""<script\b(?=[^>]*\bsrc\s*=\s*["']https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.0/dist/js/bootstrap\.bundle\.min\.js["'])[^>]*>\s*</script>""",
        re.I | re.S,
    )
    text = cdn_script.sub("", text)
    occurrences = len(re.findall(r'<script\b[^>]*src="/assets-optimized/bootstrap\.bundle\.min\.js"', text, re.I))
    if occurrences == 0:
        tag = f'    <script defer src="{BOOTSTRAP_JS}"></script>\n'
        head_end = re.search(r"</head\s*>", text, re.I)
        if not head_end:
            raise RuntimeError(page + ": </head> not found.")
        text = text[:head_end.start()] + tag + text[head_end.start():]
    elif occurrences > 1:
        raise RuntimeError(page + ": duplicate local Bootstrap scripts found.")
    return text


def update_hero(text: str) -> str:
    def update_tag(match: re.Match) -> str:
        tag = match.group(0)
        source = get_attr(tag, "src") or ""
        if "institution-png-" not in source:
            return tag
        tag = set_attr(tag, "src", "assets-optimized/institution-png-640.webp")
        tag = set_attr(
            tag,
            "srcset",
            ", ".join(f"assets-optimized/institution-png-{width}.webp {width}w" for width in HERO_WIDTHS),
        )
        tag = set_attr(tag, "sizes", "(max-width: 767px) 100vw, 50vw")
        tag = set_attr(tag, "fetchpriority", "high")
        return tag

    # Update only the institutional hero element; other imagery should keep its own sizing.
    text = re.sub(
        r'<img\b(?=[^>]*\bclass=["\'][^"\']*\bInstitution-image\b[^"\']*["\'])[^>]*>',
        update_tag,
        text,
        count=1,
        flags=re.I | re.S,
    )

    def update_preload(match: re.Match) -> str:
        tag = match.group(0)
        tag = set_attr(tag, "href", "assets-optimized/institution-png-640.webp")
        tag = set_attr(
            tag,
            "imagesrcset",
            ", ".join(f"assets-optimized/institution-png-{width}.webp {width}w" for width in HERO_WIDTHS),
        )
        tag = set_attr(tag, "imagesizes", "(max-width: 767px) 100vw, 50vw")
        tag = set_attr(tag, "fetchpriority", "high")
        return tag

    text = re.sub(
        r'<link\b(?=[^>]*\bdata-name=["\']akec-hero-image-preload["\'])[^>]*>',
        update_preload,
        text,
        count=1,
        flags=re.I | re.S,
    )
    return text


def update_gallery(text: str) -> str:
    def update_tag(match: re.Match) -> str:
        tag, number = match.group(0), match.group(1)
        prefix = f"gallery{number}-webp"
        tag = set_attr(tag, "src", f"assets-optimized/{prefix}-400.webp")
        tag = set_attr(
            tag,
            "srcset",
            ", ".join(f"assets-optimized/{prefix}-{width}.webp {width}w" for width in GALLERY_WIDTHS),
        )
        # The card layout is two columns on mobile and up to three columns on desktop.
        tag = set_attr(
            tag,
            "sizes",
            "(max-width: 767px) 44vw, (max-width: 1199px) 30vw, (max-width: 1399px) 27vw, 24vw",
        )
        return tag

    return re.sub(
        r'<img\b[^>]*\balt=["\']Gallery\s*(\d+)["\'][^>]*>',
        update_tag,
        text,
        flags=re.I | re.S,
    )


def main() -> None:
    # Never point production HTML at an asset that has not already been built.
    if not (ROOT / BOOTSTRAP_JS.lstrip("/")).is_file():
        raise SystemExit("Self-hosted Bootstrap bundle is missing; refusing to update HTML.")
    for width in HERO_WIDTHS:
        if not (ROOT / f"assets-optimized/institution-png-{width}.webp").is_file():
            raise SystemExit(f"Missing responsive hero image width {width}.")
    for number in range(1, 12):
        for width in GALLERY_WIDTHS:
            if not (ROOT / f"assets-optimized/gallery{number}-webp-{width}.webp").is_file():
                raise SystemExit(f"Missing responsive gallery asset gallery{number}-{width}.webp.")

    changed = []
    for page in PAGES:
        path = ROOT / page
        if not path.is_file():
            raise SystemExit("Expected HTML page missing: " + page)
        before = path.read_text(encoding="utf-8")
        if "[...]" in before:
            raise SystemExit(page + ": truncated markup marker found.")
        text = replace_bootstrap_script(before, page)
        if page == "index.html":
            text = update_hero(text)
            text = update_gallery(text)
        if "[...]" in text:
            raise SystemExit(page + ": generated text unexpectedly contains a truncation marker.")
        if len(re.findall(r'<script\b[^>]*src="/assets-optimized/bootstrap\.bundle\.min\.js"', text, re.I)) != 1:
            raise SystemExit(page + ": local Bootstrap reference validation failed.")
        if page == "index.html":
            if not re.search(r"<title\b[^>]*>[\s\S]*?</title>", text, re.I):
                raise SystemExit("Homepage title is malformed.")
            if len(re.findall(r"<main\b", text, re.I)) != 1:
                raise SystemExit("Homepage must contain exactly one main landmark.")
            gallery_tags = re.findall(r'<img\b[^>]*\balt=["\']Gallery\s*\d+["\'][^>]*>', text, re.I | re.S)
            if len(gallery_tags) != 11 or any("-360.webp 360w" not in tag for tag in gallery_tags):
                raise SystemExit("Homepage gallery srcset validation failed.")
        if text != before:
            path.write_text(text, encoding="utf-8")
            changed.append(page)

    print("Updated page performance markup:", ", ".join(changed) if changed else "no changes")


if __name__ == "__main__":
    main()
