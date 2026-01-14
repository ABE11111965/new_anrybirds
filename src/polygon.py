"""
多边形类（木材）定义 - 支持静态模式和物理激活
"""

import pymunk as pm
from pymunk import Vec2d
import pygame
import math


class Polygon():
    """木材类 - 可用于建造结构"""
    
    def __init__(self, pos, length, height, space, mass=5.0, static=False):
        """
        初始化木材
        
        参数:
            pos: 位置元组 (x, y)（pymunk坐标系）
            length: 长度
            height: 高度
            space: 物理空间
            mass: 质量
            static: 是否为静态物体（布防阶段使用）
        """
        self.is_static = static
        self.space = space
        self._mass = mass
        self._length = length
        self._height = height
        moment = 1000
        
        if static:
            # 布防阶段：创建静态物体
            body = pm.Body(body_type=pm.Body.STATIC)
            body.position = Vec2d(*pos)
            shape = pm.Poly.create_box(body, (length, height))
            shape.color = (0, 0, 255)
            shape.friction = 0.5
            shape.collision_type = 2
            space.add(body, shape)
        else:
            # 正常模式：创建动态物体
            body = pm.Body(mass, moment)
            body.position = Vec2d(*pos)
            shape = pm.Poly.create_box(body, (length, height))
            shape.color = (0, 0, 255)
            shape.friction = 0.5
            shape.collision_type = 2
            space.add(body, shape)
        
        self.body = body
        self.shape = shape
        
        # 延迟加载木材图片
        self.beam_image = None
        self.column_image = None
        self._images_loaded = False

    def _load_images(self):
        """延迟加载图片"""
        if self._images_loaded:
            return
        try:
            wood = pygame.image.load("../resources/images/wood.png").convert_alpha()
            wood2 = pygame.image.load("../resources/images/wood2.png").convert_alpha()
            rect = pygame.Rect(251, 357, 86, 22)
            self.beam_image = wood.subsurface(rect).copy()
            rect = pygame.Rect(16, 252, 22, 84)
            self.column_image = wood2.subsurface(rect).copy()
            self._images_loaded = True
        except pygame.error:
            pass

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
        moment = 1000
        body = pm.Body(self._mass, moment)
        body.position = pos
        body.angle = angle
        
        shape = pm.Poly.create_box(body, (self._length, self._height))
        shape.color = (0, 0, 255)
        shape.friction = 0.5
        shape.collision_type = 2
        
        space.add(body, shape)
        
        self.body = body
        self.shape = shape
        self.is_static = False

    def to_pygame(self, p):
        """将pymunk坐标转换为pygame坐标"""
        return int(p.x), int(-p.y + 600)

    def draw_poly(self, element, screen):
        """绘制木材"""
        # 确保图片已加载
        self._load_images()
        
        poly = self.shape
        ps = poly.get_vertices()
        ps.append(ps[0])
        ps = map(self.to_pygame, ps)
        ps = list(ps)
        color = (255, 0, 0)
        pygame.draw.lines(screen, color, False, ps)
        
        if element == 'beams' and self.beam_image:
            p = poly.body.position
            p = Vec2d(*self.to_pygame(p))
            angle_degrees = math.degrees(poly.body.angle) + 180
            rotated_logo_img = pygame.transform.rotate(self.beam_image,
                                                       angle_degrees)
            offset = Vec2d(*rotated_logo_img.get_size()) / 2.
            p = p - offset
            np = p
            screen.blit(rotated_logo_img, (np.x, np.y))
            
        if element == 'columns' and self.column_image:
            p = poly.body.position
            p = Vec2d(*self.to_pygame(p))
            angle_degrees = math.degrees(poly.body.angle) + 180
            rotated_logo_img = pygame.transform.rotate(self.column_image,
                                                       angle_degrees)
            offset = Vec2d(*rotated_logo_img.get_size()) / 2.
            p = p - offset
            np = p
            screen.blit(rotated_logo_img, (np.x, np.y))
