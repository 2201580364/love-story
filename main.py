"""M04: tkinter爱心动画主程序（含五阶段状态机与性能保障措施）"""
import tkinter as tk
import math
import random

from effects import (
    easing_out_cubic,
    lerp_color_rich,
    particle_size,
    glow_color,
    beat_scale,
    filled_heart_points_v2,
)
from text_animation import TextAnimator, TEXT, CHAR_REVEAL_INTERVAL

# ── 窗口与画布常量 ────────────────────────────────────────────────────────────
WIDTH: int = 800
HEIGHT: int = 600
CX: float = WIDTH / 2
CY: float = HEIGHT / 2

# ── 性能常量 ─────────────────────────────────────────────────────────────────
FPS: int = 30
DELAY: int = 1000 // FPS
PARTICLE_DENSITY: int = 1200
BASE_WIDTH: int = 800
BASE_HEIGHT: int = 600

# ── 动画阶段名称常量 ──────────────────────────────────────────────────────────
PHASE_EXPAND: str = 'expand'
PHASE_BEAT: str = 'beat'
PHASE_TEXT: str = 'text'
PHASE_HOLD: str = 'hold'
PHASE_RESTART: str = 'restart'

# ── 阶段边界帧常量 ────────────────────────────────────────────────────────────
EXPAND_START: int = 0
EXPAND_END: int = 60          # PHASE_EXPAND: 帧 0~59
BEAT_START: int = 60
BEAT_END: int = 180           # PHASE_BEAT:   帧 60~179
TEXT_START: int = 180
TEXT_EXTRA_FRAMES: int = 60   # PHASE_TEXT 结束后额外缓冲帧
HOLD_FRAMES: int = 60         # PHASE_HOLD 持续帧数

# ── 心跳参数 ─────────────────────────────────────────────────────────────────
BEAT_PERIOD: int = 30
BASE_SIZE: float = 10.0
BEAT_AMP: float = 1.0
BASE_PARTICLE_R: float = 2.0
BEAT_PARTICLE_AMP: float = 0.5

# ── canvas tag 常量 ───────────────────────────────────────────────────────────
HEART_TAG: str = 'heart_layer'
TEXT_TAG: str = 'text_layer'

# ── 调色板（深红→玫瑰红→粉红→浅粉）────────────────────────────────────────
PALETTE: list[tuple[int, int, int]] = [
    (139, 0, 0),
    (220, 20, 60),
    (255, 105, 180),
    (255, 182, 193),
]


def adaptive_density(canvas_width: int, canvas_height: int, base_density: int = 1200) -> int:
    """根据画布像素面积与基准分辨率的比例线性缩放粒子数。

    Args:
        canvas_width:  当前画布宽度（像素）。
        canvas_height: 当前画布高度（像素）。
        base_density:  基准分辨率（800x600）对应的粒子数，默认 1200。

    Returns:
        缩放后的粒子数（整数，至少为 1）。

    Raises:
        ValueError: 若 canvas_width 或 canvas_height 不为正整数。
    """
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError(
            f"canvas_width 和 canvas_height 必须为正整数，"
            f"当前值: width={canvas_width}, height={canvas_height}"
        )
    if base_density <= 0:
        raise ValueError(f"base_density 必须为正整数，当前值: {base_density}")

    base_area: int = BASE_WIDTH * BASE_HEIGHT
    current_area: int = canvas_width * canvas_height
    ratio: float = current_area / base_area
    scaled: int = max(1, round(base_density * ratio))
    return scaled


def get_phase(frame: int) -> tuple[str, int]:
    """根据全局帧号返回当前阶段名称及阶段内局部帧号。

    Args:
        frame: 全局帧计数器（从 0 开始）。

    Returns:
        (phase_name, local_frame) 的二元组。
        phase_name 为五阶段字符串之一；local_frame 为该阶段内的相对帧号。
    """
    text_frames: int = len(TEXT) * CHAR_REVEAL_INTERVAL + TEXT_EXTRA_FRAMES
    text_end: int = TEXT_START + text_frames
    hold_end: int = text_end + HOLD_FRAMES

    if frame < EXPAND_END:
        return PHASE_EXPAND, frame - EXPAND_START
    elif frame < BEAT_END:
        return PHASE_BEAT, frame - BEAT_START
    elif frame < text_end:
        return PHASE_TEXT, frame - TEXT_START
    elif frame < hold_end:
        return PHASE_HOLD, frame - text_end
    else:
        return PHASE_RESTART, 0


def run_animation() -> None:
    """启动 tkinter 窗口并以五阶段状态机循环播放爱心动画。

    阶段顺序：
      PHASE_EXPAND → PHASE_BEAT → PHASE_TEXT → PHASE_HOLD → PHASE_RESTART（循环）
    """
    root = tk.Tk()
    root.title('Love')
    root.resizable(False, False)

    canvas = tk.Canvas(
        root, width=WIDTH, height=HEIGHT, bg='black', highlightthickness=0
    )
    canvas.pack()

    # ── 一次性预生成粒子坐标（在 PHASE_EXPAND 前完成）────────────────────────
    density: int = adaptive_density(WIDTH, HEIGHT, PARTICLE_DENSITY)
    cached_points: list[tuple[float, float, float]] = filled_heart_points_v2(
        cx=0.0, cy=0.0, size=1.0, density=density
    )
    total: int = len(cached_points)

    # ── TextAnimator 实例 ─────────────────────────────────────────────────────
    text_animator = TextAnimator(
        canvas=canvas,
        text=TEXT,
        cx=CX,
        cy=CY + BASE_SIZE * BASE_SIZE,   # 文字位于爱心下方
        font_family='Arial',
        font_size=24,
        color_start='#000000',
        color_end='#ff69b4',
    )

    # ── state 字典（顶层声明，update 内使用局部引用）──────────────────────────
    state: dict = {
        'frame': 0,
        'text_animator_reset': False,
    }

    def update() -> None:
        """每帧回调：根据当前阶段更新画布。"""
        # 局部变量引用，减少字典查找
        frame: int = state['frame']
        phase, local_frame = get_phase(frame)

        # ── PHASE_RESTART：重置状态并从头循环 ───────────────────────────────
        if phase == PHASE_RESTART:
            state['frame'] = 0
            state['text_animator_reset'] = False
            text_animator.reset()
            root.after(DELAY, update)
            return

        # ── 计算当前爱心尺寸 ─────────────────────────────────────────────────
        if phase == PHASE_EXPAND:
            t_ease: float = easing_out_cubic(local_frame / max(1, EXPAND_END - EXPAND_START - 1))
            current_size: float = BASE_SIZE * t_ease
            expand_progress: float = t_ease
            beat_frame_for_color: int = 0
        else:
            current_size = beat_scale(
                frame=frame,
                beat_period=BEAT_PERIOD,
                base_size=BASE_SIZE,
                beat_amp=BEAT_AMP,
            )
            expand_progress = 1.0
            beat_frame_for_color = frame

        # ── 清空画布 ─────────────────────────────────────────────────────────
        canvas.delete('all')

        # ── 决定可见粒子数量 ─────────────────────────────────────────────────
        if phase == PHASE_EXPAND:
            raw_visible: int = int(total * expand_progress)
            visible: int = max(0, min(raw_visible, total))
        else:
            visible = total

        # ── 预计算心跳亮度因子（用于颜色脉动）───────────────────────────────
        beat_intensity: float = (
            0.5 + 0.5 * math.sin(beat_frame_for_color * 2 * math.pi / BEAT_PERIOD)
        ) if phase != PHASE_EXPAND else 0.0

        # ── 批量绘制粒子（预先用 round() 转整数）────────────────────────────
        pts = cached_points          # 局部引用
        c_size = current_size        # 局部引用
        c_cx = CX                    # 局部引用
        c_cy = CY                    # 局部引用
        c_ep = expand_progress       # 局部引用

        for i in range(visible):
            rx, ry, w = pts[i]

            # 坐标缩放
            sx: int = round(c_cx + rx * c_size * c_ep)
            sy: int = round(c_cy + ry * c_size * c_ep)

            # 颜色：按深度权重 w 在调色板中插值，再叠加心跳亮度
            color_t: float = w  # w∈[0,1]，0=深红侧，1=浅粉侧
            base_col: str = lerp_color_rich(color_t, PALETTE)

            if phase != PHASE_EXPAND and beat_intensity > 0.0:
                final_col: str = glow_color(base_col, beat_intensity * 0.4)
            else:
                final_col = base_col

            # 粒子半径
            pr: float = particle_size(
                base_r=BASE_PARTICLE_R,
                frame=beat_frame_for_color,
                beat_period=BEAT_PERIOD,
                beat_amp=BEAT_PARTICLE_AMP,
            ) if phase != PHASE_EXPAND else BASE_PARTICLE_R
            r_int: int = round(pr)

            canvas.create_oval(
                sx - r_int, sy - r_int,
                sx + r_int, sy + r_int,
                fill=final_col, outline='',
                tags=HEART_TAG,
            )

        # ── 文字层驱动 ───────────────────────────────────────────────────────
        if phase == PHASE_TEXT:
            text_animator.update(frame)
        elif phase == PHASE_HOLD:
            text_animator.update(frame)

        # ── 推进帧计数 ───────────────────────────────────────────────────────
        state['frame'] = frame + 1
        root.after(DELAY, update)

    root.after(DELAY, update)
    root.mainloop()


if __name__ == '__main__':
    run_animation()
