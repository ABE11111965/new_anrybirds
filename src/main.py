"""
愤怒的小鸟 - 双人策略对抗版
游戏流程：
1. 布防阶段 (Defense Phase) - 防守方放置猪和建筑
2. 进攻阶段 (Attack Phase) - 进攻方发射小鸟

修复版本：
- 完善的胜负判定逻辑
- 边界检测（飞出屏幕的物体自动移除）
- 60帧预热稳定期
- 场景静止检测
"""

import os
import sys
import math
import time
import pygame
current_path = os.getcwd()
import pymunk as pm
from characters import Bird, Pig
from level import Level
from polygon import Polygon


pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    print("警告: 未找到音频设备，游戏将无声运行。")

# 游戏状态常量
GAME_STATE_BUILD = 0      # 布防阶段
GAME_STATE_PLAY = 1       # 进攻阶段
GAME_STATE_PAUSE = 2      # 暂停
GAME_STATE_FAILED = 3     # 进攻失败（防守方胜）
GAME_STATE_CLEARED = 4    # 进攻成功（进攻方胜）

# 放置物体类型
PLACE_NONE = 0
PLACE_PIG = 1
PLACE_COLUMN = 2
PLACE_BEAM = 3

screen = pygame.display.set_mode((1200, 650))
pygame.display.set_caption("Angry Birds - PvP Mode")

# 加载图片资源
redbird = pygame.image.load(
    "../resources/images/red-bird3.png").convert_alpha()
background2 = pygame.image.load(
    "../resources/images/background3.png").convert_alpha()
sling_image = pygame.image.load(
    "../resources/images/sling-3.png").convert_alpha()
full_sprite = pygame.image.load(
    "../resources/images/full-sprite.png").convert_alpha()

# 裁剪猪的图片
rect = pygame.Rect(181, 1050, 50, 50)
cropped = full_sprite.subsurface(rect).copy()
pig_image = pygame.transform.scale(cropped, (30, 30))

# 加载其他资源
buttons = pygame.image.load(
    "../resources/images/selected-buttons.png").convert_alpha()
pig_happy = pygame.image.load(
    "../resources/images/pig_failed.png").convert_alpha()
stars = pygame.image.load(
    "../resources/images/stars-edited.png").convert_alpha()

# 裁剪星星图片
rect = pygame.Rect(0, 0, 200, 200)
star1 = stars.subsurface(rect).copy()
rect = pygame.Rect(204, 0, 200, 200)
star2 = stars.subsurface(rect).copy()
rect = pygame.Rect(426, 0, 200, 200)
star3 = stars.subsurface(rect).copy()

# 裁剪按钮图片
rect = pygame.Rect(164, 10, 60, 60)
pause_button = buttons.subsurface(rect).copy()
rect = pygame.Rect(24, 4, 100, 100)
replay_button = buttons.subsurface(rect).copy()
rect = pygame.Rect(142, 365, 130, 100)
next_button = buttons.subsurface(rect).copy()
rect = pygame.Rect(18, 212, 100, 100)
play_button = buttons.subsurface(rect).copy()

# 加载木材图片用于预览
wood = pygame.image.load("../resources/images/wood.png").convert_alpha()
wood2 = pygame.image.load("../resources/images/wood2.png").convert_alpha()
rect = pygame.Rect(251, 357, 86, 22)
beam_preview = wood.subsurface(rect).copy()
rect = pygame.Rect(16, 252, 22, 84)
column_preview = wood2.subsurface(rect).copy()

# 创建预览图片（半透明）
pig_preview = pig_image.copy()
pig_preview.set_alpha(150)
beam_preview_ghost = beam_preview.copy()
beam_preview_ghost.set_alpha(150)
column_preview_ghost = column_preview.copy()
column_preview_ghost.set_alpha(150)

clock = pygame.time.Clock()
running = True

# 物理引擎设置
space = pm.Space()
space.gravity = (0.0, -700.0)

# 游戏对象列表
pigs = []
birds = []
balls = []
polys = []
beams = []
columns = []
poly_points = []

# 游戏变量
ball_number = 0
polys_dict = {}
mouse_distance = 0
rope_lenght = 90
angle = 0
x_mouse = 0
y_mouse = 0
count = 0
mouse_pressed = False
t1 = 0
t2 = 0
tick_to_next_circle = 10

# 颜色定义
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
DARK_BLUE = (30, 60, 100)
ORANGE = (255, 165, 0)

# 弹弓位置
sling_x, sling_y = 135, 450
sling2_x, sling2_y = 160, 450

# 游戏状态
score = 0
game_state = GAME_STATE_BUILD
bird_path = []
counter = 0
restart_counter = False
bonus_score_once = True

# 布防阶段变量
current_place_type = PLACE_PIG  # 当前选中的放置类型
build_phase_complete = False
placed_static_bodies = []  # 存储布防阶段放置的静态物体

# 放置区域限制
PLACE_ZONE_LEFT = 600  # 只能在此x坐标右侧放置
PLACE_ZONE_BOTTOM = 60  # 地面高度（pymunk坐标系）
GROUND_Y_PYGAME = 540  # 地面Y坐标（pygame坐标系，540 = 600-60）

# ========== 物理稳定期变量 - 防止开局自爆 ==========
physics_activation_time = 0  # 物理激活时间戳
PHYSICS_STABILIZE_DURATION = 2.5  # 稳定期持续秒数（增加到2.5秒）
WARMUP_FRAMES = 60  # 预热帧数：激活物理后先运行60帧让物体稳定
damage_enabled = False  # 伤害开关：预热期间禁用伤害

# ========== 边界检测常量 ==========
BOUNDARY_LEFT = -100      # 左边界（pymunk坐标）
BOUNDARY_RIGHT = 1400     # 右边界（pymunk坐标）
BOUNDARY_BOTTOM = -100    # 下边界（pymunk坐标，物体掉落到这里就移除）
BOUNDARY_TOP = 800        # 上边界（pymunk坐标）

# 进攻阶段计时器
ATTACK_TIME_LIMIT = 180  # 进攻阶段时间限制（秒）
attack_start_time = 0

# ========== 场景静止检测 ==========
STILLNESS_THRESHOLD = 5.0  # 速度阈值：低于此值视为静止
STILLNESS_DURATION = 1.5   # 需要保持静止的秒数
scene_still_start_time = 0  # 场景开始静止的时间

# 字体
bold_font = pygame.font.SysFont("arial", 30, bold=True)
bold_font2 = pygame.font.SysFont("arial", 40, bold=True)
bold_font3 = pygame.font.SysFont("arial", 50, bold=True)
small_font = pygame.font.SysFont("arial", 20)

wall = False

# 静态地面
static_body = pm.Body(body_type=pm.Body.STATIC)
static_lines = [pm.Segment(static_body, (0.0, 60.0), (1200.0, 60.0), 0.0)]
static_lines1 = [pm.Segment(static_body, (1200.0, 060.0), (1200.0, 800.0), 0.0)]

for line in static_lines:
    line.elasticity = 0.95
    line.friction = 1
    line.collision_type = 3

for line in static_lines1:
    line.elasticity = 0.95
    line.friction = 1
    line.collision_type = 3

space.add(static_body)
for line in static_lines:
    space.add(line)


def to_pygame(p):
    """将pymunk坐标转换为pygame坐标"""
    return int(p.x), int(-p.y + 600)


def to_pymunk(p):
    """将pygame坐标转换为pymunk坐标"""
    return int(p[0]), int(-p[1] + 600)


def vector(p0, p1):
    """计算两点间的向量"""
    a = p1[0] - p0[0]
    b = p1[1] - p0[1]
    return (a, b)


def unit_vector(v):
    """计算单位向量"""
    h = ((v[0]**2) + (v[1]**2))**0.5
    if h == 0:
        h = 0.000000000000001
    ua = v[0] / h
    ub = v[1] / h
    return (ua, ub)


def distance(xo, yo, x, y):
    """计算两点间距离"""
    dx = x - xo
    dy = y - yo
    d = ((dx ** 2) + (dy ** 2)) ** 0.5
    return d


def load_music():
    """加载背景音乐"""
    if pygame.mixer.get_init() is None:
        return

    try:
        song1 = '../resources/sounds/angry-birds.ogg'
        pygame.mixer.music.load(song1)
        pygame.mixer.music.play(-1)
    except pygame.error:
        print("无法加载背景音乐")


def sling_action():
    """弹弓行为"""
    global mouse_distance, rope_lenght, angle, x_mouse, y_mouse

    v = vector((sling_x, sling_y), (x_mouse, y_mouse))
    uv = unit_vector(v)
    uv1 = uv[0]
    uv2 = uv[1]
    mouse_distance = distance(sling_x, sling_y, x_mouse, y_mouse)
    pu = (uv1 * rope_lenght + sling_x, uv2 * rope_lenght + sling_y)
    bigger_rope = 102
    x_redbird = x_mouse - 20
    y_redbird = y_mouse - 20

    if mouse_distance > rope_lenght:
        pux, puy = pu
        pux -= 20
        puy -= 20
        pul = pux, puy
        screen.blit(redbird, pul)
        pu2 = (uv1 * bigger_rope + sling_x, uv2 * bigger_rope + sling_y)
        pygame.draw.line(screen, (0, 0, 0), (sling2_x, sling2_y), pu2, 5)
        screen.blit(redbird, pul)
        pygame.draw.line(screen, (0, 0, 0), (sling_x, sling_y), pu2, 5)
    else:
        mouse_distance += 10
        pu3 = (uv1 * mouse_distance + sling_x, uv2 * mouse_distance + sling_y)
        pygame.draw.line(screen, (0, 0, 0), (sling2_x, sling2_y), pu3, 5)
        screen.blit(redbird, (x_redbird, y_redbird))
        pygame.draw.line(screen, (0, 0, 0), (sling_x, sling_y), pu3, 5)

    dy = y_mouse - sling_y
    dx = x_mouse - sling_x
    if dx == 0:
        dx = 0.00000000000001
    angle = math.atan((float(dy)) / dx)


def get_object_bounds(obj):
    """
    获取物体的边界框（pygame坐标系）
    返回: (left, right, top, bottom) - 注意pygame中y向下增大
    """
    if isinstance(obj, Pig):
        # 猪是圆形
        pos = obj.body.position
        pygame_pos = to_pygame(pos)
        radius = obj.shape.radius
        return (
            pygame_pos[0] - radius,   # left
            pygame_pos[0] + radius,   # right
            pygame_pos[1] - radius,   # top (pygame中y小的在上)
            pygame_pos[1] + radius    # bottom
        )
    elif isinstance(obj, Polygon):
        # 木材是矩形
        pos = obj.body.position
        pygame_pos = to_pygame(pos)
        # 获取半宽和半高
        half_w = obj._length / 2
        half_h = obj._height / 2
        return (
            pygame_pos[0] - half_w,   # left
            pygame_pos[0] + half_w,   # right
            pygame_pos[1] - half_h,   # top
            pygame_pos[1] + half_h    # bottom
        )
    return None


def get_snap_position(mouse_x, mouse_y, obj_width, obj_height):
    """
    智能吸附系统 - 计算物体应该放置的位置

    【坐标系说明】
    - Pygame: 原点在左上角，Y轴向下
    - Pymunk: 原点在左下角，Y轴向上
    - 转换公式: pygame_y = 600 - pymunk_y

    参数:
        mouse_x: 鼠标X坐标（pygame）
        mouse_y: 鼠标Y坐标（pygame）
        obj_width: 物体宽度
        obj_height: 物体高度

    返回:
        (snap_x, snap_y, snapped): snap后的pygame坐标（中心点），以及是否发生了吸附
    """
    # 物体的半高（用于计算放置位置）
    half_height = obj_height / 2

    # 找到鼠标X坐标下方最高的表面
    highest_surface_y = GROUND_Y_PYGAME  # 默认是地面（pygame坐标）
    snapped = False
    snap_threshold = 80  # 吸附阈值：鼠标距离表面多少像素内才吸附

    # 遍历所有已放置的物体
    all_objects = list(pigs) + list(columns) + list(beams)

    for obj in all_objects:
        bounds = get_object_bounds(obj)
        if bounds is None:
            continue

        left, right, top, bottom = bounds

        # 检查鼠标X是否在物体宽度范围内（加一点容差）
        tolerance = obj_width / 2 + 5
        if mouse_x >= left - tolerance and mouse_x <= right + tolerance:
            # 这个物体在鼠标下方的X范围内
            # top是物体顶部的pygame Y坐标（数值越小越靠上）
            if top < highest_surface_y:
                # 检查鼠标是否在物体上方
                if mouse_y < top + snap_threshold:
                    highest_surface_y = top
                    snapped = True

    # 计算最终放置位置
    # 物体中心应该在表面上方 half_height 的位置
    snap_y = highest_surface_y - half_height

    # 如果鼠标位置明显高于吸附位置（超过阈值），则使用鼠标位置
    if mouse_y < snap_y - snap_threshold and snapped:
        # 玩家明显想放在更高的位置，取消吸附
        snap_y = mouse_y
        snapped = False
    elif not snapped:
        # 没有找到可吸附的物体
        # 如果鼠标在地面以上，使用鼠标位置；否则吸附到地面
        if mouse_y < GROUND_Y_PYGAME - half_height:
            snap_y = mouse_y
        else:
            snap_y = GROUND_Y_PYGAME - half_height
            snapped = True

    return mouse_x, snap_y, snapped


def get_object_dimensions(place_type):
    """获取物体的尺寸（宽度, 高度）"""
    if place_type == PLACE_PIG:
        return 28, 28  # 猪的直径
    elif place_type == PLACE_COLUMN:
        return 20, 85  # 竖木
    elif place_type == PLACE_BEAM:
        return 85, 20  # 横木
    return 0, 0


def check_placement_valid(x, y, width, height):
    """
    检查放置位置是否有效（不与其他物体重叠）

    参数:
        x, y: pygame坐标系中的中心位置
        width, height: 物体尺寸

    返回:
        True 如果位置有效，False 如果会重叠
    """
    # 计算新物体的边界
    half_w = width / 2
    half_h = height / 2
    new_left = x - half_w
    new_right = x + half_w
    new_top = y - half_h
    new_bottom = y + half_h

    # 检查与所有已放置物体的重叠
    all_objects = list(pigs) + list(columns) + list(beams)

    for obj in all_objects:
        bounds = get_object_bounds(obj)
        if bounds is None:
            continue

        left, right, top, bottom = bounds

        # 检查矩形重叠（加一点容差防止刚好接触）
        overlap_tolerance = 3
        if (new_left < right - overlap_tolerance and
            new_right > left + overlap_tolerance and
            new_top < bottom - overlap_tolerance and
            new_bottom > top + overlap_tolerance):
            return False

    return True


def draw_build_phase_ui():
    """绘制布防阶段UI"""
    # 半透明背景面板
    panel = pygame.Surface((400, 220))
    panel.fill((50, 50, 80))
    panel.set_alpha(220)
    screen.blit(panel, (400, 10))

    # 标题
    title = bold_font2.render("DEFENSE PHASE", True, YELLOW)
    screen.blit(title, (470, 20))

    # 库存显示
    inv = level.inventory
    y_offset = 70

    # 猪的数量
    pig_text = f"[1] Pig: {inv['pigs']}"
    color = GREEN if current_place_type == PLACE_PIG else WHITE
    if inv['pigs'] == 0:
        color = GRAY
    text = small_font.render(pig_text, True, color)
    screen.blit(text, (420, y_offset))
    screen.blit(pig_image, (530, y_offset - 5))

    # 竖木数量
    y_offset += 30
    col_text = f"[2] Column: {inv['columns']}"
    color = GREEN if current_place_type == PLACE_COLUMN else WHITE
    if inv['columns'] == 0:
        color = GRAY
    text = small_font.render(col_text, True, color)
    screen.blit(text, (420, y_offset))

    # 横木数量
    y_offset += 30
    beam_text = f"[3] Beam: {inv['beams']}"
    color = GREEN if current_place_type == PLACE_BEAM else WHITE
    if inv['beams'] == 0:
        color = GRAY
    text = small_font.render(beam_text, True, color)
    screen.blit(text, (420, y_offset))

    # 提示信息
    y_offset += 40
    if not level.all_pigs_placed():
        hint = small_font.render("Place all pigs to continue!", True, RED)
    else:
        hint = small_font.render("Press SPACE to start attack!", True, GREEN)
    screen.blit(hint, (430, y_offset))

    # 右键删除提示
    y_offset += 25
    hint2 = small_font.render("Right-click to remove objects", True, ORANGE)
    screen.blit(hint2, (430, y_offset))

    # 绘制放置区域边界线
    pygame.draw.line(screen, YELLOW, (PLACE_ZONE_LEFT, 0), (PLACE_ZONE_LEFT, 540), 2)

    # 左侧提示
    zone_text = small_font.render("Place Zone ->", True, YELLOW)
    screen.blit(zone_text, (PLACE_ZONE_LEFT + 10, 300))


def draw_attack_timer():
    """绘制进攻阶段倒计时"""
    if game_state != GAME_STATE_PLAY:
        return

    elapsed = time.time() - attack_start_time
    remaining = max(0, ATTACK_TIME_LIMIT - elapsed)

    minutes = int(remaining // 60)
    seconds = int(remaining % 60)

    # 根据剩余时间选择颜色
    if remaining > 60:
        color = WHITE
    elif remaining > 30:
        color = YELLOW
    else:
        color = RED

    timer_text = f"Time: {minutes}:{seconds:02d}"
    text = bold_font.render(timer_text, True, color)
    screen.blit(text, (1050, 200))


def draw_ghost_preview():
    """绘制鼠标位置的预览图（带吸附效果）"""
    if x_mouse < PLACE_ZONE_LEFT or y_mouse > 540:
        return

    # 获取当前物体尺寸
    obj_width, obj_height = get_object_dimensions(current_place_type)
    if obj_width == 0:
        return

    # 计算吸附位置（这里得到的是物体中心点的pygame坐标）
    snap_x, snap_y, snapped = get_snap_position(x_mouse, y_mouse, obj_width, obj_height)

    # 检查放置是否有效
    is_valid = check_placement_valid(snap_x, snap_y, obj_width, obj_height)

    # 根据当前选择绘制预览
    # 【关键】预览图绘制位置 = 中心点 - 图片半尺寸
    if current_place_type == PLACE_PIG and level.can_place('pigs'):
        # 绘制吸附指示线（如果发生吸附）
        if snapped:
            pygame.draw.line(screen, GREEN, (snap_x - 20, snap_y + 14),
                           (snap_x + 20, snap_y + 14), 2)

        # 设置预览颜色（有效=半透明，无效=红色）
        preview = pig_preview.copy()
        if not is_valid:
            preview.fill((255, 100, 100), special_flags=pygame.BLEND_MULT)
        # 猪的图片是30x30，中心对齐
        screen.blit(preview, (snap_x - 15, snap_y - 15))

    elif current_place_type == PLACE_COLUMN and level.can_place('columns'):
        if snapped:
            pygame.draw.line(screen, GREEN, (snap_x - 15, snap_y + 42),
                           (snap_x + 15, snap_y + 42), 2)

        preview = column_preview_ghost.copy()
        if not is_valid:
            preview.fill((255, 100, 100), special_flags=pygame.BLEND_MULT)
        # 竖木图片是22x84，中心对齐
        screen.blit(preview, (snap_x - 11, snap_y - 42))

    elif current_place_type == PLACE_BEAM and level.can_place('beams'):
        if snapped:
            pygame.draw.line(screen, GREEN, (snap_x - 50, snap_y + 10),
                           (snap_x + 50, snap_y + 10), 2)

        preview = beam_preview_ghost.copy()
        if not is_valid:
            preview.fill((255, 100, 100), special_flags=pygame.BLEND_MULT)
        # 横木图片是86x22，中心对齐
        screen.blit(preview, (snap_x - 43, snap_y - 11))


def place_object(x, y):
    """
    在指定位置放置物体（使用智能吸附）

    【坐标转换说明】
    1. 输入: pygame屏幕坐标 (x, y)
    2. 通过 get_snap_position 计算吸附后的pygame坐标 (snap_x, snap_y)
    3. 转换为pymunk坐标: pymunk_y = 600 - snap_y
    4. 创建物体时使用pymunk坐标（物体中心点）
    """
    global current_place_type

    # 检查是否在有效放置区域
    if x < PLACE_ZONE_LEFT or y > 540:
        return False

    # 获取物体尺寸
    obj_width, obj_height = get_object_dimensions(current_place_type)
    if obj_width == 0:
        return False

    # 计算吸附位置（pygame坐标，物体中心点）
    snap_x, snap_y, snapped = get_snap_position(x, y, obj_width, obj_height)

    # 检查放置是否有效
    if not check_placement_valid(snap_x, snap_y, obj_width, obj_height):
        return False

    # 转换为pymunk坐标（物体中心点）
    pymunk_x = snap_x
    pymunk_y = 600 - snap_y  # pygame转pymunk

    if current_place_type == PLACE_PIG and level.can_place('pigs'):
        # 放置猪 - 使用静态body防止掉落
        pig = Pig(pymunk_x, pymunk_y, space, static=True)
        pigs.append(pig)
        placed_static_bodies.append(pig)
        level.consume_item('pigs')
        return True

    elif current_place_type == PLACE_COLUMN and level.can_place('columns'):
        # 放置竖木
        p = (pymunk_x, pymunk_y)
        column = Polygon(p, 20, 85, space, static=True)
        columns.append(column)
        placed_static_bodies.append(column)
        level.consume_item('columns')
        return True

    elif current_place_type == PLACE_BEAM and level.can_place('beams'):
        # 放置横木
        p = (pymunk_x, pymunk_y)
        beam = Polygon(p, 85, 20, space, static=True)
        beams.append(beam)
        placed_static_bodies.append(beam)
        level.consume_item('beams')
        return True

    return False


def remove_object_at(x, y):
    """
    移除指定位置的物体（右键删除功能）

    参数:
        x, y: pygame坐标

    返回:
        True 如果成功移除，False 如果没有找到物体
    """
    # 只在布防阶段有效
    if game_state != GAME_STATE_BUILD:
        return False

    # 检查是否在放置区域内
    if x < PLACE_ZONE_LEFT:
        return False

    # 遍历所有物体，找到被点击的那个
    # 优先检查猪（因为它们更重要）
    for pig in pigs[:]:  # 使用切片复制列表以便安全删除
        bounds = get_object_bounds(pig)
        if bounds:
            left, right, top, bottom = bounds
            if left <= x <= right and top <= y <= bottom:
                # 找到了！移除它
                space.remove(pig.shape, pig.body)
                pigs.remove(pig)
                if pig in placed_static_bodies:
                    placed_static_bodies.remove(pig)
                # 返还库存
                level.inventory['pigs'] += 1
                return True

    # 检查竖木
    for column in columns[:]:
        bounds = get_object_bounds(column)
        if bounds:
            left, right, top, bottom = bounds
            if left <= x <= right and top <= y <= bottom:
                space.remove(column.shape, column.body)
                columns.remove(column)
                if column in placed_static_bodies:
                    placed_static_bodies.remove(column)
                level.inventory['columns'] += 1
                return True

    # 检查横木
    for beam in beams[:]:
        bounds = get_object_bounds(beam)
        if bounds:
            left, right, top, bottom = bounds
            if left <= x <= right and top <= y <= bottom:
                space.remove(beam.shape, beam.body)
                beams.remove(beam)
                if beam in placed_static_bodies:
                    placed_static_bodies.remove(beam)
                level.inventory['beams'] += 1
                return True

    return False


def activate_physics():
    """
    激活所有静态物体的物理模拟

    【预热机制说明】
    为了防止"开局自爆"，我们在激活物理后执行以下步骤：
    1. 将所有静态物体转换为动态物体
    2. 执行60帧的"隐形预热"物理模拟（不渲染，不判定伤害）
    3. 让物体在这60帧内自然沉降稳定
    4. 预热完成后才开始正式的游戏渲染和伤害判定
    """
    global physics_activation_time, attack_start_time, damage_enabled

    # 记录激活时间
    physics_activation_time = time.time()
    attack_start_time = time.time()

    # 【关键】预热期间禁用伤害
    damage_enabled = False

    # 激活所有静态物体
    for obj in placed_static_bodies:
        if hasattr(obj, 'activate'):
            obj.activate(space)

    # ========== 60帧预热模拟 ==========
    # 在这里执行60帧的物理更新，但不渲染画面
    # 这让物体有时间自然沉降，避免突然激活时的剧烈碰撞
    print("[预热] 开始60帧隐形物理模拟...")
    dt = 1.0 / 60.0  # 每帧时间步长
    for frame in range(WARMUP_FRAMES):
        space.step(dt)
    print("[预热] 预热完成，物体已稳定")

    placed_static_bodies.clear()

    # 预热完成后，延迟启用伤害（在主循环中通过时间判断）


def is_in_stabilization_period():
    """
    检查是否在物理稳定期内
    稳定期内猪不会受到伤害，防止因微小穿模导致的"自爆"
    """
    if physics_activation_time == 0:
        return True  # 未激活时也返回True防止误伤
    return (time.time() - physics_activation_time) < PHYSICS_STABILIZE_DURATION


def remove_out_of_bounds_objects():
    """
    【边界检测】移除飞出屏幕边界的物体

    这是修复"游戏无法结算"问题的关键函数。
    当物体（尤其是猪）被弹飞到屏幕外时，如果不移除它们，
    pigs列表永远不为空，导致胜利判定失败。

    边界定义（pymunk坐标系）：
    - X < -100 或 X > 1400: 飞出左右边界
    - Y < -100: 掉落到地面以下
    """
    global score

    # 检查猪是否飞出边界
    pigs_to_remove = []
    for pig in pigs:
        pos = pig.body.position
        # 【关键判定】检查pymunk坐标是否超出边界
        if (pos.x < BOUNDARY_LEFT or pos.x > BOUNDARY_RIGHT or
            pos.y < BOUNDARY_BOTTOM):
            pigs_to_remove.append(pig)
            score += 5000  # 坠崖死亡也加分
            print(f"[边界检测] 猪飞出边界被移除: ({pos.x:.0f}, {pos.y:.0f})")

    for pig in pigs_to_remove:
        try:
            space.remove(pig.shape, pig.body)
        except:
            pass
        if pig in pigs:
            pigs.remove(pig)

    # 检查小鸟是否飞出边界
    birds_to_remove = []
    for bird in birds:
        pos = bird.body.position
        if (pos.x < BOUNDARY_LEFT or pos.x > BOUNDARY_RIGHT or
            pos.y < BOUNDARY_BOTTOM):
            birds_to_remove.append(bird)

    for bird in birds_to_remove:
        try:
            space.remove(bird.shape, bird.body)
        except:
            pass
        if bird in birds:
            birds.remove(bird)


def is_scene_still():
    """
    【场景静止检测】检查场景中所有动态物体是否都已静止

    用于优化失败判定：如果所有物体都静止了，不需要傻等5秒
    返回: True 如果所有物体速度都低于阈值
    """
    # 检查所有猪的速度
    for pig in pigs:
        if pig.body.velocity.length > STILLNESS_THRESHOLD:
            return False

    # 检查所有小鸟的速度
    for bird in birds:
        if bird.body.velocity.length > STILLNESS_THRESHOLD:
            return False

    # 检查所有木材的速度
    for column in columns:
        if column.body.velocity.length > STILLNESS_THRESHOLD:
            return False

    for beam in beams:
        if beam.body.velocity.length > STILLNESS_THRESHOLD:
            return False

    return True


def check_win_condition():
    """
    【核心胜负判定函数】

    这个函数每帧调用，检查游戏是否应该结束。

    进攻方胜利条件：
    - 所有猪都被消灭（pigs列表为空）

    防守方胜利条件（满足任一）：
    1. 进攻方用完所有小鸟，且场景静止，且猪还活着
    2. 超时（3分钟时间到）且猪还活着

    返回:
    - 'attacker_wins': 进攻方胜利
    - 'defender_wins': 防守方胜利
    - None: 游戏继续
    """
    global scene_still_start_time

    # 【胜利判定】进攻方胜利：所有猪都死了
    if len(pigs) == 0:
        print("[胜负判定] 所有猪已被消灭，进攻方胜利！")
        return 'attacker_wins'

    # 【失败判定1】超时判定
    if attack_start_time > 0:
        elapsed = time.time() - attack_start_time
        if elapsed >= ATTACK_TIME_LIMIT:
            print("[胜负判定] 时间耗尽，防守方胜利！")
            return 'defender_wins_timeout'

    # 【失败判定2】小鸟用完 + 场景静止
    if level.number_of_birds <= 0 and len(birds) == 0:
        # 检查场景是否静止
        if is_scene_still():
            # 记录静止开始时间
            if scene_still_start_time == 0:
                scene_still_start_time = time.time()
            # 静止超过指定时间，判定失败
            elif time.time() - scene_still_start_time > STILLNESS_DURATION:
                print("[胜负判定] 小鸟用完且场景静止，防守方胜利！")
                return 'defender_wins'
        else:
            # 场景还在动，重置静止计时
            scene_still_start_time = 0

    return None


def draw_level_cleared():
    """绘制进攻胜利画面"""
    global game_state, bonus_score_once, score

    level_cleared = bold_font3.render("ATTACKER WINS!", True, WHITE)
    score_level_cleared = bold_font2.render(str(score), True, WHITE)

    if bonus_score_once:
        score += (level.number_of_birds) * 10000
    bonus_score_once = False
    game_state = GAME_STATE_CLEARED

    rect = pygame.Rect(300, 0, 600, 800)
    pygame.draw.rect(screen, BLACK, rect)
    screen.blit(level_cleared, (400, 90))

    if score >= level.one_star and score <= level.two_star:
        screen.blit(star1, (310, 190))
    if score >= level.two_star and score <= level.three_star:
        screen.blit(star1, (310, 190))
        screen.blit(star2, (500, 170))
    if score >= level.three_star:
        screen.blit(star1, (310, 190))
        screen.blit(star2, (500, 170))
        screen.blit(star3, (700, 200))

    screen.blit(score_level_cleared, (550, 400))
    screen.blit(replay_button, (510, 480))
    screen.blit(next_button, (620, 480))


def draw_level_failed(timeout=False):
    """绘制防守胜利画面"""
    global game_state

    failed = bold_font3.render("DEFENDER WINS!", True, WHITE)
    game_state = GAME_STATE_FAILED

    rect = pygame.Rect(300, 0, 600, 800)
    pygame.draw.rect(screen, BLACK, rect)
    screen.blit(failed, (400, 90))

    # 如果是超时，显示超时信息
    if timeout:
        timeout_text = bold_font2.render("TIME'S UP!", True, RED)
        screen.blit(timeout_text, (480, 140))

    screen.blit(pig_happy, (380, 180))
    screen.blit(replay_button, (520, 460))


def restart():
    """重置关卡"""
    global placed_static_bodies, physics_activation_time, attack_start_time
    global damage_enabled, scene_still_start_time, bonus_score_once

    pigs_to_remove = []
    birds_to_remove = []
    columns_to_remove = []
    beams_to_remove = []

    for pig in pigs:
        pigs_to_remove.append(pig)
    for pig in pigs_to_remove:
        try:
            space.remove(pig.shape, pig.body)
        except:
            pass
        if pig in pigs:
            pigs.remove(pig)

    for bird in birds:
        birds_to_remove.append(bird)
    for bird in birds_to_remove:
        try:
            space.remove(bird.shape, bird.body)
        except:
            pass
        if bird in birds:
            birds.remove(bird)

    for column in columns:
        columns_to_remove.append(column)
    for column in columns_to_remove:
        try:
            space.remove(column.shape, column.body)
        except:
            pass
        if column in columns:
            columns.remove(column)

    for beam in beams:
        beams_to_remove.append(beam)
    for beam in beams_to_remove:
        try:
            space.remove(beam.shape, beam.body)
        except:
            pass
        if beam in beams:
            beams.remove(beam)

    placed_static_bodies.clear()
    physics_activation_time = 0
    attack_start_time = 0
    damage_enabled = False
    scene_still_start_time = 0
    bonus_score_once = True


def post_solve_bird_pig(arbiter, space, _):
    """鸟与猪的碰撞处理"""
    # 在稳定期内不造成伤害
    if is_in_stabilization_period():
        return

    surface = screen
    a, b = arbiter.shapes
    bird_body = a.body
    pig_body = b.body
    p = to_pygame(bird_body.position)
    p2 = to_pygame(pig_body.position)
    r = 30
    pygame.draw.circle(surface, BLACK, p, r, 4)
    pygame.draw.circle(surface, RED, p2, r, 4)

    pigs_to_remove = []
    for pig in pigs:
        if pig_body == pig.body:
            pig.life -= 20
            pigs_to_remove.append(pig)
            global score
            score += 10000

    for pig in pigs_to_remove:
        try:
            space.remove(pig.shape, pig.body)
        except:
            pass
        if pig in pigs:
            pigs.remove(pig)


def post_solve_bird_wood(arbiter, space, _):
    """鸟与木材的碰撞处理"""
    poly_to_remove = []
    if arbiter.total_impulse.length > 1100:
        a, b = arbiter.shapes
        for column in columns:
            if b == column.shape:
                poly_to_remove.append(column)
        for beam in beams:
            if b == beam.shape:
                poly_to_remove.append(beam)
        for poly in poly_to_remove:
            if poly in columns:
                columns.remove(poly)
            if poly in beams:
                beams.remove(poly)
        try:
            space.remove(b, b.body)
        except:
            pass
        global score
        score += 5000


def post_solve_pig_wood(arbiter, space, _):
    """
    猪与木材的碰撞处理

    【稳定期保护】在物理激活后的前2.5秒内，禁用此伤害判定
    这可以防止因物体紧贴而产生的"开局自爆"问题
    """
    # 【关键】在稳定期内不造成伤害
    if is_in_stabilization_period():
        return

    pigs_to_remove = []
    if arbiter.total_impulse.length > 700:
        pig_shape, wood_shape = arbiter.shapes
        for pig in pigs:
            if pig_shape == pig.shape:
                pig.life -= 20
                global score
                score += 10000
                if pig.life <= 0:
                    pigs_to_remove.append(pig)

    for pig in pigs_to_remove:
        try:
            space.remove(pig.shape, pig.body)
        except:
            pass
        if pig in pigs:
            pigs.remove(pig)


# 设置碰撞处理器
space.add_collision_handler(0, 1).post_solve = post_solve_bird_pig
space.add_collision_handler(0, 2).post_solve = post_solve_bird_wood
space.add_collision_handler(1, 2).post_solve = post_solve_pig_wood

# 加载音乐和关卡
load_music()
level = Level(pigs, columns, beams, space)
level.number = 0
level.load_level()


# ==================== 主游戏循环 ====================
while running:
    # 输入处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            # 布防阶段的按键处理
            elif game_state == GAME_STATE_BUILD:
                if event.key == pygame.K_1:
                    current_place_type = PLACE_PIG
                elif event.key == pygame.K_2:
                    current_place_type = PLACE_COLUMN
                elif event.key == pygame.K_3:
                    current_place_type = PLACE_BEAM
                elif event.key == pygame.K_SPACE:
                    # 检查是否所有猪都已放置
                    if level.all_pigs_placed():
                        game_state = GAME_STATE_PLAY
                        activate_physics()
                        t1 = time.time() * 1000

            # 其他状态的按键处理
            elif event.key == pygame.K_w:
                if wall:
                    for line in static_lines1:
                        space.remove(line)
                    wall = False
                else:
                    for line in static_lines1:
                        space.add(line)
                    wall = True

            elif event.key == pygame.K_s:
                space.gravity = (0.0, -10.0)
                level.bool_space = True

            elif event.key == pygame.K_n:
                space.gravity = (0.0, -700.0)
                level.bool_space = False

        # 鼠标左键点击处理
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == GAME_STATE_BUILD:
                # 布防阶段 - 放置物体
                place_object(x_mouse, y_mouse)

            elif game_state == GAME_STATE_PLAY:
                # 进攻阶段 - 拉弓
                if (x_mouse > 100 and x_mouse < 250 and
                        y_mouse > 370 and y_mouse < 550):
                    mouse_pressed = True

        # 鼠标右键点击处理 - 删除物体
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if game_state == GAME_STATE_BUILD:
                remove_object_at(x_mouse, y_mouse)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if game_state == GAME_STATE_PLAY:
                if mouse_pressed:
                    # 发射小鸟
                    mouse_pressed = False
                    if level.number_of_birds > 0:
                        level.number_of_birds -= 1
                        t1 = time.time() * 1000
                        xo = 154
                        yo = 156
                        if mouse_distance > rope_lenght:
                            mouse_distance = rope_lenght
                        if x_mouse < sling_x + 5:
                            bird = Bird(mouse_distance, angle, xo, yo, space)
                            birds.append(bird)
                        else:
                            bird = Bird(-mouse_distance, angle, xo, yo, space)
                            birds.append(bird)
                        if level.number_of_birds == 0:
                            t2 = time.time()

                # 暂停按钮
                if x_mouse < 60 and y_mouse < 155 and y_mouse > 90:
                    game_state = GAME_STATE_PAUSE

            elif game_state == GAME_STATE_PAUSE:
                if x_mouse > 500 and y_mouse > 200 and y_mouse < 300:
                    game_state = GAME_STATE_PLAY
                if x_mouse > 500 and y_mouse > 300:
                    restart()
                    level.load_level()
                    game_state = GAME_STATE_BUILD
                    bird_path = []
                    score = 0

            elif game_state == GAME_STATE_FAILED:
                if x_mouse > 500 and x_mouse < 620 and y_mouse > 450:
                    restart()
                    level.load_level()
                    game_state = GAME_STATE_BUILD
                    bird_path = []
                    score = 0

            elif game_state == GAME_STATE_CLEARED:
                if x_mouse > 610 and y_mouse > 450:
                    restart()
                    level.number += 1
                    game_state = GAME_STATE_BUILD
                    level.load_level()
                    score = 0
                    bird_path = []
                    bonus_score_once = True
                if x_mouse < 610 and x_mouse > 500 and y_mouse > 450:
                    restart()
                    level.load_level()
                    game_state = GAME_STATE_BUILD
                    bird_path = []
                    score = 0

    x_mouse, y_mouse = pygame.mouse.get_pos()

    # 绘制背景
    screen.fill((130, 200, 100))
    screen.blit(background2, (0, -50))

    # 绘制弹弓前部
    rect = pygame.Rect(50, 0, 70, 220)
    screen.blit(sling_image, (138, 420), rect)

    # 绘制轨迹
    for point in bird_path:
        pygame.draw.circle(screen, WHITE, point, 5, 0)

    # 绘制等待中的小鸟
    if level.number_of_birds > 0 and game_state == GAME_STATE_PLAY:
        for i in range(level.number_of_birds - 1):
            x = 100 - (i * 35)
            screen.blit(redbird, (x, 508))

    # 根据游戏状态绘制
    if game_state == GAME_STATE_BUILD:
        # 布防阶段 - 预览图先绘制
        draw_ghost_preview()
        # 绘制弹弓上的小鸟（预览）
        screen.blit(redbird, (130, 426))

    elif game_state == GAME_STATE_PLAY:
        # 进攻阶段
        if mouse_pressed and level.number_of_birds > 0:
            sling_action()
        else:
            if time.time() * 1000 - t1 > 300 and level.number_of_birds > 0:
                screen.blit(redbird, (130, 426))
            else:
                pygame.draw.line(screen, (0, 0, 0), (sling_x, sling_y - 8),
                                 (sling2_x, sling2_y - 7), 5)

    # ========== 物理更新区域（仅在进攻阶段）==========
    if game_state == GAME_STATE_PLAY:
        dt = 1.0 / 50.0 / 2.
        for _ in range(2):
            space.step(dt)

        # 【关键】边界检测：移除飞出屏幕的物体
        remove_out_of_bounds_objects()

    # 处理小鸟绘制
    birds_to_remove = []
    counter += 1

    for bird in birds:
        p = to_pygame(bird.shape.body.position)
        x, y = p
        x -= 22
        y -= 20
        screen.blit(redbird, (x, y))
        pygame.draw.circle(screen, BLUE, p, int(bird.shape.radius), 2)
        if counter >= 3 and time.time() - t1 < 5:
            bird_path.append(p)
            restart_counter = True

    if restart_counter:
        counter = 0
        restart_counter = False

    # 绘制地面
    for line in static_lines:
        body = line.body
        pv1 = body.position + line.a.rotated(body.angle)
        pv2 = body.position + line.b.rotated(body.angle)
        p1 = to_pygame(pv1)
        p2 = to_pygame(pv2)
        pygame.draw.lines(screen, (150, 150, 150), False, [p1, p2])

    # 绘制猪
    for pig in pigs:
        pig_shape = pig.shape
        p = to_pygame(pig_shape.body.position)
        x, y = p

        angle_degrees = math.degrees(pig_shape.body.angle)
        img = pygame.transform.rotate(pig_image, angle_degrees)
        w, h = img.get_size()
        x -= w * 0.5
        y -= h * 0.5
        screen.blit(img, (x, y))
        pygame.draw.circle(screen, BLUE, p, int(pig_shape.radius), 2)

    # 绘制木材
    for column in columns:
        column.draw_poly('columns', screen)
    for beam in beams:
        beam.draw_poly('beams', screen)

    # 绘制弹弓后部
    rect = pygame.Rect(0, 0, 60, 200)
    screen.blit(sling_image, (120, 420), rect)

    # 绘制分数
    score_font = bold_font.render("SCORE", True, WHITE)
    number_font = bold_font.render(str(score), True, WHITE)
    screen.blit(score_font, (1060, 90))
    if score == 0:
        screen.blit(number_font, (1100, 130))
    else:
        screen.blit(number_font, (1060, 130))

    # 绘制关卡信息
    level_text = small_font.render(f"Level: {level.number}", True, WHITE)
    screen.blit(level_text, (1060, 170))

    # 绘制暂停按钮（仅在游戏阶段）
    if game_state == GAME_STATE_PLAY:
        screen.blit(pause_button, (10, 90))
        # 绘制进攻阶段倒计时
        draw_attack_timer()

        # 显示稳定期提示
        if is_in_stabilization_period():
            stabilize_text = small_font.render("Stabilizing...", True, YELLOW)
            screen.blit(stabilize_text, (550, 300))

        # 显示剩余猪数和鸟数（调试信息）
        debug_text = small_font.render(f"Pigs: {len(pigs)} | Birds: {level.number_of_birds} | Flying: {len(birds)}", True, WHITE)
        screen.blit(debug_text, (10, 10))

    # 暂停画面
    if game_state == GAME_STATE_PAUSE:
        screen.blit(play_button, (500, 200))
        screen.blit(replay_button, (500, 300))

    # ===== 关键修复：UI在所有游戏物体之后绘制 =====
    if game_state == GAME_STATE_BUILD:
        draw_build_phase_ui()

    # ========== 【核心】胜负判定 ==========
    if game_state == GAME_STATE_PLAY:
        result = check_win_condition()
        if result == 'attacker_wins':
            draw_level_cleared()
        elif result == 'defender_wins':
            draw_level_failed(timeout=False)
        elif result == 'defender_wins_timeout':
            draw_level_failed(timeout=True)

    pygame.display.flip()
    clock.tick(50)
    pygame.display.set_caption(f"Angry Birds PvP - FPS: {int(clock.get_fps())}")

pygame.quit()
