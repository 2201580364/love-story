"""M2: tkinter爱心动画主程序"""
import tkinter as tk
import math
import random

WIDTH, HEIGHT = 800, 600
CX, CY = WIDTH / 2, HEIGHT / 2
FPS = 30
DELAY = 1000 // FPS


def heart_x(t: float, size: float) -> float:
    return size * 16 * math.sin(t) ** 3


def heart_y(t: float, size: float) -> float:
    return -size * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))


def generate_filled_points(num: int = 1000) -> list:
    """生成填充爱心的随机散点，返回(x,y)列表（相对中心）。"""
    points = []
    attempts = 0
    while len(points) < num and attempts < num * 20:
        attempts += 1
        t = random.uniform(0, 2 * math.pi)
        scale = random.uniform(0, 1)
        px = scale * 16 * math.sin(t) ** 3
        py = -scale * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((px, py))
    return points


def lerp_color(t: float) -> str:
    """从深红(139,0,0)到粉红(255,182,193)插值，t in [0,1]。"""
    t = max(0.0, min(1.0, t))
    r = int(139 + (255 - 139) * t)
    g = int(0 + (182 - 0) * t)
    b = int(0 + (193 - 0) * t)
    return f'#{r:02x}{g:02x}{b:02x}'


def run_animation() -> None:
    """启动tkinter窗口并循环播放爱心动画。"""
    root = tk.Tk()
    root.title('Love')
    root.resizable(False, False)

    canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg='black', highlightthickness=0)
    canvas.pack()

    all_points = generate_filled_points(1000)
    total = len(all_points)
    ovals = []

    # 动画状态
    state = {
        'frame': 0,
        'beat_frame': 0,
    }

    EXPAND_FRAMES = 60   # 粒子扩散帧数
    BEAT_PERIOD = 30     # 心跳周期帧数
    BASE_SIZE = 10.0
    BEAT_AMP = 1.0       # 心跳缩放幅度

    def get_size(frame: int) -> float:
        beat = math.sin(frame * 2 * math.pi / BEAT_PERIOD) * BEAT_AMP
        return BASE_SIZE + beat

    def update():
        frame = state['frame']
        size = get_size(frame)

        # 决定当前显示多少粒子（扩散效果）
        if frame < EXPAND_FRAMES:
            visible = int(total * frame / EXPAND_FRAMES)
        else:
            visible = total

        # 颜色渐变进度
        color_t = min(1.0, frame / EXPAND_FRAMES)
        color = lerp_color(color_t)

        canvas.delete('all')

        for i in range(visible):
            px, py = all_points[i]
            # 扩散：粒子从中心向外扩展
            if frame < EXPAND_FRAMES:
                progress = frame / EXPAND_FRAMES
            else:
                progress = 1.0
            sx = CX + px * size * progress
            sy = CY + py * size * progress
            r = 2
            canvas.create_oval(
                round(sx - r), round(sy - r),
                round(sx + r), round(sy + r),
                fill=color, outline=''
            )

        state['frame'] += 1
        root.after(DELAY, update)

    root.after(DELAY, update)
    root.mainloop()


if __name__ == '__main__':
    run_animation()
