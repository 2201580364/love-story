import math
import random


def heart_points(cx: float, cy: float, size: float, num_points: int = 200) -> list[tuple[float, float]]:
    """返回爱心轮廓坐标列表。

    Args:
        cx: 中心x坐标
        cy: 中心y坐标
        size: 缩放系数
        num_points: 采样点数量

    Returns:
        轮廓点坐标列表 [(x, y), ...]
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if num_points <= 0:
        raise ValueError("num_points must be positive")

    points = []
    for i in range(num_points):
        t = 2 * math.pi * i / num_points
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((cx + x * size, cy - y * size))
    return points


def filled_heart_points(cx: float, cy: float, size: float, density: int = 800) -> list[tuple[float, float]]:
    """返回填充爱心的随机散点。

    Args:
        cx: 中心x坐标
        cy: 中心y坐标
        size: 缩放系数
        density: 生成散点数量

    Returns:
        填充点坐标列表 [(x, y), ...]
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if density <= 0:
        raise ValueError("density must be positive")

    points = []
    attempts = 0
    max_attempts = density * 20
    while len(points) < density and attempts < max_attempts:
        attempts += 1
        t = random.uniform(0, 2 * math.pi)
        r = random.uniform(0, 1)
        x = r * 16 * math.sin(t) ** 3
        y = r * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((cx + x * size, cy - y * size))
    return points
