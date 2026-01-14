"""
愤怒的小鸟 - 双人策略对抗版 (修复版)
修复内容：
1. 解决结算画面不显示（渲染循环缺失）的问题
2. 调整物理数值平衡（猪更易死，木头更硬，鸟力度减弱）
3. 优化胜负判定逻辑
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
# 注意：路径可能需要根据实际运行目录调整，这里保留原有的相对路径
try:
    redbird = pygame.image.load("../resources/images/red-bird3.png").convert_alpha()
    background2 = pygame.image.load("../resources/images/background3.png").convert_alpha()
    sling_image = pygame.image.load("../resources/images/sling-3.png").convert_alpha()
    full_sprite = pygame.image.load("../resources/images/full-sprite.png").convert_alpha()
    buttons = pygame.image.load("../resources/images/selected-buttons.png").convert_alpha()
    pig_happy = pygame.image.load("../resources/images/pig_failed.png").convert_alpha()
    stars = pygame.image.load("../resources/images/stars-edited.png").convert_alpha()
    wood = pygame.image.load("../resources/images/wood.png").convert_alpha()
    wood2 = pygame.image.load("../resources/images/wood2.png").convert_alpha()
except Exception as e:
    print(f"资源加载错误: {e}")
    # 提供备用纯色Surface防止崩溃
    redbird = pygame.Surface((30,30)); redbird.fill((255,0,0))
    background2 = pygame.Surface((1200,650)); background2.fill((255,255,255))
    sling_image = pygame.Surface((50,100)); sling_image.fill((100,50,0))
    full_sprite = pygame.Surface((100,100))
    buttons = pygame.Surface((100,100))
    pig_happy = pygame.Surface((100,100))
    stars = pygame.Surface((100,100))
    wood = pygame.Surface((100,20))
    wood2 = pygame.Surface((20,100))

# 裁剪猪的图片
rect = pygame.Rect(181, 1050, 50, 50)
cropped = full_sprite.subsurface(rect).copy()
pig_image = pygame.transform.scale(cropped, (30, 30))

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

# 预览图资源
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
ORANGE = (255, 165, 0)

# 弹弓位置
sling_x, sling_y = 135, 450
sling2_x, sling2_y = 160, 450

# 游戏状态变量
score = 0
game_state = GAME_STATE_BUILD
bird_path = []
counter = 0
restart_counter = False
bonus_score_once = True
is_timeout_failure = False # 标记是否因超时导致失败

# 布防阶段变量
current_place_type = PLACE_PIG
placed_static_bodies = []

# 放置区域限制
PLACE_ZONE_LEFT = 600
PLACE_ZONE_BOTTOM = 60
GROUND_Y_PYGAME = 540

# 物理稳定期变量
physics_activation_time = 0
PHYSICS_STABILIZE_DURATION = 2.5
WARMUP_FRAMES = 60
damage_enabled = False

# 边界检测常量
BOUNDARY_LEFT = -100
BOUNDARY_RIGHT = 1400
BOUNDARY_BOTTOM = -100

# 进攻阶段计时器
ATTACK_TIME_LIMIT = 180
attack_start_time = 0

# 场景静止检测
STILLNESS_THRESHOLD = 5.0
STILLNESS_DURATION = 1.5
scene_still_start_time = 0

# 强制结算倒计时 (防止死锁)
force_end_timer_start = 0
FORCE_END_DELAY = 5.0  # 小鸟用完后最多等5秒

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

# --- 辅助函数 ---

def to_pygame(p):
    return int(p.x), int(-p.y + 600)

def vector(p0, p1):
    a = p1[0] - p0[0]
    b = p1[1] - p0[1]
    return (a, b)

def unit_vector(v):
    h = ((v[0]**2) + (v[1]**2))**0.5
    if h == 0: h = 0.000000000000001
    return (v[0] / h, v[1] / h)

def distance(xo, yo, x, y):
    return ((x - xo)**2 + (y - yo)**2)**0.5

def load_music():
    if pygame.mixer.get_init() is None: return
    try:
        pygame.mixer.music.load('../resources/sounds/angry-birds.ogg')
        pygame.mixer.music.play(-1)
    except: pass

def sling_action():
    global mouse_distance, rope_lenght, angle, x_mouse, y_mouse
    v = vector((sling_x, sling_y), (x_mouse, y_mouse))
    uv = unit_vector(v)
    mouse_distance = distance(sling_x, sling_y, x_mouse, y_mouse)
    pu = (uv[0] * rope_lenght + sling_x, uv[1] * rope_lenght + sling_y)
    bigger_rope = 102

    if mouse_distance > rope_lenght:
        pux, puy = pu
        pul = pux - 20, puy - 20
        screen.blit(redbird, pul)
        pu2 = (uv[0] * bigger_rope + sling_x, uv[1] * bigger_rope + sling_y)
        pygame.draw.line(screen, (0, 0, 0), (sling2_x, sling2_y), pu2, 5)
        screen.blit(redbird, pul)
        pygame.draw.line(screen, (0, 0, 0), (sling_x, sling_y), pu2, 5)
    else:
        mouse_distance += 10
        pu3 = (uv[0] * mouse_distance + sling_x, uv[1] * mouse_distance + sling_y)
        pygame.draw.line(screen, (0, 0, 0), (sling2_x, sling2_y), pu3, 5)
        screen.blit(redbird, (x_mouse - 20, y_mouse - 20))
        pygame.draw.line(screen, (0, 0, 0), (sling_x, sling_y), pu3, 5)

    dy = y_mouse - sling_y
    dx = x_mouse - sling_x
    if dx == 0: dx = 0.00000000000001
    angle = math.atan((float(dy)) / dx)

def get_object_bounds(obj):
    if isinstance(obj, Pig):
        pos = to_pygame(obj.body.position)
        r = obj.shape.radius
        return (pos[0]-r, pos[0]+r, pos[1]-r, pos[1]+r)
    elif isinstance(obj, Polygon):
        pos = to_pygame(obj.body.position)
        hw, hh = obj._length/2, obj._height/2
        return (pos[0]-hw, pos[0]+hw, pos[1]-hh, pos[1]+hh)
    return None

def get_snap_position(mouse_x, mouse_y, obj_width, obj_height):
    half_height = obj_height / 2
    highest_surface_y = GROUND_Y_PYGAME
    snapped = False
    snap_threshold = 80

    all_objects = list(pigs) + list(columns) + list(beams)
    tolerance = obj_width / 2 + 5

    for obj in all_objects:
        bounds = get_object_bounds(obj)
        if not bounds: continue
        left, right, top, bottom = bounds

        if mouse_x >= left - tolerance and mouse_x <= right + tolerance:
            if top < highest_surface_y:
                if mouse_y < top + snap_threshold:
                    highest_surface_y = top
                    snapped = True

    snap_y = highest_surface_y - half_height
    if mouse_y < snap_y - snap_threshold and snapped:
        snap_y = mouse_y
        snapped = False
    elif not snapped:
        if mouse_y < GROUND_Y_PYGAME - half_height:
            snap_y = mouse_y
        else:
            snap_y = GROUND_Y_PYGAME - half_height
            snapped = True

    return mouse_x, snap_y, snapped

def get_object_dimensions(place_type):
    if place_type == PLACE_PIG: return 28, 28
    elif place_type == PLACE_COLUMN: return 20, 85
    elif place_type == PLACE_BEAM: return 85, 20
    return 0, 0

def check_placement_valid(x, y, width, height):
    half_w, half_h = width/2, height/2
    nl, nr, nt, nb = x-half_w, x+half_w, y-half_h, y+half_h
    all_objects = list(pigs) + list(columns) + list(beams)

    for obj in all_objects:
        b = get_object_bounds(obj)
        if not b: continue
        if (nl < b[1]-3 and nr > b[0]+3 and nt < b[3]-3 and nb > b[2]+3):
            return False
    return True

# --- 绘制函数 ---

def draw_build_phase_ui():
    panel = pygame.Surface((400, 220))
    panel.fill((50, 50, 80)); panel.set_alpha(220)
    screen.blit(panel, (400, 10))
    screen.blit(bold_font2.render("DEFENSE PHASE", True, YELLOW), (470, 20))

    inv = level.inventory
    y_off = 70

    col = GREEN if current_place_type == PLACE_PIG else WHITE
    if inv['pigs'] == 0: col = GRAY
    screen.blit(small_font.render(f"[1] Pig: {inv['pigs']}", True, col), (420, y_off))
    screen.blit(pig_image, (530, y_off - 5))

    y_off += 30
    col = GREEN if current_place_type == PLACE_COLUMN else WHITE
    if inv['columns'] == 0: col = GRAY
    screen.blit(small_font.render(f"[2] Column: {inv['columns']}", True, col), (420, y_off))

    y_off += 30
    col = GREEN if current_place_type == PLACE_BEAM else WHITE
    if inv['beams'] == 0: col = GRAY
    screen.blit(small_font.render(f"[3] Beam: {inv['beams']}", True, col), (420, y_off))

    y_off += 40
    if not level.all_pigs_placed():
        screen.blit(small_font.render("Place all pigs to continue!", True, RED), (430, y_off))
    else:
        screen.blit(small_font.render("Press SPACE to start attack!", True, GREEN), (430, y_off))

    screen.blit(small_font.render("Right-click to remove objects", True, ORANGE), (430, y_off + 25))
    pygame.draw.line(screen, YELLOW, (PLACE_ZONE_LEFT, 0), (PLACE_ZONE_LEFT, 540), 2)
    screen.blit(small_font.render("Place Zone ->", True, YELLOW), (PLACE_ZONE_LEFT + 10, 300))

def draw_attack_timer():
    if game_state != GAME_STATE_PLAY: return
    elapsed = time.time() - attack_start_time
    remaining = max(0, ATTACK_TIME_LIMIT - elapsed)
    mins, secs = int(remaining // 60), int(remaining % 60)
    col = RED if remaining <= 30 else (YELLOW if remaining <= 60 else WHITE)
    screen.blit(bold_font.render(f"Time: {mins}:{secs:02d}", True, col), (1050, 200))

def draw_ghost_preview():
    if x_mouse < PLACE_ZONE_LEFT or y_mouse > 540: return
    w, h = get_object_dimensions(current_place_type)
    if w == 0: return

    sx, sy, snapped = get_snap_position(x_mouse, y_mouse, w, h)
    valid = check_placement_valid(sx, sy, w, h)

    if current_place_type == PLACE_PIG and level.can_place('pigs'):
        if snapped: pygame.draw.line(screen, GREEN, (sx-20, sy+14), (sx+20, sy+14), 2)
        prev = pig_preview.copy()
        if not valid: prev.fill((255, 100, 100), special_flags=pygame.BLEND_MULT)
        screen.blit(prev, (sx-15, sy-15))

    elif current_place_type == PLACE_COLUMN and level.can_place('columns'):
        if snapped: pygame.draw.line(screen, GREEN, (sx-15, sy+42), (sx+15, sy+42), 2)
        prev = column_preview_ghost.copy()
        if not valid: prev.fill((255, 100, 100), special_flags=pygame.BLEND_MULT)
        screen.blit(prev, (sx-11, sy-42))

    elif current_place_type == PLACE_BEAM and level.can_place('beams'):
        if snapped: pygame.draw.line(screen, GREEN, (sx-50, sy+10), (sx+50, sy+10), 2)
        prev = beam_preview_ghost.copy()
        if not valid: prev.fill((255, 100, 100), special_flags=pygame.BLEND_MULT)
        screen.blit(prev, (sx-43, sy-11))

def place_object(x, y):
    global current_place_type
    if x < PLACE_ZONE_LEFT or y > 540: return False
    w, h = get_object_dimensions(current_place_type)
    if w == 0: return False

    sx, sy, snapped = get_snap_position(x, y, w, h)
    if not check_placement_valid(sx, sy, w, h): return False

    px, py = sx, 600 - sy

    if current_place_type == PLACE_PIG and level.can_place('pigs'):
        pig = Pig(px, py, space, static=True)
        pigs.append(pig); placed_static_bodies.append(pig)
        level.consume_item('pigs')
    elif current_place_type == PLACE_COLUMN and level.can_place('columns'):
        col = Polygon((px, py), 20, 85, space, static=True)
        columns.append(col); placed_static_bodies.append(col)
        level.consume_item('columns')
    elif current_place_type == PLACE_BEAM and level.can_place('beams'):
        beam = Polygon((px, py), 85, 20, space, static=True)
        beams.append(beam); placed_static_bodies.append(beam)
        level.consume_item('beams')
    return True

def remove_object_at(x, y):
    if game_state != GAME_STATE_BUILD or x < PLACE_ZONE_LEFT: return False
    for lst, item_key in [(pigs, 'pigs'), (columns, 'columns'), (beams, 'beams')]:
        for obj in lst[:]:
            b = get_object_bounds(obj)
            if b and b[0] <= x <= b[1] and b[2] <= y <= b[3]:
                space.remove(obj.shape, obj.body)
                lst.remove(obj)
                if obj in placed_static_bodies: placed_static_bodies.remove(obj)
                level.inventory[item_key] += 1
                return True
    return False

def activate_physics():
    global physics_activation_time, attack_start_time, damage_enabled
    physics_activation_time = time.time()
    attack_start_time = time.time()
    damage_enabled = False

    for obj in placed_static_bodies:
        if hasattr(obj, 'activate'): obj.activate(space)

    print("[预热] 开始60帧隐形物理模拟...")
    dt = 1.0 / 60.0
    for _ in range(WARMUP_FRAMES): space.step(dt)
    print("[预热] 完成")
    placed_static_bodies.clear()

def is_in_stabilization_period():
    if physics_activation_time == 0: return True
    return (time.time() - physics_activation_time) < PHYSICS_STABILIZE_DURATION

def remove_out_of_bounds_objects():
    global score
    for pig in pigs[:]:
        pos = pig.body.position
        if pos.x < BOUNDARY_LEFT or pos.x > BOUNDARY_RIGHT or pos.y < BOUNDARY_BOTTOM:
            space.remove(pig.shape, pig.body)
            pigs.remove(pig)
            score += 5000
            print(f"猪飞出边界: {pos}")

    for bird in birds[:]:
        pos = bird.body.position
        if pos.x < BOUNDARY_LEFT or pos.x > BOUNDARY_RIGHT or pos.y < BOUNDARY_BOTTOM:
            try: space.remove(bird.shape, bird.body)
            except: pass
            if bird in birds: birds.remove(bird)

def is_scene_still():
    for obj in pigs + birds + columns + beams:
        if obj.body.velocity.length > STILLNESS_THRESHOLD: return False
    return True

def check_win_condition():
    global scene_still_start_time, force_end_timer_start

    if len(pigs) == 0: return 'attacker_wins'

    if attack_start_time > 0 and (time.time() - attack_start_time >= ATTACK_TIME_LIMIT):
        return 'defender_wins_timeout'

    if level.number_of_birds <= 0 and len(birds) == 0:
        if force_end_timer_start == 0: force_end_timer_start = time.time()

        # 强制结束：如果等待超过5秒，直接结束
        if time.time() - force_end_timer_start > FORCE_END_DELAY:
            print("[胜负判定] 强制结算时间到")
            return 'defender_wins'

        if is_scene_still():
            if scene_still_start_time == 0: scene_still_start_time = time.time()
            elif time.time() - scene_still_start_time > STILLNESS_DURATION:
                return 'defender_wins'
        else:
            scene_still_start_time = 0
    else:
        force_end_timer_start = 0

    return None

def draw_level_cleared():
    # 纯绘制函数，不修改状态
    rect = pygame.Rect(300, 0, 600, 800)
    pygame.draw.rect(screen, BLACK, rect)
    screen.blit(bold_font3.render("ATTACKER WINS!", True, WHITE), (400, 90))

    if score >= level.one_star: screen.blit(star1, (310, 190))
    if score >= level.two_star: screen.blit(star2, (500, 170))
    if score >= level.three_star: screen.blit(star3, (700, 200))

    screen.blit(bold_font2.render(str(score), True, WHITE), (550, 400))
    screen.blit(replay_button, (510, 480))
    screen.blit(next_button, (620, 480))

def draw_level_failed():
    # 纯绘制函数，不修改状态
    global is_timeout_failure
    rect = pygame.Rect(300, 0, 600, 800)
    pygame.draw.rect(screen, BLACK, rect)
    screen.blit(bold_font3.render("DEFENDER WINS!", True, WHITE), (400, 90))

    if is_timeout_failure:
        screen.blit(bold_font2.render("TIME'S UP!", True, RED), (480, 140))

    screen.blit(pig_happy, (380, 180))
    screen.blit(replay_button, (520, 460))

def restart():
    global placed_static_bodies, physics_activation_time, attack_start_time
    global damage_enabled, scene_still_start_time, bonus_score_once, force_end_timer_start

    def safe_remove(obj):
        try: space.remove(obj.shape, obj.body)
        except: pass

    for x in pigs: safe_remove(x)
    for x in birds: safe_remove(x)
    for x in columns: safe_remove(x)
    for x in beams: safe_remove(x)

    pigs.clear(); birds.clear(); columns.clear(); beams.clear()
    placed_static_bodies.clear()

    physics_activation_time = 0
    attack_start_time = 0
    damage_enabled = False
    scene_still_start_time = 0
    force_end_timer_start = 0
    bonus_score_once = True

# --- 碰撞回调 (数值调整) ---

def post_solve_bird_pig(arbiter, space, _):
    if is_in_stabilization_period(): return
    bird_body, pig_body = arbiter.shapes[0].body, arbiter.shapes[1].body
    p, p2 = to_pygame(bird_body.position), to_pygame(pig_body.position)
    pygame.draw.circle(screen, BLACK, p, 30, 4)
    pygame.draw.circle(screen, RED, p2, 30, 4)

    for pig in pigs[:]:
        if pig_body == pig.body:
            pig.life -= 20
            pigs.remove(pig)
            try: space.remove(pig.shape, pig.body)
            except: pass
            global score
            score += 10000

def post_solve_bird_wood(arbiter, space, _):
    # 【修复】增加销毁木头的冲量阈值 1100 -> 2500
    if arbiter.total_impulse.length > 2500:
        b_shape = arbiter.shapes[1]
        for lst in [columns, beams]:
            for poly in lst[:]:
                if b_shape == poly.shape:
                    lst.remove(poly)
                    try: space.remove(poly.shape, poly.body)
                    except: pass
                    global score
                    score += 5000

def post_solve_pig_wood(arbiter, space, _):
    if is_in_stabilization_period(): return
    # 【修复】降低猪受伤害的冲量阈值 700 -> 200
    if arbiter.total_impulse.length > 200:
        pig_shape = arbiter.shapes[0]
        for pig in pigs[:]:
            if pig_shape == pig.shape:
                pig.life -= 20
                global score
                score += 10000
                if pig.life <= 0:
                    pigs.remove(pig)
                    try: space.remove(pig.shape, pig.body)
                    except: pass

space.add_collision_handler(0, 1).post_solve = post_solve_bird_pig
space.add_collision_handler(0, 2).post_solve = post_solve_bird_wood
space.add_collision_handler(1, 2).post_solve = post_solve_pig_wood

load_music()
level = Level(pigs, columns, beams, space)
level.number = 0
level.load_level()

# ==================== 主游戏循环 ====================
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            elif game_state == GAME_STATE_BUILD:
                if event.key == pygame.K_1: current_place_type = PLACE_PIG
                elif event.key == pygame.K_2: current_place_type = PLACE_COLUMN
                elif event.key == pygame.K_3: current_place_type = PLACE_BEAM
                elif event.key == pygame.K_SPACE:
                    if level.all_pigs_placed():
                        game_state = GAME_STATE_PLAY
                        activate_physics()
                        t1 = time.time() * 1000

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                if game_state == GAME_STATE_BUILD: place_object(x_mouse, y_mouse)
                elif game_state == GAME_STATE_PLAY:
                    if 100 < x_mouse < 250 and 370 < y_mouse < 550: mouse_pressed = True
            elif event.button == 3: # Right click
                if game_state == GAME_STATE_BUILD: remove_object_at(x_mouse, y_mouse)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if game_state == GAME_STATE_PLAY:
                if mouse_pressed:
                    mouse_pressed = False
                    if level.number_of_birds > 0:
                        level.number_of_birds -= 1
                        t1 = time.time() * 1000
                        xo, yo = 154, 156
                        if mouse_distance > rope_lenght: mouse_distance = rope_lenght
                        # 简单的发射逻辑
                        if x_mouse < sling_x + 5: bird = Bird(mouse_distance, angle, xo, yo, space)
                        else: bird = Bird(-mouse_distance, angle, xo, yo, space)
                        birds.append(bird)
                        if level.number_of_birds == 0: t2 = time.time()

                # 暂停按钮判定
                if x_mouse < 60 and 90 < y_mouse < 155: game_state = GAME_STATE_PAUSE

            # 暂停菜单点击
            elif game_state == GAME_STATE_PAUSE:
                if x_mouse > 500:
                    if 200 < y_mouse < 300: game_state = GAME_STATE_PLAY
                    elif y_mouse > 300:
                        restart(); level.load_level()
                        game_state = GAME_STATE_BUILD
                        bird_path = []; score = 0

            # 失败/胜利菜单点击
            elif game_state in [GAME_STATE_FAILED, GAME_STATE_CLEARED]:
                # Replay
                if 500 < x_mouse < 620 and y_mouse > 450:
                    restart(); level.load_level()
                    game_state = GAME_STATE_BUILD
                    bird_path = []; score = 0
                # Next Level (Only for CLEARED)
                if game_state == GAME_STATE_CLEARED and x_mouse > 610 and y_mouse > 450:
                    restart(); level.number += 1
                    game_state = GAME_STATE_BUILD
                    level.load_level()
                    bird_path = []; score = 0

    x_mouse, y_mouse = pygame.mouse.get_pos()

    # --- 绘图 ---
    screen.fill((130, 200, 100))
    screen.blit(background2, (0, -50))
    screen.blit(sling_image, (138, 420), pygame.Rect(50, 0, 70, 220))
    for p in bird_path: pygame.draw.circle(screen, WHITE, p, 5, 0)

    if level.number_of_birds > 0 and game_state == GAME_STATE_PLAY:
        for i in range(level.number_of_birds - 1):
            screen.blit(redbird, (100 - i*35, 508))

    if game_state == GAME_STATE_BUILD:
        draw_ghost_preview()
        screen.blit(redbird, (130, 426))
    elif game_state == GAME_STATE_PLAY:
        if mouse_pressed and level.number_of_birds > 0: sling_action()
        else:
            if time.time()*1000 - t1 > 300 and level.number_of_birds > 0:
                screen.blit(redbird, (130, 426))
            else:
                pygame.draw.line(screen, BLACK, (sling_x, sling_y-8), (sling2_x, sling2_y-7), 5)

    # 物理更新
    if game_state == GAME_STATE_PLAY:
        dt = 1.0/50.0/2.
        for _ in range(2): space.step(dt)
        remove_out_of_bounds_objects()

    # 绘制小鸟
    for bird in birds[:]:
        p = to_pygame(bird.shape.body.position)
        screen.blit(redbird, (p[0]-22, p[1]-20))
        pygame.draw.circle(screen, BLUE, p, int(bird.shape.radius), 2)
        if count >= 3 and time.time()*1000 - t1 < 5000:
            bird_path.append(p)
            restart_counter = True
    if restart_counter: count = 0; restart_counter = False; count += 1

    # 地面
    for line in static_lines:
        p1 = to_pygame(line.a); p2 = to_pygame(line.b)
        pygame.draw.lines(screen, (150, 150, 150), False, [p1, p2])

    # 猪
    for pig in pigs:
        p = to_pygame(pig.shape.body.position)
        deg = math.degrees(pig.shape.body.angle)
        img = pygame.transform.rotate(pig_image, deg)
        screen.blit(img, (p[0]-img.get_width()/2, p[1]-img.get_height()/2))
        pygame.draw.circle(screen, BLUE, p, int(pig.shape.radius), 2)

    # 木材
    for c in columns: c.draw_poly('columns', screen)
    for b in beams: b.draw_poly('beams', screen)

    screen.blit(sling_image, (120, 420), pygame.Rect(0, 0, 60, 200))
    screen.blit(bold_font.render("SCORE", True, WHITE), (1060, 90))
    screen.blit(bold_font.render(str(score), True, WHITE), (1060, 130))
    screen.blit(small_font.render(f"Level: {level.number}", True, WHITE), (1060, 170))

    if game_state == GAME_STATE_PLAY:
        screen.blit(pause_button, (10, 90))
        draw_attack_timer()
        if is_in_stabilization_period():
            screen.blit(small_font.render("Stabilizing...", True, YELLOW), (550, 300))

    if game_state == GAME_STATE_PAUSE:
        screen.blit(play_button, (500, 200))
        screen.blit(replay_button, (500, 300))

    # UI 绘制 (确保在物体之后)
    if game_state == GAME_STATE_BUILD:
        draw_build_phase_ui()

    # 【修复】每一帧都绘制结算画面
    elif game_state == GAME_STATE_CLEARED:
        draw_level_cleared()
    elif game_state == GAME_STATE_FAILED:
        draw_level_failed()

    # 胜负判定逻辑
    if game_state == GAME_STATE_PLAY:
        res = check_win_condition()
        if res == 'attacker_wins':
            game_state = GAME_STATE_CLEARED
            if bonus_score_once:
                score += (level.number_of_birds) * 10000
                bonus_score_once = False
        elif res == 'defender_wins':
            game_state = GAME_STATE_FAILED
            is_timeout_failure = False
        elif res == 'defender_wins_timeout':
            game_state = GAME_STATE_FAILED
            is_timeout_failure = True

    pygame.display.flip()
    clock.tick(50)
    pygame.display.set_caption(f"Angry Birds PvP - FPS: {int(clock.get_fps())}")

pygame.quit()