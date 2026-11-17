#!/usr/bin/env python3
"""
build_monster_cache.py

Rebuild the local 5e monster cache (resources/5e_monsters.json) from a local
checkout of the 5etools-src repository (the source for 5e.tools), so the
ingress-mini-posts skill never needs a web lookup.

The cache schema consumed by categorize.py is:

    { "<lowercase monster name>": { "name": str, "type": str,
                                    "size": str, "tags": [str],
                                    "source": str } }

Data source layout (inside 5etools-src):
    data/bestiary/bestiary-<ab>.json   ->  { "monster": [ { ... }, ... ] }

Each monster entry has:
    name    : str
    source  : str  (e.g. "MM")
    size    : [ "M" ]  (list; may be absent)
    type    : str  OR  { "type": str, "tags": [str] }  OR
                 { "type": { "choose": [str, ...] } }   (multi-type)
                 OR  null  (NPCs / special entries -> skipped)

Usage:
    python3 build_monster_cache.py [options]

Options:
    --5etools-dir <path>   Path to the 5etools-src checkout.
                           Default: auto-detected relative to this script
                           (../../../../5etools-src), which works as long as
                           both repos are checked out as siblings.
                          --output <path>      Output JSON path.
                           Default: ../resources/5e_monsters.json (relative
                           to this script).
    --print-stats          Print a short summary after writing.

The script always overwrites the cache in place.
"""

import argparse
import glob
import json
import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Default location of the 5etools-src checkout, relative to this script.
# minitokens.github.io/.agents/skills/ingress-mini-posts/scripts/build_monster_cache.py
#   -> ../../../../../5etools-src  (both repos are siblings)
DEFAULT_5ETOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", "..", "5etools-src"))
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "..", "resources", "5e_monsters.json")


def norm_type(raw):
    """Return a single lowercase 5e type string, or None to skip the entry.

    Handles the three shapes found in 5etools bestiary data:
      * "humanoid"
      * {"type": "humanoid", "tags": [...]}
      * {"type": {"choose": ["celestial", "fiend"]}}   -> first choice
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip().lower()
    if isinstance(raw, dict):
        t = raw.get("type")
        if isinstance(t, dict):
            choices = t.get("choose")
            if isinstance(choices, list) and choices:
                return str(choices[0]).strip().lower()
            return None
        if isinstance(t, str):
            return t.strip().lower()
    return None


def norm_size(raw):
    """Return a single 5e size letter, defaulting to 'M'."""
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if isinstance(raw, str) and raw:
        return raw.strip().upper()
    return "M"


def extract_tags(raw_type):
    """Pull a tags list out of a dict-shaped type entry, else []."""
    if isinstance(raw_type, dict):
        tags = raw_type.get("tags")
        if isinstance(tags, list):
            return [str(t) for t in tags]
    return []


def find_bestiary_files(bestiary_dir):
    """Sort bestiary-*.json so the result is byte-identical across machines."""
    files = glob.glob(os.path.join(bestiary_dir, "bestiary-*.json"))
    # Sort by the filename's book code for deterministic first-wins ordering.
    return sorted(files, key=lambda p: os.path.basename(p))


def build_cache(bestiary_dir):
    cache = {}
    files = find_bestiary_files(bestiary_dir)
    for fn in files:
        with open(fn, "r", encoding="utf-8") as f:
            data = json.load(f)
        for m in data.get("monster", []):
            mtype = norm_type(m.get("type"))
            if not mtype:
                continue  # NPCs / special entries with no 5e type
            name = (m.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in cache:
                continue  # first occurrence wins (deterministic)
            cache[key] = {
                "name": name,
                "type": mtype,
                "size": norm_size(m.get("size")),
                "tags": extract_tags(m.get("type")),
                "source": m.get("source", ""),
            }
    return cache


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild resources/5e_monsters.json from a local 5etools-src checkout."
    )
    parser.add_argument(
        "--5etools-dir",
        dest="etools_dir",
        default=DEFAULT_5ETOOLS_DIR,
        help="Path to the 5etools-src checkout. Default: %s" % DEFAULT_5ETOOLS_DIR,
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output JSON path. Default: %s" % DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--print-stats",
        action="store_true",
        help="Print a short summary after writing.",
    )
    args = parser.parse_args()

    bestiary_dir = os.path.join(args.etools_dir, "data", "bestiary")
    if not os.path.isdir(bestiary_dir):
        sys.stderr.write(
            "Error: no bestiary data found at %s\n"
            "Pass --5etools-dir pointing to a 5etools-src checkout.\n" % bestiary_dir
        )
        return 1

    cache = build_cache(bestiary_dir)

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Wrote %d monsters to %s" % (len(cache), out_path))
    if args.print_stats:
        import collections
        types = collections.Counter(v["type"] for v in cache.values())
        print("Types:")
        for t, n in sorted(types.items(), key=lambda kv: -kv[1]):
            print("  %-12s %d" % (t, n))

    return 0


if __name__ == "__main__":
    sys.exit(main())
