#!/usr/bin/env python3
"""Apply shared responsive-image, CSS-delivery and accessibility improvements."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(".")
PAGES = ["index.html", "about.html", "admission.html", "contact.html",
         "dawa.html", "garden.html", "hifz.html", "madrassa.html"]
BOOT = "/assets-optimized/bootstrap-purged.css"
ICONS = "/assets-optimized/remixicon-purged.css"
WIDTHS = [48, 64, 96, 128, 160, 320, 480]


def attr(tag: str, name: str) -> str | None:
    m = re.search(r'\s' + re.escape(name) + r'\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
    return m.group(2) if m else None


def set_attr(tag: str, name: str, value: str) -> str:
    pattern = re.compile(r'(\s)' + re.escape(name) + r'\s*=\s*(["\']).*?\2', re.I | re.S)
    if pattern.search(tag):
        return pattern.sub(lambda m: f'{m.group(1)}{name}="{value}"', tag, count=1)
    return re.sub(r'\s*/?>$', lambda m: f' {name}="{value}"' + m.group(0), tag, count=1)


def stylesheet_links(text: str) -> str:
    def convert(m: re.Match) -> str:
        tag = m.group(0).lower()
        if "bootstrap.min.css" in tag:
            return f'<link rel="preload" as="style" href="{BOOT}">\n    <link rel="stylesheet" href="{BOOT}">'
        if "remixicon.css" in tag:
            return (f'<link rel="preload" as="style" href="{ICONS}" '
                    'onload="this.onload=null;this.rel=\'stylesheet\'">\n    '
                    f'<noscript><link rel="stylesheet" href="{ICONS}"></noscript>')
        return m.group(0)
    return re.sub(r'<link\b[^>]*>', convert, text, flags=re.I | re.S)


def logo_tag(tag: str) -> str:
    source = attr(tag, "src") or ""
    m = re.search(r'assets-optimized/(logo-(?:webp|png))-\d+\.webp$', source, re.I)
    if not m:
        return tag
    prefix = m.group(1)
    widths = [w for w in WIDTHS if (ROOT / "assets-optimized" / f"{prefix}-{w}.webp").is_file()]
    if not widths:
        return tag
    chosen = 64 if 64 in widths else widths[0]
    srcset = ", ".join(f"assets-optimized/{prefix}-{w}.webp {w}w" for w in widths)
    style = (attr(tag, "style") or "").lower()
    sizes = "60px" if "max-height: 80px" in style else "(max-width: 767px) 40px, 50px"
    return set_attr(set_attr(set_attr(tag, "src", f"assets-optimized/{prefix}-{chosen}.webp"),
                             "srcset", srcset), "sizes", sizes)


def update_page(page: str) -> bool:
    p = ROOT / page
    if not p.exists():
        print("WARNING: missing page", page)
        return False
    before = p.read_text(encoding="utf-8")
    text = stylesheet_links(before)

    skip_css = """
.skip-link{position:fixed;left:1rem;top:-6rem;z-index:100000;padding:.75rem 1rem;
background:#fff;color:#0c629e;border:2px solid #805f16;border-radius:.35rem;
font-weight:700;text-decoration:underline}
.skip-link:focus{top:1rem;left:1rem;outline:3px solid #0c629e;outline-offset:3px}
main#main-content{display:block}
"""
    if 'class="skip-link"' not in text:
        text = re.sub(r'(<body\b[^>]*>)',
                      r'\1\n<a class="skip-link" href="#main-content">Skip to main content</a>',
                      text, count=1, flags=re.I)
    if ".skip-link:focus" not in text:
        m = re.search(r"<style\b[^>]*>", text, re.I)
        if m:
            text = text[:m.end()] + skip_css + text[m.end():]

    if not re.search(r"<main\b", text, re.I):
        body = re.search(r"<body\b[^>]*>", text, re.I)
        footer = re.search(r"<footer\b", text, re.I)
        if body and footer:
            section = text[body.end():footer.start()]
            nav_end = re.search(r"</header\s*>", section, re.I) if page == "contact.html" else None
            if not nav_end:
                nav_end = re.search(r"</nav\s*>", section, re.I)
            if nav_end:
                start = body.end() + nav_end.end()
                text = text[:start] + '\n<main id="main-content" tabindex="-1">\n' + text[start:]
                footer = re.search(r"<footer\b", text, re.I)
                if footer:
                    text = text[:footer.start()] + "\n</main>\n\n" + text[footer.start():]
            else:
                print("WARNING: could not add main landmark to", page)

    # Distinguish visually identical View More links for screen-reader link lists.
    link_labels = {
        "dawa.html": "View more about Zanchari Excellence Centre for Da'wa",
        "hifz.html": "View more about Khaja Mueenudheen Hifzul Qur'an Academy",
        "madrassa.html": "View more about Ajmeer Khaja Residential Madrassa",
        "garden.html": "View more about Mueeniyya Garden of Qur'an Studies for Girls",
    }
    def named_link(m: re.Match) -> str:
        whole = m.group(0)
        opening = re.match(r"<a\b[^>]*>", whole, re.I | re.S)
        if not opening:
            return whole
        op = opening.group(0)
        href = attr(op, "href") or ""
        if href not in link_labels or not re.search(r">\s*View More\s*(?:→|&rarr;|&#8594;)?\s*</a>", whole, re.I):
            return whole
        if attr(op, "aria-label"):
            return whole
        return set_attr(op, "aria-label", link_labels[href]) + whole[opening.end():]
    text = re.sub(r"<a\b[^>]*>[\s\S]*?</a>", named_link, text, flags=re.I)
    text = re.sub(r"<img\b[^>]*>", lambda m: logo_tag(m.group(0)), text, flags=re.I | re.S)

    if page == "index.html" and 'data-name="akec-hero-image-preload"' not in text:
        hero = (
            '<link rel="preload" as="image" href="assets-optimized/institution-png-640.webp" '
            'imagesrcset="assets-optimized/institution-png-320.webp 320w, '
            'assets-optimized/institution-png-640.webp 640w, '
            'assets-optimized/institution-png-960.webp 960w, '
            'assets-optimized/institution-png-1280.webp 1280w" '
            'imagesizes="(max-width: 767px) 100vw, 50vw" fetchpriority="high" '
            'data-name="akec-hero-image-preload">'
        )
        title = re.search(r"</title\s*>", text, re.I)
        if title:
            text = text[:title.end()] + "\n    " + hero + text[title.end():]

    if text != before:
        p.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    for needed in [BOOT, ICONS]:
        if not (ROOT / needed.lstrip("/")).is_file():
            raise SystemExit("Purged stylesheet not found: " + needed)
    changed = [page for page in PAGES if update_page(page)]
    print("Updated markup:", ", ".join(changed) if changed else "no changes")


if __name__ == "__main__":
    main()
