# My SimCode City (Python)

This repo controls a city in **SimCode — Robot City Builder**. `main.py` is one Python
program that drives the whole robot fleet; **push to the default branch and the platform
hot-reloads** it into your live city.

- **Edit `main.py`** to change how your robots behave (fly out, place mines, haul, charge, grow).
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

Have fun — the map is the same for everyone, so it's all about your code.
