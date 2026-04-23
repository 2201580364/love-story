"""M03: tkinter 爱心动画主程序 — 五阶段状态机重构版本。"""
import tkinter as tk
import math

import effects
from text_animation import TextAnimator
from heart import filled_heart_points_v2

# ── 窗口与渲染常量 ──────────────────────────────────────────────────────────────
WIDTH: int = 800
HEIGHT: int = 600
CX: float = WIDTH / 2
CY: float = HEIGHT / 2
FPS: int = 30
DELAY: int = 1000 // FPS

# ── 粒子常量 ────────────────────────────────────────────────────────────────────
PARTICLE_DENSITY: int = 1200
BASE_SIZE: float = 10.0
BASE_RADIUS: float = 2.0       # 粒子基础半径(px)
BEAT_PERIOD: int = 30          # 心跳周期(帧)
BEAT_AMP: float = 1.0          # 心跳幅度

# ── 颜色混合常量 ────────────────────────────────────────────────────────────────
BEAT_COLOR_BASE: float = 0.5
BEAT_COLOR_AMP: float = 0.5
COLOR_W_MIX_BASE: float = 0.5
COLOR_W_MIX_AMP: float = 0.5

# ── 多色渐变调色盘 ──────────────────────────────────────────────────────────────
COLOR_PALETTE: list[tuple[int, int, int]] = [
    (139, 0, 0),       # 深红
    (220, 20, 60),     # 玫瑰红
    (255, 105, 147),   # 粉红
    (255, 182, 193),   # 浅粉
]

# ── 阶段边界常量 ────────────────────────────────────────────────────────────────
EXPAND_START: int = 0
EXPAND_END: int = 59           # PHASE_EXPAND: [0, 59] 共 60 帧
BEAT_START: int = 60
BEAT_END: int = 179            # PHASE_BEAT: [60, 179] 共 120 帧
TEXT_START: int = 180          # PHASE_TEXT 起始帧

# ── 文字动画常量 ────────────────────────────────────────────────────────────────
ANIMATED_TEXT: str = 'I love you fjl'
CHAR_REVEAL_INTERVAL: int = 4  # 与 text_animation 模块保持一致
TEXT_Y_OFFSET: float = 160.0   # 文字相对爱心中心的 Y 轴像素偏移
HOLD_FRAMES: int = 60          # PHASE_HOLD 持续帧数

# ── 阶段名称常量 ────────────────────────────────────────────────────────────────
PHASE_EXPAND: str = 'expand'
PHASE_BEAT: str = 'beat'
PHASE_TEXT: str = 'text'
PHASE_HOLD: str = 'hold'
PHASE_RESTART: str = 'restart'

# ── canvas tag 常量 ─────────────────────────────────────────────────────────────
HEART_TAG: str = 'heart_layer'
TEXT_TAG: str = 'text_layer'


def adaptive_density(
    canvas_width: int,
    canvas_height: int,
    base_density: int = 1200,
) -> int:
    """根据画布像素面积线性缩放粒子密度，防止高分辨率下过载。

    Args:
        canvas_width: 画布宽度（像素），必须为正整数。
        canvas_height: 画布高度（像素），必须为正整数。
        base_density: 基准密度，对应 800x600 画布，默认 1200。

    Returns:
        缩放后的粒子数量（整数）。

    Raises:
        TypeError: 若 canvas_width 或 canvas_height 非整数。
        ValueError: 若 canvas_width、canvas_height 或 base_density 不为正数。
    """
    if not isinstance(canvas_width, int) or not isinstance(canvas_height, int):
        raise TypeError(
            f"canvas_width 和 canvas_height 必须为整数，"
            f"收到 ({type(canvas_width).__name__}, {type(canvas_height).__name__})"
        )
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError(
            f"canvas_width 和 canvas_height 必须为正整数，"
            f"收到 ({canvas_width}, {canvas_height})"
        )
    if base_density <= 0:
        raise ValueError(f"base_density 必须为正整数，收到 {base_density}")

    base_area: int = WIDTH * HEIGHT  # 800 * 600 = 480000
    actual_area: int = canvas_width * canvas_height
    scaled: int = int(base_density * actual_area / base_area)
    return max(1, scaled)


def get_phase(frame: int) -> tuple[str, int]:
    """根据全局帧号返回当前动画阶段名称及阶段内本地帧号。

    动画阶段划分：
      PHASE_EXPAND : [0,  59]  — 粒子扩散
      PHASE_BEAT   : [60, 179] — 心跳
      PHASE_TEXT   : [180, TEXT_END-1] — 文字浮现
      PHASE_HOLD   : [TEXT_END, TEXT_END+59] — 静止保持
      PHASE_RESTART: TEXT_END+60 及之后 — 重置循环

    Args:
        frame: 全局帧计数器，必须为非负整数。

    Returns:
        (phase_name, local_frame) 元组，local_frame 为阶段内从 0 开始的帧号。

    Raises:
        TypeError: 若 frame 非整数。
        ValueError: 若 frame 为负数。
    """
    if not isinstance(frame, int):
        raise TypeError(
            f"frame 必须为整数，收到 {type(frame).__name__}: {frame!r}"
        )
    if frame < 0:
        raise ValueError(f"frame 必须为非负整数，收到 {frame}")

    text_phase_len: int = len(ANIMATED_TEXT) * CHAR_REVEAL_INTERVAL + HOLD_FRAMES
    text_end: int = TEXT_START + text_phase_len   # PHASE_TEXT 结束帧（不含）
    hold_end: int = text_end + HOLD_FRAMES         # PHASE_HOLD 结束帧（不含）

    if frame <= EXPAND_END:
        return (PHASE_EXPAND, frame - EXPAND_START)
    if frame <= BEAT_END:
        return (PHASE_BEAT, frame - BEAT_START)
    if frame < text_end:
        return (PHASE_TEXT, frame - TEXT_START)
    if frame < hold_end:
        return (PHASE_HOLD, frame - text_end)
    return (PHASE_RESTART, frame - hold_end)


def run_animation() -> None:
    """启动 tkinter 窗口并循环播放五阶段爱心动画。

    Args:
        无。

    Returns:
        None
    """
    root = tk.Tk()
    root.title('Love')
    root.resizable(False, False)

    canvas = tk.Canvas(
        root,
        width=WIDTH,
        height=HEIGHT,
        bg='black',
        highlightthickness=0,
    )
    canvas.pack()
    # 调用 root.update() 获取真实布局尺寸，供 adaptive_density 使用
    root.update()
    actual_w: int = canvas.winfo_width()
    actual_h: int = canvas.winfo_height()
    density: int = adaptive_density(
        actual_w or WIDTH,
        actual_h or HEIGHT,
        PARTICLE_DENSITY,
    )

    # ── 预生成粒子点位（含深度权重 w），后续帧仅缩放坐标和更新颜色 ──
    raw_points: list[tuple[float, float, float]] = filled_heart_points_v2(
        cx=0.0,
        cy=0.0,
        size=BASE_SIZE,
        density=density,
    )

    # ── 文字动画器 ──────────────────────────────────────────────────────────────
    text_animator = TextAnimator(
        canvas=canvas,
        text=ANIMATED_TEXT,
        cx=CX,
        cy=CY + TEXT_Y_OFFSET,
        font_family='Helvetica',
        font_size=24,
        color_start='#000000',
        color_end='#ff69b4',
    )

    # ── 动画状态字典 ────────────────────────────────────────────────────────────
    state: dict[str, int] = {'frame': 0}

    def update() -> None:
        """每帧动画回调：根据当前阶段状态机绘制粒子层与文字层。

        通过闭包访问 state、canvas、raw_points、text_animator 等外部变量。

        Args:
            无参数，依赖闭包捕获的外部状态。

        Returns:
            None
        """
        frame: int = state['frame']
        phase, local_frame = get_phase(frame)

        # ── PHASE_RESTART：清屏、重置后立即返回 ────────────────────────────────
        if phase == PHASE_RESTART:
            state['frame'] = 0
            text_animator.reset()
            canvas.delete('all')
            root.after(DELAY, update)
            return

        canvas.delete('all')

        # ── 计算当前爱心尺寸缩放系数 ───────────────────────────────────────────
        if phase == PHASE_EXPAND:
            # 扩散阶段：从 0 缓动到 BASE_SIZE
            t_expand: float = local_frame / max(1, EXPAND_END - EXPAND_START)
            eased: float = effects.easing_out_cubic(t_expand)
            current_size: float = BASE_SIZE * eased
        elif phase in (PHASE_BEAT, PHASE_TEXT):
            # 使用全局 frame 驱动心跳，保持跨阶段相位连续性
            current_size = effects.beat_scale(
                frame=frame,
                beat_period=BEAT_PERIOD,
                base_size=BASE_SIZE,
                beat_amp=BEAT_AMP,
            )
        else:  # PHASE_HOLD
            # 慢心跳，同样用全局 frame 保持连续性
            current_size = effects.beat_scale(
                frame=frame,
                beat_period=BEAT_PERIOD * 2,
                base_size=BASE_SIZE,
                beat_amp=BEAT_AMP * 0.5,
            )

        # ── 计算心跳颜色脉动基值（全局 frame 保持跨阶段连续） ─────────────────
        beat_t_raw: float = math.sin(frame * 2 * math.pi / BEAT_PERIOD)
        base_color_t: float = BEAT_COLOR_BASE + BEAT_COLOR_AMP * beat_t_raw

        # ── 绘制粒子层 ─────────────────────────────────────────────────────────
        if phase == PHASE_EXPAND:
            # 扩散阶段：逐渐显示粒子，坐标从中心向外扩展
            total: int = len(raw_points)
            visible: int = int(total * local_frame / max(1, EXPAND_END - EXPAND_START + 1))
            visible = min(visible, total)
            scale_ratio: float = current_size / BASE_SIZE if BASE_SIZE > 0 else 0.0

            for i in range(visible):
                px, py, w = raw_points[i]
                sx: float = CX + px * scale_ratio
                sy: float = CY + py * scale_ratio
                color_t: float = max(0.0, min(1.0, eased * (COLOR_W_MIX_BASE + COLOR_W_MIX_AMP * w)))
                color: str = effects.lerp_color_rich(color_t, COLOR_PALETTE)
                r: float = effects.particle_size(
                    base_r=BASE_RADIUS,
                    frame=frame,
                    beat_period=BEAT_PERIOD,
                    beat_amp=0.0,  # 扩散阶段无心跳抖动
                )
                canvas.create_oval(
                    round(sx - r), round(sy - r),
                    round(sx + r), round(sy + r),
                    fill=color, outline='',
                    tags=HEART_TAG,
                )
        else:
            # PHASE_BEAT / PHASE_TEXT / PHASE_HOLD：全量粒子，带心跳抖动
            scale_ratio = current_size / BASE_SIZE if BASE_SIZE > 0 else 0.0

            for px, py, w in raw_points:
                sx = CX + px * scale_ratio
                sy = CY + py * scale_ratio
                color_t = max(0.0, min(1.0, base_color_t * (COLOR_W_MIX_BASE + COLOR_W_MIX_AMP * w)))
                color = effects.lerp_color_rich(color_t, COLOR_PALETTE)
                r = effects.particle_size(
                    base_r=BASE_RADIUS,
                    frame=frame,
                    beat_period=BEAT_PERIOD,
                    beat_amp=0.5,
                )
                canvas.create_oval(
                    round(sx - r), round(sy - r),
                    round(sx + r), round(sy + r),
                    fill=color, outline='',
                    tags=HEART_TAG,
                )

        # ── 驱动文字层 ─────────────────────────────────────────────────────────
        if phase == PHASE_TEXT:
            text_animator.update(frame)
        elif phase == PHASE_HOLD:
            # HOLD 阶段无论 is_done() 与否，均继续驱动浮动和光晕效果
            text_animator.update(frame)

        # ── 推进帧计数 ─────────────────────────────────────────────────────────
        state['frame'] = frame + 1
        root.after(DELAY, update)

    root.after(DELAY, update)
    root.mainloop()


if __name__ == '__main__':
    run_animation()
