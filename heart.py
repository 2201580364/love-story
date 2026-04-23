"""Heart shape geometry utilities.

Provides outline polygon generation, point-in-polygon testing,
and filled heart scatter point generation.
"""

import math
import random

# ---------------------------------------------------------------------------
# Heart parametric equation constants
# ---------------------------------------------------------------------------
_HEART_A: float = 16.0   # x amplitude coefficient
_HEART_B: float = 13.0   # primary y cosine coefficient
_HEART_C1: float = 5.0   # second harmonic y coefficient
_HEART_C2: float = 2.0   # third harmonic y coefficient
_HEART_C3: float = 1.0   # fourth harmonic y coefficient
_HEART_C4: float = 4.0   # fourth harmonic multiplier

# Bounding box for rejection sampling (in normalised heart coords)
_SAMPLE_X_MIN: float = -16.0
_SAMPLE_X_MAX: float = 16.0
_SAMPLE_Y_MIN: float = -17.0
_SAMPLE_Y_MAX: float = 13.0

# Safety multiplier for max rejection-sampling attempts relative to density
_MAX_ATTEMPTS_FACTOR: int = 50

# Outline polygon resolution used internally for filled-point generation
_OUTLINE_RESOLUTION: int = 300

# Two-pi constant
_TWO_PI: float = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _heart_outline_polygon(num_points: int = 200) -> list[tuple[float, float]]:
    """Generate normalized heart outline polygon (no offset, no scaling).

    Args:
        num_points: Number of vertices in the outline polygon.

    Returns:
        List of (x, y) tuples in normalised heart coordinates.
    """
    polygon = []
    for i in range(num_points):
        t = _TWO_PI * i / num_points
        x = _HEART_A * math.sin(t) ** 3
        y = (
            _HEART_B * math.cos(t)
            - _HEART_C1 * math.cos(2 * t)
            - _HEART_C2 * math.cos(3 * t)
            - _HEART_C3 * math.cos(_HEART_C4 * t)
        )
        polygon.append((x, y))
    return polygon


def _point_in_polygon(px: float, py: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray casting algorithm to test if point (px, py) is inside polygon.

    Args:
        px: X coordinate of the point to test.
        py: Y coordinate of the point to test.
        polygon: List of (x, y) vertices defining the polygon boundary.

    Returns:
        True if the point is inside the polygon, False otherwise.

    Note:
        Points that lie exactly on a polygon edge have undefined behavior
        (may return True or False).  This implementation is intended for
        Monte Carlo sampling and is not suitable for exact boundary
        classification.
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
# Public functions
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
        size: Scale factor for the heart. Must be > 0.
        num_points: Number of outline points to generate. Must be > 0.

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
        t = _TWO_PI * i / num_points
        x = _HEART_A * math.sin(t) ** 3
        y = (
            _HEART_B * math.cos(t)
            - _HEART_C1 * math.cos(2 * t)
            - _HEART_C2 * math.cos(3 * t)
            - _HEART_C3 * math.cos(_HEART_C4 * t)
        )
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
        size: Scale factor for the heart. Must be > 0.
        density: Number of fill points to generate. Must be > 0.

    Returns:
        List of (x, y) tuples representing the filled heart scatter points.

    Raises:
        ValueError: If size <= 0 or density <= 0.
    """
    if size <= 0:
        raise ValueError("size must be > 0")
    if density <= 0:
        raise ValueError("density must be > 0")

    outline_polygon = _heart_outline_polygon(_OUTLINE_RESOLUTION)
    points = []
    max_attempts = density * _MAX_ATTEMPTS_FACTOR
    attempts = 0

    while len(points) < density and attempts < max_attempts:
        attempts += 1
        x0 = random.uniform(_SAMPLE_X_MIN, _SAMPLE_X_MAX)
        y0 = random.uniform(_SAMPLE_Y_MIN, _SAMPLE_Y_MAX)
        if _point_in_polygon(x0, y0, outline_polygon):
            points.append((cx + x0 * size, cy - y0 * size))

    return points


def filled_heart_points_v2(
    cx: float,
    cy: float,
    size: float,
    density: int = 1200,
    rng: random.Random | None = None,
) -> list[tuple[float, float, float]]:
    """Return filled heart scatter points with per-point depth weight.

    Each returned point carries a random depth weight *w* in [0.0, 1.0]
    suitable for colour layering: higher *w* → brighter / more saturated
    appearance in the rendering layer.

    Args:
        cx: X coordinate of the centre of the heart.
        cy: Y coordinate of the centre of the heart.
        size: Scale factor for the heart. Must be > 0.
        density: Target number of fill points to generate. Must be > 0.
        rng: Optional ``random.Random`` instance to use for sampling.
            If None, the module-level random state is used.

    Returns:
        List of ``(x, y, w)`` tuples where *x*, *y* are canvas coordinates
        and *w* ∈ [0.0, 1.0] is the depth weight.

    Raises:
        ValueError: If size <= 0 or density <= 0.
        TypeError: If rng is provided but is not a ``random.Random`` instance.

    Note:
        This function is not thread-safe when *rng* is None, because it falls
        back to the module-level random state which is shared across threads.
        For concurrent use, create and pass a dedicated instance::

            local_rng = random.Random()
            pts = filled_heart_points_v2(cx, cy, size, rng=local_rng)
    """
    if size <= 0:
        raise ValueError(f'size must be > 0, got {size!r}')
    if density <= 0:
        raise ValueError(f'density must be > 0, got {density!r}')
    if rng is not None and not isinstance(rng, random.Random):
        raise TypeError(
            f'rng must be a random.Random instance or None, '
            f'got {type(rng).__name__}: {rng!r}'
        )

    _rng = rng if rng is not None else random

    outline_polygon = _heart_outline_polygon(_OUTLINE_RESOLUTION)
    points: list[tuple[float, float, float]] = []
    max_attempts = density * _MAX_ATTEMPTS_FACTOR
    attempts = 0

    while len(points) < density and attempts < max_attempts:
        attempts += 1
        x0 = _rng.uniform(_SAMPLE_X_MIN, _SAMPLE_X_MAX)
        y0 = _rng.uniform(_SAMPLE_Y_MIN, _SAMPLE_Y_MAX)
        if _point_in_polygon(x0, y0, outline_polygon):
            w = _rng.random()
            points.append((cx + x0 * size, cy - y0 * size, w))

    return points
