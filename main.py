"""Robot City Builder — starter controller (Python).

One script controls your whole fleet; you address each robot by id. The platform
delivers events (a robot spawned, a scan finished, a robot arrived, ...) and you
react by issuing commands (scan, move, build, mine, haul). State is read fresh
from the world on every event — you never hold a live game object.

This starter grows a small mining economy:
    scout -> build a mine on a resource spot -> mine -> haul to the Base
    -> when the Base has enough, it produces another robot -> repeat

It's intentionally simple. Improve it! Ideas: balance ore vs metal, build Storage
and Road buildings, avoid robots colliding near the Base, produce robots faster.

See CLAUDE.md in this repo for the full SDK reference and the rules.
"""
from simcode import buildings, on, robots

# Per-robot memory, kept in this process (persists across events; resets on a
# fresh deploy). Maps robot id -> the (x, y) of the mine that robot works.
HOME: dict = {}

MINE_ORE, MINE_METAL = 6, 3   # cost to build a Mining building


@on.spawn
def begin(e):
    # A robot entered the world — reveal its surroundings.
    robots[e.robot_id].scan(radius=8)


@on.tick
def brain(e):
    """The reconciler: every few ticks, give each idle robot its next job.

    Driving from `tick` (instead of only chaining off other events) keeps robots
    from getting stuck — there's always a next action decided from the live world.
    """
    if (e.tick_no or 0) % 4 != 0:
        return
    base = buildings.base
    if base is None or base.position is None:
        return
    bx, by = base.position

    # Grow: when the Base can afford a robot, build one.
    if base.storage.ore >= 12 and base.storage.metal >= 6:
        base.build_robot(1)

    for r in robots.all():
        if r.state != "idle":          # busy moving/mining/building — let it finish
            continue
        inv = r.inventory
        home = HOME.get(r.id)

        if home is None:               # no mine yet: use the starter kit to build one
            if inv.ore >= MINE_ORE and inv.metal >= MINE_METAL:
                spot = _free_spot(r)
                if spot:
                    HOME[r.id] = spot
                    r.move_to(*spot) if r.position != spot else _build(r)
                else:
                    r.scan(radius=8)
            continue

        if inv.ore + inv.metal > 0:     # carrying a load -> haul to the Base
            r.move_to(bx, by) if r.position != (bx, by) else r.drop()
            continue

        if r.position != home:          # empty -> go back to our mine
            r.move_to(*home)
            continue

        b = r.here.building             # on our mine cell
        if b is None:
            _build(r)                   # claimed but not built yet
        elif b.status == "constructing":
            r.connect()
        elif b.type == "mining" and b.status == "active":
            if b.storage.ore + b.storage.metal >= 6:
                r.pick_up()             # grab a load, then haul next tick
            else:
                r.mine()                # keep accumulating


def _build(r):
    """Build a mine on the robot's current cell and start construction."""
    r.start_construction("mining")
    r.drop(MINE_ORE, MINE_METAL)        # supply the platform
    r.connect()                          # then help build it


def _free_spot(r):
    """Nearest discovered resource spot with no building and not already claimed."""
    from simcode import world

    taken = set(HOME.values())
    occupied = {b.position for b in buildings.all() if b.position}
    rx, ry = r.position
    best, best_d = None, 1 << 30
    for c in world.spots():
        p = c.position
        if p in taken or p in occupied or not c.spot or c.spot.get("remaining", 0) <= 0:
            continue
        d = abs(p[0] - rx) + abs(p[1] - ry)
        if d < best_d:
            best, best_d = p, d
    return best
