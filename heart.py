"""Heart shape geometry utilities.

Provides parametric heart outline generation, polygon point-in-polygon
testing, and filled heart scatter-point generation (standard and v2 with
depth-weight per point).
"""

import math
import random
import warnings

# ---------------------------------------------------------------------------
# Module-level constants (shared by filled_heart_points and filled_heart_points_v2)
# ---------------------------------------------------------------------------

_OUTLINE_RESOLUTION: int = 300
_HEART_X_MIN: float = -16.0
_HEART_X_MAX: float = 16.0
_HEART_Y_MIN: float = -17.0
_HEART_Y_MAX: float = 13.0
_MAX_ATTEMPTS_MULTIPLIER: int = 50


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _heart_outline_polygon(num_points: int = 200) -> list[tuple[float, float]]:
    """Generate normalized heart outline polygon (no offset, no scaling).

    Args:
        num_points: Number of vertices in the polygon.

    Returns:
        List of (x, y) tuples in normalised heart coordinates.
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
        px: X coordinate of the test point.
        py: Y coordinate of the test point.
        polygon: List of (x, y) vertices.

    Returns:
        True if (px, py) is inside *polygon*, False otherwise.
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def heart_points(
    cx: float,
    cy: float,
    size: float,
    num_points: int = 200,
) -> list[tuple[float, float]]:
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
        raise ValueError('size must be > 0')
    if num_points <= 0:
        raise ValueError('num_points must be > 0')

    points: list[tuple[float, float]] = []
    for i in range(num_points):
        t = 2 * math.pi * i / num_points
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((cx + x * size, cy - y * size))
    return points


def filled_heart_points(
    cx: float,
    cy: float,
    size: float,
    density: int = 800,
) -> list[tuple[float, float]]:
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
        raise ValueError('size must be > 0')
    if density <= 0:
        raise ValueError('density must be > 0')

    outline_polygon = _heart_outline_polygon(_OUTLINE_RESOLUTION)
    points: list[tuple[float, float]] = []
    max_attempts = density * _MAX_ATTEMPTS_MULTIPLIER
    attempts = 0

    while len(points) < density and attempts < max_attempts:
        attempts += 1
        x0 = random.uniform(_HEART_X_MIN, _HEART_X_MAX)
        y0 = random.uniform(_HEART_Y_MIN, _HEART_Y_MAX)
        if _point_in_polygon(x0, y0, outline_polygon):
            points.append((cx + x0 * size, cy - y0 * size))

    return points


def filled_heart_points_v2(
    cx: float,
    cy: float,
    size: float,
    density: int = 1200,
) -> list[tuple[float, float, float]]:
    """Return filled heart scatter points, each with a random depth weight.

    Each returned point is a 3-tuple (x, y, w) where *w* ∈ [0, 1] is a
    random depth weight used for colour layering: higher *w* values map to
    brighter / lighter pink shades.

    Args:
        cx: X coordinate of the center offset.
        cy: Y coordinate of the center offset.
        size: Scale factor for the heart (must be > 0).
        density: Target number of fill points to generate (must be > 0,
                 not bool).

    Returns:
        List of (x, y, w) tuples where x, y are canvas coordinates and
        w ∈ [0.0, 1.0] is the depth weight.

    Raises:
        TypeError: If *density* is a bool.
        ValueError: If *size* <= 0 or *density* <= 0.

    Warns:
        RuntimeWarning: If fewer than *density* points could be generated
                        within the maximum number of attempts (e.g. when
                        *size* is very small or *density* is very large).
    """
    if isinstance(density, bool):
        raise TypeError(
            f'density must be int (not bool), got {type(density).__name__!r}'
        )
    if not isinstance(density, int):
        raise TypeError(
            f'density must be int, got {type(density).__name__!r}'
        )
    if size <= 0:
        raise ValueError(f'size must be > 0, got {size!r}')
    if density <= 0:
        raise ValueError(f'density must be > 0, got {density!r}')

    outline_polygon = _heart_outline_polygon(_OUTLINE_RESOLUTION)
    points: list[tuple[float, float, float]] = []
    max_attempts = density * _MAX_ATTEMPTS_MULTIPLIER
    attempts = 0

    while len(points) < density and attempts < max_attempts:
        attempts += 1
        x0 = random.uniform(_HEART_X_MIN, _HEART_X_MAX)
        y0 = random.uniform(_HEART_Y_MIN, _HEART_Y_MAX)
        if _point_in_polygon(x0, y0, outline_polygon):
            w = random.random()  # depth weight ∈ [0, 1]
            points.append((cx + x0 * size, cy - y0 * size, w))

    if len(points) < density:
        warnings.warn(
            f'filled_heart_points_v2: generated {len(points)}/{density} points '
            f'after {max_attempts} attempts. '
            f'Consider reducing density or increasing size.',
            RuntimeWarning,
            stacklevel=2,
        )

    return points
