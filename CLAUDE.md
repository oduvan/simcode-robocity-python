# SimCode city — robot controller (Python)

This repo is the **brain of one SimCode city**. `main.py` is a single Python program
that controls *all* the robots in your city in the **Robot City Builder** game. You don't
click to place buildings — **code is the only way to influence the world**. Push to this
repo's default branch and the platform hot-reloads your code into the running city; the
robots immediately act on the new program and you watch the city evolve at your city's
live page.

> This is a **user code repo**, not the platform. You only write the controller. The
> `simcode` SDK, the world, the rules, and the robots all come from the platform.

## How it works (the model)

- **One script, whole fleet.** `main.py` controls every robot, addressed by **id**.
- **Event-driven, async.** You register handlers; the game dispatches events; you react by
  issuing **commands** (intents). Data in → intents out. You never hold a live game object.
- **State is read fresh** from the world on each event — `robots[...]`, `buildings`, `world`
  reflect the current tick when your handler runs.
- **Serial per robot.** Events for one robot arrive one at a time; a robot runs one command
  at a time (a new command replaces the active one).
- **No manifest, no config.** The repo is just this script (+ optional `lib/`). Language is
  chosen when the city is created; the entry is always `main.py`; the world and starting
  robots are defined by the game module.

## The game you're playing (Robot City Builder)

Goal of the reference module: **grow the city**. The loop the starter implements:

```
scout (reveal the map) → build a Mining building on a resource spot → mine ore/metal
  → haul it to the Base → the Base produces more robots → more robots → faster growth
```

- **Resources:** `ore` and `metal`, found at finite **spots**. Mine them into a Mining
  building's local storage, then a robot **picks up** and **hauls** to the Base/Storage.
- **Buildings:** **Base** (pre-placed, one; produces robots from its store — *not* withdrawable),
  **Mining** (placed on a spot; cap'd storage), **Storage** (cheap, big buffer), **Road**
  (cheap; robots move faster on it). All but the Base are built: `start_construction` →
  `drop` resources to fulfill the recipe → `connect` (more connected robots finish faster).
- **Construction recipe (Mining):** 6 ore + 3 metal. The fleet **starts with 2 robots**, each
  carrying a 6/3 kit (enough to build one mine). Robots the Base produces also arrive with a kit.
- **Same map for everyone.** The module fixes the world seed, so *every* city of this type
  starts from the **identical canonical map** — the only variable is your code. It's a contest
  of whose program builds the better city.

## SDK reference

```python
from simcode import on, robots, buildings, world, store
```

### Subscribe to events — `@on.<event>`
Each event carries `e.robot_id`. Common events and their extra fields:

| Event | Fields | Fires when |
| --- | --- | --- |
| **`idle`** | — | **a robot has no command and needs one** — after any command completes, or right after spawn. Fires once per free transition (not every tick). **This is the main hook: handle it, decide, issue the next command.** |
| `spawn` | — | a robot enters the world (or your code reloads). |
| `arrived` | `position` | a `move_to` reached its target. |
| `blocked` | `reason` | a move/action couldn't complete. |
| `scan_result` | `cells` | a `scan` finished; `cells` lists revealed tiles/spots. |
| `construction_complete` | `building_id`, `type` | a platform finished (now active). |
| `mining_complete` | `resource`, `amount` | a `mine` produced into the mine's store. |
| `spot_depleted` | `building_id` | the resource spot a robot was mining ran out. |
| `storage_full` | `building_id` | a building's storage is full. |
| `inventory_full` | — | a robot can't carry more. |
| `robot_produced` | `robot_id` | the Base finished a new robot. |

The cleanest controller is built around **`idle`**: it fires exactly when a robot is free,
so you don't poll and you don't have to chain every completion event by hand. The starter is
essentially one `@on.idle` handler that reads the robot's live state and issues its next move.
The other events are there when you want their payload (e.g. `scan_result.cells`).

`subscribe(event, handler, once=False)` / `unsubscribe(...)` register at runtime too.

### Command robots — `r = robots[id]`
`r.move_to(x, y)` · `r.step(dir)` · `r.scan(radius=…)` · `r.start_construction("mining"|"storage"|"road")`
· `r.connect()` · `r.mine()` · `r.pick_up(ore=…, metal=…)` *(no args = all)* · `r.drop(ore=…, metal=…)`
*(no args = all)* · `r.send(target_id, payload)` · `r.cancel()` · `r.log("…")`.

Commands are **position-based** — `mine`/`drop`/`pick_up`/`connect`/`start_construction` act on
the robot's current cell (a robot can also drop into a Base/Storage on an **adjacent** cell).

### Read the world (read-only)
- `robots[id]`, `robots.all()`, `robots.of_type(t)`. Robot: `.id .type .position .facing .state`
  `.command .inventory(.ore/.metal/.free/.capacity/.is_full)` `.here(.terrain/.spot/.building)`
  `.nearest(kind=|type=)` `.find(cells, kind=)` `.memory` `.log()`.
- `buildings[id]`, `buildings.all()`, `buildings.of_type(t)`, `buildings.base`. Building:
  `.type .position .status .storage(.ore/.metal/.capacity/.free) .spot .production .construction`.
  Base only: `buildings.base.build_robot(n=1)` and `buildings.base.cancel()`.
- `world.tick`, `world.size`, `world.spots()` (discovered spots), `world.discovered`.
- `store` — a city-wide dict for your own persistent state.

## Constraints — read before editing

- **Sandbox.** Your code runs in a restricted sandbox. You may `from simcode import …` and use
  a normal-Python subset, but **no file/network/process access, no arbitrary imports, no
  `eval`/`exec`/`open`**. Keep helpers in `lib/` and import them normally.
- **Handlers must be fast.** Each handler has a tight CPU/time budget per invocation. Do a
  little work and return; don't loop for long or block.
- **State:** module-level globals persist while the process runs but **reset on a code reload**.
  For state that must survive a push, use `store` (city-wide) or `r.memory` (per robot).
- **Determinism:** don't rely on wall-clock or randomness; the world is seeded and replayable.
- **The SDK is provided** by the platform — do **not** `pip install simcode` or vendor it.

## Working in this repo with Claude Code

- The thing to improve is the **strategy** in `main.py` (and `lib/`). The world is fixed, so
  better code = a better city.
- You can't run the engine locally; iterate by reading the logic carefully and by checking the
  live city + logs after a push (or via the platform's MCP tools).
- High-leverage improvements over the starter: keep the Base fed with **both** ore and metal
  (it needs both to produce robots), reduce robots blocking each other near the Base, build
  **Storage** as a buffer and **Roads** for speed, and call `buildings.base.build_robot(...)`
  aggressively once resources allow.
- **The game is purely event-driven — do NOT use an `on.tick` polling loop.** Build around
  **`on.idle`**: it fires precisely when a robot needs a command. The golden rule: **every
  handler must issue the robot's next command** (move/mine/build/haul/scan), so a robot is
  never left idle with no future event to wake it. If a code path would leave a
  robot with nothing to do, make it `scan` or move instead. That single discipline is what
  keeps the city growing without any polling.
