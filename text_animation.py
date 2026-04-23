"""文字动画模块，提供逐字浮现、淡入、上下浮动与光晕闪烁复合动画。

Constants:
    TEXT: 动画默认文本
    CHAR_REVEAL_INTERVAL: 每隔多少帧解锁下一个字符
    GLOW_PERIOD: 光晕闪烁周期（帧数）
    FADE_IN_FRAMES: 每个字符淡入所需帧数
    FLOAT_AMP: Y 轴浮动幅度（像素）
    FLOAT_PERIOD: Y 轴浮动周期（帧数）
    TEXT_TAG: canvas tag 字符串常量
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Optional

from effects import glow_color, lerp_color_rich

# ---------------------------------------------------------------------------
# 模块级常量
# ---------------------------------------------------------------------------

TEXT: str = "I love you fjl"
CHAR_REVEAL_INTERVAL: int = 4
GLOW_PERIOD: int = 40
FADE_IN_FRAMES: int = 12
FLOAT_AMP: float = 3.0
FLOAT_PERIOD: int = 60

TEXT_TAG: str = "text_layer"

# 插值调色板（从黑色过渡到粉色系）
_BLACK: tuple[int, int, int] = (0, 0, 0)
_FADE_PALETTE_DARK: list[tuple[int, int, int]] = [
    (0, 0, 0),
    (80, 0, 20),
    (180, 30, 80),
    (255, 105, 160),
]

# 字符水平间距系数（相对 font_size）
_CHAR_SPACING_FACTOR: float = 0.65


class TextAnimator:
    """管理文字逐字浮现、淡入、上下浮动与光晕闪烁复合动画。

    每隔 CHAR_REVEAL_INTERVAL 帧解锁下一个字符，每个字符独立执行：
    - FADE_IN_FRAMES 帧 alpha 淡入（lerp_color_rich 从黑色过渡到目标色）
    - Y 轴微浮动（sin 函数，幅度 FLOAT_AMP px，周期 FLOAT_PERIOD 帧）
    - 光晕闪烁（每 GLOW_PERIOD 帧一次正弦亮度脉冲）

    字符通过 canvas.create_text 逐个绘制，tag=TEXT_TAG。
    """

    def __init__(
        self,
        canvas: tk.Canvas,
        text: str,
        cx: float,
        cy: float,
        font_family: str,
        font_size: int,
        color_start: str,
        color_end: str,
    ) -> None:
        """初始化 TextAnimator。

        Args:
            canvas: tkinter 画布对象，不能为 None。
            text: 要显示的文本，不能为空字符串。
            cx: 文本中心 X 坐标（像素）。
            cy: 文本中心 Y 坐标（像素）。
            font_family: 字体族名称，不能为空字符串。
            font_size: 字体大小（pt），必须为正整数。
            color_start: 淡入起始颜色（'#rrggbb' 格式）。
            color_end: 淡入结束/目标颜色（'#rrggbb' 格式）。

        Raises:
            TypeError: canvas 不是 tk.Canvas 实例。
            ValueError: text 为空、font_size <= 0 或颜色格式不合法。
        """
        if not isinstance(canvas, tk.Canvas):
            raise TypeError(
                f"canvas 必须是 tk.Canvas 实例，实际类型: {type(canvas)}"
            )
        if not isinstance(text, str) or len(text) == 0:
            raise ValueError("text 不能为空字符串")
        if not isinstance(font_size, int) or font_size <= 0:
            raise ValueError(f"font_size 必须为正整数，实际值: {font_size}")
        if not isinstance(font_family, str) or len(font_family) == 0:
            raise ValueError("font_family 不能为空字符串")
        _validate_color(color_start, "color_start")
        _validate_color(color_end, "color_end")

        self._canvas = canvas
        self._text = text
        self._cx = float(cx)
        self._cy = float(cy)
        self._font_family = font_family
        self._font_size = font_size
        self._color_start = color_start
        self._color_end = color_end

        # 解析目标颜色 RGB，用于淡入终止颜色调色板
        self._target_rgb: tuple[int, int, int] = _parse_hex_color(color_end)

        # 构建淡入调色板：从黑色到目标色
        self._fade_palette: list[tuple[int, int, int]] = [
            _BLACK,
            _lerp_rgb_tuple(_BLACK, self._target_rgb, 0.2),
            _lerp_rgb_tuple(_BLACK, self._target_rgb, 0.6),
            self._target_rgb,
        ]

        # 每个字符的解锁帧（相对 global_frame，在 reset 时设置）
        self._char_unlock_frames: list[int] = []
        # 每个字符是否已完成淡入
        self._char_fade_done: list[bool] = []
        # 动画启动帧（第一次 update 调用时记录）
        self._start_frame: Optional[int] = None
        # 预计算字符 X 坐标（相对 cx 居中）
        self._char_x_positions: list[float] = _compute_char_positions(
            text, cx, font_size, _CHAR_SPACING_FACTOR
        )

        self._initialized: bool = False

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def update(self, global_frame: int) -> None:
        """根据全局帧号更新文字动画并重绘画布上的文字层。

        每帧调用一次。内部先 delete TEXT_TAG，再按各字符状态重绘。

        Args:
            global_frame: 当前全局帧编号（>=0 整数）。

        Raises:
            ValueError: global_frame 为负数。
        """
        if not isinstance(global_frame, int) or global_frame < 0:
            raise ValueError(
                f"global_frame 必须为非负整数，实际值: {global_frame}"
            )

        # 首次调用时记录起始帧并初始化解锁计划
        if self._start_frame is None:
            self._start_frame = global_frame
            self._initialize_unlock_schedule(global_frame)
            self._initialized = True

        # 清除上一帧的文字层
        self._canvas.delete(TEXT_TAG)

        n_chars = len(self._text)
        for i, char in enumerate(self._text):
            unlock_frame = self._char_unlock_frames[i]
            if global_frame < unlock_frame:
                # 尚未解锁，跳过
                continue

            # 该字符已存在的帧数（从解锁帧起算）
            char_age = global_frame - unlock_frame

            # ------ 淡入颜色计算 ------
            if char_age >= FADE_IN_FRAMES:
                fade_t = 1.0
                self._char_fade_done[i] = True
            else:
                fade_t = char_age / FADE_IN_FRAMES

            base_color = lerp_color_rich(fade_t, self._fade_palette)

            # ------ 光晕闪烁 ------
            glow_t = (math.sin(2.0 * math.pi * global_frame / GLOW_PERIOD) + 1.0) / 2.0
            # 光晕强度在淡入完成前减弱，避免黑色字符突然发光
            effective_glow = glow_t * fade_t
            display_color = glow_color(base_color, effective_glow)

            # ------ Y 轴浮动 ------
            float_offset = FLOAT_AMP * math.sin(
                2.0 * math.pi * global_frame / FLOAT_PERIOD
            )
            char_x = self._char_x_positions[i]
            char_y = self._cy + float_offset

            # ------ 绘制字符 ------
            self._canvas.create_text(
                round(char_x),
                round(char_y),
                text=char,
                fill=display_color,
                font=(self._font_family, self._font_size),
                anchor="center",
                tags=(TEXT_TAG,),
            )

    def is_done(self) -> bool:
        """判断所有字符是否已完成淡入动画。

        Returns:
            True 若所有字符均已完成 FADE_IN_FRAMES 帧淡入；否则 False。
        """
        if not self._initialized or len(self._char_fade_done) == 0:
            return False
        return all(self._char_fade_done)

    def reset(self) -> None:
        """重置所有动画状态，以便循环播放。

        清除画布上 TEXT_TAG 所有 item，重置帧计数与解锁计划。
        """
        self._canvas.delete(TEXT_TAG)
        self._start_frame = None
        self._char_unlock_frames = []
        self._char_fade_done = []
        self._initialized = False

    # ------------------------------------------------------------------
    # 私有辅助方法
    # ------------------------------------------------------------------

    def _initialize_unlock_schedule(self, start_frame: int) -> None:
        """根据起始帧计算每个字符的解锁帧号并初始化状态列表。

        Args:
            start_frame: 动画启动时的全局帧号。
        """
        n = len(self._text)
        self._char_unlock_frames = [
            start_frame + i * CHAR_REVEAL_INTERVAL for i in range(n)
        ]
        self._char_fade_done = [False] * n


# ---------------------------------------------------------------------------
# 模块级私有工具函数
# ---------------------------------------------------------------------------

def _validate_color(color: str, param_name: str) -> None:
    """验证颜色字符串是否为合法的 '#rrggbb' 六位十六进制格式。

    Args:
        color: 待验证的颜色字符串。
        param_name: 参数名称，用于错误信息。

    Raises:
        ValueError: 格式不合法时抛出，包含参数名称与实际值。
    """
    if not isinstance(color, str):
        raise ValueError(f"{param_name} 必须是字符串，实际类型: {type(color)}")
    if len(color) != 7 or color[0] != "#":
        raise ValueError(
            f"{param_name} 必须为 '#rrggbb' 格式，实际值: {color!r}"
        )
    try:
        int(color[1:], 16)
    except ValueError:
        raise ValueError(
            f"{param_name} 包含非法十六进制字符，实际值: {color!r}"
        )


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    """将 '#rrggbb' 字符串解析为 (r, g, b) 整数元组。

    Args:
        color: '#rrggbb' 格式的颜色字符串（已通过校验）。

    Returns:
        (r, g, b) 各分量取值范围 [0, 255]。
    """
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    return (r, g, b)


def _lerp_rgb_tuple(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """对两个 RGB 元组做线性插值。

    Args:
        a: 起始 RGB 元组。
        b: 结束 RGB 元组。
        t: 插值系数，自动 clamp 到 [0.0, 1.0]。

    Returns:
        插值后的 RGB 整数元组。
    """
    t = max(0.0, min(1.0, t))
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def _compute_char_positions(
    text: str,
    cx: float,
    font_size: int,
    spacing_factor: float,
) -> list[float]:
    """预计算文本中每个字符的水平居中 X 坐标。

    按等间距方式排列字符，整体以 cx 为中心。

    Args:
        text: 要显示的文本字符串。
        cx: 文本整体中心 X 坐标。
        font_size: 字体大小（pt），用于估算字符宽度。
        spacing_factor: 字符间距相对 font_size 的系数（>0）。

    Returns:
        每个字符对应的 X 坐标列表，长度与 text 相同。
    """
    n = len(text)
    if n == 0:
        return []
    char_width = font_size * spacing_factor
    total_width = char_width * (n - 1)
    start_x = cx - total_width / 2.0
    return [start_x + i * char_width for i in range(n)]
