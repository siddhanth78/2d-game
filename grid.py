import pygame
from array import array

pygame.init()

def load_tile_img(path):
    return pygame.image.load(path)

CELL_TYPES = {
    0: ("empty",     (0, 0, 0),       None),
    1: ("rock",      (128, 128, 128), load_tile_img("assets/rock.png")),
    2: ("grass",     (0, 255, 0),     load_tile_img("assets/grass.png")),
    3: ("trap",      (255, 0, 255),   load_tile_img("assets/trap.png")),
    5: ("water",     (0, 16, 255),    None),
    6: ("wet grass", (0, 192, 255),   load_tile_img("assets/wet_grass.png")),
    7: ("crops",     (255, 128, 0),   load_tile_img("assets/crops.png")),
}

ENTITY_NONE   = 0
ENTITY_PLAYER = 1
ENTITY_ENEMY  = 2
ENTITY_SEEKER = 3

IMPENETRABLE_CELLS = {1}

W, H = 40, 30

# Bit layout (32-bit uint):
# bits 31-28 : tile id   (4 bits, 0–15)
# bit  27    : dry
# bit  26    : hot
# bit  25    : wet
# bit  24    : slippery
# bits 23-0  : entity id (24 bits, 0 = none)

_TILE_SHIFT  = 12
_ENTITY_MASK = 0x000000FF
_FLAG_MASK   = 0x00000F00

FLAG_SLIPPERY = 1 << 8
FLAG_WET      = 1 << 9
FLAG_HOT      = 1 << 10
FLAG_DRY      = 1 << 11

DIRECTION_DELTA = {
    "right": ( 1,  0),
    "left":  (-1,  0),
    "down":  ( 0,  1),
    "up":    ( 0, -1),
}

def pack(tile_id, entity_id=0, slippery=False, wet=False, hot=False, dry=False):
    flags = (
        (FLAG_SLIPPERY if slippery else 0) |
        (FLAG_WET      if wet      else 0) |
        (FLAG_HOT      if hot      else 0) |
        (FLAG_DRY      if dry      else 0)
    )
    return (tile_id << _TILE_SHIFT) | flags | (entity_id & _ENTITY_MASK)

def tile_id(v):  return (v >> _TILE_SHIFT) & 0xFFFFF
def entity_id(v):   return v & _ENTITY_MASK
def is_slippery(v): return bool(v & FLAG_SLIPPERY)
def is_wet(v):      return bool(v & FLAG_WET)
def is_hot(v):      return bool(v & FLAG_HOT)
def is_dry(v):      return bool(v & FLAG_DRY)


class Grid:
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.grid = array('L', [pack(0)] * (W * H))
        self._build_cell_surface()
        self._build_grid_surface()

    def _idx(self, x, y):
        return y * W + x

    def get(self, x, y):
        return self.grid[self._idx(x, y)]

    def get_tile(self, x, y):
        return tile_id(self.grid[self._idx(x, y)])

    def get_entity(self, x, y):
        return entity_id(self.grid[self._idx(x, y)])

    def set_tile(self, x, y, tid):
        v = self.grid[self._idx(x, y)]
        self.grid[self._idx(x, y)] = (tid << _TILE_SHIFT) | (v & ~(0xFFFFF << _TILE_SHIFT))

    def set_entity(self, x, y, eid):
        v = self.grid[self._idx(x, y)]
        self.grid[self._idx(x, y)] = (v & ~_ENTITY_MASK) | (eid & _ENTITY_MASK)

    def clear_entity(self, x, y):
        self.set_entity(x, y, 0)

    def set_flags(self, x, y, slippery=None, wet=None, hot=None, dry=None):
        v = self.grid[self._idx(x, y)]
        def apply(v, flag, val):
            if val is True:  return v | flag
            if val is False: return v & ~flag
            return v
        v = apply(v, FLAG_SLIPPERY, slippery)
        v = apply(v, FLAG_WET,      wet)
        v = apply(v, FLAG_HOT,      hot)
        v = apply(v, FLAG_DRY,      dry)
        self.grid[self._idx(x, y)] = v

    def _draw_cell(self, surface, x, y):
        cell = CELL_TYPES[self.get_tile(x, y)]
        rx, ry = x * self.cell_size, y * self.cell_size
        if cell[2] is not None:
            surface.blit(cell[2], (rx, ry))
        else:
            pygame.draw.rect(surface, cell[1], (rx, ry, self.cell_size, self.cell_size))

    def _build_cell_surface(self):
        self.surface = pygame.Surface((W * self.cell_size, H * self.cell_size))
        for y in range(H):
            for x in range(W):
                self._draw_cell(self.surface, x, y)

    def _build_grid_surface(self):
        w, h = W * self.cell_size, H * self.cell_size
        self.grid_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(0, w, self.cell_size):
            pygame.draw.line(self.grid_surface, (128, 128, 128), (x, 0), (x, h))
        for y in range(0, h, self.cell_size):
            pygame.draw.line(self.grid_surface, (128, 128, 128), (0, y), (w, y))

    def draw(self, screen):
        screen.blit(self.grid_surface, (0, 0))

    def draw_cells(self, screen):
        screen.blit(self.surface, (0, 0))

    def place_object(self, x, y, id_):
        self.set_tile(x, y, id_)
        self._draw_cell(self.surface, x, y)

    def remove_object(self, x, y):
        self.set_tile(x, y, 0)
        self._draw_cell(self.surface, x, y)

    def is_cell_occupied(self, x, y, direction=None, player_check=False):
        if player_check and direction in DIRECTION_DELTA:
            dx, dy = DIRECTION_DELTA[direction]
            x, y = x + dx, y + dy
        tid = self.get_tile(x, y)
        return tid in IMPENETRABLE_CELLS if player_check else tid != 0