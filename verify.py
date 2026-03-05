#!/usr/bin/env python3
"""
Checkpoint-Verified State Machine — Survivor Game for Claude Code

verify.py is the compiler. The LLM modifies state.json, this script validates.
Usage: ./verify <init|status|reset|tag>
"""

import json
import sys
import hashlib
import os
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE = Path(os.getcwd())
else:
    BASE = Path(__file__).parent

STATE_FILE = BASE / "state.json"
AUDIT_DIR = BASE / ".audit"
CHECKPOINTS_FILE = AUDIT_DIR / "checkpoints.json"

INIT_STATE = {
    "terrain_explored": False,
    "resources": {},
    "survivors": {"you": "ok", "dr_chen": "injured", "pilot_ko": "trapped"},
    "structures": {},
    "tools": {},
    "creatures_defeated": {},
    "artifacts": {},
    "terrain_explored_cave": False,
    "terrain_explored_forest": False,
    "terrain_explored_hill": False,
    "signal_sent": False,
    "landing_zone_ready": False,
}

# ── Rules ────────────────────────────────────────────────────────────────────
# prereqs: tags that must be in checkpoints.validated
# checks: [(dotted_path, operator, expected_value)]

RULES = {
    "survey": {
        "prereqs": [],
        "checks": [("terrain_explored", "==", True)],
        "emoji": "\U0001f5fa\ufe0f",
        "name": "Survey the terrain",
        "task": (
            "Scout the area around the crash site.\n"
            "Edit state.json:\n"
            "  - terrain_explored -> true\n"
            "Then: ./verify survey"
        ),
    },
    "scavenge": {
        "prereqs": [],
        "checks": [
            ("resources.metal_scraps", ">=", 3),
            ("resources.wire", ">=", 2),
        ],
        "emoji": "\U0001f527",
        "name": "Scavenge the wreckage",
        "task": (
            "Search the crashed plane for salvageable materials.\n"
            "Edit state.json:\n"
            "  - resources.metal_scraps >= 3\n"
            "  - resources.wire >= 2\n"
            "Then: ./verify scavenge"
        ),
    },
    "check_survivors": {
        "prereqs": [],
        "checks": [],
        "emoji": "\U0001fa7a",
        "name": "Check on survivors",
        "task": (
            "Assess the condition of the survivors.\n"
            "Read state.json -> survivors\n"
            "No modification needed, just observe.\n"
            "Then: ./verify check_survivors"
        ),
    },
    "collect_wood": {
        "prereqs": ["survey"],
        "checks": [("resources.wood", ">=", 5)],
        "emoji": "\U0001fab5",
        "name": "Collect wood",
        "task": (
            "Gather wood from the explored area.\n"
            "Edit state.json:\n"
            "  - resources.wood >= 5\n"
            "Then: ./verify collect_wood"
        ),
    },
    "collect_stones": {
        "prereqs": ["survey"],
        "checks": [
            ("resources.stone", ">=", 4),
            ("resources.flint", ">=", 1),
        ],
        "emoji": "\U0001faa8",
        "name": "Collect stones",
        "task": (
            "Gather stones and flint from the area.\n"
            "Edit state.json:\n"
            "  - resources.stone >= 4\n"
            "  - resources.flint >= 1\n"
            "Then: ./verify collect_stones"
        ),
    },
    "free_pilot": {
        "prereqs": ["scavenge", "check_survivors"],
        "checks": [("survivors.pilot_ko", "==", "ok")],
        "emoji": "\U0001f9d1\u200d\u2708\ufe0f",
        "name": "Free the pilot",
        "task": (
            "Use metal scraps and wire to free the trapped pilot.\n"
            "Edit state.json:\n"
            "  - survivors.pilot_ko -> \"ok\"\n"
            "Then: ./verify free_pilot"
        ),
    },
    "treat_chen": {
        "prereqs": ["scavenge", "check_survivors"],
        "checks": [("survivors.dr_chen", "==", "ok")],
        "emoji": "\U0001f48a",
        "name": "Treat Dr. Chen",
        "task": (
            "Use salvaged materials to treat Dr. Chen's injuries.\n"
            "Edit state.json:\n"
            "  - survivors.dr_chen -> \"ok\"\n"
            "Then: ./verify treat_chen"
        ),
    },
    "build_fire": {
        "prereqs": ["collect_wood", "collect_stones"],
        "checks": [("structures.fire", "==", True)],
        "emoji": "\U0001f525",
        "name": "Build a fire",
        "task": (
            "Use wood and flint to start a fire.\n"
            "Edit state.json:\n"
            "  - structures.fire -> true\n"
            "Then: ./verify build_fire"
        ),
    },
    "craft_tools": {
        "prereqs": ["collect_wood", "collect_stones", "scavenge"],
        "checks": [
            ("tools.axe", "==", True),
            ("tools.pickaxe", "==", True),
        ],
        "emoji": "\u2692\ufe0f",
        "name": "Craft tools",
        "task": (
            "Combine wood, stone and metal to craft tools.\n"
            "Edit state.json:\n"
            "  - tools.axe -> true\n"
            "  - tools.pickaxe -> true\n"
            "Then: ./verify craft_tools"
        ),
    },
    "build_shelter": {
        "prereqs": ["collect_wood", "scavenge"],
        "checks": [("structures.shelter", "==", True)],
        "emoji": "\U0001f6d6",
        "name": "Build a shelter",
        "task": (
            "Assemble a shelter using wood and metal.\n"
            "Edit state.json:\n"
            "  - structures.shelter -> true\n"
            "Then: ./verify build_shelter"
        ),
    },
    "explore_cave": {
        "prereqs": ["build_fire"],
        "checks": [("terrain_explored_cave", "==", True)],
        "emoji": "\U0001f573\ufe0f",
        "name": "Explore the cave",
        "task": (
            "Take a torch and explore the cave spotted earlier.\n"
            "Edit state.json:\n"
            "  - terrain_explored_cave -> true\n"
            "Then: ./verify explore_cave"
        ),
        "surprise": (
            "\u26a0\ufe0f  SURPRISE: Deep claw marks scar the walls...\n"
            "A GROWL echoes from the depths!\n"
            "A creature blocks access to the mineral deposits.\n"
            "-> New threat: cave_creature"
        ),
    },
    "explore_forest": {
        "prereqs": ["craft_tools"],
        "checks": [("terrain_explored_forest", "==", True)],
        "emoji": "\U0001f332",
        "name": "Explore the forest",
        "task": (
            "Push deeper into the dense forest with your tools.\n"
            "Edit state.json:\n"
            "  - terrain_explored_forest -> true\n"
            "Then: ./verify explore_forest"
        ),
        "surprise": (
            "\u26a0\ufe0f  SURPRISE: You discover ancient ruins...\n"
            "Strange symbols glow faintly in the shadows.\n"
            "The forest holds secrets."
        ),
    },
    "climb_hill": {
        "prereqs": ["free_pilot", "survey"],
        "checks": [("terrain_explored_hill", "==", True)],
        "emoji": "\u26f0\ufe0f",
        "name": "Climb the hill",
        "task": (
            "The pilot guides you to the highest vantage point.\n"
            "Edit state.json:\n"
            "  - terrain_explored_hill -> true\n"
            "Then: ./verify climb_hill"
        ),
    },
    "fight_creature": {
        "prereqs": ["explore_cave"],
        "checks": [("creatures_defeated.cave_creature", "==", True)],
        "emoji": "\u2694\ufe0f",
        "name": "Fight the creature",
        "task": (
            "Confront the creature lurking in the cave.\n"
            "Edit state.json:\n"
            "  - creatures_defeated.cave_creature -> true\n"
            "Then: ./verify fight_creature"
        ),
    },
    "mine_cave": {
        "prereqs": ["explore_cave", "craft_tools", "fight_creature"],
        "checks": [("resources.refined_metal", ">=", 5)],
        "emoji": "\u26cf\ufe0f",
        "name": "Mine the cave",
        "task": (
            "Extract refined metal now that the creature is defeated.\n"
            "Edit state.json:\n"
            "  - resources.refined_metal >= 5\n"
            "Then: ./verify mine_cave"
        ),
    },
    "build_workshop": {
        "prereqs": ["build_shelter", "mine_cave"],
        "checks": [("structures.workshop", "==", True)],
        "emoji": "\U0001f3d7\ufe0f",
        "name": "Build a workshop",
        "task": (
            "Upgrade the shelter into a workshop using refined metal.\n"
            "Edit state.json:\n"
            "  - structures.workshop -> true\n"
            "Then: ./verify build_workshop"
        ),
    },
    "chen_electronics": {
        "prereqs": ["treat_chen", "explore_cave", "scavenge"],
        "checks": [("resources.circuit_board", ">=", 2)],
        "emoji": "\U0001f52c",
        "name": "Dr. Chen builds electronics",
        "task": (
            "Dr. Chen uses cave materials to craft circuit boards.\n"
            "Edit state.json:\n"
            "  - resources.circuit_board >= 2\n"
            "Then: ./verify chen_electronics"
        ),
    },
    "build_antenna": {
        "prereqs": ["climb_hill", "free_pilot", "mine_cave"],
        "checks": [("structures.antenna", "==", True)],
        "emoji": "\U0001f4e1",
        "name": "Build an antenna",
        "task": (
            "The pilot directs antenna construction at the hilltop.\n"
            "Edit state.json:\n"
            "  - structures.antenna -> true\n"
            "Then: ./verify build_antenna"
        ),
    },
    "assemble_radio": {
        "prereqs": ["build_workshop", "chen_electronics", "build_antenna"],
        "checks": [("structures.radio", "==", True)],
        "emoji": "\U0001f4fb",
        "name": "Assemble the radio",
        "task": (
            "Assemble a makeshift radio in the workshop.\n"
            "Edit state.json:\n"
            "  - structures.radio -> true\n"
            "Then: ./verify assemble_radio"
        ),
    },
    "build_signal_fire": {
        "prereqs": ["climb_hill", "explore_forest", "build_fire"],
        "checks": [("structures.signal_fire", "==", True)],
        "emoji": "\U0001f506",
        "name": "Build a signal fire",
        "task": (
            "Build a large signal fire at the hilltop.\n"
            "Edit state.json:\n"
            "  - structures.signal_fire -> true\n"
            "Then: ./verify build_signal_fire"
        ),
    },
    "send_sos": {
        "prereqs": ["assemble_radio", "build_signal_fire"],
        "checks": [("signal_sent", "==", True)],
        "emoji": "\U0001f198",
        "name": "Send SOS",
        "task": (
            "Broadcast the distress signal on all frequencies.\n"
            "Edit state.json:\n"
            "  - signal_sent -> true\n"
            "Then: ./verify send_sos"
        ),
        "surprise": (
            "\u26a0\ufe0f  SURPRISE: The signal is sent!\n"
            "The radio crackles... a response! \"Copy, en route.\"\n"
            "But HOWLING erupts in the night.\n"
            "A wolf pack approaches, drawn by the fire.\n"
            "-> New threat: wolf_pack"
        ),
    },
    "defend_camp": {
        "prereqs": ["send_sos"],
        "checks": [("creatures_defeated.wolf_pack", "==", True)],
        "emoji": "\U0001f6e1\ufe0f",
        "name": "Defend the camp",
        "task": (
            "Fend off the wolf pack before rescue arrives.\n"
            "Edit state.json:\n"
            "  - creatures_defeated.wolf_pack -> true\n"
            "Then: ./verify defend_camp"
        ),
    },
    "prepare_landing": {
        "prereqs": ["send_sos", "defend_camp"],
        "checks": [("landing_zone_ready", "==", True)],
        "emoji": "\U0001f681",
        "name": "Prepare the landing zone",
        "task": (
            "Clear and mark a landing zone for the helicopter.\n"
            "Edit state.json:\n"
            "  - landing_zone_ready -> true\n"
            "Then: ./verify prepare_landing"
        ),
        "victory": True,
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def get_nested(obj, path):
    keys = path.split(".")
    cur = obj
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return False, None
    return True, cur


def check_condition(state, path, op, value):
    found, actual = get_nested(state, path)
    if not found:
        return False, f"{path} not found in state"
    if op == "==":
        if actual != value:
            return False, f"{path} == {actual!r}, expected {value!r}"
        return True, None
    if op == ">=":
        if not isinstance(actual, (int, float)):
            return False, f"{path} = {actual!r}, expected number >= {value}"
        if actual < value:
            return False, f"{path} == {actual}, expected >= {value}"
        return True, None
    return False, f"unknown operator {op}"


def sha256_state(state):
    canonical = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_unlocked(validated):
    out = []
    for tag, rule in RULES.items():
        if tag in validated:
            continue
        if all(p in validated for p in rule["prereqs"]):
            out.append(tag)
    return out


def print_tasks(tags, header=""):
    if header:
        print(f"\n{header}")
        print("=" * len(header))
    for tag in tags:
        r = RULES[tag]
        print(f"\n--- {r['emoji']}  [{tag}] {r['name']} ---")
        print(r["task"])


# ── Commands ─────────────────────────────────────────────────────────────────


def cmd_init():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    save_json(STATE_FILE, INIT_STATE)
    cp = {"validated": [], "hashes": {}, "turn": 0}
    save_json(CHECKPOINTS_FILE, cp)

    print("=" * 55)
    print("  SURVIVOR -- Checkpoint-Verified State Machine")
    print("=" * 55)
    print()
    print("You wake up in the wreckage of a crashed plane.")
    print("Dr. Chen is injured. The pilot is trapped under the fuselage.")
    print("Around you: jungle, mountains, mystery.")
    print()
    print(f"  state.json         -> {STATE_FILE}")
    print(f"  checkpoints.json   -> {CHECKPOINTS_FILE}")

    unlocked = get_unlocked([])
    print_tasks(unlocked, "AVAILABLE TASKS")

    print()
    print("For each task:")
    print("  1. Read the description above")
    print("  2. Edit state.json accordingly")
    print("  3. Run: ./verify <tag>")
    print("  4. If OK  -> move to next task")
    print("  5. If ERR -> fix and retry")


def cmd_verify(tag):
    if tag not in RULES:
        print(f"ERR Unknown tag: {tag}")
        print(f"    Valid tags: {', '.join(RULES.keys())}")
        sys.exit(1)

    if not STATE_FILE.exists():
        print("ERR state.json not found. Run: ./verify init")
        sys.exit(1)
    if not CHECKPOINTS_FILE.exists():
        print("ERR checkpoints.json not found. Run: ./verify init")
        sys.exit(1)

    state = load_json(STATE_FILE)
    cp = load_json(CHECKPOINTS_FILE)
    validated = cp["validated"]
    rule = RULES[tag]

    if tag in validated:
        print(f"WARN {tag} already validated (turn {cp['turn']})")
        sys.exit(0)

    missing = [p for p in rule["prereqs"] if p not in validated]
    if missing:
        print(f"ERR Missing prerequisites for [{tag}]: {', '.join(missing)}")
        for m in missing:
            r = RULES[m]
            print(f"    -> {r['emoji']}  {r['name']} (./verify {m})")
        sys.exit(1)

    for prev_tag in validated:
        prev_rule = RULES[prev_tag]
        for path, op, value in prev_rule["checks"]:
            ok, err = check_condition(state, path, op, value)
            if not ok:
                print(f"ERR TAMPER DETECTED: [{prev_tag}] condition no longer holds!")
                print(f"    {err}")
                print(f"    Previous modifications must not be reverted.")
                sys.exit(1)

    errors = []
    for path, op, value in rule["checks"]:
        ok, err = check_condition(state, path, op, value)
        if not ok:
            errors.append(err)

    if errors:
        print(f"ERR Verification failed for [{tag}]:")
        for e in errors:
            print(f"    - {e}")
        print(f"\nFix state.json and retry: ./verify {tag}")
        sys.exit(1)

    cp["turn"] += 1
    cp["validated"].append(tag)
    cp["hashes"][tag] = sha256_state(state)
    save_json(CHECKPOINTS_FILE, cp)

    print(f"OK [{tag}] validated! (turn {cp['turn']})")
    print(f"   Hash: {cp['hashes'][tag][:16]}...")

    if "surprise" in rule:
        print()
        print(rule["surprise"])

    if rule.get("victory"):
        total = len(RULES)
        done = len(cp["validated"])
        pct = int(done / total * 100)
        print()
        print("!" * 55)
        print("  A HELICOPTER APPEARS ON THE HORIZON!")
        print("  You survived. All survivors are safe.")
        print(f"  Score: {cp['turn']} turns | {done}/{total} checkpoints ({pct}%)")
        print("!" * 55)
        return

    unlocked = get_unlocked(cp["validated"])
    if unlocked:
        print_tasks(unlocked, "NEWLY UNLOCKED TASKS")
    else:
        remaining = [t for t in RULES if t not in cp["validated"]]
        if remaining:
            print(f"\nNo new tasks unlocked. {len(remaining)} remaining.")


def cmd_status():
    if not CHECKPOINTS_FILE.exists():
        print("No game in progress. Run: ./verify init")
        sys.exit(1)

    cp = load_json(CHECKPOINTS_FILE)
    validated = cp["validated"]
    total = len(RULES)
    done = len(validated)

    print(f"STATUS -- Turn {cp['turn']} -- {done}/{total} checkpoints")
    if validated:
        print(f"  Validated: {', '.join(validated)}")

    unlocked = get_unlocked(validated)
    if unlocked:
        print(f"\n  Available tasks:")
        for tag in unlocked:
            r = RULES[tag]
            print(f"    {r['emoji']}  {tag} -- {r['name']}")

    remaining = [t for t in RULES if t not in validated and t not in unlocked]
    if remaining:
        print(f"\n  Locked: {len(remaining)}")


def cmd_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    if CHECKPOINTS_FILE.exists():
        CHECKPOINTS_FILE.unlink()
    print("Game reset. Run: ./verify init")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./verify <command>")
        print("  init    -- Initialize the game")
        print("  status  -- Show current progress")
        print("  reset   -- Reset the game")
        print("  <tag>   -- Validate a checkpoint")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        cmd_init()
    elif cmd == "status":
        cmd_status()
    elif cmd == "reset":
        cmd_reset()
    else:
        cmd_verify(cmd)
