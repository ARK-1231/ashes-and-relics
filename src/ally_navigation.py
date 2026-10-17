"""A* path-finding used by the ally follower."""

import heapq
import math
from collections.abc import Callable


Point = tuple[float, float]
Cell = tuple[int, int]
BlockedCheck = Callable[[float, float, float], bool]


def find_path(
    start_position: Point,
    target_position: Point,
    blocked: BlockedCheck,
    world_size: int,
    *,
    cell_size: int = 48,
    radius: float = 18.0,
) -> list[Point]:
    """Return a collision-safe four-directional grid path."""
    start = _nearest_open_cell(
        start_position, blocked, world_size, cell_size, radius,
    )
    goal = _nearest_open_cell(
        target_position, blocked, world_size, cell_size, radius,
    )
    if start is None or goal is None or start == goal:
        return []

    frontier: list[tuple[int, int, Cell]] = [(0, 0, start)]
    sequence = 0
    came_from: dict[Cell, Cell | None] = {start: None}
    costs = {start: 0}

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for offset_x, offset_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (current[0] + offset_x, current[1] + offset_y)
            world_x, world_y = _world_position(neighbor, cell_size)
            if not _inside_world(world_x, world_y, radius, world_size):
                continue
            if blocked(world_x, world_y, radius):
                continue

            new_cost = costs[current] + 1
            if neighbor in costs and new_cost >= costs[neighbor]:
                continue
            costs[neighbor] = new_cost
            came_from[neighbor] = current
            sequence += 1
            heuristic = abs(goal[0] - neighbor[0]) + abs(goal[1] - neighbor[1])
            heapq.heappush(frontier, (new_cost + heuristic, sequence, neighbor))

    if goal not in came_from:
        return []

    cells: list[Cell] = []
    current = goal
    while current != start:
        cells.append(current)
        parent = came_from[current]
        if parent is None:
            return []
        current = parent
    cells.reverse()
    return [_world_position(cell, cell_size) for cell in cells]


def _nearest_open_cell(
    position: Point,
    blocked: BlockedCheck,
    world_size: int,
    cell_size: int,
    radius: float,
) -> Cell | None:
    x, y = position
    center = (round(x / cell_size), round(y / cell_size))
    for ring in range(4):
        candidates = [
            (center[0] + dx, center[1] + dy)
            for dx in range(-ring, ring + 1)
            for dy in range(-ring, ring + 1)
            if max(abs(dx), abs(dy)) == ring
        ]
        candidates.sort(key=lambda cell: math.hypot(
            cell[0] * cell_size - x, cell[1] * cell_size - y,
        ))
        for cell in candidates:
            world_x, world_y = _world_position(cell, cell_size)
            if not _inside_world(world_x, world_y, radius, world_size):
                continue
            if not blocked(world_x, world_y, radius):
                return cell
    return None


def _world_position(cell: Cell, cell_size: int) -> Point:
    return cell[0] * cell_size, cell[1] * cell_size


def _inside_world(x: float, y: float, radius: float, world_size: int) -> bool:
    return (
        radius <= x <= world_size - radius
        and radius <= y <= world_size - radius
    )
