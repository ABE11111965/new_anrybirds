"""
角色类定义 - 支持静态模式和物理激活
"""

import pymunk as pm
from pymunk import Vec2d


class Bird():
    """小鸟类 - 进攻方单位"""
    
    def __init__(self, distance, angle, x, y, space):
        self.life = 20
        mass = 5
        radius = 12
        inertia = pm.moment_for_circle(mass, 0, radius, (0, 0))
        body = pm.Body(mass, inertia)
        body.position = x, y
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


class Pig():
    """猪类 - 防守方单位"""
    
    def __init__(self, x, y, space, static=False):
        """
        初始化猪
        
        参数:
            x: x坐标（pymunk坐标系）
            y: y坐标（pymunk坐标系）
            space: 物理空间
            static: 是否为静态物体（布防阶段使用）
        """
        self.life = 20
        self.is_static = static
        self.space = space
        mass = 5
        radius = 14
        
        if static:
            # 布防阶段：创建静态物体
            body = pm.Body(body_type=pm.Body.STATIC)
            body.position = x, y
            shape = pm.Circle(body, radius, (0, 0))
            shape.elasticity = 0.95
            shape.friction = 1
            shape.collision_type = 1
            space.add(body, shape)
            
            # 保存参数用于后续激活
            self._mass = mass
            self._radius = radius
            self._inertia = pm.moment_for_circle(mass, 0, radius, (0, 0))
        else:
            # 正常模式：创建动态物体
            inertia = pm.moment_for_circle(mass, 0, radius, (0, 0))
            body = pm.Body(mass, inertia)
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
