"""文字动画模块 text_animation.py。

提供 TextAnimator 类，管理「I love you fjl」逐字浮现+淡入+上下浮动+光晕闪烁复合动画。
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Optional

# ---------------------------------------------------------------------------
# 模块级公开常量
# ---------------------------------------------------------------------------
TEXT: str = "I love you fjl"
CHAR_REVEAL_INTERVAL: int = 4
GLOW_PERIOD: int = 40
FADE_IN_FRAMES: int = 12
FLOAT_AMP: float = 3.0
FLOAT_PERIOD: int = 60

# ---------------------------------------------------------------------------
# 模块级 canvas tag 常量
# ---------------------------------------------------------------------------
TEXT_TAG: str = "text_layer"

# ---------------------------------------------------------------------------
# 私有内部常量
# ---------------------------------------------------------------------------
_CHAR_SPACING_FACTOR: float = 0.65   # 普通字符宽度 = font_size * 该系数
_SPACE_SPACING_FACTOR: float = 0.35  # 空格字符宽度 = font_size * 该系数

_FADE_STOP_LOW: float = 0.2    # 渐变调色板第二节点插值 t 值
_FADE_STOP_HIGH: float = 0.6   # 渐变调色板第三节点插值 t 值

# 光晕对淡入颜色的最大叠加权重
_GLOW_BLEND_FACTOR: float = 0.3

_TWO_PI: float = 2.0 * math.pi

# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """将 value 限制在 [lo, hi] 区间内。

    Args:
        value: 待限制的数值。
        lo: 下界。
        hi: 上界。

    Returns:
        限制后的数值。

    Raises:
        ValueError: 若 lo > hi。
    """
    if lo > hi:
        raise ValueError(f"_clamp: lo ({lo}) > hi ({hi})")
    return max(lo, min(hi, value))


def _parse_hex_color(hex_color: str) -> tuple[int, int, int]:
    """将 '#rrggbb' 格式颜色字符串解析为 (r, g, b) 整数元组。

    Args:
        hex_color: 形如 '#rrggbb' 的六位十六进制颜色字符串（大小写均可）。

    Returns:
        (r, g, b) 整数元组，各分量范围 [0, 255]。

    Raises:
        ValueError: 若字符串格式不符合要求。
    """
    if not isinstance(hex_color, str):
        raise ValueError(f"颜色值必须为字符串，实际类型: {type(hex_color).__name__!r}")
    s = hex_color.strip().lower()
    if not s.startswith("#") or len(s) != 7:
        raise ValueError(f"颜色值必须为 '#rrggbb' 格式，实际值: {hex_color!r}")
    try:
        r = int(s[1:3], 16)
        g = int(s[3:5], 16)
        b = int(s[5:7], 16)
    except ValueError as exc:
        raise ValueError(f"颜色值包含非法十六进制字符: {hex_color!r}") from exc
    return (r, g, b)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """将 (r, g, b) 整数元组转换为 '#rrggbb' 字符串。

    Args:
        rgb: (r, g, b) 整数元组，各分量范围 [0, 255]。

    Returns:
        形如 '#rrggbb' 的小写十六进制颜色字符串。
    """
    r, g, b = rgb
    r = int(_clamp(r, 0, 255))
    g = int(_clamp(g, 0, 255))
    b = int(_clamp(b, 0, 255))
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp_rgb_tuple(
    c0: tuple[int, int, int],
    c1: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """在两个 RGB 元组之间线性插值。

    Args:
        c0: 起始颜色 (r, g, b)。
        c1: 结束颜色 (r, g, b)。
        t: 插值参数，自动 clamp 到 [0.0, 1.0]。

    Returns:
        插值结果 (r, g, b) 整数元组。
    """
    t = _clamp(t, 0.0, 1.0)
    r = round(c0[0] + (c1[0] - c0[0]) * t)
    g = round(c0[1] + (c1[1] - c0[1]) * t)
    b = round(c0[2] + (c1[2] - c0[2]) * t)
    return (r, g, b)


def _lerp_color_palette(
    t: float,
    palette: list[tuple[int, int, int]],
) -> str:
    """在多色调色板中插值，返回 '#rrggbb' 字符串。

    Args:
        t: 插值参数，自动 clamp 到 [0.0, 1.0]。
        palette: 至少含 2 个 RGB 元组的调色板列表。

    Returns:
        插值后的颜色字符串 '#rrggbb'。

    Raises:
        ValueError: 若 palette 长度小于 2。
    """
    if len(palette) < 2:
        raise ValueError(f"调色板至少需要 2 个颜色，实际数量: {len(palette)}")
    t = _clamp(t, 0.0, 1.0)
    n_segments = len(palette) - 1
    scaled = t * n_segments
    seg_idx = int(scaled)
    if seg_idx >= n_segments:
        seg_idx = n_segments - 1
    local_t = scaled - seg_idx
    rgb = _lerp_rgb_tuple(palette[seg_idx], palette[seg_idx + 1], local_t)
    return _rgb_to_hex(rgb)


# ---------------------------------------------------------------------------
# TextAnimator 类
# ---------------------------------------------------------------------------

class TextAnimator:
    """管理逐字浮现+淡入+上下浮动+光晕闪烁的复合文字动画。

    每隔 CHAR_REVEAL_INTERVAL 帧解锁下一个字符。每个字符独立执行：
    - FADE_IN_FRAMES 帧 alpha 淡入（从 color_start 渐变到目标色）
    - Y 轴微浮动（基于各字符的 char_age 独立计时）
    - 光晕闪烁（基于各字符的 char_age 独立计时）

    字符通过 canvas.create_text 绘制，tag=TEXT_TAG。
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
            canvas: 目标 tkinter 画布。
            text: 要逐字显示的文本字符串。
            cx: 文字整体中心 X 坐标（像素）。
            cy: 文字基准 Y 坐标（像素）。
            font_family: 字体名称，如 'Arial'。
            font_size: 字体大小（像素/pt）。
            color_start: 淡入起始颜色 '#rrggbb'，作为调色板起点。
            color_end: 最终目标颜色 '#rrggbb'。

        Raises:
            TypeError: 若 canvas 不是 tk.Canvas 或坐标不是数值类型。
            ValueError: 若 text 为空字符串、font_size <= 0 或颜色格式非法，
                        或模块级常量 FADE_IN_FRAMES / GLOW_PERIOD / FLOAT_PERIOD
                        被修改为零或负值。
        """
        if not isinstance(canvas, tk.Canvas):
            raise TypeError(
                f"canvas 必须为 tk.Canvas 实例，实际类型: {type(canvas).__name__!r}"
            )
        if not isinstance(text, str) or len(text) == 0:
            raise ValueError(f"text 必须为非空字符串，实际值: {text!r}")
        if not isinstance(cx, (int, float)):
            raise TypeError(f"cx 必须为数值类型，实际类型: {type(cx).__name__!r}")
        if not isinstance(cy, (int, float)):
            raise TypeError(f"cy 必须为数值类型，实际类型: {type(cy).__name__!r}")
        if not isinstance(font_family, str) or len(font_family) == 0:
            raise ValueError(f"font_family 必须为非空字符串，实际值: {font_family!r}")
        if isinstance(font_size, bool) or not isinstance(font_size, int) or font_size <= 0:
            raise ValueError(f"font_size 必须为正整数，实际值: {font_size!r}")

        # 防御性断言：模块级分母常量必须为正整数（fix issue #3）
        assert FADE_IN_FRAMES > 0, "FADE_IN_FRAMES 必须为正整数"
        assert GLOW_PERIOD > 0, "GLOW_PERIOD 必须为正整数"
        assert FLOAT_PERIOD > 0, "FLOAT_PERIOD 必须为正整数"

        # 校验并解析颜色（会在格式非法时抛出 ValueError）
        _parse_hex_color(color_start)
        _parse_hex_color(color_end)

        self._canvas = canvas
        self._text = text
        self._cx = cx
        self._cy = cy
        self._font_family = font_family
        self._font_size = font_size
        # 规范化为小写 '#rrggbb' 格式存储（fix issue #4）
        self._color_start: str = color_start.strip().lower()
        self._color_end: str = color_end.strip().lower()

        # 解析颜色为 RGB 元组（基于规范化后的字符串）
        self._start_rgb: tuple[int, int, int] = _parse_hex_color(self._color_start)
        self._target_rgb: tuple[int, int, int] = _parse_hex_color(self._color_end)

        # 构建淡入调色板：color_start -> ... -> color_end
        # 使用 _FADE_STOP_LOW 和 _FADE_STOP_HIGH 作为中间节点
        self._fade_palette: list[tuple[int, int, int]] = [
            self._start_rgb,
            _lerp_rgb_tuple(self._start_rgb, self._target_rgb, _FADE_STOP_LOW),
            _lerp_rgb_tuple(self._start_rgb, self._target_rgb, _FADE_STOP_HIGH),
            self._target_rgb,
        ]

        # 字符 X 坐标列表（构造时预计算，不依赖帧状态）
        self._char_x_positions: list[float] = []
        self._compute_char_positions()

        # 动画运行时状态
        self._start_frame: Optional[int] = None   # 首次 update() 时记录起始帧
        self._char_unlock_frames: list[int] = []  # 各字符的解锁帧号（绝对帧）
        self._initialized: bool = False
        self._last_frame: int = -1  # 最后一次 update() 传入的 global_frame

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _compute_char_positions(self) -> None:
        """预计算每个字符的 X 坐标，基于等宽假设（空格使用更小系数）。

        注意：reset() 不重置坐标，因为坐标仅依赖构造参数（cx/cy/font_size），
        与动画帧状态无关。若需动态更新位置，请调用 reset(cx=new_cx, cy=new_cy)。
        """
        n = len(self._text)
        if n == 0:
            self._char_x_positions = []
            return

        # 计算总宽度（累加各字符宽度）
        char_widths: list[float] = []
        for ch in self._text:
            if ch == " ":
                char_widths.append(self._font_size * _SPACE_SPACING_FACTOR)
            else:
                char_widths.append(self._font_size * _CHAR_SPACING_FACTOR)

        total_width = sum(char_widths)
        # 起始 X（使整体居中）
        start_x = self._cx - total_width / 2.0

        positions: list[float] = []
        x = start_x
        for width in char_widths:
            positions.append(x + width / 2.0)  # 字符中心 X
            x += width

        self._char_x_positions = positions

    def _initialize_unlock_frames(self, start_frame: int) -> None:
        """根据起始帧计算每个字符的解锁帧号。

        Args:
            start_frame: 动画第一帧的全局帧号。
        """
        self._start_frame = start_frame
        self._char_unlock_frames = [
            start_frame + i * CHAR_REVEAL_INTERVAL
            for i in range(len(self._text))
        ]
        self._initialized = True

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def update(self, global_frame: int) -> None:
        """根据当前全局帧号更新并重绘所有可见字符。

        每帧先通过 canvas.delete(TEXT_TAG) 清除上一帧文字层，再重新绘制。
        每个字符基于自身 char_age（从解锁帧起算）独立计算淡入、浮动和光晕。
        若 canvas 已被销毁（tk.TclError），则静默退出，与 reset() 的容错策略一致。

        Args:
            global_frame: 当前全局帧号，必须为非负整数。

        Raises:
            ValueError: 若 global_frame 不是非负整数（bool 不接受）。
        """
        if isinstance(global_frame, bool) or not isinstance(global_frame, int) or global_frame < 0:
            raise ValueError(
                f"global_frame 必须为非负整数，实际值: {global_frame!r}"
            )

        # 首次调用时初始化解锁帧列表
        if not self._initialized:
            self._initialize_unlock_frames(global_frame)

        # 对 canvas 操作整体加保护，防止 canvas 已销毁时崩溃（fix issue #5）
        try:
            # 清除上一帧文字层
            self._canvas.delete(TEXT_TAG)

            font_spec = (self._font_family, self._font_size, "bold")

            for i, char in enumerate(self._text):
                unlock_frame = self._char_unlock_frames[i]

                # 尚未解锁，跳过
                if global_frame < unlock_frame:
                    continue

                # 该字符从解锁时刻起的独立帧龄
                char_age: int = global_frame - unlock_frame

                # ---- 淡入进度 ------------------------------------------------
                # 使用 max(..., 1) 作为额外防御（fix issue #3，配合 __init__ assert）
                fade_t: float = _clamp(char_age / max(FADE_IN_FRAMES, 1), 0.0, 1.0)

                # ---- 颜色（淡入 + 光晕）-------------------------------------
                # 光晕：基于 char_age 独立计时
                # sin(x) ∈ [-1, 1]，加 1 后 ∈ [0, 2]，乘 0.5 后归一化到 [0, 1]
                glow_t: float = (
                    math.sin(_TWO_PI * char_age / max(GLOW_PERIOD, 1)) + 1.0
                ) * 0.5  # 将 sin[-1,1] 归一化到 [0,1]

                # combo_t 综合淡入进度与光晕：淡入完成前以 fade_t 为主，完成后光晕在目标色基础上脉冲
                # fix issue #1: 删除死代码 effective_t 及草稿注释
                # fix issue #2: 使用具名常量 _GLOW_BLEND_FACTOR 替代魔数 0.3
                combo_t: float = _clamp(
                    fade_t + glow_t * (1.0 - fade_t) * _GLOW_BLEND_FACTOR,
                    0.0,
                    1.0,
                )
                color_hex: str = _lerp_color_palette(combo_t, self._fade_palette)

                # ---- Y 轴浮动（每字符独立相位，基于 char_age）---------------
                # 使用 char_age 使每个字符从各自解锁时刻起独立计时
                float_offset: float = FLOAT_AMP * math.sin(
                    _TWO_PI * char_age / max(FLOAT_PERIOD, 1)
                )
                draw_y: float = self._cy + float_offset

                # ---- 绘制字符 -----------------------------------------------
                draw_x: float = self._char_x_positions[i]
                self._canvas.create_text(
                    round(draw_x),
                    round(draw_y),
                    text=char,
                    font=font_spec,
                    fill=color_hex,
                    tag=TEXT_TAG,
                    anchor="center",
                )

        except tk.TclError:
            return  # canvas 已销毁，静默退出

        # 记录最后一帧帧号（供 is_done() 使用，放在 try 外以防止未更新）
        self._last_frame = global_frame

    def is_done(self) -> bool:
        """判断所有字符是否已完成淡入。

        直接基于 _last_frame 与最后一个字符解锁帧+FADE_IN_FRAMES 计算，
        不依赖缓存标记状态，支持非连续帧跳跃场景。

        Returns:
            True 若所有字符均已完成淡入，否则 False。
        """
        if not self._initialized:
            return False
        if self._start_frame is None:
            return False
        if len(self._char_unlock_frames) == 0:
            return False
        if self._last_frame < 0:
            return False
        last_char_done_frame: int = self._char_unlock_frames[-1] + FADE_IN_FRAMES
        return self._last_frame >= last_char_done_frame

    def reset(
        self,
        cx: Optional[float] = None,
        cy: Optional[float] = None,
    ) -> None:
        """重置动画状态以备下一次循环。

        清除帧计时状态，字符 X 坐标默认不重置（因为坐标仅依赖构造参数）。
        若传入新的 cx/cy，则同步更新中心坐标并重新计算字符位置。

        注意：_char_x_positions 在未传入新坐标时保持不变，
              因为它不依赖动画帧状态，可安全复用。

        Args:
            cx: 可选的新中心 X 坐标；非 None 时同步更新并重算字符位置。
            cy: 可选的新中心 Y 坐标；非 None 时同步更新。
        """
        if cx is not None:
            if not isinstance(cx, (int, float)):
                raise TypeError(f"cx 必须为数值类型，实际类型: {type(cx).__name__!r}")
            self._cx = float(cx)
        if cy is not None:
            if not isinstance(cy, (int, float)):
                raise TypeError(f"cy 必须为数值类型，实际类型: {type(cy).__name__!r}")
            self._cy = float(cy)

        # 若坐标有变更，重新计算字符位置
        if cx is not None or cy is not None:
            self._compute_char_positions()

        # 重置帧状态
        self._start_frame = None
        self._char_unlock_frames = []
        self._initialized = False
        self._last_frame = -1

        # 清除画布上的文字层
        try:
            self._canvas.delete(TEXT_TAG)
        except Exception:  # noqa: BLE001
            pass  # canvas 可能已销毁，静默忽略
