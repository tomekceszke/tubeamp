"""Shared color utilities for gradient rendering."""

from __future__ import annotations


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> str:
    r = int(c1[0] * (1 - t) + c2[0] * t)
    g = int(c1[1] * (1 - t) + c2[1] * t)
    b = int(c1[2] * (1 - t) + c2[2] * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def gradient_steps(
    color_from: str, color_to: str, count: int, span: int
) -> list[str]:
    """Colours for the first `count` cells of a `span`-wide gradient.

    The bar widgets render into different media — Rich markup in one case,
    Text.append in another — so this yields the colours and leaves the
    drawing to the caller.
    """
    rgb_from = hex_to_rgb(color_from)
    rgb_to = hex_to_rgb(color_to)
    divisor = max(span - 1, 1)
    return [lerp_color(rgb_from, rgb_to, i / divisor) for i in range(count)]
