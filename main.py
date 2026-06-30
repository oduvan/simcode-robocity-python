"""Robot City Builder — starter controller (Python).

One script drives your whole fleet by id. The game is **event-driven**: whenever
a robot is free it fires `idle`, and you give it its next command. Because `idle`
fires exactly when (and only when) a robot needs direction, the whole controller
is essentially one handler — no polling, no chaining every completion by hand.

The growth loop, per robot, all decided in `on_idle` from the robot's live state:
  no mine + has the starter kit -> claim a free spot, walk there, build a Mining
  building -> mine -> once it holds a load, haul to the Base -> go back and mine.
  When the Base has enough ore+metal it builds a new robot, which does the same.

It's a solid base — improve it! Ideas: build Storage/Roads, balance ore vs metal,
keep robots from bunching at the Base. See CLAUDE.md for the full SDK + rules.
"""

from simcode import buildings, on, robots

HOME: dict = {}   # robot id -> (x, y) of the mine it works (process state)

MINE_ORE, MINE_METAL = 6, 3   # Mining recipe (the kit a robot drops to build one)
HAUL_AT = 6                   # haul once the robot's mine holds at least this much
DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def _num(rid: str) -> int:
    d = "".join(ch for ch in rid if ch.isdigit())
    return int(d) if d else 0


def _build(r):
    """Build a Mining building on the robot's current cell."""
    r.start_construction("mining")
    r.drop(MINE_ORE, MINE_METAL)   # supply the recipe
    r.connect()                    # then help build it


def _maybe_build_robot():
    """Grow: have the Base produce a robot when it can afford one (one at a time)."""
    b = buildings.base
    if b is None:
        return
    prod = b.production
    busy = bool(prod.get("active")) or (prod.get("queued") or 0) > 0
    if b.storage.ore >= 12 and b.storage.metal >= 6 and not busy:
        b.build_robot(1)


def _haul_to_base(r):
    """Drop into the Base if adjacent, else head for a free Base-neighbour cell
    (you can drop in from an adjacent cell, so haulers don't fight for one cell)."""
    b = buildings.base
    bx, by = b.position
    p = r.position
    if abs(p[0] - bx) + abs(p[1] - by) <= 1:
        r.drop()
        _maybe_build_robot()
        return
    occ = {x.position for x in robots.all() if x.id != r.id}
    cands = sorted(
        (abs(p[0] - (bx + dx)) + abs(p[1] - (by + dy)), (bx + dx, by + dy))
        for dx, dy in DIRS
        if (bx + dx, by + dy) not in occ
    )
    r.move_to(*(cands[0][1] if cands else (bx, by)))


def _mine_active(pos):
    """True if there's a finished Mining building at pos (our mine is built)."""
    for b in buildings.of_type("mining"):
        if b.position == pos and b.status == "active":
            return True
    return False


def claim_spot(r):
    """Nearest discovered, unbuilt, unclaimed spot, preferring the resource the
    Base has less of (so the fleet supplies both ore and metal)."""
    from simcode import world

    b = buildings.base
    prefer = "ore"
    if b is not None:
        if b.storage.ore == b.storage.metal:
            prefer = "ore" if _num(r.id) % 2 == 1 else "metal"
        elif b.storage.ore > b.storage.metal:
            prefer = "metal"
    taken = set(HOME.values())
    built = {x.position for x in buildings.all() if x.position}
    rx, ry = r.position
    best, best_key = None, None
    for c in world.spots():
        p = c.position
        if p in taken or p in built or not c.spot or c.spot.get("remaining", 0) <= 0:
            continue
        key = (0 if c.spot.get("resource") == prefer else 1, abs(p[0] - rx) + abs(p[1] - ry))
        if best_key is None or key < best_key:
            best, best_key = p, key
    return best


@on.idle
def on_idle(e):
    """A robot is free — decide its next command from its live state. Every path
    issues exactly one command, so the robot becomes busy and fires `idle` again
    when next free."""
    r = robots[e.robot_id]
    inv = r.inventory
    home = HOME.get(r.id)

    if buildings.base is None or buildings.base.position is None:
        r.scan(radius=8)
        return

    # No mine yet: spend the starter kit to build one (scan first if no spot known).
    # NB: the kit (6 ore/3 metal) is inventory but is for BUILDING, not hauling.
    if home is None:
        if inv.ore >= MINE_ORE and inv.metal >= MINE_METAL:
            spot = claim_spot(r)
            if spot is not None:
                HOME[r.id] = spot
                _build(r) if r.position == spot else r.move_to(*spot)
            else:
                r.scan(radius=8)
        else:
            r.scan(radius=8)            # no kit, no mine -> scout
        return

    built = _mine_active(home)

    # Not standing on our mine yet.
    if r.position != home:
        if inv.ore + inv.metal > 0 and built:
            _haul_to_base(r)            # carrying MINED output -> haul
        else:
            r.move_to(*home)            # carrying the kit (to build) or empty -> go to mine
        return

    # On our mine cell.
    if not built:
        b = r.here.building
        if b is not None and b.status == "constructing":
            r.connect()
        elif b is None and r.here.spot and inv.ore >= MINE_ORE and inv.metal >= MINE_METAL:
            _build(r)
        else:
            HOME.pop(r.id, None)
            r.scan(radius=8)
        return
    # Our mine is active.
    if inv.ore + inv.metal > 0:
        _haul_to_base(r)                # we just picked up a load
    elif r.here.building.storage.ore + r.here.building.storage.metal >= HAUL_AT:
        r.pick_up()
    else:
        r.mine()


@on.spot_depleted
def on_spot_depleted(e):
    """Our mine ran dry — abandon it; `idle` will fire and we'll scout again."""
    HOME.pop(e.robot_id, None)
    robots[e.robot_id].scan(radius=8)
