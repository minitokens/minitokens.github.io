#!/usr/bin/env python3
"""
fix_image_extensions.py

Detects image files with incorrect extensions (such as transparent PNGs named .jpg / .jpeg),
renames them to proper transparent extensions (.png), updates all matching Jekyll post
markdown references in _posts/, and optionally optimizes oversized images.

Usage:
    python3 fix_image_extensions.py --dry-run
    python3 fix_image_extensions.py
    python3 fix_image_extensions.py --optimize-oversized
"""

import argparse
import glob
import os
import subprocess
import sys
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../.."))
ASSETS_MINIS_DIR = os.path.join(PROJECT_ROOT, "assets/images/minis")
POSTS_DIR = os.path.join(PROJECT_ROOT, "_posts")


def optimize_image(img_path, max_dim=800, max_size_mb=1.0):
    """Downscales an image proportionally to max_dim and ensures file size <= max_size_mb."""
    im = Image.open(img_path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")

    if max_dim and (im.width > max_dim or im.height > max_dim):
        im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb else None
    curr = im
    while True:
        curr.save(img_path, format="PNG", optimize=True)
        file_size = os.path.getsize(img_path)
        if not max_bytes or file_size <= max_bytes or curr.width <= 300 or curr.height <= 300:
            break
        new_w = max(300, int(curr.width * 0.9))
        new_h = max(300, int(curr.height * 0.9))
        curr = curr.resize((new_w, new_h), Image.Resampling.LANCZOS)

    return os.path.getsize(img_path)


def main():
    parser = argparse.ArgumentParser(
        description="Fix image files incorrectly named with non-transparent extensions (like .jpg) to .png."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without renaming files or modifying posts.",
    )
    parser.add_argument(
        "--optimize-oversized",
        action="store_true",
        help="Resize and compress any images exceeding 1.0MB to max 800px.",
    )
    parser.add_argument(
        "--target-format",
        default="png",
        choices=["png", "webp"],
        help="Target transparent image extension (default: png).",
    )
    args = parser.parse_args()

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Scanning for non-transparent extensions in: {ASSETS_MINIS_DIR}")

    # 1. Find all .jpg / .jpeg files in assets/images/minis/
    mismatched_images = []
    for root, dirs, files in os.walk(ASSETS_MINIS_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                src_path = os.path.join(root, f)
                mismatched_images.append(src_path)

    mismatched_images.sort()
    print(f"Found {len(mismatched_images)} image(s) with .jpg/.jpeg extension.\n")

    if not mismatched_images:
        print("No mismatched image files found. Everything is in order!")
        return 0

    # 2. Verify image formats and determine target paths
    rename_plan = []
    for src in mismatched_images:
        rel_src = os.path.relpath(src, PROJECT_ROOT)
        base, old_ext = os.path.splitext(src)
        dest = base + f".{args.target_format}"
        rel_dest = os.path.relpath(dest, PROJECT_ROOT)

        try:
            with Image.open(src) as im:
                actual_fmt = im.format
                mode = im.mode
        except Exception as e:
            print(f"[ERROR] Could not read {rel_src}: {e}")
            continue

        if os.path.exists(dest):
            print(f"[ERROR] Target already exists: {rel_dest}! Skipping {rel_src}.")
            continue

        rename_plan.append({
            "src": src,
            "dest": dest,
            "rel_src": rel_src,
            "rel_dest": rel_dest,
            "actual_format": actual_fmt,
            "mode": mode,
            "size_mb": os.path.getsize(src) / (1024 * 1024),
        })

    print(f"Planned renames: {len(rename_plan)} file(s)")

    # 3. Find matching post files in _posts/
    post_files = glob.glob(os.path.join(POSTS_DIR, "**/*.md"), recursive=True)
    post_updates = {}  # post_path -> list of (old_ref, new_ref)

    # Build lookup table of relative web paths: e.g. "/assets/images/minis/.../foo.jpg"
    ref_map = {}
    for item in rename_plan:
        old_web_ref = "/" + item["rel_src"]
        new_web_ref = "/" + item["rel_dest"]
        ref_map[old_web_ref] = new_web_ref
        # Also handle without leading slash
        ref_map[item["rel_src"]] = item["rel_dest"]

    for p in post_files:
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        for old_ref, new_ref in ref_map.items():
            if old_ref in content:
                if p not in post_updates:
                    post_updates[p] = []
                post_updates[p].append((old_ref, new_ref))

    print(f"Found {len(post_updates)} Jekyll post(s) referencing these images.\n")

    if args.dry_run:
        print("=== DRY RUN PREVIEW ===")
        for item in rename_plan[:10]:
            print(f"  RENAME: {item['rel_src']} -> {item['rel_dest']} (Format: {item['actual_format']}, Mode: {item['mode']}, Size: {item['size_mb']:.2f}MB)")
        if len(rename_plan) > 10:
            print(f"  ... and {len(rename_plan) - 10} more image files.")

        print("\nSample Post Updates:")
        for p, updates in list(post_updates.items())[:5]:
            rel_p = os.path.relpath(p, PROJECT_ROOT)
            for old_ref, new_ref in updates:
                print(f"  POST: {rel_p} | {old_ref} -> {new_ref}")
        if len(post_updates) > 5:
            print(f"  ... and {len(post_updates) - 5} more posts.")

        print("\nDry run complete. Run without --dry-run to apply.")
        return 0

    # 4. Perform git mv or os.rename
    print("Renaming image files...")
    renamed_count = 0
    for item in rename_plan:
        src = item["src"]
        dest = item["dest"]
        # Try git mv first to preserve history
        res = subprocess.run(["git", "mv", src, dest], cwd=PROJECT_ROOT, capture_output=True, text=True)
        if res.returncode == 0:
            renamed_count += 1
        else:
            # Fallback to os.rename
            os.rename(src, dest)
            renamed_count += 1

        # Check if oversized optimization is requested
        if args.optimize_oversized and item["size_mb"] > 1.0:
            print(f"  Optimizing oversized image {item['rel_dest']} ({item['size_mb']:.2f}MB)...")
            new_size = optimize_image(dest, max_dim=800, max_size_mb=1.0)
            print(f"    -> Now {new_size / 1024:.1f} KB")

    print(f"Successfully renamed {renamed_count} image files.")

    # 5. Update posts
    print(f"Updating {len(post_updates)} Jekyll post files...")
    updated_posts_count = 0
    for p, updates in post_updates.items():
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = content
        for old_ref, new_ref in updates:
            new_content = new_content.replace(old_ref, new_ref)

        if new_content != content:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated_posts_count += 1

    print(f"Successfully updated {updated_posts_count} post markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
