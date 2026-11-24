"""Seeded, composition-specific cream clusters and small droplets."""

from hashlib import sha256
import json
import math

import numpy as np


def gaussian_recipe(width, height, slot):
    if width <= 0 or height <= 0 or slot not in range(12):
        raise ValueError("Positive artwork dimensions and one of twelve orientation slots are required.")
    seed = 2026100900 + slot * 1009
    rng = np.random.default_rng(seed)
    unit = min(width, height)
    orientation = (slot * math.tau / 12 + float(np.clip(rng.normal(0, .055), -.1, .1))) % math.tau

    def rotate(point, angle):
        x, y = point
        return np.array([x * math.cos(angle) - y * math.sin(angle),
                         x * math.sin(angle) + y * math.cos(angle)])

    forms, groups = [], []
    counts = rng.permutation([4, 3, 3, 2]).tolist()
    scales = rng.permutation([.085, .102, .119, .136])
    directions = [-2.85, -1.3, .3, 1.93]
    for index, count in enumerate(counts):
        radius = float(np.clip(scales[index] * math.exp(rng.normal(0, .12)), .076, .145)) * unit
        angle = orientation + directions[index] + float(rng.normal(0, .22))
        local = [{"offset": np.zeros(2), "radius": radius,
                  "peak": float(np.clip(rng.normal(.45, .25), .05, .95))}]
        for lobe in range(count - 1):
            for _ in range(2000):
                offset = rotate(np.clip(rng.normal([.45, 0], [.30, .34]), -.75, .75) * radius, angle)
                lobe_radius = radius * float(np.clip(math.exp(rng.normal(math.log(.72), .19)), .46, .96))
                protrusion = float(np.linalg.norm(offset)) + lobe_radius
                if protrusion <= radius * 1.55 and (lobe > 0 or protrusion >= radius * 1.15):
                    break
            else:
                raise ValueError("Could not form a connected, visibly irregular cream cluster.")
            local.append({"offset": offset, "radius": lobe_radius,
                          "peak": float(np.clip(rng.normal(.50, .27), 0, .98))})
        extent = max(float(np.linalg.norm(item["offset"])) + item["radius"] for item in local)
        anchor = rotate(np.array([math.cos(directions[index]), math.sin(directions[index])]) * .35, orientation)
        for attempt in range(2000):
            point = (np.array([.5, .5]) + anchor + rng.normal(0, .065, 2)) * [width, height]
            centers = [point + item["offset"] for item in local]
            if not all(8 < center[0] < width - 8 and 8 < center[1] < height - 8 for center in centers):
                continue
            if any(np.linalg.norm(point - group["center"]) < extent + group["extent"] + unit * .035 for group in groups):
                continue
            break
        else:
            raise ValueError(f"Could not place cream cluster {index} for orientation slot {slot}.")
        start = len(forms)
        forms.extend({"x": float(center[0]), "y": float(center[1]),
                      "radius": item["radius"], "peak": item["peak"]}
                     for center, item in zip(centers, local))
        groups.append({"center": point, "extent": extent, "members": list(range(start, len(forms)))})
    for index in range(5):
        radius = unit * float(np.clip(.028 * math.exp(rng.normal(0, .34)), .019, .050))
        anchor = rotate([(-.3, .1), (.03, -.32), (.35, .04), (.08, .36), (-.12, -.08)][index], orientation)
        for attempt in range(3000):
            point = (np.array([.5, .5]) + anchor + rng.normal(0, .15, 2)) * [width, height]
            if not radius + 4 < point[0] < width - radius - 4 or not radius + 4 < point[1] < height - radius - 4:
                continue
            if any(np.linalg.norm(point - group["center"]) < radius + group["extent"] + unit * .035 for group in groups):
                continue
            break
        else:
            raise ValueError(f"Could not place small cream droplet {index} for orientation slot {slot}.")
        forms.append({"x": float(point[0]), "y": float(point[1]), "radius": radius,
                      "peak": float(np.clip(rng.normal(.3, .2), 0, .8))})
        groups.append({"center": point, "extent": radius, "members": [len(forms) - 1]})
    normalized = [[round(f["x"] / width, 6), round(f["y"] / height, 6),
                   round(f["radius"] / unit, 6), round(f["peak"], 6)] for f in forms]
    return {
        "seed": seed, "orientation_slot": slot, "orientation_radians": orientation,
        "distribution": "Seeded Gaussian centroid, lobe-offset, log-radius and peak variation.",
        "cluster_count": 4, "droplet_count": 5, "forms": forms,
        "every_cluster_has_protruding_lobes": True,
        "groups": [{"members": group["members"], "center": group["center"].tolist(),
                    "extent": group["extent"]} for group in groups],
        "normalized_geometry_sha256": sha256(json.dumps(normalized).encode()).hexdigest(),
    }


def validate_distinct_recipes(recipes):
    if len(recipes) != 12 or len({r["normalized_geometry_sha256"] for r in recipes}) != 12:
        raise ValueError("Every portrait and landscape needs its own cream structure.")
    angles = sorted(r["orientation_radians"] for r in recipes)
    gaps = [b - a for a, b in zip(angles, angles[1:])] + [angles[0] + math.tau - angles[-1]]
    if min(gaps) < .3:
        raise ValueError("Cream composition orientations are not sufficiently distinct.")
    return {"unique_layouts": 12, "minimum_orientation_gap_radians": min(gaps)}
