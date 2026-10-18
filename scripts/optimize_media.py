#!/usr/bin/env python3
"""Create responsive WebP derivatives while keeping every original asset intact."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageOps

ROOT = Path(".")
OUT = ROOT / "assets-optimized"
REPORT = ROOT / "optimization-report.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SKIP_NAMES = {"favicon.png", "favicon.ico", "favicon.svg"}
OUT.mkdir(exist_ok=True)

def clean_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()

def is_logo(path: Path) -> bool:
    return path.stem.lower() == "logo"

def is_gallery(path: Path) -> bool:
    return bool(re.fullmatch(r"gallery\d+", path.stem.lower()))

def widths_for(path: Path, original_width: int) -> list[int]:
    if is_logo(path):
        desired = [160, 320, 480]
    elif is_gallery(path):
        desired = [320, 640, 960, 1280]
    elif path.stem.lower() == "institution":
        desired = [320, 640, 960, 1280]
    else:
        desired = [320, 640, 960, 1280]
    values = sorted({min(w, original_width) for w in desired if min(w, original_width) > 0})
    if not values:
        values = [original_width]
    return values

def rel_asset(path: Path) -> str:
    return path.as_posix()

def optimize_images() -> tuple[dict[str, dict], list[dict]]:
    source_map: dict[str, dict] = {}
    report_rows: list[dict] = []
    for source in sorted(ROOT.iterdir()):
        if not source.is_file() or source.suffix.lower() not in IMAGE_EXTS:
            continue
        if source.name.lower() in SKIP_NAMES or source.name.lower().startswith("favicon"):
            continue
        # Very small existing assets (for example secretary.webp) are already cheap to transfer.
        if source.stat().st_size < 20 * 1024:
            continue
        try:
            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened)
                image.load()
                original_width, original_height = image.size
                if original_width < 1 or original_height < 1:
                    continue
                has_alpha = "A" in image.getbands() or "transparency" in image.info
                image = image.convert("RGBA" if has_alpha else "RGB")
                prefix = f"{clean_name(source.stem)}-{clean_name(source.suffix.lstrip('.'))}"
                created = []
                quality = 82 if is_logo(source) else 76
                for target_width in widths_for(source, original_width):
                    target_height = max(1, round(original_height * target_width / original_width))
                    resized = image.copy()
                    if resized.size != (target_width, target_height):
                        resized = resized.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    out_path = OUT / f"{prefix}-{target_width}.webp"
                    resized.save(
                        out_path,
                        format="WEBP",
                        quality=quality,
                        method=6,
                        exact=has_alpha,
                    )
                    created.append({
                        "width": target_width,
                        "height": target_height,
                        "path": rel_asset(out_path),
                        "bytes": out_path.stat().st_size,
                    })
                # Match source URLs by basename, including the remote logo.png URL in admission.html.
                item = {
                    "source": source.name,
                    "source_bytes": source.stat().st_size,
                    "width": original_width,
                    "height": original_height,
                    "variants": created,
                }
                source_map[source.name.lower()] = item
                report_rows.append(item)
        except Exception as exc:
            print(f"WARNING: couldn't optimize {source.name}: {exc}")

    return source_map, report_rows

def variants_for(source_map: dict[str, dict], source_url: str) -> tuple[dict | None, str]:
    parsed = urlparse(source_url.strip())
    base = Path(parsed.path).name.lower()
    item = source_map.get(base)
    # contact.html referenced an absent assets/images/gallery1.jpeg; use the existing gallery image instead.
    if item is None and base == "gallery1.jpeg":
        item = source_map.get("gallery1.webp")
    return item, base

def candidate_sizes(item: dict, preferred: int = 640) -> list[dict]:
    variants = item["variants"]
    return variants

def choose_variant(item: dict, preferred: int = 640) -> dict:
    variants = item["variants"]
    under = [v for v in variants if v["width"] <= preferred]
    return under[-1] if under else variants[0]

def set_html_attr(tag: str, name: str, value: str) -> str:
    pattern = re.compile(r'(\s)' + re.escape(name) + r'\s*=\s*(["\']).*?\2', re.I | re.S)
    replacement = lambda m: f'{m.group(1)}{name}="{value}"'
    if pattern.search(tag):
        return pattern.sub(replacement, tag, count=1)
    # Insert before a possible self-closing slash.
    return re.sub(r'\s*/?>$', lambda m: f' {name}="{value}"' + m.group(0), tag, count=1)

def has_html_attr(tag: str, name: str) -> bool:
    return re.search(r'\s' + re.escape(name) + r'\s*=', tag, re.I) is not None

def get_html_attr(tag: str, name: str) -> str | None:
    m = re.search(r'\s' + re.escape(name) + r'\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
    return m.group(2) if m else None

def update_html(page: Path, source_map: dict[str, dict]) -> bool:
    original = page.read_text(encoding="utf-8")
    text = original

    def update_img(match: re.Match) -> str:
        tag = match.group(0)
        src = get_html_attr(tag, "src")
        if not src or "assets-optimized/" in src:
            return tag
        item, base = variants_for(source_map, src)
        if item is None:
            return tag

        variants = candidate_sizes(item)
        fallback = choose_variant(item, 640)
        srcset = ", ".join(f'{v["path"]} {v["width"]}w' for v in variants)
        alt = (get_html_attr(tag, "alt") or "").lower()
        classes = (get_html_attr(tag, "class") or "").lower()

        if "institution-image" in classes:
            sizes = "(max-width: 767px) 100vw, 50vw"
        elif "akec-secretary-img" in classes:
            sizes = "(max-width: 767px) 100vw, 42vw"
        elif "logo" in base or "logo" in alt:
            sizes = "180px"
        elif re.search(r"\bgallery\s*\d+", alt):
            sizes = "(max-width: 767px) 50vw, 280px"
        elif "admission" in base:
            sizes = "(max-width: 767px) 100vw, 50vw"
        else:
            sizes = "(max-width: 767px) 100vw, 640px"

        tag = set_html_attr(tag, "src", fallback["path"])
        tag = set_html_attr(tag, "srcset", srcset)
        tag = set_html_attr(tag, "sizes", sizes)
        if not has_html_attr(tag, "decoding"):
            tag = set_html_attr(tag, "decoding", "async")
        if not has_html_attr(tag, "width"):
            tag = set_html_attr(tag, "width", str(item["width"]))
        if not has_html_attr(tag, "height"):
            tag = set_html_attr(tag, "height", str(item["height"]))
        return tag

    text = re.sub(r"<img\b[^>]*>", update_img, text, flags=re.I | re.S)

    # Replace static CSS background images with their largest optimized derivative.
    url_re = re.compile(r"url\(\s*(?P<q>['\"]?)(?P<url>[^)'\"\s]+)(?P=q)\s*\)", re.I)
    def update_css_url(match: re.Match) -> str:
        old_url = match.group("url")
        if "assets-optimized/" in old_url:
            return match.group(0)
        item, base = variants_for(source_map, old_url)
        if item is None or not item["variants"]:
            return match.group(0)
        return f'url("{item["variants"][-1]["path"]}")'
    text = url_re.sub(update_css_url, text)

    # Use the lightweight logo derivative as the video poster; the source video stays available.
    poster_re = re.compile(r'(\bposter\s*=\s*)(["\'])logo\.webp\2', re.I)
    logo = source_map.get("logo.webp")
    if logo:
        poster = choose_variant(logo, 160)["path"]
        text = poster_re.sub(lambda m: f'{m.group(1)}"{poster}"', text)

    if text != original:
        page.write_text(text, encoding="utf-8")
        return True
    return False

def optimize_video() -> dict | None:
    source = ROOT / "nasim.mp4"
    ffmpeg = shutil.which("ffmpeg")
    if not source.exists() or not ffmpeg:
        return None
    output = OUT / "nasim-optimized.mp4"
    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
        "-vf", "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "28",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", str(output),
    ]
    try:
        subprocess.run(command, check=True, timeout=600)
        result = {
            "source": source.name,
            "source_bytes": source.stat().st_size,
            "optimized": rel_asset(output),
            "optimized_bytes": output.stat().st_size,
            "used": output.stat().st_size < source.stat().st_size * 0.95,
        }
        if not result["used"]:
            output.unlink(missing_ok=True)
            result["optimized"] = None
            result["optimized_bytes"] = None
        return result
    except Exception as exc:
        print(f"WARNING: video optimization skipped: {exc}")
        output.unlink(missing_ok=True)
        return {"source": source.name, "error": str(exc), "used": False}

def main() -> None:
    source_map, rows = optimize_images()
    changed_pages = []
    for page in sorted(ROOT.glob("*.html")):
        if update_html(page, source_map):
            changed_pages.append(page.name)

    video_row = optimize_video()
    if video_row and video_row.get("used"):
        page = ROOT / "index.html"
        if page.exists():
            content = page.read_text(encoding="utf-8")
            content = re.sub(
                r'(<source\b[^>]*\bsrc\s*=\s*)(["\'])nasim\.mp4\2',
                lambda m: f'{m.group(1)}"{video_row["optimized"]}"',
                content,
                flags=re.I,
            )
            page.write_text(content, encoding="utf-8")
            if "index.html" not in changed_pages:
                changed_pages.append("index.html")

    report = {
        "sources": rows,
        "source_image_bytes": sum(r["source_bytes"] for r in rows),
        "largest_variants_bytes": sum(r["variants"][-1]["bytes"] for r in rows if r["variants"]),
        "small_variants_bytes": sum(choose_variant(r, 640)["bytes"] for r in rows if r["variants"]),
        "optimized_variants_bytes": sum(v["bytes"] for r in rows for v in r["variants"]),
        "generated_files": [v["path"] for r in rows for v in r["variants"]],
        "changed_pages": changed_pages,
        "video": video_row,
        "probe_path": next((v["path"] for r in rows if r["source"].lower() == "logo.webp" for v in r["variants"] if v["width"] <= 160), None),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Optimized {len(rows)} original images into {sum(len(r['variants']) for r in rows)} WebP variants.")
    print(f"Updated HTML pages: {', '.join(changed_pages) if changed_pages else 'none'}")
    print(f"Original source images: {report['source_image_bytes'] / 1024 / 1024:.2f} MiB")
    print(f"640px-or-smaller variants total: {report['small_variants_bytes'] / 1024 / 1024:.2f} MiB")
    print(f"All derivatives total: {report['optimized_variants_bytes'] / 1024 / 1024:.2f} MiB")
    if video_row:
        if video_row.get("used"):
            print(f"Video: {video_row['source_bytes']/1024/1024:.2f} MiB -> {video_row['optimized_bytes']/1024/1024:.2f} MiB")
        else:
            print("Video optimization did not produce a smaller usable file.")
    print(f"Report written to {REPORT}")

if __name__ == "__main__":
    main()
