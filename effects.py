"""Visual enhancement utility module for heart animation.

Provides easing functions, multi-color gradient interpolation,
particle size pulsation, glow color overlay, beat scaling, and
other pure functions for visual effects.
"""

import math

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Default rich color palette: deep red -> rose red -> pink -> light pink
DEFAULT_PALETTE: list[tuple[int, int, int]] = [
    (180, 0, 0),      # deep red
    (220, 20, 60),    # rose red (crimson)
    (255, 105, 147),  # pink (hot pink)
    (255, 182, 193),  # light pink
]

# Clamp bounds for easing input
_T_MIN: float = 0.0
_T_MAX: float = 1.0

# Math constant
_TWO_PI: float = 2.0 * math.pi
_HALF_PI: float = math.pi / 2.0

# Color channel bounds
_CHANNEL_MIN: int = 0
_CHANNEL_MAX: int = 255


# ---------------------------------------------------------------------------
# Easing functions
# ---------------------------------------------------------------------------

def easing_out_cubic(t: float) -> float:
    """Cubic ease-out function: decelerates from fast to slow.

    Args:
        t: Normalized time value, clamped internally to [0.0, 1.0].

    Returns:
        Eased float value in [0.0, 1.0].

    Raises:
        TypeError: If t is not a numeric type.
    """
    if not isinstance(t, (int, float)):
        raise TypeError(f"t must be a numeric type, got {type(t).__name__}")
    t_clamped = max(_T_MIN, min(_T_MAX, float(t)))
    return 1.0 - (1.0 - t_clamped) ** 3


def easing_in_out_sine(t: float) -> float:
    """Sine ease-in-out function: smooth acceleration and deceleration.

    Args:
        t: Normalized time value, clamped internally to [0.0, 1.0].

    Returns:
        Eased float value in [0.0, 1.0].

    Raises:
        TypeError: If t is not a numeric type.
    """
    if not isinstance(t, (int, float)):
        raise TypeError(f"t must be a numeric type, got {type(t).__name__}")
    t_clamped = max(_T_MIN, min(_T_MAX, float(t)))
    return -(math.cos(math.pi * t_clamped) - 1.0) / 2.0


# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------

def _clamp_channel(value: float) -> int:
    """Clamp a color channel value to [0, 255] and convert to int.

    Args:
        value: Raw channel value (float).

    Returns:
        Integer in [0, 255].
    """
    return max(_CHANNEL_MIN, min(_CHANNEL_MAX, round(value)))


def lerp_color_rich(
    t: float,
    palette: list[tuple[int, int, int]],
) -> str:
    """Interpolate through a multi-stop color palette.

    Linearly maps t in [0, 1] across the palette stops.
    For example, with 4 stops, t=0 -> stop[0], t=1/3 -> stop[1], etc.

    Args:
        t: Normalized position in [0.0, 1.0], clamped internally.
        palette: List of at least 2 RGB tuples (r, g, b) each in [0, 255].

    Returns:
        Hex color string in '#rrggbb' format.

    Raises:
        TypeError: If t is not numeric or palette entries are invalid.
        ValueError: If palette has fewer than 2 entries.
    """
    if not isinstance(t, (int, float)):
        raise TypeError(f"t must be a numeric type, got {type(t).__name__}")
    if not isinstance(palette, list) or len(palette) < 2:
        raise ValueError("palette must be a list with at least 2 color stops")
    for i, stop in enumerate(palette):
        if not (isinstance(stop, tuple) and len(stop) == 3):
            raise TypeError(f"palette[{i}] must be a tuple of 3 ints, got {stop!r}")

    t_clamped = max(_T_MIN, min(_T_MAX, float(t)))
    num_segments = len(palette) - 1
    # Determine which segment we are in
    segment_index = min(int(t_clamped * num_segments), num_segments - 1)
    segment_t = t_clamped * num_segments - segment_index

    r0, g0, b0 = palette[segment_index]
    r1, g1, b1 = palette[segment_index + 1]

    r = _clamp_channel(r0 + (r1 - r0) * segment_t)
    g = _clamp_channel(g0 + (g1 - g0) * segment_t)
    b = _clamp_channel(b0 + (b1 - b0) * segment_t)

    return f"#{r:02x}{g:02x}{b:02x}"


def glow_color(base_color: str, intensity: float) -> str:
    """Blend a base color toward white by an intensity factor.

    Args:
        base_color: Hex color string in '#rrggbb' format.
        intensity: Blend factor in [0.0, 1.0]; 0 = original, 1 = white.
                   Clamped internally.

    Returns:
        Hex color string in '#rrggbb' format.

    Raises:
        TypeError: If intensity is not numeric.
        ValueError: If base_color is not a valid '#rrggbb' string.
    """
    if not isinstance(intensity, (int, float)):
        raise TypeError(f"intensity must be a numeric type, got {type(intensity).__name__}")
    if not isinstance(base_color, str) or len(base_color) != 7 or base_color[0] != '#':
        raise ValueError(
            f"base_color must be a '#rrggbb' hex string, got {base_color!r}"
        )
    try:
        r0 = int(base_color[1:3], 16)
        g0 = int(base_color[3:5], 16)
        b0 = int(base_color[5:7], 16)
    except ValueError as exc:
        raise ValueError(
            f"base_color contains invalid hex digits: {base_color!r}"
        ) from exc

    intensity_clamped = max(_T_MIN, min(_T_MAX, float(intensity)))
    white = _CHANNEL_MAX

    r = _clamp_channel(r0 + (white - r0) * intensity_clamped)
    g = _clamp_channel(g0 + (white - g0) * intensity_clamped)
    b = _clamp_channel(b0 + (white - b0) * intensity_clamped)

    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Particle / beat utilities
# ---------------------------------------------------------------------------

def particle_size(
    base_r: float,
    frame: int,
    beat_period: int,
    beat_amp: float,
) -> float:
    """Calculate pulsating particle radius driven by a beat cycle.

    Args:
        base_r: Base radius in pixels (must be > 0).
        frame: Current animation frame (non-negative integer).
        beat_period: Number of frames per beat cycle (must be > 0).
        beat_amp: Amplitude of radius oscillation in pixels (>= 0).

    Returns:
        Computed radius as float (>= 0).

    Raises:
        ValueError: If base_r <= 0 or beat_period <= 0 or beat_amp < 0.
        TypeError: If arguments are of incorrect types.
    """
    if not isinstance(base_r, (int, float)):
        raise TypeError(f"base_r must be numeric, got {type(base_r).__name__}")
    if not isinstance(frame, int):
        raise TypeError(f"frame must be int, got {type(frame).__name__}")
    if not isinstance(beat_period, int):
        raise TypeError(f"beat_period must be int, got {type(beat_period).__name__}")
    if not isinstance(beat_amp, (int, float)):
        raise TypeError(f"beat_amp must be numeric, got {type(beat_amp).__name__}")
    if base_r <= 0:
        raise ValueError(f"base_r must be > 0, got {base_r}")
    if beat_period <= 0:
        raise ValueError(f"beat_period must be > 0, got {beat_period}")
    if beat_amp < 0:
        raise ValueError(f"beat_amp must be >= 0, got {beat_amp}")
    if frame < 0:
        raise ValueError(f"frame must be >= 0, got {frame}")

    phase = _TWO_PI * frame / beat_period
    return base_r + beat_amp * math.sin(phase)


def beat_scale(
    frame: int,
    beat_period: int,
    base_size: float,
    beat_amp: float,
) -> float:
    """Calculate the heart scale factor driven by a beat cycle.

    Uses a sine wave to oscillate the scale around base_size.

    Args:
        frame: Current animation frame (non-negative integer).
        beat_period: Number of frames per beat cycle (must be > 0).
        base_size: Base scale factor (must be > 0).
        beat_amp: Amplitude of scale oscillation (>= 0).

    Returns:
        Computed scale factor as float.

    Raises:
        ValueError: If base_size <= 0 or beat_period <= 0 or beat_amp < 0.
        TypeError: If arguments are of incorrect types.
    """
    if not isinstance(frame, int):
        raise TypeError(f"frame must be int, got {type(frame).__name__}")
    if not isinstance(beat_period, int):
        raise TypeError(f"beat_period must be int, got {type(beat_period).__name__}")
    if not isinstance(base_size, (int, float)):
        raise TypeError(f"base_size must be numeric, got {type(base_size).__name__}")
    if not isinstance(beat_amp, (int, float)):
        raise TypeError(f"beat_amp must be numeric, got {type(beat_amp).__name__}")
    if base_size <= 0:
        raise ValueError(f"base_size must be > 0, got {base_size}")
    if beat_period <= 0:
        raise ValueError(f"beat_period must be > 0, got {beat_period}")
    if beat_amp < 0:
        raise ValueError(f"beat_amp must be >= 0, got {beat_amp}")
    if frame < 0:
        raise ValueError(f"frame must be >= 0, got {frame}")

    phase = _TWO_PI * frame / beat_period
    return base_size + beat_amp * math.sin(phase)
