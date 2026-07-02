"""Robot City Builder — starter controller (Python).

The simplest thing that works: each robot flies OUTWARD from the Base to reveal
the map, and flies back to recharge before its battery runs out. The Base doubles
as a charging pad, so there's nothing to build — this is just "hello, world".

Whenever a robot is free it fires `idle`; you read its live state and give it its
next command. Robots FLY over float coordinates and spend ENERGY doing it (run dry
mid-flight and the robot is destroyed) — so we turn back to charge in time.

Make it do more — mine, haul, build a city. See CLAUDE.md for the full SDK.
"""

from simcode import buildings, on, robots

# Each robot scouts a different direction, so together they fan out.
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


@on.idle
def act(e):
    r = robots[e.robot_id]
    base = buildings.base
    if base is None:
        return
    bx, by = base.position
    x, y = r.position
    home = abs(x - bx) + abs(y - by)          # ~energy needed to fly back

    # Turn back and charge while the battery can still get us home.
    if r.energy is not None and r.energy <= home + 15:
        r.charge() if r.cell == (bx, by) else r.move_to(bx, by)
        return

    # Otherwise keep flying outward to discover new map.
    dx, dy = DIRS[sum(map(ord, r.id)) % len(DIRS)]
    r.move_to(x + dx * 5, y + dy * 5)
