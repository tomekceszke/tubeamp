"""Shared color utilities for gradient rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


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


def sample_gradient(stops: Sequence[str], t: float) -> str:
    """Colour at position `t` (0..1) along a gradient through `stops`.

    Two stops behave exactly like `lerp_color`; three let a theme bend the
    spectrum through a middle hue the way a hardware analyser ramps green to
    amber to red, instead of only brightening one hue.
    """
    if not stops:
        return "#000000"
    if len(stops) == 1:
        return stops[0]

    t = min(max(t, 0.0), 1.0)
    segments = len(stops) - 1
    pos = t * segments
    index = min(int(pos), segments - 1)
    return lerp_color(
        hex_to_rgb(stops[index]), hex_to_rgb(stops[index + 1]), pos - index
    )


def relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance of a colour, 0.0 (black) to 1.0 (white)."""
    channels = []
    for value in hex_to_rgb(hex_color):
        c = value / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(color_a: str, color_b: str) -> float:
    """WCAG contrast ratio between two colours, 1.0 (identical) to 21.0."""
    lum_a, lum_b = relative_luminance(color_a), relative_luminance(color_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)
