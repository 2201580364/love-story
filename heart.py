import math
import random


def _heart_outline_polygon(num_points: int = 200) -> list[tuple[float, float]]:
    """Generate normalized heart outline polygon (no offset, no scaling)."""
    polygon = []
    for i in range(num_points):
        t = 2 * math.pi * i / num_points
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        polygon.append((x, y))
    return polygon


def _point_in_polygon(px: float, py: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray casting algorithm to test if point (px, py) is inside polygon."""
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
