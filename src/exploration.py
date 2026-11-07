"""Per-floor exploration memory. Walls and closed gates block discovery."""
import math

CELL_SIZE = 96
DISCOVERY_RADIUS = 330


class Exploration:
    def __init__(self):
        self.discovered = set()
        self.visible = set()
        self.last_cell = None
        self._mask_key = None
        self._mask_rectangles = ()

    def unknown_rectangles(self, world_size):
        """Merge consecutive unknown cells; cache until discovery changes."""
        key = (world_size, len(self.discovered))
        if key == self._mask_key:
            return self._mask_rectangles
        count = math.ceil(world_size / CELL_SIZE)
        rectangles = []
        active = {}
        for y in range(count):
            spans = []
            x = 0
            while x < count:
                if (x, y) in self.discovered:
                    x += 1
                    continue
                start = x
                while x < count and (x, y) not in self.discovered:
                    x += 1
                spans.append((start, x))
            next_active = {}
            for span in spans:
                rectangle = active.pop(span, None)
                if rectangle is None:
                    rectangle = [span[0]*CELL_SIZE, y*CELL_SIZE,
                                 min(world_size, span[1]*CELL_SIZE), 0]
                rectangle[3] = min(world_size, (y+1)*CELL_SIZE)
                next_active[span] = rectangle
            rectangles.extend(active.values())
            active = next_active
        rectangles.extend(active.values())
        self._mask_key = key
        self._mask_rectangles = tuple(tuple(rect) for rect in rectangles)
        return self._mask_rectangles

    @staticmethod
    def cell(x, y):
        return int(x // CELL_SIZE), int(y // CELL_SIZE)

    def update(self, x, y, world_size, line_blocked, gate_state=None):
        # Recalculate after moving 24px, or when a gate changes state.
        signature = (int(x // 24), int(y // 24), gate_state)
        if signature == self.last_cell:
            return
        self.last_cell = signature
        visible = {self.cell(x, y)}
        count = math.ceil(world_size / CELL_SIZE)
        cx, cy = self.cell(x, y)
        reach = math.ceil(DISCOVERY_RADIUS / CELL_SIZE)
        for gx in range(max(0, cx-reach), min(count, cx+reach+1)):
            for gy in range(max(0, cy-reach), min(count, cy+reach+1)):
                tx = min(world_size-1, (gx + 0.5)*CELL_SIZE)
                ty = min(world_size-1, (gy + 0.5)*CELL_SIZE)
                if math.hypot(tx-x, ty-y) <= DISCOVERY_RADIUS and not line_blocked(x, y, tx, ty):
                    visible.add((gx, gy))
        self.visible = visible
        self.discovered.update(visible)
