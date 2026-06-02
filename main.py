import pygame
from grid import Grid, CELL_DATA
from renderer import Renderer
import json
import os

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
renderer.build_atlas(CELL_DATA, CELL_SIZE)
renderer.init_selection()

def save_player(path, camera_x, camera_y, curr_chunk, equipped):
    with open(path, 'w') as f:
        json.dump({'camera_x': camera_x, 'camera_y': camera_y, 'curr_chunk': curr_chunk, 'equipped': equipped}, f)

def load_player(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {'camera_x': 0, 'camera_y': 0, 'curr_chunk': 0, 'equipped': 'dirt'}

player_data = load_player('player.json')
camera_x = player_data['camera_x']
camera_y = player_data['camera_y']
curr_chunk = player_data['curr_chunk']
prev_chunk = curr_chunk - 1
equipped = player_data['equipped']

running = True
while running:
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        x = int((mx - camera_x) // CELL_SIZE)
        y = int((my - camera_y) // CELL_SIZE)

        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                chunk_col = x // GRID_WIDTH
                chunk_row = y // GRID_HEIGHT
                chunk = chunk_row * (grid.chunks // 4) + chunk_col
                lx = x % GRID_WIDTH
                ly = y % GRID_HEIGHT
                if 0 <= chunk < grid.chunks:
                    grid.place(lx, ly, chunk, equipped)
                    instance_data = grid.build_instances(curr_chunk, renderer.tile_uvs, view_z=GRID_DEPTH)
                    renderer.upload(instance_data)
            elif event.button == 3:
                chunk_col = x // GRID_WIDTH
                chunk_row = y // GRID_HEIGHT
                chunk = chunk_row * (grid.chunks // 4) + chunk_col
                lx = x % GRID_WIDTH
                ly = y % GRID_HEIGHT
                if 0 <= chunk < grid.chunks:
                    grid.dig(lx, ly, chunk)
                    instance_data = grid.build_instances(curr_chunk, renderer.tile_uvs, view_z=GRID_DEPTH)
                    renderer.upload(instance_data)

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
        instance_data = grid.build_instances(curr_chunk, renderer.tile_uvs, view_z=GRID_DEPTH)
        renderer.upload(instance_data)
        prev_chunk = curr_chunk

    renderer.render(camera_x, camera_y)
    tx = int((mx - camera_x) // CELL_SIZE)
    ty = int((my - camera_y) // CELL_SIZE)
    chunk_col = tx // GRID_WIDTH
    chunk_row = ty // GRID_HEIGHT
    chunk = chunk_row * (grid.chunks // 4) + chunk_col
    lx = tx % GRID_WIDTH
    ly = ty % GRID_HEIGHT
    if 0 <= chunk < grid.chunks:
        g = grid.get_cell_level(lx, ly, chunk)
        wx = tx * CELL_SIZE + g
        wy = ty * CELL_SIZE - g
        renderer.render_selection(wx, wy, camera_x, camera_y)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
grid.save()
save_player('player.json', camera_x, camera_y, curr_chunk, equipped)
exit()