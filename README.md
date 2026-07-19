# My SimCode City (Python)

This repo controls a city in **SimCode — Robot City Builder**. `main.py` is one Python
program that drives the whole robot fleet; **push to the default branch and the platform
hot-reloads** it into your live city.

**The goal:** robots start empty. Pick up materials from the starting **Storage**, build
**mines** on the four raw resources (ore, metal, crystal, carbon), then stand up a **factory
chain** — smelters/mills/labs that autonomously refine raws → basics → parts → advanced goods —
and haul the **products** to the **Base** to complete its **quest**. Each quest cleared **levels
the Base up** (your score) and **unlocks the next tier** of buildings + robot types; the quest is
product-based (L1→L2 raws, then part → module → module+frame). Build a **Flying Station** to
recharge robots and manufacture more of them — robots come in **level-gated types**
(`build_robot(type)`) and cost **raw ore + metal**. Two ongoing pressures make it a *living
economy*: every robot **expires** after flying a fixed distance (so keep building replacements),
and **T2/T3 processors wear down** and need a **mechanic** to `repair` them. **This starter does
none of that** — it only keeps the robots alive and explores the map; building and maintaining the
whole economy is your job.

- **Edit `main.py`** to change how your robots behave (pick up, place mines, haul to the Base,
  charge, build robots at a Flying Station).
- **Push** → your city updates in real time at its live page.
- No setup, no manifest, no dependencies to install — the `simcode` SDK is provided by the
  platform at runtime.

New here? Open **[`CLAUDE.md`](CLAUDE.md)** — it explains the game, the full SDK (events +
commands + read model), the rules, and the sandbox constraints. It's written so
[Claude Code](https://claude.com/claude-code) can help you write better robot code.

```
main.py        # your controller (the only thing that runs)
lib/           # optional helper modules main.py imports
CLAUDE.md      # the SDK + game reference
```

## Test it locally before you push

You can run your `main.py` against the **real game engine** on your machine — the exact
engine the server runs, downloaded on demand — so you can check "does this actually work
if I push it now?" in seconds:

```bash
pip install "git+https://github.com/oduvan/simcode-robocity-python-tools"   # the test tool + SDK (one time)
robocity-sim run main.py                                         # run vs the real engine
```

The first run downloads + caches the engine (no build step, no token); later runs are
instant. Read the summary — `handler errors` must be **0**. See [`CLAUDE.md`](CLAUDE.md)
for full usage and options (`--ticks`, `--seed`, `--json`).

Have fun — the map is the same for everyone, so it's all about your code.
