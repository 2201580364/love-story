"""Visual enhancement utilities for the heart animation.

Provides easing functions, multi-stop color interpolation, particle size
pulsation, glow color blending, beat scaling, and re-exports
filled_heart_points_v2 from heart.py so that downstream modules can import
everything from a single namespace.

All functions are pure (no side-effects, no global mutable state).
"""

import math
import re

# ---------------------------------------------------------------------------
# Re-export from heart module so callers can do: from effects import ...
# ---------------------------------------------------------------------------
from heart import filled_heart_points_v2 as filled_heart_points_v2  # noqa: F401

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Canvas layer tag constants – all modules must import from here to stay in sync.
HEART_TAG: str = 'heart_layer'
TEXT_TAG: str = 'text_layer'

# Default rich colour palette: dark-red → rose-red → pink → light-pink
DEFAULT_PALETTE: list[tuple[int, int, int]] = [
    (139, 0, 0),    # dark red
    (220, 20, 60),  # crimson / rose-red
    (255, 105, 180),  # hot pink
    (255, 182, 193),  # light pink
]

# Compiled regex for hex colour validation
_HEX_COLOR_RE: re.Pattern[str] = re.compile(r'^#[0-9a-fA-F]{6}$')

# Clamp boundaries for normalised time parameter
_T_MIN: float = 0.0
_T_MAX: float = 1.0

# ---------------------------------------------------------------------------
# Internal helper validators
# ---------------------------------------------------------------------------


def _require_finite(val: float, name: str) -> None:
    """Raise ValueError if *val* is not a finite real number (NaN or Inf).

    Args:
        val: The value to check.
        name: Parameter name used in the error message.

    Raises:
        ValueError: If *val* is NaN or infinite.
    """
    if not math.isfinite(val):
        raise ValueError(f'{name} must be a finite number, got {val!r}')


def _require_int(val: object, name: str) -> None:
    """Raise TypeError if *val* is not a plain int (bool is rejected).

    Args:
        val: The value to check.
        name: Parameter name used in the error message.

    Raises:
        TypeError: If *val* is not an int, or is a bool.
    """
    if not isinstance(val, int) or isinstance(val, bool):
        raise TypeError(
            f'{name} must be int (not bool or other type), '
            f'got {type(val).__name__!r}'
        )


def _clamp(value: float, lo: float, hi: float) -> float:
    """Return *value* clamped to the closed interval [lo, hi].

    Args:
        value: The value to clamp.
        lo: Lower bound.
        hi: Upper bound.

    Returns:
        Clamped float value.
    """
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _clamp_channel(channel: float) -> int:
    """Clamp a colour channel to [0, 255] and return as int.

    Args:
        channel: Raw channel value (may be fractional).

    Returns:
        Integer channel value in [0, 255].
    """
    return int(_clamp(channel, 0.0, 255.0))


# ---------------------------------------------------------------------------
# Easing functions
# ---------------------------------------------------------------------------


def easing_out_cubic(t: float) -> float:
    """Cubic ease-out: fast start, slow finish.

    Args:
        t: Normalised time in [0.0, 1.0].  Values outside this range are
           clamped.  NaN / Inf are rejected.

    Returns:
        Eased value in [0.0, 1.0].

    Raises:
        ValueError: If *t* is NaN or infinite.
    """
    _require_finite(t, 't')
    t = _clamp(t, _T_MIN, _T_MAX)
    return 1.0 - (1.0 - t) ** 3


def easing_in_out_sine(t: float) -> float:
    """Sine ease-in-out: smooth acceleration and deceleration.

    Args:
        t: Normalised time in [0.0, 1.0].  Values outside this range are
           clamped.  NaN / Inf are rejected.

    Returns:
        Eased value in [0.0, 1.0].

    Raises:
        ValueError: If *t* is NaN or infinite.
    """
    _require_finite(t, 't')
    t = _clamp(t, _T_MIN, _T_MAX)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


# ---------------------------------------------------------------------------
# Colour utilities
# ---------------------------------------------------------------------------


def lerp_color_rich(
    t: float,
    palette: list[tuple[int, int, int]],
) -> str:
    """Interpolate a colour from a multi-stop palette.

    The palette stops are distributed evenly across [0, 1].  *t* is clamped
    to [0, 1] before interpolation.

    Args:
        t: Normalised position in [0.0, 1.0].
        palette: List of at least 2 RGB tuples, each channel in [0, 255].

    Returns:
        Hex colour string in '#rrggbb' format.

    Raises:
        ValueError: If *t* is NaN / Inf, or palette has fewer than 2 stops,
                    or any channel value is outside [0, 255].
        TypeError: If palette elements are not 3-tuples of int.
    """
    _require_finite(t, 't')
    if not isinstance(palette, list) or len(palette) < 2:
        raise ValueError(
            f'palette must be a list of at least 2 colour stops, '
            f'got {len(palette) if isinstance(palette, list) else type(palette).__name__!r}'
        )
    for i, stop in enumerate(palette):
        if not (isinstance(stop, tuple) and len(stop) == 3):
            raise TypeError(
                f'palette[{i}] must be a 3-tuple of int, got {stop!r}'
            )
        r, g, b = stop
        if not all(isinstance(c, int) and 0 <= c <= 255 for c in (r, g, b)):
            raise ValueError(
                f'palette[{i}] channels must be int in [0, 255], got {stop!r}'
            )

    t = _clamp(t, _T_MIN, _T_MAX)
    num_segments = len(palette) - 1
    # Map t to segment index and local position
    scaled = t * num_segments
    idx = int(scaled)
    if idx >= num_segments:
        idx = num_segments - 1
    local_t = scaled - idx

    r0, g0, b0 = palette[idx]
    r1, g1, b1 = palette[idx + 1]

    r = _clamp_channel(r0 + (r1 - r0) * local_t)
    g = _clamp_channel(g0 + (g1 - g0) * local_t)
    b = _clamp_channel(b0 + (b1 - b0) * local_t)
    return f'#{r:02x}{g:02x}{b:02x}'


def glow_color(base_color: str, intensity: float) -> str:
    """Blend *base_color* towards white by *intensity* to simulate a glow.

    Args:
        base_color: Hex colour string in '#rrggbb' format (case-insensitive).
        intensity: Blend factor towards white in [0.0, 1.0].
                   0.0 → original colour, 1.0 → white (#ffffff).
                   Values are clamped to [0, 1].  NaN / Inf are rejected.

    Returns:
        Hex colour string in '#rrggbb' format.

    Raises:
        ValueError: If *base_color* is not a valid hex colour string, or
                    *intensity* is NaN / Inf.
    """
    if not isinstance(base_color, str) or not _HEX_COLOR_RE.match(base_color):
        raise ValueError(
            f'base_color must be a valid hex colour string like #rrggbb, '
            f'got {base_color!r}'
        )
    _require_finite(intensity, 'intensity')
    intensity = _clamp(intensity, _T_MIN, _T_MAX)

    hex_body = base_color.lstrip('#')
    r = int(hex_body[0:2], 16)
    g = int(hex_body[2:4], 16)
    b = int(hex_body[4:6], 16)

    r = _clamp_channel(r + (255 - r) * intensity)
    g = _clamp_channel(g + (255 - g) * intensity)
    b = _clamp_channel(b + (255 - b) * intensity)
    return f'#{r:02x}{g:02x}{b:02x}'


# ---------------------------------------------------------------------------
# Animation helpers
# ---------------------------------------------------------------------------


def particle_size(
    base_r: float,
    frame: int,
    beat_period: int,
    beat_amp: float,
) -> float:
    """Compute the pulsating radius of a particle for the given frame.

    Args:
        base_r: Base radius in pixels (> 0).
        frame: Current animation frame (>= 0, not bool).
        beat_period: Number of frames per heartbeat cycle (> 0, not bool).
        beat_amp: Amplitude of size pulsation in pixels (>= 0).

    Returns:
        Computed radius as float (>= 0).

    Raises:
        TypeError: If *frame* or *beat_period* are bool or non-int.
        ValueError: If any float argument is NaN / Inf, or *base_r* <= 0,
                    or *beat_period* <= 0, or *beat_amp* < 0.
    """
    _require_int(frame, 'frame')
    _require_int(beat_period, 'beat_period')
    _require_finite(base_r, 'base_r')
    _require_finite(beat_amp, 'beat_amp')
    if base_r <= 0:
        raise ValueError(f'base_r must be > 0, got {base_r!r}')
    if beat_period <= 0:
        raise ValueError(f'beat_period must be > 0, got {beat_period!r}')
    if beat_amp < 0:
        raise ValueError(f'beat_amp must be >= 0, got {beat_amp!r}')
    if frame < 0:
        raise ValueError(f'frame must be >= 0, got {frame!r}')

    phase = 2.0 * math.pi * frame / beat_period
    result = base_r + beat_amp * math.sin(phase)
    return max(0.0, result)


def beat_scale(
    frame: int,
    beat_period: int,
    base_size: float,
    beat_amp: float,
) -> float:
    """Compute the overall scale factor of the heart for the given frame.

    Args:
        frame: Current animation frame (>= 0, not bool).
        beat_period: Number of frames per heartbeat cycle (> 0, not bool).
        base_size: Base scale factor (> 0).
        beat_amp: Fractional amplitude of the heartbeat pulsation (>= 0).
                  The scale oscillates between base_size*(1-beat_amp) and
                  base_size*(1+beat_amp).

    Returns:
        Computed scale factor as float (>= 0).

    Raises:
        TypeError: If *frame* or *beat_period* are bool or non-int.
        ValueError: If any float argument is NaN / Inf, or *base_size* <= 0,
                    or *beat_period* <= 0, or *beat_amp* < 0.
    """
    _require_int(frame, 'frame')
    _require_int(beat_period, 'beat_period')
    _require_finite(base_size, 'base_size')
    _require_finite(beat_amp, 'beat_amp')
    if base_size <= 0:
        raise ValueError(f'base_size must be > 0, got {base_size!r}')
    if beat_period <= 0:
        raise ValueError(f'beat_period must be > 0, got {beat_period!r}')
    if beat_amp < 0:
        raise ValueError(f'beat_amp must be >= 0, got {beat_amp!r}')
    if frame < 0:
        raise ValueError(f'frame must be >= 0, got {frame!r}')

    phase = 2.0 * math.pi * frame / beat_period
    scale = base_size * (1.0 + beat_amp * math.sin(phase))
    return max(0.0, scale)


# ---------------------------------------------------------------------------
# Public API list
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    'HEART_TAG',
    'TEXT_TAG',
    'DEFAULT_PALETTE',
    # Easing
    'easing_out_cubic',
    'easing_in_out_sine',
    # Colour
    'lerp_color_rich',
    'glow_color',
    # Animation
    'particle_size',
    'beat_scale',
    # Re-exported from heart
    'filled_heart_points_v2',
]
