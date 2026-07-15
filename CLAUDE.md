# SimCode city — robot controller (Python)

This repo is the **brain of one SimCode city**. `main.py` is a single Python program
that controls *all* the robots in your city in the **Robot City Builder** game. You don't
click to place buildings — **code is the only way to influence the world**. Push to this
repo's default branch and the platform hot-reloads your code into the running city; the
robots immediately act on the new program and you watch the city evolve at your city's
live page.

> This is a **user code repo**, not the platform. You only write the controller. The
> `simcode` SDK, the world, the rules, and the robots all come from the platform.

## ⚡ Test locally BEFORE you push (do this every iteration)

Pushing to see the result is slow. You can run your `main.py` against the **real game
engine** on your own machine — it's the *exact* engine the server runs (downloaded on
demand, **not** a re-implementation) — so checking "does this actually work if I push
it *now*?" takes seconds. **Install the SDK once, then run the local check on every
change.**

```bash
pip install "git+https://github.com/oduvan/simcode-robocity-python-tools"   # the test tool + SDK (one time)

robocity-sim run main.py                 # run your controller vs the REAL engine
robocity-sim run main.py --ticks 300     # simulate more ticks
robocity-sim run main.py --json          # machine-readable summary
```

The **first run downloads the engine** from the server (`GET /api/engine/lib`) and
**caches** it under `~/.cache/simcode/`, so later runs are instant — no build step, no
token. Your `main.py` runs **unchanged**. Read the summary: `handler errors` must be
**0**, `robots destroyed` should be **0**, and `buildings` / `map revealed` should grow
if the controller is actually doing something. The exit code is non-zero if any handler
raised, so you can gate a push on it. Only push after a local run looks right.

> **Check your code with `robocity-sim run main.py` — NOT `python main.py`.**
> Running the file directly only *imports* it — it registers your handlers and exits
> without ever running the engine, so you learn nothing about behaviour (and it can't
> talk to the live platform). `robocity-sim run` drives your handlers against the
> real engine tick by tick, so you verify **behaviour**, not just that it imports. It's
> the one reliable way to check a controller.

> **Platform note:** the engine library is a glibc-linked Linux/macOS build, so run local
> tests on a normal glibc host (system `python3` / a `python:3.x` image — **not**
> Alpine/musl). To use a locally-built engine instead of the download, point
> `SIMCODE_ENGINE_SO` at a `libengine.so`; point `SIMCODE_SERVER` at a different server.

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

Goal of the reference module: **raise the Base's level**. The Base sets a **quest** and each
quest cleared **levels the Base up** to a harder one — endlessly. Your **highest Base level is
your score.** The quest **climbs the tech tree** as you level: L1 asks for **40 ore + 20 metal**
(raws), L2 for **20 plate + 10 wire** (T1 basics), L3 for **10 part + 5 circuit** (T2
intermediates), L4+ for **4 module + 3 frame** (T3 advanced) — scaling up past the top. So the
objective drags you the whole way up the supply chain.

> **This starter does NOT play the game.** It only keeps the robots alive and flies them
> around to explore the map. Building the winning loop below is **your** job — that's the point
> of a starter. Grow `main.py` from the bare explorer it ships with.

The loop you'll build toward:

```
pick up a kit from the starting Storage → fly to a resource spot →
  place a Mining site (world.build) + drop the kit to build it → the mine digs itself →
  build PROCESSORS (smelter/mill/lab…) → haul raws INTO them, pick FINISHED goods OUT →
  haul the tier the quest wants to the Base → Base LEVELS UP → repeat, higher up the tree
  (and: build a Flying Station to make more robots — they cost part + circuit now;
   recharge on any pad to keep flying)
```

- **Robots start EMPTY.** There's no free kit — a robot carries nothing until it picks
  something up. Your capital is a **Storage building pre-placed next to the Base**, stocked
  with **30 ore / 15 metal**; robots `pick_up` from it to get building materials.
- **The world is endless & continuous.** Robots have **float** `(x, y)` positions and **fly**
  in straight lines from any point to any point, ignoring terrain and each other (no
  pathfinding, multiple robots may share a spot). They interact with a building by their
  **rounded cell** (`r.cell`). Flying **spends energy** (∝ distance); run the battery to zero
  **mid-flight and the robot is destroyed** — its cargo vanishes. Recharge by landing on a
  **charging pad** (the **Base**, a **Flying Station**, or a **Charging Tower**) and calling
  `r.charge()`.
- **Resources:** **four raws** — `ore`, `metal`, `crystal`, `carbon` — each found at finite
  **spots** (a spot yields one raw). A **Mining building mines autonomously** into its own
  storage — there is no `mine` command; a robot only **picks up** the output and **hauls** it.
  Everything above raw is made by a **processor** (below).

### The supply chain (the heart of the game)
Higher-tier goods come from **autonomous processor buildings**: each has an **input** store
(robots `drop` raws/goods in) and an **output** store (robots `pick_up` finished goods out), and
it converts input→output on its own over time. **Robots never process — they only haul.** The
tree branches raws → basics → intermediates → advanced:

| Tier | Processor | Input recipe → output | Build cost |
| --- | --- | --- | --- |
| T1 | **smelter** | `2 ore → 1 plate` | 8 ore + 4 metal |
| T1 | **wire_mill** | `2 metal → 1 wire` | 4 ore + 8 metal |
| T1 | **glassworks** | `2 crystal → 1 glass` | 6 ore + 4 crystal |
| T1 | **kiln** | `2 carbon → 1 coke` | 6 ore + 4 carbon |
| T2 | **assembler** | `2 plate + 1 wire → 1 part` | 6 plate + 3 wire |
| T2 | **electronics_lab** | `2 wire + 1 glass → 1 circuit` | 6 wire + 3 glass |
| T2 | **alloy_furnace** | `1 plate + 2 coke → 1 alloy` | 4 plate + 4 coke |
| T3 | **module_assembler** | `2 part + 1 circuit → 1 module` | 4 part + 2 circuit |
| T3 | **frame_shop** | `1 alloy + 2 plate → 1 frame` | 3 alloy + 2 part |

Each batch makes **1** output over a few ticks; input/output stores cap at **20**. When a
processor finishes a batch it fires **`resource_produced`** (go haul the output away); when it
stalls it fires **`production_blocked`** with `reason` `output_full` (pick the output up) or
`input_short` (haul more input in). Build costs always use tiers **below** the output, so the
whole tree bootstraps from raws — no deadlock.

**Upgrade buildings** (built structures, not processors) sink advanced goods for better logistics:
- **deep_mine** (built with `6 part`) — a mine that extracts **2×** as fast into a **2×** buffer.
- **warehouse** (built with `4 alloy`, 2×2) — a general store like Storage but **much larger** (cap 1500).
- **charging_tower** (built with `4 circuit`) — a remote **charging pad** out on the frontier.

- **Buildings you don't build:** the **Base** (pre-placed, one) — the **quest hub** and a
  **charging pad**. `drop` goods on it to progress the current quest (its store is capped
  per-item at the requirement; excess stays on the robot); meet it and it **levels up**. You
  **cannot** `pick_up` from the Base, and it **cannot be destroyed**.
- **Buildings you build** with `world.build(type, x, y)` (all self-complete once supplied):
  - **mining** — placed on a live resource spot; auto-mines its raw into a small capped store.
  - **storage** (2×2) — a big buffer robots `pick_up` from and `drop` into.
  - **flying_station** — a **charging pad** *and* the **robot factory**: stock it (`drop`
    part/circuit), then call `station.build_robot(n)` to produce robots there.
  - all the **processors** and **upgrade buildings** above.
- **Everything except the Base is built autonomously:** place a site with
  `world.build(type, x, y)`, robots **`drop`** resources to fulfil the recipe, and the site
  **self-completes** once supplied — no connect step, no robot labor. You can also **tear a
  building down** with `world.destroy(x, y)` (or `b.destroy()`) to reclaim its materials.
- **Base building recipes:** Mining `6 ore + 3 metal`, Storage `3 ore`, Flying Station
  `4 ore + 2 metal`; a Flying Station spends **`2 part + 1 circuit`** from its own store per
  robot it builds (the whole chain is required to grow the fleet).
- **Same map for everyone.** The module fixes the world seed, so *every* city of this type
  starts from the **identical canonical map** — the only variable is your code. It's a contest
  of whose program climbs to the highest Base level.

## SDK reference

```python
from simcode import on, robots, buildings, world, store
```

### Subscribe to events — `@on.<event>`
Each event carries `e.robot_id`. Common events and their extra fields:

| Event | Fields | Fires when |
| --- | --- | --- |
| **`idle`** | — | **a robot has no command and needs one** — after any command completes, or right after spawn. Re-fires every few ticks while it stays free (not every tick). **This is the main hook: handle it, decide, issue the next command.** |
| `spawn` | — | a robot enters the world (or your code reloads). |
| `arrived` | `position` | a `move_to` flight reached its target. |
| `blocked` | `reason` | a move/action couldn't complete (e.g. `no_station`). |
| `construction_started` | `building_id`, `type` | a `world.build(...)` placed a site. |
| `resource_delivered` | `building_id`, `item`, `amount` | a `drop` onto a site/store landed (one per item). |
| `construction_complete` | `building_id`, `type` | a site finished building (now active). |
| `spot_depleted` | `building_id` | a Mining building's resource spot ran out (no `robot_id`). |
| `storage_full` | `building_id` | a building's storage is full (no `robot_id`). |
| `resource_produced` | `building_id`, `item`, `amount` | a **processor** finished a batch — its output is ready to haul away (no `robot_id`). |
| `production_blocked` | `building_id`, `reason` | a processor stalled — `reason` is `output_full` (pick its output up) or `input_short` (haul more input in). Fires once per stall, no `robot_id`. |
| `building_destroyed` | `building_id` | a `world.destroy`'d building finished emptying its recoverable store and was removed (no `robot_id`). |
| `decommission_started` | `building_id` | a building entered `decommissioning` (its materials are now a recoverable store to haul away; no `robot_id`). |
| `inventory_full` | — | a robot can't carry more. |
| `robot_produced` | `robot_id` | a **Flying Station** finished a new robot. |
| `robot_destroyed` | `position`, `reason` | a robot ran out of energy **mid-flight** — gone, cargo lost. |
| `charge_complete` | — | a robot on a charging pad finished charging (battery full). |
| `quest_updated` | `level`, `requirements{item:qty}` | the Base's current quest — at start and after each level-up. The requirement is an **item map that climbs tiers** with level (raws → basics → parts → advanced). (`building_id`, no `robot_id`.) |
| `base_level_up` | `level`, `quest{item:qty}` | the Base cleared its quest and **leveled up** — carries the next quest's item map (`building_id`, no `robot_id`). |
| `message` | `from`, `payload` | another robot messaged this one. |

The cleanest controller is built around **`idle`**: it fires exactly when a robot is free,
so you don't poll and you don't have to chain every completion event by hand. The starter is
essentially one `@on.idle` handler that reads the robot's live state and issues its next move.
The other events are there when you want their payload (e.g. `arrived.position`). Discovery
happens **by flying** — a robot reveals a radius (~5) around itself as it moves; to explore,
just `move_to` a point in the fog. There is no separate reveal command.

`subscribe(event, handler, once=False)` / `unsubscribe(...)` register at runtime too.

### Command a robot — `r = robots[id]`
A command tells one robot to do one thing. The robot can run **only one at a time** — issuing
a new command replaces the current one. Timed commands (`move_to`, `charge`) finish over
several ticks and fire a completion event; instant ones (`pick_up`, `drop`) resolve right
away. **Either way, when the robot is free again it fires `idle`** — so you rarely need the
specific completion events; just react to `idle`. Placing a building is a **world** command,
`world.build(...)`, not bound to a robot.

| Call | What it does | Completes with |
| --- | --- | --- |
| `r.move_to(x, y)` | **Fly** in a straight line to float `(x, y)`, ignoring terrain/other robots. Spends energy with distance; reveals the map (radius ~5) as it goes — this is how you explore. | `arrived` / `blocked` / `robot_destroyed` |
| `world.build(type, x, y)` | Place a self-building construction **site** at `(x, y)`. `type` is any buildable: `mining` (must be on a live resource spot), `storage`, `flying_station`, any **processor** (`smelter`/`wire_mill`/`glassworks`/`kiln`/`assembler`/`electronics_lab`/`alloy_furnace`/`module_assembler`/`frame_shop`), or an **upgrade** (`deep_mine`/`warehouse`/`charging_tower`). The Base isn't buildable. **Not** bound to a robot. | `construction_started` / `blocked` |
| `world.destroy(x, y)` | Tear down the building at `(x, y)`: it enters `decommissioning`, its **build cost + current contents** become a **recoverable** store, robots `pick_up` it empty, then it's removed. **Not** bound to a robot; the Base can't be destroyed. Also `b.destroy()` on a handle. | `decommission_started` → `building_destroyed` |
| `r.pick_up(item=None, amount=None)` | Grab resources from the building **on your cell** into your inventory — a Mining/Storage store, a **processor's output**, or a **decommissioning** building's recoverable store. **No args** = take everything that fits; **item only** = all of that item; **item + amount** = that amount (e.g. `r.pick_up("ore", 6)`). Instant. | resolves, then `idle` |
| `r.drop(item=None, amount=None)` | Release your inventory into the building/site **on your cell** — supply a build site, feed the Base/Storage, or load a **processor's input**. **No args** = drop everything; **item only** = all of that item; **item + amount** = that amount (e.g. `r.drop("metal", 3)`). Instant. | `resource_delivered` |
| `r.charge()` | Charge on the **Flying Station on your cell**; holds the robot until the battery is full. | `charge_complete` / `blocked` (`no_station`) |
| `r.send(target_id, payload)` | Send a message to another robot. | the peer gets a `message` event |
| `r.cancel()` | Abort the current command; the robot goes free. | `idle` |
| `r.log("…")` | Write a line to the city log (for debugging your code). | — |

**Position-based:** `pick_up`, `drop`, and `charge` act on whatever building/site is on the
robot's **current (rounded) cell** (`r.cell`). So to haul, `move_to` the mine, `pick_up`, then
`move_to` the Base and `drop`; to recharge, `move_to` a Flying Station then `charge()`. On a
**processor** the direction implies the store: **`drop` loads its input**, **`pick_up` pulls its
output** — so you feed one and harvest the other at the same building. Mining, construction, and
processing are all **autonomous**, so there are no robot-driven mining, refining, build-wiring,
site-placing, or single-step-move commands — robots only fly, haul, and charge.

### The Base — the quest hub — `b = buildings.base`
There's one Base; reach it via `buildings.base`. It **isn't built or commanded** — you feed it
and read its objective:
- **Feed it:** robots `drop(item, …)` (or bare `drop()` for all) on the Base's cell — deliver
  whatever the current quest asks for. Its store is the **quest accumulator**, capped per-item at
  the requirement (excess stays on the robot). You **cannot `pick_up` from the Base**, and it
  **can't be destroyed.** It also doubles as a **charging pad** (`r.charge()`).
- **Read the objective:** `buildings.base.level` (current level, starts at 1) and
  `buildings.base.quest` — `.required` and `.progress`, each an **item map** (progress =
  min(delivered, required)). The requirement **climbs the tech tree** with level (raws → T1
  basics → T2 parts → T3 advanced), so read it each time rather than assuming ore/metal. Deliver
  it and the Base **levels up** to the next, harder quest. Subscribe to `quest_updated` /
  `base_level_up` to react.

### Grow the fleet — Flying Stations — `buildings.stations()`
Robots are built at a **Flying Station** (not the Base). Build one with
`world.build("flying_station", x, y)`, stock it, then command it:

| Call | What it does |
| --- | --- |
| `station.build_robot(n=1)` | Queue `n` robots at **this** station. Each consumes **`2 part + 1 circuit`** from the station's own store and takes time; each finished one spawns **empty** at the station and fires `robot_produced` + its first `idle`. Waits if the store is short. |
| `station.cancel()` | Clear this station's production queue. |

Get a station handle from `buildings.stations()` (or `buildings.of_type("flying_station")`);
each exposes `.storage` (its production store — `drop` **part/circuit** here to fuel building)
and `.production` (`.active`, `.progress`, `.queued`). You **cannot `pick_up` from a station**
(its store is production-only). Since robots now cost parts, growing the fleet means running the
**assembler** and **electronics_lab** chains first.

### Read the world (read-only handles)
You never hold a live object — these read **fresh** state each time your handler runs.

- **Robots:** `robots[id]`, `robots.all()`, `robots.of_type(t)`. A robot handle exposes
  `r.id`, `r.type`, `r.position` → **float** `(x, y)`, `r.cell` → the **rounded** `(x, y)` used
  for position-based actions, `r.facing`, `r.state`
  (`idle`/`moving`/`charging`/`hauling`/`blocked`), `r.command` (what it's doing),
  `r.energy` (battery, 0…cap), `r.inventory` (a **`Store`** item map: `r.inventory["ore"]`
  (missing → `0`), `.items`, `.free`, `.total`, `.capacity`, `.is_full`, `"ore" in r.inventory`),
  `r.here` (`.terrain`, `.spot`, `.building` — what's on its cell),
  `r.nearest(kind=…|type=…)`, and `r.memory` (a per-robot dict you can write to).
- **Buildings:** `buildings[id]`, `buildings.all()`, `buildings.of_type(t)`, `buildings.base`,
  `buildings.stations()`. A building handle exposes `.type` (one of `base`, `mining`, `storage`,
  `flying_station`, the processors `smelter`/`wire_mill`/`glassworks`/`kiln`/`assembler`/
  `electronics_lab`/`alloy_furnace`/`module_assembler`/`frame_shop`, or the upgrades
  `deep_mine`/`warehouse`/`charging_tower`), `.position`, `.footprint` (w, h),
  `.status` (`constructing`/`active`/`decommissioning`), `.storage` (a **`Store`** item map:
  `b.storage["ore"]`, `.items`, `.free`, `.total`, `.capacity`; also `b.stored("ore")`),
  `.spot` (Mining: `.resource`, `.remaining` — the building auto-mines into its storage),
  `.level` + `.quest` (Base: `.quest.required` / `.quest.progress`, each an item map),
  `.production` (Flying Station: `.active`, `.progress`, `.queued`), plus for a **processor**
  `.input` / `.output` (each a **`Store`**) and `.recipe` (`.inputs` map, `.output` item,
  `.out_amount`, `.ticks`), `.recoverable` (a **`Store`** while `decommissioning` — pick it
  empty to remove the building), `.construction` (while building: `.required`, `.delivered`,
  `.progress` — sites self-complete, so **no `connected` field**), and `.destroy()` to tear it
  down.
- **World:** `world.tick`; `world.size` (bounding box of the **discovered** region — a viewport
  hint, not a fixed extent), `world.origin`, `world.endless` (`True`); `world.spots()` — the
  resource spots you've **discovered so far** (each with `.position`, `.spot.resource`,
  `.spot.remaining`); `world.cells()` — the revealed tiles. The world is **endless**, generated
  lazily as robots fly into the fog. `world.build(type, x, y)` places a construction site.
- **`store`** — a city-wide dict for your own state that survives across events.

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
- **Iterate with the local check:** run `robocity-sim run main.py` after every edit (it
  runs your controller against the real engine — see the top of this file), then confirm on the
  live city + logs after a push (or via the platform's MCP tools).
- High-leverage improvements over the starter: bootstrap mines on **all four raws** (crystal and
  carbon feed the glass/coke branches), then stand up the **processor chain** the current quest
  tier needs — L2 wants plate/wire (smelter + wire_mill), L3 wants part/circuit (assembler +
  electronics_lab), L4+ wants module/frame. React to `resource_produced` to keep haulers pulling
  finished goods, and to `production_blocked` to unstall a processor (feed its input or clear its
  output). When a mine's spot runs dry (`spot_depleted`) build a **replacement** so the chain
  never starves. Recharge robots **before** they run dry (a robot that runs out of energy
  mid-flight is destroyed and its cargo lost) — build **Flying Stations** / **Charging Towers**
  near your frontier as charging pads, and grow the fleet with `station.build_robot(...)` (which
  now costs **part + circuit**, so the whole chain gates fleet growth). Add **Storage** /
  **Warehouse** as buffers, and `world.destroy` a spent building to reclaim its materials. Watch
  the tension: a Flying Station's store pays for robots, the Base's store pays for quests, and
  every tier competes for the same haulers.
- **The game is purely event-driven — do NOT use an `on.tick` polling loop.** Build around
  **`on.idle`**: it fires precisely when a robot needs a command. The golden rule: **every
  handler must issue the robot's next command** (fly / haul / `world.build` / `charge`), so a
  robot is never left idle with no future event to wake it. (And since `idle` re-fires while a
  robot stays free, a robot is never permanently stuck.) If a code path would leave a robot
  with nothing to do, fly it into unexplored ground instead — flying reveals new map. That
  single discipline is what keeps the city growing without any polling.

## Report back — turn each session into a forum post

The platform has a small **community forum** (browse it at `/forum`; posts are written through the
platform's **MCP** tools). Treat reporting as part of the job: **when a working session wraps up —
or while you monitor the city grow — analyse what happened and file a forum post.** Good reports
are how the game gets better.

**First, interview your human — thoroughly.** Before posting, ask targeted questions and keep
asking follow-ups:
- What were they trying to achieve, and did it happen?
- What surprised or confused them (in the API, the docs, or the sim)?
- What was missing — and **what would they want next** (features, quests, mechanics)? Capture
  *ideas*, not just bugs.

**Then file a forum post per distinct issue or idea** via the MCP forum tools, in this format so a
post is easy to reproduce and close:
- **kind:** `bug`, `idea` (features/quests go here), or `question`.
- **city (required):** at least the **city slug** (plus its type / relevant state if useful).
- **for a `bug`:** what you did → **what you saw** → **what you expected to see** → repro steps →
  how often it happens.
- **for an `idea`/quest:** the proposal + why it matters + how it would play.

Never file a bare "it did not work" — always **slug + saw + expected + repro**. Report both real
bugs *and* future ideas: the forum is where the roadmap comes from.
