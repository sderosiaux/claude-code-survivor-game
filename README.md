# claude-code-survivor-game

A survival game designed to be played by [Claude Code](https://docs.anthropic.com/en/docs/claude-code). The LLM modifies a JSON world state, and a verifier script validates each move through a DAG of 23 checkpoints with anti-cheat protections.

![Crash Landing Showcase](assets/showcase.gif)

## Why

Claude Code has an internal task system (TaskCreate/TaskUpdate) that tracks work items. We wanted to test driving that system from the outside — by having a script generate task descriptions on stdout, and letting Claude pick them up, execute them, and validate each step.

The challenge: LLMs tend to batch-complete tasks without doing actual work. This game forces Claude to **prove** each step by modifying `state.json` with correct values, then running a verifier that checks preconditions, expected state, and integrity of previous moves.

## How it works

```
state.json        ← Claude edits this (the world state)
.audit/
  checkpoints.json ← only the verifier writes (validated tags + hashes)
verify             ← compiled binary — the "compiler"
```

Each checkpoint follows this flow:

```
Claude reads task description
  → edits state.json
    → runs ./verify <tag>
      → verifier checks:
         1. prerequisites validated?
         2. state.json has correct values?
         3. previous checkpoints still intact? (anti-tampering)
      → OK: checkpoint recorded, new tasks printed
      → ERR: error message, Claude fixes and retries
```

## Setup

```bash
pip install pyinstaller
make build    # compiles verify.py → ./verify binary, removes source
./verify init # creates state.json + .audit/, prints first tasks
```

The binary is compiled so Claude cannot read the rules/solutions from source.

## Playing

Tell Claude Code:

> Play the survival game in this directory. Run `./verify init` to start. For each task printed, edit `state.json` with the required changes, then run `./verify <tag>` to validate. On OK, move to the next unlocked task. On ERR, fix and retry. Do NOT read the `verify` binary. Keep going until victory.

## Commands

| Command | Description |
|---------|-------------|
| `./verify init` | Initialize — creates state.json and prints first tasks |
| `./verify <tag>` | Validate a checkpoint |
| `./verify status` | Show progress and available tasks |
| `./verify reset` | Wipe game state |

## Anti-cheat

1. **Prerequisite gating** — each checkpoint requires prior ones to be validated first
2. **Value verification** — exact values checked, not just key presence
3. **Anti-tampering** — all previously validated conditions re-checked on every verify call
4. **Hash chain** — SHA256 of state.json recorded after each checkpoint for audit trail
5. **Compiled binary** — Claude cannot read rules from source

## Checkpoint DAG

23 checkpoints with parallel branches and convergence points. 3 surprise events.

```mermaid
graph TD
    survey["survey<br/>Survey the terrain"]
    scavenge["scavenge<br/>Scavenge the wreckage"]
    check_survivors["check_survivors<br/>Check on survivors"]

    collect_wood["collect_wood<br/>Collect wood"]
    collect_stones["collect_stones<br/>Collect stones"]
    free_pilot["free_pilot<br/>Free the pilot"]
    treat_chen["treat_chen<br/>Treat Dr. Chen"]

    build_fire["build_fire<br/>Build a fire"]
    craft_tools["craft_tools<br/>Craft tools"]
    build_shelter["build_shelter<br/>Build a shelter"]
    climb_hill["climb_hill<br/>Climb the hill"]

    explore_cave["explore_cave<br/>Explore the cave ⚠️"]
    explore_forest["explore_forest<br/>Explore the forest ⚠️"]
    fight_creature["fight_creature<br/>Fight the creature"]

    mine_cave["mine_cave<br/>Mine the cave"]
    build_workshop["build_workshop<br/>Build a workshop"]
    chen_electronics["chen_electronics<br/>Dr. Chen builds electronics"]
    build_antenna["build_antenna<br/>Build an antenna"]
    build_signal_fire["build_signal_fire<br/>Build a signal fire"]

    assemble_radio["assemble_radio<br/>Assemble the radio"]
    send_sos["send_sos<br/>Send SOS ⚠️"]
    defend_camp["defend_camp<br/>Defend the camp"]
    prepare_landing["prepare_landing<br/>VICTORY 🚁"]

    survey --> collect_wood
    survey --> collect_stones
    survey --> climb_hill

    scavenge --> free_pilot
    scavenge --> treat_chen
    scavenge --> craft_tools
    scavenge --> build_shelter
    scavenge --> chen_electronics

    check_survivors --> free_pilot
    check_survivors --> treat_chen

    collect_wood --> build_fire
    collect_wood --> craft_tools
    collect_wood --> build_shelter
    collect_stones --> build_fire
    collect_stones --> craft_tools

    free_pilot --> climb_hill
    free_pilot --> build_antenna

    treat_chen --> chen_electronics

    build_fire --> explore_cave
    build_fire --> build_signal_fire

    craft_tools --> explore_forest
    craft_tools --> mine_cave

    build_shelter --> build_workshop

    explore_cave --> fight_creature
    explore_cave --> mine_cave
    explore_cave --> chen_electronics

    explore_forest --> build_signal_fire

    climb_hill --> build_antenna
    climb_hill --> build_signal_fire

    fight_creature --> mine_cave

    mine_cave --> build_workshop
    mine_cave --> build_antenna

    build_workshop --> assemble_radio
    chen_electronics --> assemble_radio
    build_antenna --> assemble_radio

    assemble_radio --> send_sos
    build_signal_fire --> send_sos

    send_sos --> defend_camp
    send_sos --> prepare_landing
    defend_camp --> prepare_landing

    style prepare_landing fill:#22c55e,color:#fff
    style explore_cave fill:#f59e0b,color:#000
    style explore_forest fill:#f59e0b,color:#000
    style send_sos fill:#f59e0b,color:#000
```

Nodes marked ⚠️ trigger surprise events that spawn new threats.
