"""Validate runtime sprite dimensions, alpha content, alignment, and text encoding."""

from __future__ import annotations

import ast
import struct
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read_alpha(path: Path) -> tuple[int, int, list[list[int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos = 8
    packed = bytearray()
    width = height = color_type = bit_depth = 0
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += length + 12
        if kind == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk[:10])
        elif kind == b"IDAT":
            packed.extend(chunk)
        elif kind == b"IEND":
            break
    channels = {4: 2, 6: 4}.get(color_type)
    if bit_depth != 8 or channels is None:
        raise ValueError(f"unsupported PNG format: depth={bit_depth}, color={color_type}")
    raw = zlib.decompress(packed)
    stride = width * channels
    rows: list[list[int]] = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scan = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        for index in range(stride):
            left = scan[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 1:
                scan[index] = (scan[index] + left) & 255
            elif filter_type == 2:
                scan[index] = (scan[index] + above) & 255
            elif filter_type == 3:
                scan[index] = (scan[index] + ((left + above) // 2)) & 255
            elif filter_type == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
                scan[index] = (scan[index] + predictor) & 255
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter: {filter_type}")
        rows.append([scan[index] for index in range(channels - 1, stride, channels)])
        previous = scan
    return width, height, rows


def opaque_bounds(alpha: list[list[int]]) -> tuple[int, int, int, int, int]:
    points = [(x, y) for y, row in enumerate(alpha) for x, value in enumerate(row) if value]
    if not points:
        return 0, 0, -1, -1, 0
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys), len(points)


def validate_set(root: Path, expected_size: int, expected_count: int) -> list[str]:
    errors: list[str] = []
    files = sorted(root.rglob("*.png"))
    if len(files) != expected_count:
        errors.append(f"{root}: expected {expected_count} PNGs, found {len(files)}")
    for path in files:
        try:
            width, height, alpha = read_alpha(path)
            bounds = opaque_bounds(alpha)
            if (width, height) != (expected_size, expected_size):
                errors.append(f"{path}: {width}x{height}, expected {expected_size}x{expected_size}")
            if bounds[4] == 0:
                errors.append(f"{path}: empty image")
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return errors


def validate_player(root: Path) -> list[str]:
    errors = validate_set(root, 84, 48)
    for animation in ("idle", "walk", "attack"):
        for index in range(1, 5):
            pairs = []
            for direction in ("left", "right"):
                _, _, alpha = read_alpha(root / direction / animation / f"{index:02}.png")
                pairs.append(opaque_bounds(alpha))
            left, right = pairs
            if (left[2] - left[0], left[3] - left[1], left[4]) != (
                right[2] - right[0], right[3] - right[1], right[4]
            ):
                errors.append(f"player {animation}/{index:02}: left/right silhouette mismatch")
    return errors


def validate_enemies(root: Path) -> list[str]:
    errors = validate_set(root, 96, 144)
    for path in sorted(root.rglob("*.png")):
        _, _, alpha = read_alpha(path)
        central = [(x, y) for y, row in enumerate(alpha) for x in range(24, 73) if row[x]]
        body_height = max((y for _, y in central), default=-1) - min((y for _, y in central), default=0) + 1
        if len(central) < 450 or body_height < 35:
            errors.append(f"{path}: probable missing body ({len(central)} pixels, {body_height}px high)")
    return errors


def validate_source_text() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT / "src").glob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
            if "\ufffd" in text:
                errors.append(f"{path}: contains Unicode replacement characters")
            ast.parse(text, filename=str(path))
        except (UnicodeError, SyntaxError) as exc:
            errors.append(f"{path}: {exc}")
    return errors


def validate_environment() -> list[str]:
    errors: list[str] = []
    expected = {"floor_tile.png": 96, "wall_tile.png": 32}
    root = ROOT / "assets" / "environment"
    for name, size in expected.items():
        path = root / name
        try:
            width, height, alpha = read_alpha(path)
            if (width, height) != (size, size):
                errors.append(f"{path}: {width}x{height}, expected {size}x{size}")
            if opaque_bounds(alpha)[4] == 0:
                errors.append(f"{path}: empty texture")
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return errors


def main() -> int:
    errors = []
    errors += validate_player(ROOT / "assets" / "sprites" / "player" / "frames_v5")
    errors += validate_enemies(ROOT / "assets" / "sprites" / "enemies" / "frames_v6")
    errors += validate_set(ROOT / "assets" / "sprites" / "relics", 96, 9)
    errors += validate_set(ROOT / "assets" / "sprites" / "boss_projectiles", 48, 80)
    errors += validate_environment()
    errors += validate_source_text()
    if errors:
        print("Sprite validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Sprite validation passed: 48 player frames, 144 enemy frames, UTF-8 sources OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
