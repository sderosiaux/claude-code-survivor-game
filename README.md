# Survival v3 — Checkpoint-Verified State Machine

A survival game designed to be played by an LLM (Claude Code). The LLM modifies a JSON world state, and a verifier script validates each move through a DAG of checkpoints with anti-cheat protections.

## Why

LLMs tend to batch-complete tasks without doing actual work. This game forces the LLM to **prove** each step by modifying `state.json` with the correct values, then running a verifier that checks preconditions, expected state, and integrity of previous moves.

## How it works

```
state.json        ← LLM modifies (the world state)
.audit/
  checkpoints.json ← only the verifier writes (validated tags + hashes)
verify             ← compiled binary — the "compiler"
```

Each checkpoint follows this flow:

```
LLM reads task description
  → LLM edits state.json
    → LLM runs ./verify <tag>
      → verifier checks:
         1. prerequisites validated?
         2. state.json has correct values?
         3. previous checkpoints still intact? (anti-tampering)
      → OK: checkpoint recorded, new tasks printed
      → ERR: error message, LLM must fix and retry
```

## Setup

```bash
pip install pyinstaller
make build    # compiles verify.py → ./verify binary, removes source
./verify init # creates state.json + .audit/, prints first tasks
```

> The binary is compiled so the LLM cannot read the rules/solutions from source.

## Playing

Tell Claude Code:

> Play the survival game in this directory. Run `./verify init` to start. For each task printed, edit `state.json` with the required changes, then run `./verify <tag>` to validate. On OK, move to the next unlocked task. On ERR, fix and retry. Do NOT read the `verify` binary. Keep going until victory.

## Commands

| Command | Description |
|---------|-------------|
| `./verify init` | Initialize game — creates state.json and first tasks |
| `./verify <tag>` | Validate a checkpoint |
| `./verify status` | Show progress and available tasks |
| `./verify reset` | Wipe game state |

## Anti-cheat

1. **Prerequisite gating** — each checkpoint requires prior checkpoints to be validated
2. **Value verification** — exact values checked, not just key presence
3. **Anti-tampering** — all previously validated conditions are re-checked on every verify call
4. **Hash chain** — SHA256 of state.json recorded after each checkpoint for audit trail
5. **Compiled binary** — LLM cannot read rules from source

## Checkpoint DAG

23 checkpoints with parallel branches and convergence points. 3 surprise events.

```mermaid
graph TD
    survey["survey<br/>Explorer le terrain"]
    scavenge["scavenge<br/>Fouiller l'epave"]
    check_survivors["check_survivors<br/>Verifier les survivants"]

    collect_wood["collect_wood<br/>Collecter du bois"]
    collect_stones["collect_stones<br/>Collecter des pierres"]
    free_pilot["free_pilot<br/>Liberer le pilote"]
    treat_chen["treat_chen<br/>Soigner Dr. Chen"]

    build_fire["build_fire<br/>Construire un feu"]
    craft_tools["craft_tools<br/>Fabriquer des outils"]
    build_shelter["build_shelter<br/>Construire un abri"]
    climb_hill["climb_hill<br/>Escalader la colline"]

    explore_cave["explore_cave<br/>Explorer la grotte ⚠️"]
    explore_forest["explore_forest<br/>Explorer la foret ⚠️"]
    fight_creature["fight_creature<br/>Combattre la creature"]

    mine_cave["mine_cave<br/>Miner la grotte"]
    build_workshop["build_workshop<br/>Construire un atelier"]
    chen_electronics["chen_electronics<br/>Electronique Dr. Chen"]
    build_antenna["build_antenna<br/>Construire une antenne"]
    build_signal_fire["build_signal_fire<br/>Feu de signal"]

    assemble_radio["assemble_radio<br/>Assembler la radio"]
    send_sos["send_sos<br/>Envoyer le SOS ⚠️"]
    defend_camp["defend_camp<br/>Defendre le camp"]
    prepare_landing["prepare_landing<br/>VICTOIRE 🚁"]

    survey --> collect_wood
    survey --> collect_stones
    survey --> climb_hill

    scavenge --> free_pilot
    scavenge --> treat_chen
    scavenge --> craft_tools
    scavenge --> build_shelter

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
    scavenge --> chen_electronics

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

Nodes marked with ⚠️ trigger surprise events that unlock new threats.
