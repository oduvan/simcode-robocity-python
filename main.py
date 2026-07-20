"""SimCode city controller — a MINIMAL starting point.

This starter does one thing on purpose: it keeps the robots alive and flies them
around to **explore the map**. It does NOT mine, build, haul, or climb Base levels —
that is for YOU to add.

Note: robots wear out two ways — running the battery to zero mid-flight (avoidable:
charge in time, handled below) AND simply flying too far. Every robot has a max
cumulative flight distance (its lifespan, `r.life_remaining` / `r.life_max`); once
it's flown that far it EXPIRES and is removed (`robot_expired`). This starter does
NOT replace expired robots, mine, process, repair, or level up the Base — growing and
replacing the fleet and running the whole economy (robot types, mining, the factory
tree, mechanic repairs, Base leveling) is YOUR job.

Read CLAUDE.md for the whole game (the goal, the buildings, the full SDK API) and
grow this controller from here. The idea is simple: `@on.idle` fires whenever a robot
needs its next order, so decide what the robot should do and issue one command.
"""

from simcode import on, robots

# Compass headings. A robot advances one heading per trip (kept in its memory) so the
# fleet fans out across the map instead of re-treading a single line into the fog.
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

EXPLORE_HOP = 5    # world units to fly per exploration step
CHARGE_MARGIN = 15  # spare battery to keep beyond the planned flight


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


@on.idle
def act(e):
    r = robots[e.robot_id]
    here = r.position
    pad = (0, 0)  # the Base sits at the origin and doubles as a charging pad

    # Pick the next explore target: a short hop along a rotating heading. Flying reveals
    # the map (~5 cells around the robot), so this is how you uncover resource spots.
    n = r.memory.get("hop", 0) + 1
    dx, dy = DIRS[n % len(DIRS)]
    dest = (here[0] + dx * EXPLORE_HOP, here[1] + dy * EXPLORE_HOP)

    # Stay alive — budget the WHOLE ROUND TRIP, not just the way home. A robot that flies
    # out to `dest` and can't get back to a charging pad dies mid-flight, so before we
    # commit to the hop we require enough battery for here→dest AND dest→pad plus a margin.
    # If it can't afford the round trip, divert to the pad and charge now. (The starter
    # only knows the Base pad; you can also charge on Flying Stations / Charging Towers.)
    if r.energy is not None:
        round_trip = _dist(here, dest) + _dist(dest, pad) + CHARGE_MARGIN
        if r.energy < round_trip:
            if r.cell == pad:
                r.charge()
            else:
                r.move_to(*pad)
            return

    # Enough battery for the round trip → commit to the explore hop.
    r.memory["hop"] = n
    r.move_to(*dest)
