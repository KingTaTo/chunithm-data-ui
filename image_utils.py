from __future__ import annotations

import struct
import zlib
from pathlib import Path


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def rgba_to_png(width: int, height: int, rgba: bytes) -> bytes:
    rows = []
    stride = width * 4
    for y in range(height):
        rows.append(b"\x00" + rgba[y * stride:(y + 1) * stride])
    raw = b"".join(rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(raw)) + png_chunk(b"IEND", b"")


def resize_rgba_nearest(width: int, height: int, rgba: bytes, max_dimension: int) -> tuple[int, int, bytes]:
    if max_dimension <= 0:
        raise ValueError("max_dimension must be positive")
    largest = max(width, height)
    if largest <= max_dimension:
        return width, height, rgba

    scale = max_dimension / largest
    target_width = max(1, int(width * scale))
    target_height = max(1, int(height * scale))
    resized = bytearray(target_width * target_height * 4)

    for y in range(target_height):
        source_y = min(height - 1, int(y / scale))
        for x in range(target_width):
            source_x = min(width - 1, int(x / scale))
            source_offset = (source_y * width + source_x) * 4
            target_offset = (y * target_width + x) * 4
            resized[target_offset:target_offset + 4] = rgba[source_offset:source_offset + 4]

    return target_width, target_height, bytes(resized)


def dds_to_png(path: Path, max_dimension: int | None = None) -> bytes:
    try:
        import py_dds
    except ImportError as exc:
        raise RuntimeError("py_dds is not installed. Run: python -m pip install -r requirements.txt") from exc

    dds = py_dds.DDSImage(str(path))
    width = dds.width(mip=0)
    height = dds.height(mip=0)
    rgba = bytearray(width * height * 4)

    def set_pixel(x: int, y: int, r: int, g: int, b: int, a: int) -> None:
        offset = (y * width + x) * 4
        rgba[offset:offset + 4] = bytes((r, g, b, a))

    dds.draw(set_pixel_callback=set_pixel, mip=0)
    rgba_bytes = bytes(rgba)
    if max_dimension is not None:
        width, height, rgba_bytes = resize_rgba_nearest(width, height, rgba_bytes, max_dimension)
    return rgba_to_png(width, height, rgba_bytes)
