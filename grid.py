import pygame
import numpy as np
from bitarray import bitarray
from noise import pnoise2
import json
import os

pygame.init()

CELL_TYPES = {
    'grass': '00001',
    'dirt': '00010',
    'rock': '00011',
    'water': '00100',
    'lava': '00101',
    'sand': '00110',
    'ice': '00111'
}

CELL_DATA = {
    'grass': [(0, 255, 0),    'assets/grass.png'],
    'dirt':  [(128, 128, 0),  'assets/dirt.png'],
    'rock':  [(128, 128, 128),'assets/rock.png'],
    'water': [(0, 0, 255),    'assets/water.png'],
    'lava':  [(255, 0, 0),    'assets/lava.png'],
    'sand':  [(255, 255, 0),  'assets/sand.png'],
    'ice':   [(0, 255, 255),  'assets/ice.png'],
}

class Grid:
    def __init__(self, cell_size, width=12, height=12, depth=16, chunks=32, seed=0):
        self.cell_size = cell_size
        self.width = width * cell_size
        self.height = height * cell_size
        self.depth = depth
        self.chunks = chunks
        self.grid = {}
        self.map_ = {}
        self.seed = seed
        if os.path.exists('world.json'):
            self.load('world.json')
        else:
            self.generate_world_heightmap(levels=self.depth, seed=self.seed)
            self.init_cell_types()

    def generate_world_heightmap(self, scale=8.0, levels=16, seed=0):
        cols = self.chunks // 4
        rows = 4
        tile = self.width // self.cell_size
        world_w = cols * tile
        world_h = rows * tile
        raw = np.array([
            [pnoise2(x / scale, y / scale, base=seed) for x in range(world_w)]
            for y in range(world_h)
        ])
        mn, mx = raw.min(), raw.max()
        heightmap = ((raw - mn) / (mx - mn) * levels).astype(np.uint8)
        for row in range(rows):
            for col in range(cols):
                c = row * cols + col
                y0, y1 = row * tile, (row + 1) * tile
                x0, x1 = col * tile, (col + 1) * tile
                self.map_[c] = heightmap[y0:y1, x0:x1].tolist()

    def init_cell_types(self):
        for c in range(self.chunks):
            tile = self.width // self.cell_size
            self.grid[c] = [[bitarray('0000000000000000') for _ in range(tile)] for _ in range(tile)]
            for y in range(len(self.map_[c])):
                for x in range(len(self.map_[c][y])):
                    self.grid[c][y][x][:5] = bitarray(CELL_TYPES['grass'])

    def get_visible_chunks(self, curr_chunk):
        col = curr_chunk % (self.chunks // 4)
        row = curr_chunk // (self.chunks // 4)
        stride = self.chunks // 4
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                r, c = row + dr, col + dc
                if 0 <= r < 4 and 0 <= c < stride:
                    neighbors.append(r * stride + c)
        return neighbors

    def get_cell_level(self, x, y, chunk):
        return self.map_[chunk][y][x]

    def get_cell_type(self, x, y, chunk):
        ba = self.grid[chunk][y][x][:5].to01()
        reverse = {v: k for k, v in CELL_TYPES.items()}
        return reverse.get(ba, None)

    def get_cell_type_by_level(self, level):
        if level == 0:
            return 'rock'
        elif 1 <= level <= 5:
            return 'dirt'
        return 'grass'

    def set_cell_level(self, x, y, chunk, level):
        self.map_[chunk][y][x] = level

    def set_cell_type(self, x, y, chunk):
        cell_type = self.get_cell_type_by_level(self.map_[chunk][y][x])
        self.grid[chunk][y][x][:5] = bitarray(CELL_TYPES[cell_type])

    def build_instances(self, curr_chunk, tile_uvs):
        stride = self.chunks // 4
        tile = self.width // self.cell_size
        visible = self.get_visible_chunks(curr_chunk)
        instances = []
        for chunk in visible:
            chunk_col = chunk % stride
            chunk_row = chunk // stride
            ox = chunk_col * tile * self.cell_size
            oy = chunk_row * tile * self.cell_size
            for y in range(tile):
                for x in range(tile):
                    g = self.map_[chunk][y][x]
                    cell = self.get_cell_type(x, y, chunk)
                    u_min, u_max = tile_uvs.get(cell, (0, 1))
                    wx = ox + x * self.cell_size
                    wy = oy + y * self.cell_size
                    instances.append((wx, wy, g, u_min, u_max))
        instances.sort(key=lambda t: t[2])
        return np.array(instances, dtype='f4')

    def save(self, path):
        data = {
            'map': {str(c): self.map_[c] for c in self.map_},
            'grid': {str(c): [[self.grid[c][y][x].to01() for x in range(len(self.grid[c][y]))] for y in range(len(self.grid[c]))] for c in self.grid}
        }
        with open(path, 'w') as f:
            json.dump(data, f)

    def load(self, path):
        with open(path, 'r') as f:
            data = json.load(f)
        self.map_ = {int(c): v for c, v in data['map'].items()}
        self.grid = {int(c): [[bitarray(data['grid'][c][y][x]) for x in range(len(data['grid'][c][y]))] for y in range(len(data['grid'][c]))] for c in data['grid']}