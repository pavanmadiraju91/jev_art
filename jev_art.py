#!/usr/bin/env python3
"""Generative art where Jev judges perceptual axes and code renders them.

No hardcoded palettes, shapes, or scene rules. The prompt is the `state`. Jev
answers a handful of atomic, generic questions -- warmth, brightness, roundness,
"does this have one dominant focal element", "does this have strong horizontal
structure" -- and the renderer is a smooth continuous function of that vector.
Representational structure (a sun over a horizon) emerges from the axes, it is
never coded per subject.

Usage:
    export TYPESAFE_API_KEY=...
    python3 jev_art.py "sunset over the sea" -o art.png
    python3 jev_art.py --test        # render canned params, no API call
"""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
import math
import os
import random
import sys
import urllib.request

API_URL = "https://api.typesafe.ai/v1/systemone"


def _load_env():
    """Load KEY=value lines from a sibling .env unless already in the environment."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

# Every question is a generic perceptual axis, not a subject. Score = position on
# a spectrum (0..1); Noul = truth of a statement (0..1). Nothing here names a scene.
QUESTIONS = {
    "warmth": {"type": "score", "instructions": "Color temperature of the mood",
               "criteria": ["Cold, icy blues", "Neutral", "Hot, fiery reds and oranges"]},
    "brightness": {"type": "score", "instructions": "Overall lightness",
                   "criteria": ["Dark, night, deep shadow", "Even", "Bright, glowing, full daylight"]},
    "saturation": {"type": "score", "instructions": "Color intensity",
                   "criteria": ["Washed out, grey, muted", "Moderate", "Vivid, electric, pure color"]},
    "hue_variety": {"type": "score", "instructions": "Range of different colors present",
                    "criteria": ["A single color", "A few related colors", "Many clashing colors"]},
    "roundness": {"type": "score", "instructions": "Are the forms soft/round or sharp/angular?",
                  "criteria": ["Jagged, spiky, angular", "Mixed", "Soft, round, organic"]},
    "density": {"type": "score", "instructions": "How crowded the image feels",
                "criteria": ["Nearly empty", "Balanced", "Packed with elements"]},
    "order": {"type": "score", "instructions": "How orderly versus chaotic",
              "criteria": ["Turbulent, chaotic, random", "Loose", "Calm, aligned, orderly"]},
    "focal": {"type": "noul", "instructions": "The scene is dominated by one large central element"},
    "horizon": {"type": "noul", "instructions": "The scene has strong horizontal structure, like a horizon or sky"},
}
AXES = list(QUESTIONS)


def ask_jev(prompt: str) -> dict:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        sys.exit("Set TYPESAFE_API_KEY (see header).")
    body = json.dumps({"state": prompt, "model": "jev-latest", "questions": QUESTIONS}).encode()
    req = urllib.request.Request(
        API_URL, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["answers"]


def params_from_answers(answers: dict) -> dict:
    """Flatten every answer to a 0..1 knob. Scores are damped toward neutral by
    their confidence, so an unsure judgment pulls the image toward the middle
    instead of committing to a value."""
    out = {}
    for name in AXES:
        a = answers[name]
        if a["type"] == "noul":
            out[name] = a["noul"]
        else:
            v = a["score"] / (len(a["legend"]) - 1)
            out[name] = 0.5 + (v - 0.5) * a.get("confidence", 1.0)
    return out


def _rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360, max(0, min(1, s)), max(0, min(1, v)))
    return (int(r * 255), int(g * 255), int(b * 255))


def _mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def render(p: dict, prompt: str = "", size=(1024, 1024)) -> "Image.Image":
    """A continuous function from the perceptual vector to pixels."""
    from PIL import Image, ImageDraw  # lazy: only the CLI renderer needs Pillow
    w, h = size
    seed = int(hashlib.sha256((prompt + json.dumps(p, sort_keys=True)).encode()).hexdigest(), 16)
    rnd = random.Random(seed)

    base_h = 210 - p["warmth"] * 185          # cool blue (210) -> warm orange/red (25)
    bg_v = 0.05 + p["brightness"] * 0.85
    sat = p["saturation"]

    # Background: vertical gradient whose strength is the horizon axis. When horizon
    # ~0 the top equals the bottom (flat). A warm, horizon-heavy prompt becomes a sky.
    bottom = _rgb(base_h, sat * 0.9 + 0.1, bg_v)
    top = _mix(bottom, _rgb(base_h + 35, sat * 0.6, bg_v * (1 - 0.8 * p["horizon"])), p["horizon"])
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        row = _mix(top, bottom, y / h)
        for x in range(w):
            px[x, y] = row
    draw = ImageDraw.Draw(img, "RGBA")

    # A single dominant element when Jev says so (a sun, a moon, a subject).
    if p["focal"] > 0.15:
        r = min(w, h) * (0.10 + 0.32 * p["focal"])
        cx, cy = w * 0.5, h * (0.62 - 0.18 * p["horizon"])
        col = _rgb(base_h, sat, min(1, bg_v + 0.45))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (235,))

    # Scattered forms. Count from density; grid<->random blended by order; jitter and
    # angular-vs-round shape both continuous.
    count = int(6 + p["density"] * 460)
    count = int(count * (1 - 0.55 * p["focal"]))
    cols = max(1, round(math.sqrt(max(1, count) * w / h)))
    rows = max(1, math.ceil(max(1, count) / cols))
    base = min(w, h) * (0.14 - 0.09 * p["density"])
    order = p["order"]
    sides = max(3, round(3 + p["roundness"] * 17))     # 3 = triangle ... ~20 = circle

    for i in range(count):
        gx, gy = (i % cols + 0.5) / cols * w, (i // cols + 0.5) / rows * h
        rx, ry = rnd.uniform(0, w), rnd.uniform(0, h)
        x = gx * order + rx * (1 - order) + rnd.gauss(0, 1) * (1 - order) * base
        y = gy * order + ry * (1 - order) + rnd.gauss(0, 1) * (1 - order) * base
        s = max(3, base * rnd.uniform(0.5, 1.5) * (1 + (1 - order)))
        hue = base_h + rnd.uniform(-1, 1) * p["hue_variety"] * 70
        col = _rgb(hue, sat + rnd.uniform(-.15, .15), max(bg_v + .12, .35 + p["brightness"] * .5))
        rot = rnd.uniform(0, math.tau)
        verts = [(x + s * math.cos(rot + math.tau * k / sides),
                  y + s * math.sin(rot + math.tau * k / sides)) for k in range(sides)]
        draw.polygon(verts, fill=col + (int(150 + 90 * rnd.random()),))

    return img


def generate(prompt: str, out: str):
    p = params_from_answers(ask_jev(prompt))
    print("Jev judged:", json.dumps({k: round(v, 2) for k, v in p.items()}, indent=2))
    render(p, prompt).save(out)
    print(f"Saved {out}")


def _test():
    warm = {**{a: 0.5 for a in AXES}, "warmth": 0.95, "focal": 0.8, "horizon": 0.8, "brightness": 0.4}
    cold = {**{a: 0.5 for a in AXES}, "warmth": 0.05, "focal": 0.0, "horizon": 0.0, "density": 0.9}
    a, b = render(warm, "x"), render(cold, "x")
    assert a.size == (1024, 1024)
    assert len(a.getcolors(1 << 24)) > 1, "blank"
    assert list(a.getdata()) != list(b.getdata()), "warmth/focal made no difference"
    # warm image should be redder than the cold one on average
    ar = sum(c[0] for c in a.getdata()); br = sum(c[0] for c in b.getdata())
    ab = sum(c[2] for c in a.getdata()); bb = sum(c[2] for c in b.getdata())
    assert ar > br and bb > ab, "warmth axis not driving hue"
    print("ok")


def main():
    ap = argparse.ArgumentParser(description="Jev-directed generative art.")
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("-o", "--out", default="art.png")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    if args.test:
        _test()
    elif args.prompt:
        generate(args.prompt, args.out)
    else:
        ap.error("give a prompt or use --test")


if __name__ == "__main__":
    main()
