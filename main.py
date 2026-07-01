"""Robot City Builder — starter controller (Python).

One script drives the whole fleet by id. The game is event-driven: whenever a
robot is free it fires ``idle``, and you give it its next command.

The world (redesigned): robots **fly** in straight lines over float coordinates
and spend **energy** doing it — run out mid-flight and the robot is destroyed.
Mining and construction are **autonomous**: you place a build site with
``world.build(...)`` and robots only **haul** resources to it; a Mining building
then digs on its own. Robots recharge by landing on a **Flying Station** and
calling ``charge()``.

This starter loop, per robot:

    holds a starter kit  ->  fly to a resource spot, place a Mining site, drop the kit
    empty-handed         ->  haul a Mining building's output to the Base (which builds
                             more robots) or to a build site that still needs it
    low on energy        ->  fly to a Flying Station and charge

Read it, then make it smarter. See CLAUDE.md for the full SDK + rules.
"""

from simcode import buildings, on, robots, world

LOW_ENERGY = 30            # recharge below this much battery
MINE_COST = (6, 3)         # a Mining site needs 6 ore + 3 metal
STATION_COST = (4, 2)      # a Flying Station needs 4 ore + 2 metal

STEP: dict = {}            # robot id -> explore counter (so robots fan out)


# --- reading the world (fresh each event) ----------------------------------

def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def built_cells():
    """Cells that already hold a building OR a pending construction site."""
    return {b.position for b in buildings.all()}


def unbuilt_spot(r, want):
    """Nearest discovered resource spot with nothing built on it, preferring the
    resource `want` (so the fleet mines both ore and metal, not just one)."""
    built = built_cells()
    cands = [s for s in world.spots()
             if s.position not in built and s.spot.remaining > 0]
    if not cands:
        return None
    cands.sort(key=lambda s: (s.spot.resource != want, dist(r.position, s.position)))
    return cands[0].position


def stocked_mine(r):
    """Nearest active Mining building holding enough output to be worth a trip."""
    mines = [b for b in buildings.of_type("mining")
             if b.status == "active" and b.storage.ore + b.storage.metal >= 6]
    if not mines:
        return None
    return min(mines, key=lambda b: dist(r.position, b.position))


def active_station(r):
    """Nearest active Flying Station, or None."""
    stations = [b for b in buildings.of_type("flying_station") if b.status == "active"]
    if not stations:
        return None
    return min(stations, key=lambda b: dist(r.position, b.position))


def any_station():
    """True if a Flying Station exists or is being built."""
    return any(b.type == "flying_station" for b in buildings.all())


def mine_covers(res):
    """True if a Mining building for `res` exists (active or under construction).
    The Base needs BOTH ore and metal to make robots, and the two starting kits
    fund exactly one ore + one metal mine — so build the missing one first."""
    return any(b.type == "mining" and b.spot and b.spot.resource == res
               for b in buildings.all())


def needy_site(inv):
    """A construction site that still needs a resource this robot is carrying."""
    for b in buildings.all():
        if b.status != "constructing":
            continue
        c = b.construction
        need_ore = c.required.get("ore", 0) - c.delivered.get("ore", 0)
        need_metal = c.required.get("metal", 0) - c.delivered.get("metal", 0)
        if (need_ore > 0 and inv.ore > 0) or (need_metal > 0 and inv.metal > 0):
            return b
    return None


def empty_near_base(base):
    """Nearest discovered empty cell (no spot, no building) around the Base."""
    built = built_cells()
    best, bestd = None, 10**9
    for c in world.cells():
        p = (c.x, c.y)
        if p in built or c.spot is not None:
            continue
        d = dist(base.position, p)
        if 0 < d < bestd:
            best, bestd = p, d
    return best


def goto(r, pos, then):
    """Fly to a cell, or run `then()` once we're on it."""
    if r.cell == tuple(pos):
        then()
    else:
        r.move_to(*pos)


def explore(r):
    """Fly outward to reveal more of the endless map (robots fan out)."""
    i = STEP.get(r.id, 0)
    STEP[r.id] = i + 1
    dx, dy = ((6, 0), (0, 6), (-6, 0), (0, -6))[(i + len(r.id)) % 4]
    x, y = r.position
    r.move_to(x + dx, y + dy)


# --- the brain: one handler, fires whenever a robot is free ----------------

@on.idle
def act(e):
    r = robots[e.robot_id]
    base = buildings.base
    if base is None:
        return

    # 0. Low battery -> land on a Flying Station and charge (if one exists).
    st = active_station(r)
    if r.energy is not None and r.energy <= LOW_ENERGY and st is not None:
        goto(r, st.position, r.charge)
        return

    # 1. Holding a full starter kit -> turn a resource spot into a Mining site.
    #    (Starting/produced robots arrive with 6 ore / 3 metal — one mine's worth.)
    if r.inventory.ore >= MINE_COST[0] and r.inventory.metal >= MINE_COST[1]:
        # Cover BOTH resources first (the Base needs ore AND metal to grow); only
        # then mine whichever the Base is shorter on.
        if not mine_covers("metal"):
            want = "metal"
        elif not mine_covers("ore"):
            want = "ore"
        else:
            want = "ore" if base.storage.ore <= base.storage.metal else "metal"
        spot = unbuilt_spot(r, want)
        if spot is not None:
            if r.cell == spot:
                world.build("mining", *spot)   # self-builds once supplied
                r.drop(*MINE_COST)
            else:
                r.move_to(*spot)
        else:
            explore(r)                          # nothing to claim — reveal more map
        return

    # 2. Carrying mined output -> deliver to a build site that needs it, else Base.
    if r.inventory.ore + r.inventory.metal > 0:
        site = needy_site(r.inventory)
        target = site.position if site else base.position
        if r.cell == tuple(target):
            r.drop()
            if not site:
                base.build_robot(1)             # feed growth at the Base
        else:
            r.move_to(*target)
        return

    # 3. Empty-handed -> haul a stocked mine's output.
    mine = stocked_mine(r)
    if mine is not None:
        goto(r, mine.position, r.pick_up)
        return

    # 4. Idle with nothing to haul -> once both mines exist, make sure a Flying
    #    Station exists (don't spend the scarce starting metal on it too early),
    #    else explore.
    if st is None and not any_station() and mine_covers("ore") and mine_covers("metal"):
        spot = empty_near_base(base)
        if spot is not None:
            world.build("flying_station", *spot)  # haulers will supply it
            return
    explore(r)
