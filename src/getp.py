import pygame
import os

# 初始化
pygame.init()

# --- 配置 ---
# 请确保这里的路径能找到你的 full-sprite.png
IMAGE_PATH = '../resources/images/angry_birds.png'
# 如果你是在 src 目录下运行，可能需要用 '../resources/...'
# 如果图片加载失败，请尝试绝对路径或调整这里的相对路径

try:
    sprite_sheet = pygame.image.load(IMAGE_PATH)
except FileNotFoundError:
    print(f"错误: 找不到文件 {IMAGE_PATH}")
    print("请确认你运行脚本的目录，或者修改代码中的 IMAGE_PATH")
    exit()

# 设置窗口
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sprite Coordinate Finder - 框选并查看控制台")

# 缩放/滚动变量
offset_x, offset_y = 0, 0
is_dragging = False
drag_start_pos = (0, 0)
selection_start = None
selection_end = None

running = True
clock = pygame.time.Clock()

print("=" * 50)
print("【使用说明】")
print("1. 按住【鼠标右键】拖动图片")
print("2. 按住【鼠标左键】框选你想要的元素")
print("3. 松开左键后，控制台会输出坐标代码")
print("=" * 50)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # --- 右键拖动图片 ---
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            is_dragging = True
            drag_start_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            is_dragging = False
        elif event.type == pygame.MOUSEMOTION and is_dragging:
            dx = event.pos[0] - drag_start_pos[0]
            dy = event.pos[1] - drag_start_pos[1]
            offset_x += dx
            offset_y += dy
            drag_start_pos = event.pos

        # --- 左键框选区域 ---
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 记录相对于图片的实际坐标
            img_x = event.pos[0] - offset_x
            img_y = event.pos[1] - offset_y
            selection_start = (img_x, img_y)
            selection_end = (img_x, img_y)  # 重置终点

        elif event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            if selection_start:
                img_x = event.pos[0] - offset_x
                img_y = event.pos[1] - offset_y
                selection_end = (img_x, img_y)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if selection_start and selection_end:
                # 计算最终矩形
                x1 = min(selection_start[0], selection_end[0])
                y1 = min(selection_start[1], selection_end[1])
                w = abs(selection_end[0] - selection_start[0])
                h = abs(selection_end[1] - selection_start[1])

                if w > 0 and h > 0:
                    print(f"\n[选中坐标] rect = pygame.Rect({x1}, {y1}, {w}, {h})")
                    print(f"建议代码:\ncropped = angry_birds.subsurface(pygame.Rect({x1}, {y1}, {w}, {h})).copy()")

                selection_start = None
                selection_end = None

    # --- 绘制 ---
    screen.fill((50, 50, 50))  # 深灰背景

    # 绘制大图
    screen.blit(sprite_sheet, (offset_x, offset_y))

    # 绘制正在框选的红框
    if selection_start and selection_end:
        # 转换回屏幕坐标进行绘制
        draw_x = min(selection_start[0], selection_end[0]) + offset_x
        draw_y = min(selection_start[1], selection_end[1]) + offset_y
        draw_w = abs(selection_end[0] - selection_start[0])
        draw_h = abs(selection_end[1] - selection_start[1])
        pygame.draw.rect(screen, (255, 0, 0), (draw_x, draw_y, draw_w, draw_h), 2)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()