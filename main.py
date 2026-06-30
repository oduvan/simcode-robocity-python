"""Robot City Builder — starter controller (Python).

One script drives the whole fleet by id. The game is event-driven: whenever a
robot is free it fires `idle`, and you give it its next command. This starter is
a simple loop per robot:

    find a free resource spot  ->  build a mine on it  ->  mine  ->  haul to the
    Base  ->  go back and mine again.  (And the Base builds more robots.)

That's the whole thing. Read it, then make it smarter — balance ore vs metal,
build Storage/Roads, keep robots from bunching at the Base, etc.
See CLAUDE.md for the full SDK + rules.
"""

from simcode import buildings, on, robots, world

MINE: dict = {}   # robot id -> the (x, y) spot it claimed and works
STEP: dict = {}   # robot id -> a counter, so exploring changes direction


def free_spot(want):
    """A discovered resource spot that no robot has claimed yet, preferring the
    resource `want` (so the fleet mines both ore and metal, not just one)."""
    claimed = set(MINE.values())
    cands = [s for s in world.spots()
             if s.position not in claimed and s.spot.remaining > 0]
    cands.sort(key=lambda s: s.spot.resource != want)   # wanted resource first
    return cands[0].position if cands else None


def mine_built(pos):
    """True once a Mining building stands on `pos`."""
    return any(b.position == pos and b.type == "mining" for b in buildings.all())


def explore(r):
    """Move to reveal more of the map (direction rotates so robots fan out)."""
    w, h = world.size
    i = STEP.get(r.id, 0)
    STEP[r.id] = i + 1
    dx, dy = ((5, 0), (0, 5), (-5, 0), (0, -5))[(i + len(r.id)) % 4]
    x, y = r.position
    r.move_to(max(0, min(x + dx, w - 1)), max(0, min(y + dy, h - 1)))


@on.idle
def act(e):
    r = robots[e.robot_id]
    base = buildings.base
    if base is None:
        return

    # 1. No spot yet — claim one (or move to reveal more map if none is in view).
    if r.id not in MINE:
        # Mine whichever resource the Base has less of; if it's even (e.g. the
        # very start, 0/0), split robots by id so we get BOTH ore and metal.
        o, m = base.storage.ore, base.storage.metal
        if o == m:
            want = "ore" if sum(map(ord, r.id)) % 2 else "metal"
        else:
            want = "ore" if o < m else "metal"
        spot = free_spot(want)
        if spot is None:
            explore(r)
            return
        MINE[r.id] = spot

    spot = MINE[r.id]

    # 2. My mine isn't built yet — go to the spot and build it with my kit.
    if not mine_built(spot):
        if r.position == spot:
            r.start_construction("mining")
            r.drop(6, 3)
            r.connect()
        else:
            r.move_to(*spot)
        return

    # 3. Carrying ore/metal — haul it to the Base (which builds more robots).
    if r.inventory.ore + r.inventory.metal > 0:
        bx, by = base.position
        if abs(r.position[0] - bx) + abs(r.position[1] - by) <= 1:
            r.drop()
            base.build_robot(1)
        else:
            r.move_to(bx, by)
        return

    # 4. Empty — work my mine: stand on it, fill it up, then carry a load.
    if r.position != spot:
        r.move_to(*spot)
    elif r.here.building.storage.ore + r.here.building.storage.metal >= 6:
        r.pick_up()
    else:
        r.mine()


@on.spot_depleted
def depleted(e):
    # My spot ran out — forget it; next `idle` I'll look for a new one.
    MINE.pop(e.robot_id, None)
