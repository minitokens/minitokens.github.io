#!/usr/bin/env python3
"""
categorize.py

Identifies D&D 5e monster type and maps miniature filenames to site categories,
target directories, and Jekyll frontmatter metadata.

Usage:
    python3 categorize.py <name_or_filename> [...]

Example:
    python3 categorize.py BlackDrake1 Chiwingas2 DragonTurtle DrakeHandler
"""

import argparse
import difflib
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_FILE = os.path.join(SCRIPT_DIR, "..", "resources", "5e_monsters.json")

CATEGORY_MAP = {
    "aberration": ("aberrations", "Abberations"),
    "beast": ("beasts", "Beasts"),
    "celestial": ("celestials", "Celestials"),
    "construct": ("constructs", "Constructs"),
    "dragon": ("dragons", "Dragons"),
    "elemental": ("elementals", "Elementals"),
    "fey": ("fey", "Fey"),
    "fiend": ("fiends", "Fiends"),
    "giant": ("giants", "Giants"),
    "humanoid": ("humanoid/humans", "Humans"),
    "monstrosity": ("monstrosity", "Monstrocities"),
    "ooze": ("oozes", "Oozes"),
    "plant": ("plants", "Plants"),
    "undead": ("undead", "Undead"),
}

HUMANOID_RACES = {
    "gnome": ("humanoid/gnomes", "Gnomes"),
    "gnomes": ("humanoid/gnomes", "Gnomes"),
    "elf": ("humanoid/elves", "Elves"),
    "elves": ("humanoid/elves", "Elves"),
    "dwarf": ("humanoid/dwarves", "Dwarves"),
    "dwarves": ("humanoid/dwarves", "Dwarves"),
    "goblin": ("humanoid/goblins", "Goblins"),
    "goblins": ("humanoid/goblins", "Goblins"),
    "kobold": ("humanoid/kobolds", "Kobolds"),
    "kobolds": ("humanoid/kobolds", "Kobolds"),
    "orc": ("humanoid/orcs", "Orcs"),
    "orcs": ("humanoid/orcs", "Orcs"),
    "drow": ("humanoid/drow", "Drow"),
    "dragonborn": ("humanoid/dragonborn", "Dragonborn"),
    "tabaxi": ("humanoid/tabaxi", "Tabaxi"),
    "tiefling": ("humanoid/tiefling", "Tieflings"),
    "tieflings": ("humanoid/tiefling", "Tieflings"),
    "lycanthrope": ("humanoid/lycanthropes", "Lycanthropes"),
    "wereboar": ("humanoid/lycanthropes", "Lycanthropes"),
    "werewolf": ("humanoid/lycanthropes", "Lycanthropes"),
    "wererat": ("humanoid/lycanthropes", "Lycanthropes"),
    "merfolk": ("humanoid/merfolk", "Merfolk"),
    "mermaid": ("humanoid/merfolk", "Merfolk"),
    "sahuagin": ("humanoid/sahuagin", "Sahuagin"),
    "gnoll": ("humanoid/gnolls", "Gnolls"),
    "beastman": ("humanoid/beastmen", "Beastmen"),
    "beastmen": ("humanoid/beastmen", "Beastmen"),
    "human": ("humanoid/humans", "Humans"),
    "humans": ("humanoid/humans", "Humans"),
}

HUMANOID_ROLES = {
    "handler": "Casters",
    "cultist": "Cultists",
    "guard": "NPCs",
    "knight": "Fighters",
    "mage": "Casters",
    "wizard": "Casters",
    "sorcerer": "Casters",
    "warlock": "Casters",
    "priest": "Priests",
    "cleric": "Priests",
    "warpriest": "Casters",
    "thief": "Rogue",
    "rogue": "Rogue",
    "archer": "Archers",
    "commoner": "NPCs",
    "merchant": "NPCs",
    "barkeep": "NPCs",
    "barmaid": "NPCs",
    "butler": "NPCs",
    "bandit": "Fighters",
    "pirate": "Fighters",
    "paladin": "Fighters",
    "barbarian": "Fighters",
    "druid": "Casters",
    "bard": "Bards",
    "sailor": "NPCs",
}


def load_monsters_db():
    if os.path.exists(RESOURCE_FILE):
        try:
            with open(RESOURCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            sys.stderr.write(f"Warning: Could not read {RESOURCE_FILE}: {e}\n")
    return {}


_MONSTERS_DB = None


def get_monsters_db():
    global _MONSTERS_DB
    if _MONSTERS_DB is None:
        _MONSTERS_DB = load_monsters_db()
    return _MONSTERS_DB


def split_words(name):
    # CamelCase or snake_case / kebab-case to space-separated words
    clean = re.sub(r"[-_]+", " ", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", clean)
    return re.sub(r"([a-z\d])([A-Z])", r"\1 \2", s)


def slugify(title):
    s = title.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[-\s]+", "-", s)


def classify_monster(raw_input):
    """
    Given a raw filename or monster string, returns:
    {
        'folder': 'dragons',
        'category': 'Dragons',
        'extra_categories': ['Casters'], # if any
        'title': 'Black Drake',
        'slug': 'black-drake',
        'number_suffix': '2' or '',
        'dest_image_name': 'BlackDrake2.png'
    }
    """
    # Strip path and file extension if present
    base = os.path.splitext(os.path.basename(raw_input))[0]

    # Extract trailing number (e.g. BlackDrake2 -> 2, BlackDrake1 -> 1)
    m_num = re.search(r"(\d+)$", base)
    num_str = m_num.group(1) if m_num else ""
    no_num = re.sub(r"\d+$", "", base)

    words = split_words(no_num).strip().split()
    lower_words = [w.lower() for w in words]
    clean_title = " ".join(words)
    slug_base = slugify(clean_title)

    extra_categories = []
    folder = None
    category = None

    # Check for role tag (e.g. Caster, Cultist)
    for w in lower_words:
        if w in HUMANOID_ROLES:
            extra_categories.append(HUMANOID_ROLES[w])

    # 1. Humanoid Race check
    for w in lower_words:
        if w in HUMANOID_RACES:
            folder, category = HUMANOID_RACES[w]
            break

    # 2. Humanoid Role check if race not specified
    if not folder:
        for w in lower_words:
            if w in HUMANOID_ROLES:
                folder, category = "humanoid/humans", "Humans"
                break

    # 3. Dragons / Drakes
    if not folder:
        for w in lower_words:
            if any(k in w for k in ["drake", "dragon", "wyvern", "wyrmling"]):
                folder, category = "dragons", "Dragons"
                break

    # 4. Elementals
    if not folder:
        for w in lower_words:
            if any(k in w for k in ["elemental", "chwinga", "chiwinga", "genie", "djinn", "efreet", "dao", "mephit"]):
                folder, category = "elementals", "Elementals"
                break

    # 5. Fiends / Demons / Devils
    if not folder:
        for w in lower_words:
            if "demon" in w:
                folder, category = "demons", "Fiends"
                extra_categories.append("Demons")
                break
            elif "devil" in w:
                folder, category = "devils", "Fiends"
                extra_categories.append("Devils")
                break
            elif "fiend" in w:
                folder, category = "fiends", "Fiends"
                break

    # 6. Undead
    if not folder:
        for w in lower_words:
            if any(k in w for k in ["skeleton", "zombie", "ghoul", "ghast", "wight", "wraith", "ghost", "vampire", "lich", "mummy"]):
                folder, category = "undead", "Undead"
                break

    # 7. Check 5e DB lookup
    if not folder:
        db = get_monsters_db()
        query = " ".join(lower_words)
        if query in db:
            mtype = db[query]["type"]
            clean_title = db[query]["name"]
            slug_base = slugify(clean_title)
            if mtype in CATEGORY_MAP:
                folder, category = CATEGORY_MAP[mtype]

        if not folder:
            # Fuzzy match
            matches = difflib.get_close_matches(query, db.keys(), n=1, cutoff=0.7)
            if matches:
                mtype = db[matches[0]]["type"]
                clean_title = db[matches[0]]["name"]
                slug_base = slugify(clean_title)
                if mtype in CATEGORY_MAP:
                    folder, category = CATEGORY_MAP[mtype]

    # 8. Fallback
    if not folder:
        folder, category = "monstrosity", "Monstrocities"

    # Numbering convention:
    # First item: BlackDrake.png, slug: black-drake
    # Second item: BlackDrake2.png, slug: black-drake-2
    suffix = f"-{num_str}" if (num_str and num_str != "1") else ""
    post_slug = f"{slug_base}{suffix}"

    camel_title = "".join(words)
    img_num_suffix = num_str if (num_str and num_str != "1") else ""
    dest_image_base = f"{camel_title}{img_num_suffix}"

    return {
        "folder": folder,
        "category": category,
        "extra_categories": extra_categories,
        "title": clean_title,
        "slug": post_slug,
        "number_suffix": num_str,
        "dest_image_base": dest_image_base,
    }


def main():
    parser = argparse.ArgumentParser(description="Categorize miniatures into 5e monster categories.")
    parser.add_argument("names", nargs="+", help="Monster names or filenames to classify")
    args = parser.parse_args()

    for n in args.names:
        res = classify_monster(n)
        print(f"Input: {n}")
        print(f"  Title:            {res['title']}")
        print(f"  Category Folder:  {res['folder']}")
        print(f"  Primary Category: {res['category']}")
        print(f"  Extra Categories: {res['extra_categories']}")
        print(f"  Post Slug:        {res['slug']}")
        print(f"  Image Basename:   {res['dest_image_base']}")
        print()


if __name__ == "__main__":
    main()
