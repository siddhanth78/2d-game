def grass_interacted(x, y, grid, id_):
    if id_ == 5:
        grid.set_flags(x, y, wet=True)
        grid.place_object(x, y, 6)
    return grid