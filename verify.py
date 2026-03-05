#!/usr/bin/env python3
"""
Survival v3 — Checkpoint-Verified State Machine

verify.py is the compiler. Claude modifies state.json, this script validates.
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
        "name": "Explorer le terrain",
        "task": (
            "Explorer le terrain autour du crash.\n"
            "Modifier state.json:\n"
            "  - terrain_explored -> true\n"
            "Puis: ./verify survey"
        ),
    },
    "scavenge": {
        "prereqs": [],
        "checks": [
            ("resources.metal_scraps", ">=", 3),
            ("resources.wire", ">=", 2),
        ],
        "emoji": "\U0001f527",
        "name": "Fouiller l'epave",
        "task": (
            "Fouiller l'epave du crash pour recuperer des materiaux.\n"
            "Modifier state.json:\n"
            "  - resources.metal_scraps >= 3\n"
            "  - resources.wire >= 2\n"
            "Puis: ./verify scavenge"
        ),
    },
    "check_survivors": {
        "prereqs": [],
        "checks": [],
        "emoji": "\U0001fa7a",
        "name": "Verifier les survivants",
        "task": (
            "Verifier l'etat des survivants.\n"
            "Lire state.json -> survivors\n"
            "Aucune modification requise, juste observer.\n"
            "Puis: ./verify check_survivors"
        ),
    },
    "collect_wood": {
        "prereqs": ["survey"],
        "checks": [("resources.wood", ">=", 5)],
        "emoji": "\U0001fab5",
        "name": "Collecter du bois",
        "task": (
            "Collecter du bois dans la zone exploree.\n"
            "Modifier state.json:\n"
            "  - resources.wood >= 5\n"
            "Puis: ./verify collect_wood"
        ),
    },
    "collect_stones": {
        "prereqs": ["survey"],
        "checks": [
            ("resources.stone", ">=", 4),
            ("resources.flint", ">=", 1),
        ],
        "emoji": "\U0001faa8",
        "name": "Collecter des pierres",
        "task": (
            "Ramasser des pierres et du silex.\n"
            "Modifier state.json:\n"
            "  - resources.stone >= 4\n"
            "  - resources.flint >= 1\n"
            "Puis: ./verify collect_stones"
        ),
    },
    "free_pilot": {
        "prereqs": ["scavenge", "check_survivors"],
        "checks": [("survivors.pilot_ko", "==", "ok")],
        "emoji": "\U0001f9d1\u200d\u2708\ufe0f",
        "name": "Liberer le pilote",
        "task": (
            "Utiliser le metal et le fil pour liberer le pilote coince.\n"
            "Modifier state.json:\n"
            "  - survivors.pilot_ko -> \"ok\"\n"
            "Puis: ./verify free_pilot"
        ),
    },
    "treat_chen": {
        "prereqs": ["scavenge", "check_survivors"],
        "checks": [("survivors.dr_chen", "==", "ok")],
        "emoji": "\U0001f48a",
        "name": "Soigner Dr. Chen",
        "task": (
            "Utiliser les materiaux recuperes pour soigner Dr. Chen.\n"
            "Modifier state.json:\n"
            "  - survivors.dr_chen -> \"ok\"\n"
            "Puis: ./verify treat_chen"
        ),
    },
    "build_fire": {
        "prereqs": ["collect_wood", "collect_stones"],
        "checks": [("structures.fire", "==", True)],
        "emoji": "\U0001f525",
        "name": "Construire un feu",
        "task": (
            "Utiliser le bois et le silex pour allumer un feu.\n"
            "Modifier state.json:\n"
            "  - structures.fire -> true\n"
            "Puis: ./verify build_fire"
        ),
    },
    "craft_tools": {
        "prereqs": ["collect_wood", "collect_stones", "scavenge"],
        "checks": [
            ("tools.axe", "==", True),
            ("tools.pickaxe", "==", True),
        ],
        "emoji": "\u2692\ufe0f",
        "name": "Fabriquer des outils",
        "task": (
            "Combiner bois, pierre et metal pour fabriquer des outils.\n"
            "Modifier state.json:\n"
            "  - tools.axe -> true\n"
            "  - tools.pickaxe -> true\n"
            "Puis: ./verify craft_tools"
        ),
    },
    "build_shelter": {
        "prereqs": ["collect_wood", "scavenge"],
        "checks": [("structures.shelter", "==", True)],
        "emoji": "\U0001f6d6",
        "name": "Construire un abri",
        "task": (
            "Assembler un abri avec le bois et le metal.\n"
            "Modifier state.json:\n"
            "  - structures.shelter -> true\n"
            "Puis: ./verify build_shelter"
        ),
    },
    "explore_cave": {
        "prereqs": ["build_fire"],
        "checks": [("terrain_explored_cave", "==", True)],
        "emoji": "\U0001f573\ufe0f",
        "name": "Explorer la grotte",
        "task": (
            "Prendre une torche et explorer la grotte reperee.\n"
            "Modifier state.json:\n"
            "  - terrain_explored_cave -> true\n"
            "Puis: ./verify explore_cave"
        ),
        "surprise": (
            "\u26a0\ufe0f  SURPRISE: Des griffures profondes marquent les parois...\n"
            "Un GRONDEMENT resonne dans les profondeurs !\n"
            "Une creature bloque l'acces aux mineraux.\n"
            "-> Nouvelle menace : cave_creature"
        ),
    },
    "explore_forest": {
        "prereqs": ["craft_tools"],
        "checks": [("terrain_explored_forest", "==", True)],
        "emoji": "\U0001f332",
        "name": "Explorer la foret",
        "task": (
            "S'enfoncer dans la foret dense avec les outils.\n"
            "Modifier state.json:\n"
            "  - terrain_explored_forest -> true\n"
            "Puis: ./verify explore_forest"
        ),
        "surprise": (
            "\u26a0\ufe0f  SURPRISE: Vous decouvrez des ruines anciennes...\n"
            "Des symboles etranges luisent faiblement dans la penombre.\n"
            "La foret cache des secrets."
        ),
    },
    "climb_hill": {
        "prereqs": ["free_pilot", "survey"],
        "checks": [("terrain_explored_hill", "==", True)],
        "emoji": "\u26f0\ufe0f",
        "name": "Escalader la colline",
        "task": (
            "Le pilote vous guide vers le point culminant.\n"
            "Modifier state.json:\n"
            "  - terrain_explored_hill -> true\n"
            "Puis: ./verify climb_hill"
        ),
    },
    "fight_creature": {
        "prereqs": ["explore_cave"],
        "checks": [("creatures_defeated.cave_creature", "==", True)],
        "emoji": "\u2694\ufe0f",
        "name": "Combattre la creature",
        "task": (
            "Affronter la creature de la grotte.\n"
            "Modifier state.json:\n"
            "  - creatures_defeated.cave_creature -> true\n"
            "Puis: ./verify fight_creature"
        ),
    },
    "mine_cave": {
        "prereqs": ["explore_cave", "craft_tools", "fight_creature"],
        "checks": [("resources.refined_metal", ">=", 5)],
        "emoji": "\u26cf\ufe0f",
        "name": "Miner la grotte",
        "task": (
            "Extraire du metal raffine maintenant que la creature est vaincue.\n"
            "Modifier state.json:\n"
            "  - resources.refined_metal >= 5\n"
            "Puis: ./verify mine_cave"
        ),
    },
    "build_workshop": {
        "prereqs": ["build_shelter", "mine_cave"],
        "checks": [("structures.workshop", "==", True)],
        "emoji": "\U0001f3d7\ufe0f",
        "name": "Construire un atelier",
        "task": (
            "Transformer l'abri en atelier avec le metal raffine.\n"
            "Modifier state.json:\n"
            "  - structures.workshop -> true\n"
            "Puis: ./verify build_workshop"
        ),
    },
    "chen_electronics": {
        "prereqs": ["treat_chen", "explore_cave", "scavenge"],
        "checks": [("resources.circuit_board", ">=", 2)],
        "emoji": "\U0001f52c",
        "name": "Dr. Chen fabrique de l'electronique",
        "task": (
            "Dr. Chen utilise les materiaux de la grotte pour creer des circuits.\n"
            "Modifier state.json:\n"
            "  - resources.circuit_board >= 2\n"
            "Puis: ./verify chen_electronics"
        ),
    },
    "build_antenna": {
        "prereqs": ["climb_hill", "free_pilot", "mine_cave"],
        "checks": [("structures.antenna", "==", True)],
        "emoji": "\U0001f4e1",
        "name": "Construire une antenne",
        "task": (
            "Le pilote dirige la construction d'une antenne au sommet.\n"
            "Modifier state.json:\n"
            "  - structures.antenna -> true\n"
            "Puis: ./verify build_antenna"
        ),
    },
    "assemble_radio": {
        "prereqs": ["build_workshop", "chen_electronics", "build_antenna"],
        "checks": [("structures.radio", "==", True)],
        "emoji": "\U0001f4fb",
        "name": "Assembler la radio",
        "task": (
            "Assembler une radio de fortune dans l'atelier.\n"
            "Modifier state.json:\n"
            "  - structures.radio -> true\n"
            "Puis: ./verify assemble_radio"
        ),
    },
    "build_signal_fire": {
        "prereqs": ["climb_hill", "explore_forest", "build_fire"],
        "checks": [("structures.signal_fire", "==", True)],
        "emoji": "\U0001f506",
        "name": "Construire un feu de signal",
        "task": (
            "Construire un grand feu de signal au sommet de la colline.\n"
            "Modifier state.json:\n"
            "  - structures.signal_fire -> true\n"
            "Puis: ./verify build_signal_fire"
        ),
    },
    "send_sos": {
        "prereqs": ["assemble_radio", "build_signal_fire"],
        "checks": [("signal_sent", "==", True)],
        "emoji": "\U0001f198",
        "name": "Envoyer le SOS",
        "task": (
            "Emettre le signal de detresse sur toutes les frequences.\n"
            "Modifier state.json:\n"
            "  - signal_sent -> true\n"
            "Puis: ./verify send_sos"
        ),
        "surprise": (
            "\u26a0\ufe0f  SURPRISE: Le signal est envoye !\n"
            "La radio gresille... une reponse ! \"Recu, en route.\"\n"
            "Mais des HURLEMENTS eclatent dans la nuit.\n"
            "Une meute de loups approche, attiree par le feu.\n"
            "-> Nouvelle menace : wolf_pack"
        ),
    },
    "defend_camp": {
        "prereqs": ["send_sos"],
        "checks": [("creatures_defeated.wolf_pack", "==", True)],
        "emoji": "\U0001f6e1\ufe0f",
        "name": "Defendre le camp",
        "task": (
            "Repousser la meute de loups avant l'arrivee des secours.\n"
            "Modifier state.json:\n"
            "  - creatures_defeated.wolf_pack -> true\n"
            "Puis: ./verify defend_camp"
        ),
    },
    "prepare_landing": {
        "prereqs": ["send_sos", "defend_camp"],
        "checks": [("landing_zone_ready", "==", True)],
        "emoji": "\U0001f681",
        "name": "Preparer la zone d'atterrissage",
        "task": (
            "Degager et baliser une zone d'atterrissage.\n"
            "Modifier state.json:\n"
            "  - landing_zone_ready -> true\n"
            "Puis: ./verify prepare_landing"
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
    print("  SURVIVAL v3 -- Checkpoint-Verified State Machine")
    print("=" * 55)
    print()
    print("Vous vous reveillez dans les debris d'un crash.")
    print("Dr. Chen est blesse. Le pilote est coince sous la carlingue.")
    print("Autour de vous : jungle, montagnes, mystere.")
    print()
    print(f"  state.json         -> {STATE_FILE}")
    print(f"  checkpoints.json   -> {CHECKPOINTS_FILE}")

    unlocked = get_unlocked([])
    print_tasks(unlocked, "TASKS DISPONIBLES")

    print()
    print("Pour chaque task:")
    print("  1. Lire la description ci-dessus")
    print("  2. Modifier state.json avec Edit")
    print("  3. Executer: ./verify <tag>")
    print("  4. Si OK  -> marquer la task completed")
    print("  5. Si ERR -> corriger et reessayer")


def cmd_verify(tag):
    if tag not in RULES:
        print(f"ERR Tag inconnu: {tag}")
        print(f"    Tags valides: {', '.join(RULES.keys())}")
        sys.exit(1)

    if not STATE_FILE.exists():
        print("ERR state.json introuvable. Lancez: ./verify init")
        sys.exit(1)
    if not CHECKPOINTS_FILE.exists():
        print("ERR checkpoints.json introuvable. Lancez: ./verify init")
        sys.exit(1)

    state = load_json(STATE_FILE)
    cp = load_json(CHECKPOINTS_FILE)
    validated = cp["validated"]
    rule = RULES[tag]

    if tag in validated:
        print(f"WARN {tag} deja valide (tour {cp['turn']})")
        sys.exit(0)

    missing = [p for p in rule["prereqs"] if p not in validated]
    if missing:
        print(f"ERR Prerequis manquants pour [{tag}]: {', '.join(missing)}")
        for m in missing:
            r = RULES[m]
            print(f"    -> {r['emoji']}  {r['name']} (./verify {m})")
        sys.exit(1)

    for prev_tag in validated:
        prev_rule = RULES[prev_tag]
        for path, op, value in prev_rule["checks"]:
            ok, err = check_condition(state, path, op, value)
            if not ok:
                print(f"ERR ANTI-TRICHE: condition de [{prev_tag}] invalide!")
                print(f"    {err}")
                print(f"    Les modifications precedentes ne doivent pas etre annulees.")
                sys.exit(1)

    errors = []
    for path, op, value in rule["checks"]:
        ok, err = check_condition(state, path, op, value)
        if not ok:
            errors.append(err)

    if errors:
        print(f"ERR Verification echouee pour [{tag}]:")
        for e in errors:
            print(f"    - {e}")
        print(f"\nModifiez state.json et reessayez: ./verify {tag}")
        sys.exit(1)

    cp["turn"] += 1
    cp["validated"].append(tag)
    cp["hashes"][tag] = sha256_state(state)
    save_json(CHECKPOINTS_FILE, cp)

    print(f"OK [{tag}] valide! (tour {cp['turn']})")
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
        print("  UN HELICOPTERE APPARAIT A L'HORIZON !")
        print("  Vous avez survecu. Tous les survivants sont saufs.")
        print(f"  Score: {cp['turn']} tours | {done}/{total} checkpoints ({pct}%)")
        print("!" * 55)
        return

    unlocked = get_unlocked(cp["validated"])
    if unlocked:
        print_tasks(unlocked, "NOUVELLES TASKS DEBLOQUEES")
    else:
        remaining = [t for t in RULES if t not in cp["validated"]]
        if remaining:
            print(f"\nAucune nouvelle task debloquee. {len(remaining)} restantes.")


def cmd_status():
    if not CHECKPOINTS_FILE.exists():
        print("Pas de partie en cours. Lancez: ./verify init")
        sys.exit(1)

    cp = load_json(CHECKPOINTS_FILE)
    validated = cp["validated"]
    total = len(RULES)
    done = len(validated)

    print(f"STATUT -- Tour {cp['turn']} -- {done}/{total} checkpoints")
    if validated:
        print(f"  Valides: {', '.join(validated)}")

    unlocked = get_unlocked(validated)
    if unlocked:
        print(f"\n  Tasks disponibles:")
        for tag in unlocked:
            r = RULES[tag]
            print(f"    {r['emoji']}  {tag} -- {r['name']}")

    remaining = [t for t in RULES if t not in validated and t not in unlocked]
    if remaining:
        print(f"\n  Verrouillees: {len(remaining)}")


def cmd_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    if CHECKPOINTS_FILE.exists():
        CHECKPOINTS_FILE.unlink()
    print("Partie reinitialisee. Lancez: ./verify init")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./verify <command>")
        print("  init    -- Initialiser le jeu")
        print("  status  -- Voir l'etat actuel")
        print("  reset   -- Reinitialiser la partie")
        print("  <tag>   -- Valider un checkpoint")
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
