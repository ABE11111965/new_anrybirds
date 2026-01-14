"""
愤怒的小鸟 - 双人策略对抗版
游戏流程：
1. 布防阶段 (Defense Phase) - 防守方放置猪和建筑
2. 进攻阶段 (Attack Phase) - 进攻方发射小鸟
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
PLACE_ZONE_BOTTOM = 60  # 地面高度

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


def draw_build_phase_ui():
    """绘制布防阶段UI"""
    # 半透明背景面板
    panel = pygame.Surface((400, 200))
    panel.fill((50, 50, 80))
    panel.set_alpha(200)
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

    # 绘制放置区域边界线
    pygame.draw.line(screen, YELLOW, (PLACE_ZONE_LEFT, 0), (PLACE_ZONE_LEFT, 540), 2)

    # 左侧提示
    zone_text = small_font.render("Place Zone ->", True, YELLOW)
    screen.blit(zone_text, (PLACE_ZONE_LEFT + 10, 300))


def draw_ghost_preview():
    """绘制鼠标位置的预览图"""
    if x_mouse < PLACE_ZONE_LEFT or y_mouse > 540:
        return

    # 根据当前选择绘制预览
    if current_place_type == PLACE_PIG and level.can_place('pigs'):
        screen.blit(pig_preview, (x_mouse - 15, y_mouse - 15))
    elif current_place_type == PLACE_COLUMN and level.can_place('columns'):
        screen.blit(column_preview_ghost, (x_mouse - 11, y_mouse - 42))
    elif current_place_type == PLACE_BEAM and level.can_place('beams'):
        screen.blit(beam_preview_ghost, (x_mouse - 43, y_mouse - 11))


def place_object(x, y):
    """在指定位置放置物体"""
    global current_place_type

    # 检查是否在有效放置区域
    if x < PLACE_ZONE_LEFT or y > 540:
        return False

    # 转换为pymunk坐标
    pymunk_y = -y + 600

    # 确保不会放置在地面以下
    if pymunk_y < PLACE_ZONE_BOTTOM + 20:
        pymunk_y = PLACE_ZONE_BOTTOM + 20

    if current_place_type == PLACE_PIG and level.can_place('pigs'):
        # 放置猪 - 使用静态body防止掉落
        pig = Pig(x, pymunk_y, space, static=True)
        pigs.append(pig)
        placed_static_bodies.append(pig)
        level.consume_item('pigs')
        return True

    elif current_place_type == PLACE_COLUMN and level.can_place('columns'):
        # 放置竖木
        p = (x, pymunk_y)
        column = Polygon(p, 20, 85, space, static=True)
        columns.append(column)
        placed_static_bodies.append(column)
        level.consume_item('columns')
        return True

    elif current_place_type == PLACE_BEAM and level.can_place('beams'):
        # 放置横木
        p = (x, pymunk_y)
        beam = Polygon(p, 85, 20, space, static=True)
        beams.append(beam)
        placed_static_bodies.append(beam)
        level.consume_item('beams')
        return True

    return False


def activate_physics():
    """激活所有静态物体的物理模拟"""
    for obj in placed_static_bodies:
        if hasattr(obj, 'activate'):
            obj.activate(space)
    placed_static_bodies.clear()


def draw_level_cleared():
    """绘制进攻胜利画面"""
    global game_state, bonus_score_once, score

    level_cleared = bold_font3.render("ATTACKER WINS!", True, WHITE)
    score_level_cleared = bold_font2.render(str(score), True, WHITE)

    if level.number_of_birds >= 0 and len(pigs) == 0:
        if bonus_score_once:
            score += (level.number_of_birds - 1) * 10000
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


def draw_level_failed():
    """绘制防守胜利画面"""
    global game_state

    failed = bold_font3.render("DEFENDER WINS!", True, WHITE)

    if level.number_of_birds <= 0 and time.time() - t2 > 5 and len(pigs) > 0:
        game_state = GAME_STATE_FAILED

        rect = pygame.Rect(300, 0, 600, 800)
        pygame.draw.rect(screen, BLACK, rect)
        screen.blit(failed, (400, 90))
        screen.blit(pig_happy, (380, 120))
        screen.blit(replay_button, (520, 460))


def restart():
    """重置关卡"""
    global placed_static_bodies

    pigs_to_remove = []
    birds_to_remove = []
    columns_to_remove = []
    beams_to_remove = []

    for pig in pigs:
        pigs_to_remove.append(pig)
    for pig in pigs_to_remove:
        space.remove(pig.shape, pig.shape.body)
        pigs.remove(pig)

    for bird in birds:
        birds_to_remove.append(bird)
    for bird in birds_to_remove:
        space.remove(bird.shape, bird.shape.body)
        birds.remove(bird)

    for column in columns:
        columns_to_remove.append(column)
    for column in columns_to_remove:
        space.remove(column.shape, column.shape.body)
        columns.remove(column)

    for beam in beams:
        beams_to_remove.append(beam)
    for beam in beams_to_remove:
        space.remove(beam.shape, beam.shape.body)
        beams.remove(beam)

    placed_static_bodies.clear()


def post_solve_bird_pig(arbiter, space, _):
    """鸟与猪的碰撞处理"""
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
        space.remove(pig.shape, pig.shape.body)
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
        space.remove(b, b.body)
        global score
        score += 5000


def post_solve_pig_wood(arbiter, space, _):
    """猪与木材的碰撞处理"""
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
        space.remove(pig.shape, pig.shape.body)
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


# 主游戏循环
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

        # 鼠标点击处理
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == GAME_STATE_BUILD:
                # 布防阶段 - 放置物体
                place_object(x_mouse, y_mouse)

            elif game_state == GAME_STATE_PLAY:
                # 进攻阶段 - 拉弓
                if (x_mouse > 100 and x_mouse < 250 and
                        y_mouse > 370 and y_mouse < 550):
                    mouse_pressed = True

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
        # 布防阶段
        draw_build_phase_ui()
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

    # 处理小鸟
    birds_to_remove = []
    pigs_to_remove = []
    counter += 1

    for bird in birds:
        if bird.shape.body.position.y < 0:
            birds_to_remove.append(bird)
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

    # 移除小鸟和猪
    for bird in birds_to_remove:
        space.remove(bird.shape, bird.shape.body)
        birds.remove(bird)

    for pig in pigs_to_remove:
        space.remove(pig.shape, pig.shape.body)
        pigs.remove(pig)

    # 绘制地面
    for line in static_lines:
        body = line.body
        pv1 = body.position + line.a.rotated(body.angle)
        pv2 = body.position + line.b.rotated(body.angle)
        p1 = to_pygame(pv1)
        p2 = to_pygame(pv2)
        pygame.draw.lines(screen, (150, 150, 150), False, [p1, p2])

    # 绘制猪
    i = 0
    for pig in pigs:
        i += 1
        pig_shape = pig.shape
        if pig_shape.body.position.y < 0:
            pigs_to_remove.append(pig)

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

    # 更新物理（仅在非布防阶段）
    if game_state != GAME_STATE_BUILD:
        dt = 1.0 / 50.0 / 2.
        for x in range(2):
            space.step(dt)

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

    # 暂停画面
    if game_state == GAME_STATE_PAUSE:
        screen.blit(play_button, (500, 200))
        screen.blit(replay_button, (500, 300))

    # 胜负判定
    if game_state == GAME_STATE_PLAY:
        draw_level_cleared()
        draw_level_failed()

    pygame.display.flip()
    clock.tick(50)
    pygame.display.set_caption(f"Angry Birds PvP - FPS: {int(clock.get_fps())}")

pygame.quit()
