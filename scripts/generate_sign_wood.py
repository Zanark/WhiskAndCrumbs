"""Generate original walnut-style grain and plank joints without reference photographs."""

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1600, 600


def generate():
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    board = np.floor(x / 200).astype(np.int32)
    across = np.mod(x, 200)
    rng = np.random.default_rng(20261008)
    grain = np.zeros_like(x)
    tones = np.array([-4, 3, -1, 4, 0, -3, 2, -2], dtype=np.float32)
    for index in range(8):
        phase = index * 1.618
        warp = across + 3.6 * np.sin(y * .010 + phase) + 1.2 * np.sin(y * .035 + phase)
        if index in (1, 3, 6):
            dx = (across - (85 + index * 7 % 45)) / 30
            dy = (y - (155 + index * 91 % 310)) / 95
            warp += 17 * np.exp(-(dx * dx + dy * dy) * .45) * np.sin(dy * 2)
            knot = np.exp(-(dx * dx + dy * dy) * 1.4)
        else:
            knot = np.zeros_like(x)
        rings = np.sin(warp * .29 + .9 * np.sin(warp * .033 + phase))
        fibers = np.sin(warp * 1.9 + np.sin(y * .065 + phase)) * .55
        broad = np.sin(warp * .056 + phase) * 2.7
        growth = -4.4 * np.maximum(rings, 0) ** 7 + rings * 1.5
        shade = broad + growth + fibers - knot * 10 + tones[index]
        grain += np.where(board == index, shade, 0)
    grain += rng.normal(0, .52, grain.shape)
    grain -= 12 * np.exp(-np.minimum(across, 200 - across) ** 2 / 2.2)
    grain += 3.2 * np.exp(-((across - 3) / 1.3) ** 2)
    base = np.array([99, 65, 42], dtype=np.float32)
    rgb = np.clip(base + grain[..., None] * np.array([1, .74, .53]), [55, 34, 20], [128, 91, 62]).astype(np.uint8)
    image = Image.fromarray(rgb)
    target = ROOT / "web" / "assets" / "bakery-sign-wood.webp"
    image.save(target, "WEBP", lossless=True, method=6)
    evidence = ROOT / ".local" / "wood-grain-raised-sign-20261008"
    receipt = {
        "source": "Original deterministic grain, fiber, growth-ring and knot fields; no reference pixels.",
        "file": str(target.relative_to(ROOT)), "dimensions": [WIDTH, HEIGHT], "mode": image.mode,
        "sha256": sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size,
        "channel_min": rgb.min(axis=(0, 1)).tolist(), "channel_max": rgb.max(axis=(0, 1)).tolist(),
        "center_channel_stddev": rgb[120:480, 500:1100].std(axis=(0, 1)).tolist(),
        "image_tool_views": 0,
    }
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "texture-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    generate()
