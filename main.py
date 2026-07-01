"""Robot City Builder — starter controller (Python).

One script drives the whole fleet by id. Whenever a robot is free it fires
`idle`; you read its live state and give it its next command.

Robots FLY (float coords) and spend ENERGY — run dry mid-flight and a robot is
destroyed. Mining and construction are AUTONOMOUS: place a site with
`world.build(...)` and robots only HAUL to it; a Mining building then digs by
itself. Recharge with `charge()` on the Flying Station (one sits by the Base).

The loop, per robot: charge if low → spend a starter kit to build a mine → haul
mine output to the Base (which builds more robots) → repeat. Read it, then make
it smarter. See CLAUDE.md for the full SDK.
"""

from simcode import buildings, on, robots, world

KIT = (6, 3)  # a Mining site costs 6 ore + 3 metal — exactly one starter kit


def near(cells, to):
    """The cell nearest `to`, or None."""
    return min(cells, key=lambda c: abs(c[0] - to[0]) + abs(c[1] - to[1]), default=None)


@on.idle
def act(e):
    r, base = robots[e.robot_id], buildings.base
    if base is None:
        return
    inv, pos = r.inventory, r.position

    # Low battery → land on the Flying Station and charge.
    st = near([b.position for b in buildings.of_type("flying_station")], pos)
    if r.energy is not None and r.energy < 35 and st:
        r.charge() if r.cell == st else r.move_to(*st)
        return

    # Holding a starter kit → fly to a spot and turn it into a mine. Split the
    # first robots by id so the Base gets BOTH ore and metal (it needs both).
    if inv.ore >= KIT[0] and inv.metal >= KIT[1]:
        o, m = base.storage.ore, base.storage.metal
        want = "ore" if o < m else "metal" if m < o else ("ore" if sum(map(ord, r.id)) % 2 else "metal")
        taken = {b.position for b in buildings.all()}
        pref = [s.position for s in world.spots() if s.spot.resource == want and s.position not in taken]
        free = [s.position for s in world.spots() if s.position not in taken]
        spot = near(pref, pos) or near(free, pos)
        if spot is None:
            r.move_to(pos[0] + 6, pos[1])          # nothing known → explore
        elif r.cell == spot:
            world.build("mining", *spot)           # self-builds once we drop the kit
            r.drop(*KIT)
        else:
            r.move_to(*spot)
        return

    # Carrying mined output → haul to the Base, which produces more robots.
    if inv.ore + inv.metal > 0:
        if r.cell == tuple(base.position):
            r.drop()
            base.build_robot(1)
        else:
            r.move_to(*base.position)
        return

    # Empty → haul from a stocked mine, else explore to reveal more map.
    mines = [b.position for b in buildings.of_type("mining")
             if b.status == "active" and b.storage.ore + b.storage.metal >= 6]
    m = near(mines, pos)
    if m:
        r.pick_up() if r.cell == m else r.move_to(*m)
    else:
        r.move_to(pos[0] + 6, pos[1])
