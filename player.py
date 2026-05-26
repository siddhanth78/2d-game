import pygame
import math
from grid import W, H, ENTITY_PLAYER, ENTITY_NONE

DIRECTION_KEYS = {
    pygame.K_w: (0, -1, "up"),
    pygame.K_s: (0,  1, "down"),
    pygame.K_a: (-1, 0, "left"),
    pygame.K_d: (1,  0, "right"),
}

class Player:
    def __init__(self, x, y, range_=2):
        self.x = x
        self.y = y
        self.width = 20
        self.height = 20
        self.color = (255, 0, 0)
        self.range = range_
        self.num_traps = 3
        self.health = 10

    def move(self, dt, key, grid):
        dx, dy, direction = DIRECTION_KEYS[key]
        nx = self.x + dx
        ny = self.y + dy

        if not (0 <= nx < W and 0 <= ny < H):
            return
        if grid.is_cell_occupied(round(self.x), round(self.y), direction, player_check=True):
            return

        old_x, old_y = round(self.x), round(self.y)
        self.x += dx * dt * 60
        self.y += dy * dt * 60
        new_x, new_y = round(self.x), round(self.y)

        if (old_x, old_y) != (new_x, new_y):
            grid.clear_entity(old_x, old_y)
            grid.set_entity(new_x, new_y, ENTITY_PLAYER)

    def snap_to_grid(self):
        self.x = max(0, min(W - 1, round(self.x)))
        self.y = max(0, min(H - 1, round(self.y)))

    def get_direction(self, mp):
        angle = math.atan2(mp[1] - self.y * 20, mp[0] - self.x * 20)
        if   -math.pi/4  < angle <= math.pi/4:   return "right"
        elif  math.pi/4  < angle <= 3*math.pi/4: return "down"
        elif -3*math.pi/4 < angle <= -math.pi/4: return "up"
        else:                                      return "left"

    def attack(self, entities):
        return [
            e for e in entities
            if not (abs(e.x - self.x) <= self.range and abs(e.y - self.y) <= self.range)
        ]

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x * 20, self.y * 20, self.width, self.height))