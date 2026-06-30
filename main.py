"""Robot City Builder — starter controller (Python).

One script drives your whole fleet by id. The game is **event-driven**: every
command a robot runs finishes with an event (arrived, mining_complete,
construction_complete, blocked, ...), and you react by issuing the next command.
There is no polling — the golden rule is simply: **every handler must give the
robot its next command**, so a robot is never left idle with nothing to wake it.

The growth loop, per robot:
  scout -> walk to a free resource spot -> build a Mining building (drop the kit,
  connect) -> mine -> haul a load to the Base -> go back and mine again. When the
  Base has enough ore+metal it produces a new robot, which does the same.

It's a solid base — improve it! Ideas: build Storage/Roads, balance ore vs metal,
reduce robots bunching at the Base. See CLAUDE.md for the full SDK + rules.
"""

from simcode import buildings, on, robots

# Per-robot memory (persists while the city runs; resets on a fresh deploy).
HOME: dict = {}   # robot id -> (x, y) of the mine it works
GOAL: dict = {}   # robot id -> what its current move is for: spot|base|mine|explore

MINE_ORE, MINE_METAL = 6, 3   # Mining recipe (the kit a robot drops to build one)
HAUL_AT = 6                   # haul once the robot's mine holds at least this much


def _num(rid: str) -> int:
    d = "".join(ch for ch in rid if ch.isdigit())
    return int(d) if d else 0


def _base():
    b = buildings.base
    return b if (b and b.position) else None


def _go_base(r):
    """Head for a free cell next to the Base (you can drop in from an adjacent
    cell), so haulers don't all fight for its single cell."""
    b = _base()
    if b is None:
        return
    bx, by = b.position
    GOAL[r.id] = "base"
    p = r.position
    if abs(p[0] - bx) + abs(p[1] - by) <= 1:
        r.drop()            # already adjacent/on it
        _maybe_build_robot()
        _send_home(r)
        return
    occ = {x.position for x in robots.all() if x.id != r.id}
    cands = sorted(
        (abs(p[0] - (bx + dx)) + abs(p[1] - (by + dy)), (bx + dx, by + dy))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
        if (bx + dx, by + dy) not in occ
    )
    r.move_to(*(cands[0][1] if cands else (bx, by)))


def _send_home(r):
    if r.id in HOME:
        GOAL[r.id] = "mine"
        r.move_to(*HOME[r.id])
    else:
        GOAL[r.id] = "explore"
        r.scan(radius=8)


def _maybe_build_robot():
    b = _base()
    if b is None:
        return
    prod = b.production
    busy = bool(prod.get("active")) or (prod.get("queued") or 0) > 0
    if b.storage.ore >= 12 and b.storage.metal >= 6 and not busy:
        b.build_robot(1)   # the growth driver — a new robot will spawn


def claim_spot(r):
    """Nearest discovered, unbuilt, unclaimed spot, preferring the resource the
    Base has less of (so the fleet supplies both ore and metal)."""
    from simcode import world

    b = _base()
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


def _seek_spot(r):
    """Claim a spot and walk to it; if none discovered, drift and scan again."""
    spot = claim_spot(r)
    if spot is not None:
        HOME[r.id] = spot
        GOAL[r.id] = "spot"
        r.move_to(*spot)
    else:
        GOAL[r.id] = "explore"
        x, y = r.position
        r.move_to(x + 6, y)   # arrived(explore) -> scan again


# --- handlers: each one ALWAYS issues a next command for the robot ---

@on.spawn
def spawn(e):
    robots[e.robot_id].scan(radius=8)


@on.scan_result
def scanned(e):
    r = robots[e.robot_id]
    if r.id in HOME:
        GOAL[r.id] = "mine"
        r.move_to(*HOME[r.id])
        return
    if r.inventory.ore >= MINE_ORE and r.inventory.metal >= MINE_METAL:
        _seek_spot(r)
    else:
        # No kit and no mine — drift and keep looking (a future robot will mine).
        GOAL[r.id] = "explore"
        x, y = r.position
        r.move_to(x + 6, y)


@on.arrived
def arrived(e):
    r = robots[e.robot_id]
    goal = GOAL.get(r.id, "explore")
    if goal == "spot":
        if r.here.spot and not r.here.building \
                and r.inventory.ore >= MINE_ORE and r.inventory.metal >= MINE_METAL:
            r.start_construction("mining")
            r.drop(MINE_ORE, MINE_METAL)
            r.connect()                       # -> construction_complete
            GOAL[r.id] = "building"
        else:
            HOME.pop(r.id, None)
            r.scan(radius=8)
    elif goal == "base":
        r.drop()
        _maybe_build_robot()
        _send_home(r)
    elif goal == "mine":
        r.mine()                              # -> mining_complete
    else:
        r.scan(radius=8)                      # explore -> rescan


@on.construction_complete
def built(e):
    robots[e.robot_id].mine()


@on.mining_complete
def mined(e):
    r = robots[e.robot_id]
    b = r.here.building
    if b and b.type == "mining" and (b.storage.ore + b.storage.metal) >= HAUL_AT:
        r.pick_up()
        _go_base(r)
    else:
        r.mine()


@on.storage_full
def overflow(e):
    r = robots[e.robot_id]
    r.pick_up()
    _go_base(r)


@on.blocked
def blocked(e):
    r = robots[e.robot_id]
    goal = GOAL.get(r.id, "explore")
    if goal == "base":
        _go_base(r)                           # retry (pathfinding routes around)
    elif goal in ("mine", "spot") and r.id in HOME:
        r.move_to(*HOME[r.id])
    else:
        GOAL[r.id] = "explore"
        r.scan(radius=8)
