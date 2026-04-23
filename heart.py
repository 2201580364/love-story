"""Heart shape generation utilities.

Provides parametric heart outline generation and filled heart point
sampling via rejection sampling.
"""

import math
import random


def _heart_outline_polygon(num_points: int = 200) -> list[tuple[float, float]]:
    """Generate normalized heart outline polygon (no offset, no scaling).

    Args:
        num_points: Number of polygon vertices to generate.

    Returns:
        List of (x, y) tuples in normalized heart coordinate space.
    """
    polygon = []
    for i in range(num_points):
        t = 2 * math.pi * i / num_points
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        polygon.append((x, y))
    return polygon


def _point_in_polygon(px: float, py: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray casting algorithm to test if point (px, py) is inside polygon.

    Args:
        px: X coordinate of the point to test.
        py: Y coordinate of the point to test.
        polygon: List of (x, y) tuples defining the polygon vertices.

    Returns:
        True if the point is inside the polygon, False otherwise.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def heart_points(cx: float, cy: float, size: float, num_points: int = 200) -> list[tuple[float, float]]:
    """Return heart outline coordinate list using parametric equations.

    Args:
        cx: X coordinate of the center offset.
        cy: Y coordinate of the center offset.
        size: Scale factor for the heart.
        num_points: Number of outline points to generate.

    Returns:
        List of (x, y) tuples representing the heart outline.

    Raises:
        ValueError: If size <= 0 or num_points <= 0.
    """
    if size <= 0:
        raise ValueError("size must be > 0")
    if num_points <= 0:
        raise ValueError("num_points must be > 0")

    points = []
    for i in range(num_points):
        t = 2 * math.pi * i / num_points
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((cx + x * size, cy - y * size))
    return points


def filled_heart_points(cx: float, cy: float, size: float, density: int = 800) -> list[tuple[float, float]]:
    """Return filled heart as random scatter points using rejection sampling.

    Args:
        cx: X coordinate of the center offset.
        cy: Y coordinate of the center offset.
        size: Scale factor for the heart.
        density: Number of fill points to generate.

    Returns:
        List of (x, y) tuples representing the filled heart scatter points.

    Raises:
        ValueError: If size <= 0 or density <= 0.
    """
    if size <= 0:
        raise ValueError("size must be > 0")
    if density <= 0:
        raise ValueError("density must be > 0")

    outline_polygon = _heart_outline_polygon(300)
    points = []
    max_attempts = density * 50
    attempts = 0

    while len(points) < density and attempts < max_attempts:
        attempts += 1
        x0 = random.uniform(-16, 16)
        y0 = random.uniform(-17, 13)
        if _point_in_polygon(x0, y0, outline_polygon):
            points.append((cx + x0 * size, cy - y0 * size))

    return points


def filled_heart_points_v2(
    cx: float,
    cy: float,
    size: float,
    density: int = 1200,
) -> list[tuple[float, float, float]]:
    """Return filled heart scatter points with depth-weight for color layering.

    Each returned point carries a random depth weight w in [0, 1] that can
    be used for color layering: higher w values map to brighter/pinker colors.
    Uses rejection sampling within the heart bounding box.

    Args:
        cx: X coordinate of the center offset in canvas pixels.
        cy: Y coordinate of the center offset in canvas pixels.
        size: Scale factor for the heart (must be > 0).
        density: Target number of fill points to generate (must be > 0).

    Returns:
        List of (x, y, w) tuples where:
            x, y: Canvas pixel coordinates.
            w: Random depth weight in [0.0, 1.0] for color layering.

    Raises:
        ValueError: If size <= 0 or density <= 0.
        TypeError: If cx, cy, size are not numeric or density is not int.
    """
    if not isinstance(cx, (int, float)):
        raise TypeError(f"cx must be numeric, got {type(cx).__name__}")
    if not isinstance(cy, (int, float)):
        raise TypeError(f"cy must be numeric, got {type(cy).__name__}")
    if not isinstance(size, (int, float)):
        raise TypeError(f"size must be numeric, got {type(size).__name__}")
    if not isinstance(density, int):
        raise TypeError(f"density must be int, got {type(density).__name__}")
    if size <= 0:
        raise ValueError(f"size must be > 0, got {size}")
    if density <= 0:
        raise ValueError(f"density must be > 0, got {density}")

    # Use a higher-resolution polygon for more accurate rejection sampling
    _OUTLINE_RESOLUTION: int = 300
    # Bounding box of the normalized heart: x in [-16, 16], y in [-17, 13]
    _X_MIN: float = -16.0
    _X_MAX: float = 16.0
    _Y_MIN: float = -17.0
    _Y_MAX: float = 13.0
    _MAX_ATTEMPTS_MULTIPLIER: int = 50

    outline_polygon = _heart_outline_polygon(_OUTLINE_RESOLUTION)
    points: list[tuple[float, float, float]] = []
    max_attempts = density * _MAX_ATTEMPTS_MULTIPLIER
    attempts = 0

    while len(points) < density and attempts < max_attempts:
        attempts += 1
        x0 = random.uniform(_X_MIN, _X_MAX)
        y0 = random.uniform(_Y_MIN, _Y_MAX)
        if _point_in_polygon(x0, y0, outline_polygon):
            w = random.random()  # depth weight in [0.0, 1.0]
            px = cx + x0 * size
            py = cy - y0 * size
            points.append((px, py, w))

    return points
