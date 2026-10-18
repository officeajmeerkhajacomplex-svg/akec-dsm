#!/usr/bin/env python3
"""Generate a WebVTT caption file from the homepage video using Whisper.

This transcription is automatic and should be reviewed by a fluent listener. The script
never invents a caption track when Whisper finds no speech.
"""
from __future__ import annotations

import re
from pathlib import Path

import whisper
from whisper.tokenizer import LANGUAGES

ROOT = Path(".")
VIDEO = ROOT / "nasim.mp4"
OUTPUT_DIR = ROOT / "assets-optimized"
VTT_PATH = OUTPUT_DIR / "nasim-captions.vtt"
HTML_PATH = ROOT / "index.html"


def vtt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, rem = divmod(milliseconds, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    whole_seconds, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{ms:03d}"


def main() -> None:
    if not VIDEO.exists() or not HTML_PATH.exists():
        raise SystemExit("Homepage video or index.html was not found.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading Whisper base model for automatic speech recognition.")
    model = whisper.load_model("base")
    result = model.transcribe(
        str(VIDEO),
        task="transcribe",
        verbose=False,
        fp16=False,
        condition_on_previous_text=False,
    )

    segments = []
    for segment in result.get("segments", []):
        text = re.sub(r"\s+", " ", str(segment.get("text", ""))).strip()
        if not text:
            continue
        no_speech = float(segment.get("no_speech_prob", 0) or 0)
        avg_logprob = float(segment.get("avg_logprob", 0) or 0)
        # Avoid the most obvious silent-section hallucinations.
        if no_speech > 0.80 and avg_logprob < -0.80:
            continue
        start = float(segment.get("start", 0) or 0)
        end = float(segment.get("end", 0) or 0)
        if end <= start:
            continue
        text = text.replace("-->", "—>")
        segments.append((start, end, text))

    if not segments:
        print("WARNING: Whisper found no reliable speech segments; no empty caption track was added.")
        return

    captions = ["WEBVTT", ""]
    for start, end, text in segments:
        captions.extend([f"{vtt_time(start)} --> {vtt_time(end)}", text, ""])
    VTT_PATH.write_text("\n".join(captions).rstrip() + "\n", encoding="utf-8")

    language = str(result.get("language", "en")).lower()
    if not re.fullmatch(r"[a-z]{2,3}", language):
        language = "en"
    language_label = LANGUAGES.get(language, language).title()
    track = (
        '<track kind="captions" src="assets-optimized/nasim-captions.vtt" '
        f'srclang="{language}" label="{language_label}">'
    )

    html = HTML_PATH.read_text(encoding="utf-8")
    video_pattern = re.compile(
        r'(<video\b[^>]*\bid=["\']akecScrollVideo["\'][^>]*>)([\s\S]*?)(</video>)',
        re.IGNORECASE,
    )
    match = video_pattern.search(html)
    if not match:
        raise SystemExit('The video element with id="akecScrollVideo" was not found.')

    opening, inner, closing = match.groups()
    inner = re.sub(r"<track\b[^>]*>", "", inner, flags=re.IGNORECASE)
    source_pattern = re.compile(r"(<source\b[^>]*>)", re.IGNORECASE)
    if source_pattern.search(inner):
        inner = source_pattern.sub(lambda m: m.group(1) + "\n                            " + track, inner, count=1)
    else:
        inner = "\n                            " + track + "\n" + inner
    updated = html[:match.start()] + opening + inner + closing + html[match.end():]
    if updated != html:
        HTML_PATH.write_text(updated, encoding="utf-8")

    print(f"Generated {len(segments)} caption cues in {VTT_PATH}.")
    print(f"Detected spoken language: {language_label} ({language}).")
    print("Review automatic captions for names, regional terms and music before treating them as a verified transcript.")


if __name__ == "__main__":
    main()
