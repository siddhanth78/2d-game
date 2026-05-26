import pygame
from collections import deque
import heapq
import random
from grid import W, H, tile_id, ENTITY_SEEKER, ENTITY_ENEMY


class Seeker:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 20
        self.height = 20
        self.color = (0, 0, 255)
        self.state = "idle"
        self.move_timer = 0
        self.move_interval = 30
        self.roam_path = []
        self.roam_target = None
        self.idle_timer = 0

    def update(self, flow_field, seekers, grid):
        if self.idle_timer > 0:
            self.idle_timer -= 1
            self.state = "idle"
            return

        self.move_timer += 1
        if self.move_timer < self.move_interval:
            return

        self.move_timer = 0

        if flow_field.can_reach(self.x, self.y):
            dx, dy = flow_field.get_direction(self.x, self.y)
            self.state = "chasing"
            self.roam_path = []
            self.roam_target = None
        else:
            self._update_roam(flow_field)
            dx, dy = 0, 0
            if self.roam_path:
                nx, ny = self.roam_path[0]
                dx, dy = nx - self.x, ny - self.y

        if (dx, dy) != (0, 0):
            nx, ny = self.x + dx, self.y + dy
            
            if grid.get_entity(nx, ny) == ENTITY_SEEKER:
                if dx != 0:
                    alts = [(self.x, self.y - 1), (self.x, self.y + 1)]
                else:
                    alts = [(self.x - 1, self.y), (self.x + 1, self.y)]
                
                for ax, ay in alts:
                    if (0 <= ax < W and 0 <= ay < H and
                        flow_field.is_walkable(ax, ay) and
                        grid.get_entity(ax, ay) != ENTITY_SEEKER):
                        nx, ny = ax, ay
                        break
                else:
                    nx, ny = self.x, self.y

            if (nx, ny) != (self.x, self.y):
                grid.clear_entity(self.x, self.y)
                self.x, self.y = nx, ny
                grid.set_entity(self.x, self.y, ENTITY_SEEKER)
                if self.roam_path and (self.x, self.y) == self.roam_path[0]:
                    self.roam_path.pop(0)
        elif flow_field.can_reach(self.x, self.y):
            self.state = "idle"

    def _update_roam(self, flow_field):
        if not self.roam_path and random.random() < 0.3:
            self.state = "idle"
            self.idle_timer = random.randint(20, 80)
            return

        self.state = "roaming"
        if not self.roam_target or (self.x, self.y) == self.roam_target or not self.roam_path:
            self.roam_target = flow_field.random_walkable_cell()
            if self.roam_target:
                self.roam_path = astar(flow_field, (self.x, self.y), self.roam_target) or []

    def draw(self, screen):
        color = {
            "idle":    (255, 128, 255),
            "chasing": (0, 255, 0),
            "roaming": (0, 128, 0),
        }.get(self.state, self.color)
        pygame.draw.rect(screen, color, (self.x * 20, self.y * 20, self.width, self.height))


def astar(flow_field, start, goal):
    def h(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_set = [(0, start)]
    came_from = {}
    g = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        x, y = current
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nb = (x + dx, y + dy)
            if not flow_field.is_walkable(nb[0], nb[1]):
                continue
            tg = g[current] + 1
            if tg < g.get(nb, float('inf')):
                came_from[nb] = current
                g[nb] = tg
                heapq.heappush(open_set, (tg + h(nb, goal), nb))

    return None


class SeekerFlowField:
    def __init__(self, grid, walls):
        # grid is a flat array('L') of packed uint32
        self.grid = grid
        self.walls = walls
        self.field = {}
        self._walkable = []

    def build(self, goal):
        dist = {goal: 0}
        queue = deque([goal])

        while queue:
            x, y = queue.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    if tile_id(self.grid[ny * W + nx]) not in self.walls:
                        if (nx, ny) not in dist:
                            dist[(nx, ny)] = dist[(x, y)] + 1
                            queue.append((nx, ny))

        self.field = {}
        for (x, y) in dist:
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in dist:
                    neighbors.append((dist[(nx, ny)], dx, dy))
            if neighbors:
                _, dx, dy = min(neighbors)
                self.field[(x, y)] = (dx, dy)

        self._walkable = [
            (x, y)
            for y in range(H)
            for x in range(W)
            if tile_id(self.grid[y * W + x]) not in self.walls
        ]

    def get_direction(self, x, y):
        return self.field.get((x, y), (0, 0))

    def can_reach(self, x, y):
        return (x, y) in self.field

    def is_walkable(self, x, y):
        if not (0 <= x < W and 0 <= y < H):
            return False
        return tile_id(self.grid[y * W + x]) not in self.walls

    def random_walkable_cell(self):
        return random.choice(self._walkable) if self._walkable else None

    def draw(self, screen, cell_size):
        font = pygame.font.SysFont(None, 14)
        arrows = {(0, -1): "^", (0, 1): "v", (-1, 0): "<", (1, 0): ">"}
        for (x, y), (dx, dy) in self.field.items():
            arrow = arrows.get((dx, dy), "?")
            surf = font.render(arrow, True, (100, 255, 100))
            screen.blit(surf, (x * cell_size + cell_size // 4, y * cell_size + cell_size // 4))