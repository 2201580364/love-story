"""Visual enhancement utility module for heart animation.

Provides easing functions, multi-color gradient interpolation,
particle size pulsation, glow color overlay, and beat scaling.
All functions are pure with no side effects.
"""

import math

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Palette index boundaries
_PALETTE_MIN_LEN: int = 2

# Hex color string constants
_HEX_PREFIX: str = '#'
_HEX_BODY_LEN: int = 6

# Bit-shift amounts for channel extraction from 24-bit int
_RED_SHIFT: int = 16
_GREEN_SHIFT: int = 8
_CHANNEL_MASK: int = 0xFF

# Minimum positive scale to prevent zero-size drawing artifacts
_MIN_SCALE: float = 1e-3

# Clamping bounds for normalized time parameter
_T_MIN: float = 0.0
_T_MAX: float = 1.0

# Intensity bounds
_INTENSITY_MIN: float = 0.0
_INTENSITY_MAX: float = 1.0

# Two-pi constant
_TWO_PI: float = 2.0 * math.pi

# Maximum channel value
_CHANNEL_MAX: int = 255


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _require_float(value: object, name: str) -> float:
    """Validate that *value* is a real float/int (not bool) and return it.

    Args:
        value: The value to validate.
        name: Parameter name used in error messages.

    Returns:
        The value cast to float.

    Raises:
        TypeError: If value is bool or not numeric.
    """
    if isinstance(value, bool):
        raise TypeError(f'{name} must be a float, got bool: {value!r}')
    if not isinstance(value, (int, float)):
        raise TypeError(f'{name} must be a float, got {type(value).__name__}: {value!r}')
    return float(value)


def _require_int(value: object, name: str) -> int:
    """Validate that *value* is a plain int (not bool) and return it.

    Args:
        value: The value to validate.
        name: Parameter name used in error messages.

    Returns:
        The validated int value.

    Raises:
        TypeError: If value is bool or not an int.
    """
    if isinstance(value, bool):
        raise TypeError(f'{name} must be an int, got bool: {value!r}')
    if not isinstance(value, int):
        raise TypeError(f'{name} must be an int, got {type(value).__name__}: {value!r}')
    return value


def _clamp(t: float, lo: float, hi: float) -> float:
    """Clamp *t* to the closed interval [lo, hi].

    Args:
        t: Value to clamp.
        lo: Lower bound.
        hi: Upper bound.

    Returns:
        Clamped value.
    """
    return max(lo, min(hi, t))


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    """Parse a '#rrggbb' hex color string into (r, g, b) integer components.

    Args:
        color: Hex color string in '#rrggbb' format (lowercase or uppercase).

    Returns:
        Tuple of (r, g, b) each in [0, 255].

    Raises:
        TypeError: If color is not a str.
        ValueError: If color is not in '#rrggbb' format.
    """
    if not isinstance(color, str):
        raise TypeError(f'color must be a str, got {type(color).__name__}: {color!r}')
    if len(color) != _HEX_BODY_LEN + len(_HEX_PREFIX) or not color.startswith(_HEX_PREFIX):
        raise ValueError(
            f'color must be in "#rrggbb" format, got {color!r}'
        )
    hex_body = color[len(_HEX_PREFIX):]
    try:
        val = int(hex_body, 16)
    except ValueError:
        raise ValueError(f'color contains non-hex characters: {color!r}')
    r = (val >> _RED_SHIFT) & _CHANNEL_MASK
    g = (val >> _GREEN_SHIFT) & _CHANNEL_MASK
    b = val & _CHANNEL_MASK
    return r, g, b


# ---------------------------------------------------------------------------
# Public easing functions
# ---------------------------------------------------------------------------

def easing_out_cubic(t: float) -> float:
    """Cubic ease-out function: fast start, slow end.

    Args:
        t: Normalized time in [0.0, 1.0]. Values outside this range are
            clamped before computation.

    Returns:
        Eased value in [0.0, 1.0].

    Raises:
        TypeError: If t is not a numeric type (or is bool).
    """
    t = _require_float(t, 't')
    t = _clamp(t, _T_MIN, _T_MAX)
    return 1.0 - (1.0 - t) ** 3


def easing_in_out_sine(t: float) -> float:
    """Sine-based ease-in-out function: smooth acceleration and deceleration.

    Args:
        t: Normalized time in [0.0, 1.0]. Values outside this range are
            clamped before computation.

    Returns:
        Eased value in [0.0, 1.0].

    Raises:
        TypeError: If t is not a numeric type (or is bool).
    """
    t = _require_float(t, 't')
    t = _clamp(t, _T_MIN, _T_MAX)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


# ---------------------------------------------------------------------------
# Color functions
# ---------------------------------------------------------------------------

def lerp_color_rich(
    t: float,
    palette: list[tuple[int, int, int]],
) -> str:
    """Interpolate across a multi-stop color palette.

    Maps the normalized parameter *t* to a color by linearly interpolating
    between adjacent palette stops.  The default palette progresses from
    deep red → rose red → pink → light pink.

    Args:
        t: Normalized position in [0.0, 1.0]. Clamped automatically.
        palette: Ordered list of at least 2 RGB stops, each a
            ``tuple[int, int, int]`` with channels in [0, 255].
            Must be a ``list`` (not tuple or other sequence).
            Bool channel values are rejected.

    Returns:
        Interpolated color as a lowercase ``'#rrggbb'`` hex string.

    Raises:
        TypeError: If t is bool or non-numeric, or if palette is not a list.
        ValueError: If palette has fewer than 2 stops, any stop is not a
            3-tuple, or any channel value is out of [0, 255] or is bool.
    """
    t = _require_float(t, 't')
    t = _clamp(t, _T_MIN, _T_MAX)

    if not isinstance(palette, list):
        raise TypeError(
            f'palette must be a list, got type={type(palette).__name__}, value={palette!r}'
        )
    if len(palette) < _PALETTE_MIN_LEN:
        raise ValueError(
            f'palette must have at least {_PALETTE_MIN_LEN} stops, '
            f'got {len(palette)}'
        )

    # Validate each stop
    for i, stop in enumerate(palette):
        if not isinstance(stop, tuple) or len(stop) != 3:
            raise ValueError(
                f'palette[{i}] must be a tuple of 3 ints, got {stop!r}'
            )
        r, g, b = stop
        if not all(
            isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= _CHANNEL_MAX
            for c in (r, g, b)
        ):
            raise ValueError(
                f'palette[{i}] channels must be int in [0, {_CHANNEL_MAX}], got {stop!r}'
            )

    num_segments = len(palette) - 1
    # Map t to segment index and local parameter
    scaled = t * num_segments
    segment_idx = int(_clamp(math.floor(scaled), 0, num_segments - 1))
    local_t = scaled - segment_idx  # in [0.0, 1.0)

    r0, g0, b0 = palette[segment_idx]
    r1, g1, b1 = palette[segment_idx + 1]

    r_out = round(r0 + (r1 - r0) * local_t)
    g_out = round(g0 + (g1 - g0) * local_t)
    b_out = round(b0 + (b1 - b0) * local_t)

    # Clamp to valid range after rounding
    r_out = int(_clamp(r_out, 0, _CHANNEL_MAX))
    g_out = int(_clamp(g_out, 0, _CHANNEL_MAX))
    b_out = int(_clamp(b_out, 0, _CHANNEL_MAX))

    return f'#{r_out:02x}{g_out:02x}{b_out:02x}'


def glow_color(base_color: str, intensity: float) -> str:
    """Blend *base_color* towards white according to *intensity*.

    A higher intensity brightens the color toward ``#ffffff``.

    Args:
        base_color: Source color in ``'#rrggbb'`` format.
        intensity: Blend factor in [0.0, 1.0]; clamped automatically.
            0.0 returns *base_color* unchanged, 1.0 returns white.

    Returns:
        Resulting color as a lowercase ``'#rrggbb'`` hex string.

    Raises:
        TypeError: If base_color is not a str, or intensity is bool/non-numeric.
        ValueError: If base_color is not in valid ``'#rrggbb'`` format.
    """
    intensity = _require_float(intensity, 'intensity')
    intensity = _clamp(intensity, _INTENSITY_MIN, _INTENSITY_MAX)

    r, g, b = _parse_hex_color(base_color)

    r_out = round(r + (_CHANNEL_MAX - r) * intensity)
    g_out = round(g + (_CHANNEL_MAX - g) * intensity)
    b_out = round(b + (_CHANNEL_MAX - b) * intensity)

    r_out = int(_clamp(r_out, 0, _CHANNEL_MAX))
    g_out = int(_clamp(g_out, 0, _CHANNEL_MAX))
    b_out = int(_clamp(b_out, 0, _CHANNEL_MAX))

    return f'#{r_out:02x}{g_out:02x}{b_out:02x}'


# ---------------------------------------------------------------------------
# Animation / particle functions
# ---------------------------------------------------------------------------

def particle_size(
    base_r: float,
    frame: int,
    beat_period: int,
    beat_amp: float,
) -> float:
    """Compute the pulsating radius of a particle for the given frame.

    The radius oscillates sinusoidally around *base_r* with amplitude
    *beat_amp* at the frequency defined by *beat_period*.

    Args:
        base_r: Base (resting) particle radius in pixels. Must be > 0.
        frame: Current animation frame index (>= 0).
        beat_period: Number of frames per beat cycle. Must be > 0.
        beat_amp: Amplitude of the pulsation in pixels. Must be >= 0.
            For a positive radius at all frames, beat_amp should be < base_r.

    Returns:
        Particle radius for the current frame, always >= _MIN_SCALE.

    Raises:
        TypeError: If any numeric argument is bool.
        ValueError: If base_r <= 0, beat_period <= 0, or beat_amp < 0.
    """
    base_r = _require_float(base_r, 'base_r')
    frame = _require_int(frame, 'frame')
    beat_period = _require_int(beat_period, 'beat_period')
    beat_amp = _require_float(beat_amp, 'beat_amp')

    if base_r <= 0.0:
        raise ValueError(f'base_r must be > 0, got {base_r!r}')
    if beat_period <= 0:
        raise ValueError(f'beat_period must be > 0, got {beat_period!r}')
    if beat_amp < 0.0:
        raise ValueError(f'beat_amp must be >= 0, got {beat_amp!r}')

    phase = _TWO_PI * frame / beat_period
    radius = base_r + beat_amp * math.sin(phase)
    return max(_MIN_SCALE, radius)


def beat_scale(
    frame: int,
    beat_period: int,
    base_size: float,
    beat_amp: float,
) -> float:
    """Compute the scaled heart size for the given frame driven by a heartbeat.

    The scale factor oscillates sinusoidally around *base_size* with
    relative amplitude *beat_amp*.

    Args:
        frame: Current animation frame index (>= 0).
        beat_period: Number of frames per beat cycle. Must be > 0.
        base_size: Base (resting) heart size. Must be > 0.
        beat_amp: Relative amplitude of the heartbeat oscillation. Must be
            >= 0. To guarantee a strictly positive return value at all frames,
            beat_amp must be < 1.0; when beat_amp >= 1.0 and sin(phase) = -1
            the computed scale reaches base_size * (1 - beat_amp) <= 0 and
            will be clamped to _MIN_SCALE (1e-3), which may cause visual
            artifacts (zero-size heart) or ValueError in downstream callers
            that require size > 0. Keep beat_amp in [0.0, 1.0) for safe use.

    Returns:
        Heart size for the current frame, always >= _MIN_SCALE.

    Raises:
        TypeError: If any numeric argument is bool.
        ValueError: If beat_period <= 0, base_size <= 0, or beat_amp < 0.
    """
    frame = _require_int(frame, 'frame')
    beat_period = _require_int(beat_period, 'beat_period')
    base_size = _require_float(base_size, 'base_size')
    beat_amp = _require_float(beat_amp, 'beat_amp')

    if beat_period <= 0:
        raise ValueError(f'beat_period must be > 0, got {beat_period!r}')
    if base_size <= 0.0:
        raise ValueError(f'base_size must be > 0, got {base_size!r}')
    if beat_amp < 0.0:
        raise ValueError(f'beat_amp must be >= 0, got {beat_amp!r}')

    phase = _TWO_PI * frame / beat_period
    scale = base_size * (1.0 + beat_amp * math.sin(phase))
    return max(_MIN_SCALE, scale)
