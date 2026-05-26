import pygame
from player import Player
from grid import Grid, IMPENETRABLE_CELLS, ENTITY_NONE, ENTITY_PLAYER, ENTITY_ENEMY, ENTITY_SEEKER
from enemy import FlowField, Enemy
from seeker import SeekerFlowField, Seeker
from grass.grass import grass_interacted

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("2d game")
pygame.key.set_repeat(200, 50)

clock = pygame.time.Clock()

player = Player(0, 0)
grid = Grid(20)

enemies = [
    Enemy(10, 5),
    Enemy(15, 8),
    Enemy(20, 3),
    Enemy(20, 8),
    Enemy(12, 17),
    Enemy(34, 6),
]
seekers = []
traps = set()
seekerflowfield = None

flow_field = FlowField(grid.grid, IMPENETRABLE_CELLS)
flow_field.build((round(player.x), round(player.y)))
last_player_tile = (round(player.x), round(player.y))
current_tile = last_player_tile

grid.set_entity(round(player.x), round(player.y), ENTITY_PLAYER)
for e in enemies:
    grid.set_entity(e.x, e.y, ENTITY_ENEMY)

moving = False
direction = "right"
show_grid = False
equipped_item_id = 1

font = pygame.font.SysFont(None, 24)

INDICATOR_COLORS = {
    1: (128, 128, 128),
    2: (0, 255, 0),
    3: (255, 128, 255),
    4: (255, 0, 128),
    5: (0, 165, 255),
}

inventory = {
    1: ("rock", 1),
    2: ("grass", 2),
    3: ("trap", 3),
    4: ("seek potion", 4),
    5: ("water", 5),
}

equipped_item = inventory[1][0]
text_surface = font.render(f"Equipped: {equipped_item}", True, (255, 255, 255))

running = True
while running:
    dt = clock.tick(60) / 1000
    mp = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            elif event.key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
                moving = True
                player.move(dt, event.key, grid)

            elif event.key == pygame.K_g:
                show_grid = not show_grid

            elif pygame.K_0 <= event.key <= pygame.K_9:
                inv_id = event.key - pygame.K_0
                if inv_id in inventory:
                    equipped_item_id = inventory[inv_id][1]
                    equipped_item = inventory[inv_id][0]
                    text_surface = font.render(f"Equipped: {equipped_item}", True, (255, 255, 255))

            elif event.key == pygame.K_RETURN:
                enemies = player.attack(enemies)
                seekers = player.attack(seekers)

        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
                moving = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                target_x, target_y = mp[0] // 20, mp[1] // 20

                if (target_x, target_y) != (round(player.x), round(player.y)):
                    cell_entity = grid.get_entity(target_x, target_y)
                    cell_tile   = grid.get_tile(target_x, target_y)

                    if cell_entity == ENTITY_ENEMY:
                        if equipped_item_id == 4:
                            enemy = next(e for e in enemies if e.x == target_x and e.y == target_y)
                            grid.set_entity(enemy.x, enemy.y, ENTITY_SEEKER)
                            seekers.append(Seeker(enemy.x, enemy.y))
                            enemies.remove(enemy)
                            if enemies:
                                seekerflowfield = SeekerFlowField(grid.grid, IMPENETRABLE_CELLS)
                                seekerflowfield.build((enemies[-1].x, enemies[-1].y))

                    elif cell_entity == ENTITY_SEEKER:
                        pass

                    elif cell_tile != 0:
                        if cell_tile == 2:
                            grid = grass_interacted(target_x, target_y, grid, equipped_item_id)
                        elif (target_x, target_y) in traps:
                            traps.discard((target_x, target_y))
                            grid.remove_object(target_x, target_y)
                            player.num_traps += 1
                        else:
                            grid.remove_object(target_x, target_y)

                    else:
                        if equipped_item_id == 3 and player.num_traps > 0:
                            traps.add((target_x, target_y))
                            player.num_traps -= 1
                            grid.place_object(target_x, target_y, equipped_item_id)
                        elif equipped_item_id not in (3, 4, 6):
                            grid.place_object(target_x, target_y, equipped_item_id)
                            if equipped_item_id in IMPENETRABLE_CELLS:
                                flow_field = FlowField(grid.grid, IMPENETRABLE_CELLS)
                                flow_field.build(current_tile)
                                for enemy in enemies:
                                    if (target_x, target_y) in enemy.roam_path:
                                        enemy.roam_path = []
                                        enemy.roam_target = None

                    if seekers and enemies and seekerflowfield:
                        seekerflowfield.build((enemies[-1].x, enemies[-1].y))
                    elif seekers and not enemies:
                        for seeker in seekers:
                            grid.clear_entity(seeker.x, seeker.y)
                        seekers.clear()

    if moving:
        player.snap_to_grid()

    grid.draw_cells(screen)
    player.draw(screen)

    for enemy in enemies[:]:
        if (enemy.x, enemy.y) in traps:
            grid.clear_entity(enemy.x, enemy.y)
            traps.discard((enemy.x, enemy.y))
            grid.remove_object(enemy.x, enemy.y)
            enemies.remove(enemy)
        else:
            enemy.update(flow_field, enemies, grid)
            enemy.attack(player)
            if player.health <= 0:
                print("Game Over!")
                running = False
                break
            enemy.draw(screen)

    for seeker in seekers[:]:
        if (seeker.x, seeker.y) in traps:
            grid.clear_entity(seeker.x, seeker.y)
            traps.discard((seeker.x, seeker.y))
            grid.remove_object(seeker.x, seeker.y)
            seekers.remove(seeker)
        else:
            if enemies and seekerflowfield:
                seeker.update(seekerflowfield, seekers, grid)
                enemy = next((e for e in enemies if e.x == seeker.x and e.y == seeker.y), None)
                if enemy:
                    grid.clear_entity(enemy.x, enemy.y)
                    grid.clear_entity(seeker.x, seeker.y)
                    enemies.remove(enemy)
                    seekers.remove(seeker)
                    continue
            seeker.draw(screen)

    if not enemies and seekers:
        for seeker in seekers:
            grid.clear_entity(seeker.x, seeker.y)
        seekers.clear()

    current_tile = (round(player.x), round(player.y))
    if current_tile != last_player_tile:
        if enemies:
            flow_field.build(current_tile)
        last_player_tile = current_tile

    if enemies and seekers and seekerflowfield:
        seekerflowfield.build((enemies[-1].x, enemies[-1].y))

    if show_grid:
        grid.draw(screen)
        if enemies:
            flow_field.draw(screen, 20)
        if seekers and seekerflowfield:
            seekerflowfield.draw(screen, 20)

    direction = player.get_direction(mp)
    indicator = INDICATOR_COLORS.get(equipped_item_id, (0, 0, 0))
    pygame.draw.rect(screen, indicator, (mp[0] // 20 * 20, mp[1] // 20 * 20, 20, 20), 2)
    screen.blit(text_surface, (10, 10))
    pygame.display.update()

pygame.quit()