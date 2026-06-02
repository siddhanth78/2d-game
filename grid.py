import pygame
import numpy as np
from bitarray import bitarray
from noise import pnoise2
import os

pygame.init()

CELL_TYPES = {
    'grass': '00001',
    'dirt':  '00010',
    'rock':  '00011',
    'water': '00100',
    'lava':  '00101',
    'sand':  '00110',
    'ice':   '00111'
}

CELL_DATA = {
    'grass': [(0, 255, 0),     'assets/grass.png'],
    'dirt':  [(128, 128, 0),   'assets/dirt.png'],
    'rock':  [(128, 128, 128), 'assets/rock.png'],
    'water': [(0, 0, 255),     'assets/water.png'],
    'lava':  [(255, 0, 0),     'assets/lava.png'],
    'sand':  [(255, 255, 0),   'assets/sand.png'],
    'ice':   [(0, 255, 255),   'assets/ice.png'],
}

REVERSE_TYPES = {v: k for k, v in CELL_TYPES.items()}

def get_layer_type(surface_level, z):
    if z <= 2:
        return 'lava'
    elif z <= 5:
        return 'rock'
    elif z <= surface_level - 1:
        return 'dirt'
    else:
        return 'grass'


class Grid:
    def __init__(self, cell_size, width=12, height=12, depth=16, chunks=32, seed=0):
        self.cell_size = cell_size
        self.width     = width * cell_size
        self.height    = height * cell_size
        self.depth     = depth
        self.chunks    = chunks
        self.seed      = seed
        self.grid      = {}
        self.map_      = {}
        self.chunk_dir = 'chunks'
        os.makedirs(self.chunk_dir, exist_ok=True)

        if os.path.exists(os.path.join(self.chunk_dir, 'heightmap.npy')):
            self._load_heightmap()
        else:
            self.generate_world_heightmap(levels=self.depth, seed=self.seed)
            self._save_heightmap()
            self.init_cell_types()

    def generate_world_heightmap(self, scale=8.0, levels=16, seed=0):
        cols    = self.chunks // 4
        rows    = 4
        tile    = self.width // self.cell_size
        world_w = cols * tile
        world_h = rows * tile
        raw = np.array([
            [pnoise2(x / scale, y / scale, base=seed) for x in range(world_w)]
            for y in range(world_h)
        ])
        mn, mx = raw.min(), raw.max()
        heightmap = ((raw - mn) / (mx - mn) * (levels - 1)).astype(np.uint8)
        for row in range(rows):
            for col in range(cols):
                c      = row * cols + col
                y0, y1 = row * tile, (row + 1) * tile
                x0, x1 = col * tile, (col + 1) * tile
                self.map_[c] = heightmap[y0:y1, x0:x1].tolist()

    def _save_heightmap(self):
        hm_stack = np.array([self.map_[c] for c in range(self.chunks)], dtype=np.uint8)
        np.save(os.path.join(self.chunk_dir, 'heightmap.npy'), hm_stack)

    def _load_heightmap(self):
        hm_stack = np.load(os.path.join(self.chunk_dir, 'heightmap.npy'))
        for c in range(self.chunks):
            self.map_[c] = hm_stack[c].tolist()

    def init_cell_types(self):
        tile = self.width // self.cell_size
        for c in range(self.chunks):
            self.grid[c] = [
                [[bitarray('0000000000000000') for _ in range(tile)]
                 for _ in range(tile)]
                for _ in range(self.depth)
            ]
            for y in range(tile):
                for x in range(tile):
                    surface = self.map_[c][y][x]
                    for z in range(1, surface + 1):
                        cell_type = get_layer_type(surface, z)
                        self.grid[c][z][y][x][:5] = bitarray(CELL_TYPES[cell_type])
            self._save_chunk(c)
        self.grid = {}

    def _chunk_path(self, chunk):
        return os.path.join(self.chunk_dir, f'chunk_{chunk:04d}.npy')

    def _save_chunk(self, chunk):
        tile = self.width // self.cell_size
        arr = np.array([
            [[int(self.grid[chunk][z][y][x].to01(), 2) for x in range(tile)]
             for y in range(tile)]
            for z in range(self.depth)
        ], dtype=np.uint16)
        np.save(self._chunk_path(chunk), arr)

    def _load_chunk(self, chunk):
        tile = self.width // self.cell_size
        arr  = np.load(self._chunk_path(chunk))
        self.grid[chunk] = [
            [[bitarray(f'{arr[z, y, x]:016b}') for x in range(tile)]
             for y in range(tile)]
            for z in range(self.depth)
        ]

    def ensure_chunk_loaded(self, chunk):
        if chunk not in self.grid:
            self._load_chunk(chunk)

    def unload_chunk(self, chunk):
        if chunk in self.grid:
            self._save_chunk(chunk)
            del self.grid[chunk]

    def get_visible_chunks(self, curr_chunk):
        col    = curr_chunk % (self.chunks // 4)
        row    = curr_chunk // (self.chunks // 4)
        stride = self.chunks // 4
        neighbours = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                r, c = row + dr, col + dc
                if 0 <= r < 4 and 0 <= c < stride:
                    neighbours.append(r * stride + c)
        return neighbours

    def get_cell_level(self, x, y, chunk):
        return self.map_[chunk][y][x]

    def get_cell_type(self, x, y, chunk, z=None):
        if z is None:
            z = self.map_[chunk][y][x]
        self.ensure_chunk_loaded(chunk)
        ba = self.grid[chunk][z][y][x][:5].to01()
        return REVERSE_TYPES.get(ba, None)

    def get_cell_type_by_level(self, level):
        if level <= 2:
            return 'lava'
        elif level <= 5:
            return 'rock'
        else:
            return 'dirt'

    def set_cell_level(self, x, y, chunk, level):
        self.map_[chunk][y][x] = level

    def set_cell_type(self, x, y, chunk, z=None):
        if z is None:
            z = self.map_[chunk][y][x]
        self.ensure_chunk_loaded(chunk)
        surface   = self.map_[chunk][y][x]
        cell_type = get_layer_type(surface, z)
        self.grid[chunk][z][y][x][:5] = bitarray(CELL_TYPES[cell_type])

    def dig(self, x, y, chunk):
        surface = self.map_[chunk][y][x]
        if surface == 0:
            return None
        self.ensure_chunk_loaded(chunk)
        self.grid[chunk][surface][y][x] = bitarray('0000000000000000')
        self.map_[chunk][y][x] = surface - 1
        return self.get_cell_type(x, y, chunk)
    
    def place(self, x, y, chunk, type_):
        surface = self.map_[chunk][y][x]
        new_surface = min(self.depth - 1, surface + 1)
        if new_surface == surface:
            return None
        self.ensure_chunk_loaded(chunk)
        self.map_[chunk][y][x] = new_surface
        self.grid[chunk][new_surface][y][x][:5] = bitarray(CELL_TYPES[type_])
        return type_

    def get_visible_z_range(self, x, y, chunk):
        surface   = self.map_[chunk][y][x]
        tile      = self.width // self.cell_size
        stride    = self.chunks // 4
        chunk_col = chunk % stride
        chunk_row = chunk // stride

        left_surface   = None
        bottom_surface = None

        if x > 0:
            left_surface = self.map_[chunk][y][x - 1]
        elif chunk_col > 0:
            nc = chunk_row * stride + (chunk_col - 1)
            left_surface = self.map_[nc][y][tile - 1]
        else:
            return 1, surface

        if y < tile - 1:
            bottom_surface = self.map_[chunk][y + 1][x]
        elif chunk_row < 3:
            nc = (chunk_row + 1) * stride + chunk_col
            bottom_surface = self.map_[nc][0][x]
        else:
            return 1, surface

        neighbors = [n for n in [left_surface, bottom_surface] if n is not None]
        if not neighbors:
            return 1, surface

        max_diff = max(surface - n for n in neighbors)

        if max_diff <= 0:
            return surface, surface

        return max(1, surface - max_diff), surface

    def build_instances(self, curr_chunk, tile_uvs, view_z=None):
        stride    = self.chunks // 4
        tile      = self.width // self.cell_size
        visible   = self.get_visible_chunks(curr_chunk)
        instances = []

        for chunk in visible:
            self.ensure_chunk_loaded(chunk)
            chunk_col = chunk % stride
            chunk_row = chunk // stride
            ox = chunk_col * tile * self.cell_size
            oy = chunk_row * tile * self.cell_size

            for y in range(tile):
                for x in range(tile):
                    surface = self.map_[chunk][y][x]
                    wx = ox + x * self.cell_size
                    wy = oy + y * self.cell_size

                    if view_z is None:
                        cell = self.get_cell_type(x, y, chunk, surface)
                        u_min, u_max = tile_uvs.get(cell, (0, 1))
                        instances.append((wx, wy, surface, u_min, u_max))
                    else:
                        top = min(surface, view_z)
                        z_min, z_max = self.get_visible_z_range(x, y, chunk)
                        for z in range(z_min, min(z_max, top) + 1):
                            ba = self.grid[chunk][z][y][x][:5].to01()
                            if ba == '00000':
                                continue
                            cell = REVERSE_TYPES.get(ba, None)
                            if cell is None:
                                continue
                            u_min, u_max = tile_uvs.get(cell, (0, 1))
                            instances.append((wx, wy, z, u_min, u_max))

        instances.sort(key=lambda t: t[2])
        return np.array(instances, dtype='f4')

    def save(self):
        for chunk in list(self.grid.keys()):
            self._save_chunk(chunk)
        self._save_heightmap()

    def load(self):
        self._load_heightmap()