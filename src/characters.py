"""
角色类定义 - 支持多种类型的鸟和猪
"""

import pymunk as pm
from pymunk import Vec2d
import math


class Bird():
    """小鸟类 - 支持多种类型"""
    RED = 0
    BLUE = 1
    YELLOW = 2
    ORANGE = 3
    PINK = 4

    def __init__(self, distance, angle, x, y, space, bird_type=0):
        self.life = 20
        self.bird_type = bird_type
        self.space = space
        self.activated = False

        # 基础属性
        mass = 5
        radius = 12
        self.radius = radius
        inertia = pm.moment_for_circle(mass, 0, radius, (0, 0))
        body = pm.Body(mass, inertia)
        body.position = x, y

        # 发射力度
        power = distance * 53
        impulse = power * Vec2d(1, 0)
        angle = -angle
        body.apply_impulse_at_local_point(impulse.rotated(angle))

        shape = pm.Circle(body, radius, (0, 0))
        shape.elasticity = 0.95
        shape.friction = 1
        shape.collision_type = 0
        space.add(body, shape)

        self.body = body
        self.shape = shape

    def activate_special(self):
        """触发特殊技能"""
        if self.activated:
            return
        self.activated = True

        if self.bird_type == Bird.YELLOW:
            # 黄鸟：加速冲刺
            self.body.apply_impulse_at_local_point(self.body.velocity * 1.5)

        elif self.bird_type == Bird.BLUE:
            # 蓝鸟：变轻以便飞得更远
            self.body.mass = 1

        elif self.bird_type == Bird.ORANGE:
            # 橘鸟：极速膨胀
            self.expand()

        elif self.bird_type == Bird.PINK:
            # 粉鸟：反重力升空 - 给予巨大的向上冲量
            self.body.apply_impulse_at_local_point((0, 8000))

    def expand(self):
        """橘鸟膨胀逻辑"""
        # 移除旧的形状
        self.space.remove(self.shape)

        # 创建新的大形状
        new_radius = self.radius * 3.5  # 变大3.5倍
        new_mass = self.body.mass * 5   # 质量变大

        # 更新形状属性
        self.shape = pm.Circle(self.body, new_radius, (0, 0))
        self.shape.elasticity = 0.5
        self.shape.friction = 1
        self.shape.collision_type = 0
        self.body.mass = new_mass

        self.space.add(self.shape)
        self.radius = new_radius


class Pig():
    """猪类 - 支持多种类型"""
    NORMAL = 1
    HELMET = 2
    KING = 3

    def __init__(self, x, y, space, pig_type=1, static=False):
        """
        初始化猪

        参数:
            x: x坐标（pymunk坐标系）
            y: y坐标（pymunk坐标系）
            space: 物理空间
            pig_type: 猪的类型 (NORMAL=1, HELMET=2, KING=3)
            static: 是否为静态物体（布防阶段使用）
        """
        self.life = 20
        self.pig_type = pig_type
        self.is_static = static
        self.space = space

        # 根据类型设定属性
        radius = 14
        mass = 5

        if pig_type == Pig.HELMET:
            self.life = 60  # 头盔猪血量是普通猪的3倍
            mass = 8
        elif pig_type == Pig.KING:
            self.life = 100  # 猪王血量是普通猪的5倍
            radius = 25      # 体型更大
            mass = 15        # 质量更大，难以击飞

        self.radius = radius
        self._mass = mass
        self._radius = radius
        self._inertia = pm.moment_for_circle(mass, 0, radius, (0, 0))

        if static:
            # 布防阶段：创建静态物体
            body = pm.Body(body_type=pm.Body.STATIC)
            body.position = x, y
            shape = pm.Circle(body, radius, (0, 0))
            shape.elasticity = 0.95
            shape.friction = 1
            shape.collision_type = 1
            space.add(body, shape)
        else:
            # 正常模式：创建动态物体
            body = pm.Body(mass, self._inertia)
            body.position = x, y
            shape = pm.Circle(body, radius, (0, 0))
            shape.elasticity = 0.95
            shape.friction = 1
            shape.collision_type = 1
            space.add(body, shape)

        self.body = body
        self.shape = shape

    def activate(self, space):
        """
        激活物理模拟 - 将静态物体转换为动态物体
        """
        if not self.is_static:
            return

        # 保存当前位置和角度
        pos = self.body.position
        angle = self.body.angle

        # 移除旧的静态物体
        space.remove(self.shape, self.body)

        # 创建新的动态物体
        body = pm.Body(self._mass, self._inertia)
        body.position = pos
        body.angle = angle

        shape = pm.Circle(body, self._radius, (0, 0))
        shape.elasticity = 0.95
        shape.friction = 1
        shape.collision_type = 1

        space.add(body, shape)

        self.body = body
        self.shape = shape
        self.is_static = False
