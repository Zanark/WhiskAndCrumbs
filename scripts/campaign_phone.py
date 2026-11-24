"""Original raised-glass phone surrounds; never deform the supplied viewport."""

import numpy as np
from PIL import Image


def rounded_surface(size, bounds, radius, bevel, colour, specular):
    width, height = size
    y, x = np.mgrid[:height, :width].astype(np.float32)
    left, top, right, bottom = bounds
    qx = np.abs(x - (left + right) / 2) - ((right - left) / 2 - radius)
    qy = np.abs(y - (top + bottom) / 2) - ((bottom - top) / 2 - radius)
    distance = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - radius
    gy, gx = np.gradient(distance)
    depth = np.clip(-distance / bevel, 0, 1)
    side = np.sqrt(1 - depth ** 2)
    nx, ny, nz = gx * side, gy * side, depth
    light = np.array([-.55, -.65, .65], dtype=np.float32)
    light /= np.linalg.norm(light)
    half = light + (0, 0, 1)
    half /= np.linalg.norm(half)
    diffuse = np.maximum(0, nx * light[0] + ny * light[1] + nz * light[2])
    shine = np.maximum(0, nx * half[0] + ny * half[1] + nz * half[2]) ** 26
    rgb = np.array(colour) * (.46 + .65 * diffuse[..., None]) + shine[..., None] * specular
    alpha = np.clip(.5 - distance, 0, 1) * 255
    return Image.fromarray(np.dstack((np.clip(rgb, 0, 255), alpha)).astype(np.uint8))


def raised_phone_shell(size, scale):
    if scale <= 0 or min(size) < 60 * scale:
        raise ValueError("Raised phone glass needs a positive scale and a complete phone surround.")
    width, height = size
    frame = Image.new("RGBA", size)
    layers = (
        ((3, 5, width / scale - 1, height / scale - 1), 29, 3, (35, 48, 43), 65),
        ((.5, .5, width / scale - 4, height / scale - 5), 29, 4, (100, 119, 112), 135),
        ((3.5, 3.5, width / scale - 7, height / scale - 8), 26, 7, (26, 42, 36), 210),
    )
    for bounds, radius, bevel, colour, specular in layers:
        frame.alpha_composite(rounded_surface(
            size, tuple(value * scale for value in bounds), radius * scale,
            bevel * scale, colour, specular,
        ))
    return frame, {
        "kind": "rounded-convex-glass-with-sidewall",
        "glass_roll_width_px": 7,
        "body_depth_offset_px": [3, 4],
        "light_direction": "upper-left",
        "screen_overlay": False,
        "screen_distortion": False,
    }


def validate_raised_phones(entries):
    found = []
    for entry in entries:
        for device in entry["devices"]:
            proof = device.get("raised_glass")
            expected = entry["edition"] == "portrait" and device["device"] == "mobile"
            if expected:
                if (proof is None or proof.get("kind") != "rounded-convex-glass-with-sidewall"
                        or proof.get("glass_roll_width_px") != 7 or proof.get("body_depth_offset_px") != [3, 4]
                        or proof.get("screen_overlay") is not False or proof.get("screen_distortion") is not False
                        or proof.get("unaltered_screen_raster") is not True):
                    raise ValueError("Raised portrait phones need curved glass and an unaltered viewport.")
                found.append(entry["filename"])
            elif proof is not None:
                raise ValueError("Raised-phone revision must not change README or desktop surrounds.")
    if sorted(found) != ["01-welcome.jpg", "06-simple-ordering.jpg"]:
        raise ValueError("Only first and last Instagram portraits may contain raised phones.")
    return {"scope": "instagram-phones-01-and-06", "phones": 2, "unaltered_viewports": True}
