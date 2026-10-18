#!/usr/bin/env python3
"""Generate appropriately sized WebP variants without changing source assets."""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(".")
OUT = ROOT / "assets-optimized"
OUT.mkdir(parents=True, exist_ok=True)

GALLERY_WIDTHS = [320, 360, 400, 480, 640, 960, 1280]
LOGO_WIDTHS = [48, 64, 96, 128, 160, 320, 480]
HERO_WIDTHS = [320, 480, 640, 800, 960, 1280]


def save_variants(source: Path, prefix: str, widths: list[int], quality: int) -> list[dict]:
    results = []
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        image.load()
        original_w, original_h = image.size
        alpha = "A" in image.getbands() or "transparency" in image.info
        image = image.convert("RGBA" if alpha else "RGB")
        target_widths = sorted({min(w, original_w) for w in widths if w > 0})
        for width in target_widths:
            height = max(1, round(original_h * width / original_w))
            resized = image.copy()
            if resized.size != (width, height):
                resized = resized.resize((width, height), Image.Resampling.LANCZOS)
            output = OUT / f"{prefix}-{width}.webp"
            resized.save(
                output,
                "WEBP",
                quality=quality,
                method=6,
                exact=alpha,
            )
            results.append({
                "source": source.name,
                "path": output.as_posix(),
                "width": width,
                "height": height,
                "bytes": output.stat().st_size,
            })
    return results


def main() -> None:
    all_results = []
    gallery_sources = sorted(ROOT.glob("gallery*.webp"))
    gallery_sources = [p for p in gallery_sources if p.stem[7:].isdigit()]
    if not gallery_sources:
        raise SystemExit("No original galleryN.webp source images were found.")

    for source in gallery_sources:
        all_results.extend(save_variants(source, f"{source.stem}-webp", GALLERY_WIDTHS, 70))

    logo_webp = ROOT / "logo.webp"
    if logo_webp.exists():
        all_results.extend(save_variants(logo_webp, "logo-webp", LOGO_WIDTHS, 74))
    logo_png = ROOT / "logo.png"
    if logo_png.exists():
        all_results.extend(save_variants(logo_png, "logo-png", LOGO_WIDTHS, 74))

    hero = ROOT / "institution.png"
    if hero.exists():
        all_results.extend(save_variants(hero, "institution-png", HERO_WIDTHS, 68))

    report_path = OUT / "responsive-asset-report.json"
    report_path.write_text(json.dumps({
        "variants": all_results,
        "variant_count": len(all_results),
        "bytes": sum(item["bytes"] for item in all_results),
    }, indent=2), encoding="utf-8")

    total = sum(item["bytes"] for item in all_results)
    print(f"Generated/refreshened {len(all_results)} responsive WebP assets.")
    print(f"Total derivative size: {total / 1024 / 1024:.2f} MiB.")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
