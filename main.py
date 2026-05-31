import pygame
import moderngl
from grid import Grid
from renderer import Renderer

pygame.init()
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

GRID_WIDTH = 12
GRID_HEIGHT = 12
GRID_DEPTH = 25
CELL_SIZE = 64
CHUNKS = 32
SPEED = 8

HEIGHT = GRID_WIDTH * CELL_SIZE + CELL_SIZE
WIDTH = GRID_HEIGHT * CELL_SIZE + CELL_SIZE

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
pygame.display.set_caption("My Game")
clock = pygame.time.Clock()

grid = Grid(CELL_SIZE, GRID_WIDTH, GRID_HEIGHT, GRID_DEPTH, CHUNKS)
renderer = Renderer(WIDTH, HEIGHT, CELL_SIZE, GRID_DEPTH)

camera_x = 0
camera_y = 0
curr_chunk = 0
prev_chunk = -1

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        camera_x += SPEED
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        camera_x -= SPEED
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        camera_y += SPEED
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        camera_y -= SPEED

    stride = grid.chunks // 4
    tile = GRID_WIDTH * CELL_SIZE
    padding = 16

    camera_x = min(padding, max(-(stride * tile - WIDTH + padding + 16), camera_x))
    camera_y = min(padding + 16, max(-(4 * tile - HEIGHT + padding), camera_y))
    chunk_col = max(1, min(stride - 2, int(-camera_x / tile)))
    chunk_row = max(1, min(2, int(-camera_y / tile)))
    curr_chunk = int(chunk_row * stride + chunk_col)

    if curr_chunk != prev_chunk:
        instance_data = grid.build_instances(curr_chunk)
        renderer.upload(instance_data)
        prev_chunk = curr_chunk

    renderer.render(camera_x, camera_y)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()