"""M03: tkinter爱心动画主程序 — 五阶段状态机重构版本"""
import tkinter as tk
import math

from text_animation import TextAnimator, TEXT, CHAR_REVEAL_INTERVAL
import effects
from heart import filled_heart_points_v2

# ── 窗口与帧率常量 ──────────────────────────────────────────────
WIDTH: int = 800
HEIGHT: int = 600
CX: float = WIDTH / 2
CY: float = HEIGHT / 2
FPS: int = 30
DELAY: int = 1000 // FPS

# ── 粒子与心跳常量 ─────────────────────────────────────────────
PARTICLE_DENSITY: int = 1200
BASE_SIZE: float = 10.0
BASE_PARTICLE_R: float = 2.0
BEAT_AMP: float = 1.0
PARTICLE_BEAT_AMP: float = 0.5
BEAT_PERIOD: int = 30

# ── 多色渐变调色板（深红→玫瑰红→粉红→浅粉） ──────────────────
COLOR_PALETTE: list[tuple[int, int, int]] = [
    (139, 0, 0),
    (220, 20, 60),
    (255, 105, 180),
    (255, 182, 193),
]

# ── 阶段常量 ───────────────────────────────────────────────────
PHASE_EXPAND: str = 'expand'
PHASE_BEAT: str = 'beat'
PHASE_TEXT: str = 'text'
PHASE_HOLD: str = 'hold'
PHASE_RESTART: str = 'restart'

# ── 阶段边界帧数 ───────────────────────────────────────────────
EXPAND_START: int = 0
EXPAND_END: int = 59          # 0~59 共60帧
BEAT_START: int = 60
BEAT_END: int = 179           # 60~179 共120帧
TEXT_START: int = 180
_TEXT_DURATION: int = len(TEXT) * CHAR_REVEAL_INTERVAL + 60
TEXT_END: int = TEXT_START + _TEXT_DURATION - 1
HOLD_START: int = TEXT_END + 1
HOLD_DURATION: int = 60
HOLD_END: int = HOLD_START + HOLD_DURATION - 1

# ── Canvas tag 常量 ────────────────────────────────────────────
HEART_TAG: str = 'heart_layer'
TEXT_TAG: str = 'text_layer'

# ── 字体常量 ───────────────────────────────────────────────────
TEXT_FONT_FAMILY: str = 'Helvetica'
TEXT_FONT_SIZE: int = 28
TEXT_COLOR_START: str = '#000000'
TEXT_COLOR_END: str = '#ff69b4'


def adaptive_density(canvas_width: int, canvas_height: int, base_density: int = 1200) -> int:
    """根据画布像素面积与基准 800x600 的比例线性缩放粒子数。

    Args:
        canvas_width: 实际画布宽度（像素）。
        canvas_height: 实际画布高度（像素）。
        base_density: 基准粒子数，默认1200。

    Returns:
        缩放后的粒子数（最小为1）。

    Raises:
        ValueError: 若 canvas_width 或 canvas_height 不为正整数。
    """
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError(
            f"canvas_width 和 canvas_height 必须为正整数，"
            f"收到 ({canvas_width}, {canvas_height})"
        )
    base_area: float = 800.0 * 600.0
    actual_area: float = float(canvas_width) * float(canvas_height)
    ratio: float = actual_area / base_area
    return max(1, round(base_density * ratio))


def get_phase(frame: int) -> tuple[str, int]:
    """根据全局帧号返回当前阶段名称与阶段内局部帧号。

    Args:
        frame: 全局动画帧计数（从0开始）。

    Returns:
        (phase_name, local_frame) 元组：
            phase_name — PHASE_* 常量之一；
            local_frame — 当前帧在该阶段内的偏移（从0起）。

    Raises:
        ValueError: 若 frame 为负数。
    """
    if frame < 0:
        raise ValueError(f"frame 不能为负数，收到 {frame}")

    if frame <= EXPAND_END:
        return PHASE_EXPAND, frame - EXPAND_START
    if frame <= BEAT_END:
        return PHASE_BEAT, frame - BEAT_START
    if frame <= TEXT_END:
        return PHASE_TEXT, frame - TEXT_START
    if frame <= HOLD_END:
        return PHASE_HOLD, frame - HOLD_START
    return PHASE_RESTART, frame - (HOLD_END + 1)


def run_animation() -> None:
    """启动 tkinter 窗口并循环播放五阶段爱心动画。

    五个阶段依次为：
        PHASE_EXPAND  — 粒子从中心扩散（0-59帧）
        PHASE_BEAT    — 爱心持续心跳（60-179帧）
        PHASE_TEXT    — 文字逐字浮现（180-TEXT_END帧）
        PHASE_HOLD    — 静止慢心跳+文字浮动（HOLD_START-HOLD_END帧）
        PHASE_RESTART — 重置 frame=0 循环

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

    # ── 预计算粒子坐标（只调用一次） ───────────────────────────
    density: int = adaptive_density(WIDTH, HEIGHT, PARTICLE_DENSITY)
    raw_points: list[tuple[float, float, float]] = filled_heart_points_v2(
        cx=0.0, cy=0.0, size=1.0, density=density
    )
    # raw_points 中每个元素为 (px, py, w)，坐标相对于(0,0)，size=1.0

    # ── TextAnimator ────────────────────────────────────────────
    text_animator = TextAnimator(
        canvas=canvas,
        text=TEXT,
        cx=CX,
        cy=CY + 160.0,   # 文字位于爱心下方
        font_family=TEXT_FONT_FAMILY,
        font_size=TEXT_FONT_SIZE,
        color_start=TEXT_COLOR_START,
        color_end=TEXT_COLOR_END,
    )

    # ── 动画状态字典（顶层声明，避免重复查找） ──────────────────
    state: dict = {
        'frame': 0,
    }

    def update() -> None:
        """每帧回调：根据阶段状态机绘制粒子层与文字层。"""
        # 局部变量引用，减少字典查找
        frame: int = state['frame']
        phase, local_frame = get_phase(frame)

        # ── 阶段 RESTART：重置状态 ──────────────────────────────
        if phase == PHASE_RESTART:
            state['frame'] = 0
            text_animator.reset()
            root.after(DELAY, update)
            return

        # ── 计算当前爱心大小与可见粒子数 ────────────────────────
        if phase == PHASE_EXPAND:
            # easing_out_cubic 缓动扩散
            t_expand: float = local_frame / max(1, EXPAND_END - EXPAND_START)
            eased: float = effects.easing_out_cubic(t_expand)
            current_size: float = BASE_SIZE * eased
            visible_count: int = round(len(raw_points) * eased)
        elif phase == PHASE_HOLD:
            # 慢心跳：beat_period 翻倍
            current_size = effects.beat_scale(
                frame=local_frame,
                beat_period=BEAT_PERIOD * 2,
                base_size=BASE_SIZE,
                beat_amp=BEAT_AMP * 0.5,
            )
            visible_count = len(raw_points)
        else:
            # PHASE_BEAT / PHASE_TEXT：正常心跳
            current_size = effects.beat_scale(
                frame=local_frame,
                beat_period=BEAT_PERIOD,
                base_size=BASE_SIZE,
                beat_amp=BEAT_AMP,
            )
            visible_count = len(raw_points)

        # ── 清除上一帧 ──────────────────────────────────────────
        canvas.delete('all')

        # ── 绘制粒子层 ──────────────────────────────────────────
        # 颜色插值进度：扩散阶段随 eased 增长，其余阶段随心跳亮度脉动
        local_pts = raw_points  # 局部引用
        palette = COLOR_PALETTE  # 局部引用

        if phase == PHASE_EXPAND:
            # 扩散时颜色从暗到亮（t=eased 驱动调色板）
            base_color_t: float = eased
        else:
            # 心跳时颜色亮度随心跳周期脉动
            beat_t_raw: float = math.sin(
                local_frame * 2 * math.pi / (
                    BEAT_PERIOD * 2 if phase == PHASE_HOLD else BEAT_PERIOD
                )
            )
            # 将 sin 映射到 [0.5, 1.0]
            base_color_t = 0.5 + 0.5 * beat_t_raw

        for i in range(min(visible_count, len(local_pts))):
            px, py, w = local_pts[i]

            # 扩散阶段：坐标从中心向外扩展
            if phase == PHASE_EXPAND:
                progress: float = eased
            else:
                progress = 1.0

            sx: float = CX + px * current_size * progress
            sy: float = CY + py * current_size * progress

            # w 越大越亮粉：将 base_color_t 与 w 混合后查调色板
            color_t: float = min(1.0, base_color_t * (0.5 + 0.5 * w))
            color: str = effects.lerp_color_rich(color_t, palette)

            # 粒子半径随心跳脉动
            if phase == PHASE_EXPAND:
                r: float = BASE_PARTICLE_R * eased if eased > 0 else BASE_PARTICLE_R
            else:
                r = effects.particle_size(
                    base_r=BASE_PARTICLE_R,
                    frame=local_frame,
                    beat_period=BEAT_PERIOD * 2 if phase == PHASE_HOLD else BEAT_PERIOD,
                    beat_amp=PARTICLE_BEAT_AMP,
                )

            ix: int = round(sx)
            iy: int = round(sy)
            ir: int = max(1, round(r))

            canvas.create_oval(
                ix - ir, iy - ir,
                ix + ir, iy + ir,
                fill=color,
                outline='',
                tags=(HEART_TAG,),
            )

        # ── 绘制文字层 ──────────────────────────────────────────
        if phase in (PHASE_TEXT, PHASE_HOLD):
            text_animator.update(frame)

        # ── 推进帧计数 ──────────────────────────────────────────
        state['frame'] = frame + 1
        root.after(DELAY, update)

    root.after(DELAY, update)
    root.mainloop()


if __name__ == '__main__':
    run_animation()
