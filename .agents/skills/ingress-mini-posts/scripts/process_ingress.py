#!/usr/bin/env python3
"""
process_ingress.py

Master automation script for the ingress-mini-posts skill.
Automates the entire ingestion pipeline:
1. Detects new miniature images in ingress/
2. Removes backgrounds (producing transparent PNG or WebP cropped to bounding box)
3. Classifies monster type and determines category folder, post slug, and frontmatter
4. Moves image to assets/images/minis/<category_folder>/
5. Generates Jekyll markdown post in _posts/<category_folder>/
6. Cleans up ingress/ while retaining .gitkeep
7. Runs validation

Usage:
    python3 process_ingress.py [options] [files...]

Examples:
    # Process all minis in ingress/ for Archon-Studio Deuslair campaign
    python3 process_ingress.py --manufacturer Archon-Studio --campaign DnL-Deuslair

    # Dry-run to preview categorization, target image paths, and post markdown
    python3 process_ingress.py --dry-run

    # Process specific files
    python3 process_ingress.py ingress/RedDrake1.jpg --manufacturer Archon-Studio --campaign DnL-Deuslair
"""

import argparse
import datetime
import os
import shutil
import sys
import time

# Import sibling modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

sys.path.insert(0, SCRIPT_DIR)
from categorize import classify_monster
from knockout_background import process_image

try:
    from validate_posts import validate_posts, check_ingress
except ImportError:
    validate_posts = None
    check_ingress = None


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end ingestion script: background knockout, categorization, and post generation."
    )
    parser.add_argument("files", nargs="*", help="Optional specific files to process.")
    parser.add_argument(
        "--ingress-dir",
        default=os.path.join(REPO_ROOT, "ingress"),
        help="Path to ingress folder. Default: <repo_root>/ingress",
    )
    parser.add_argument(
        "--manufacturer",
        "-m",
        default="Archon-Studio",
        help="Miniature manufacturer name for frontmatter (e.g. Archon-Studio, Northstar, Loot-Studios).",
    )
    parser.add_argument(
        "--campaign",
        "-c",
        default="DnL-Deuslair",
        help="Campaign / set name for frontmatter (e.g. DnL-Deuslair, Frostgrave).",
    )
    parser.add_argument(
        "--visit",
        "-v",
        default="https://archon-studio.com/",
        help="Manufacturer / product URL.",
    )
    parser.add_argument(
        "--date",
        "-d",
        default=datetime.date.today().strftime("%Y-%m-%d"),
        help="Date for Jekyll post filename (YYYY-MM-DD). Default: today.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["png", "webp"],
        default="png",
        help="Image format (png or webp). Default: png.",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=10,
        help="Padding margin around bounding box. Default: 10.",
    )
    parser.add_argument(
        "--skip-knockout",
        action="store_true",
        help="Skip background removal (use if images are already transparent).",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Stage, commit, and push created posts and assets to git repository.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without writing files or moving images.",
    )

    args = parser.parse_args()

    # Determine input files
    target_files = []
    if args.files:
        target_files = [os.path.abspath(f) for f in args.files]
    else:
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        if os.path.exists(args.ingress_dir):
            for fname in sorted(os.listdir(args.ingress_dir)):
                if fname.startswith("."):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext in valid_exts:
                    target_files.append(os.path.join(args.ingress_dir, fname))

    if not target_files:
        print(f"No image files found in {args.ingress_dir}.")
        return

    print(f"Found {len(target_files)} image(s) to process:")
    for f in target_files:
        print(f"  - {os.path.basename(f)}")

    # Plan each file's categorization and target locations
    plan = []
    for file_path in target_files:
        base_name = os.path.basename(file_path)
        classification = classify_monster(base_name)

        folder = classification["folder"]
        category = classification["category"]
        extra_cats = classification["extra_categories"]
        title = classification["title"]
        slug = classification["slug"]
        img_base = classification["dest_image_base"]

        # Build categories list
        categories_list = [category]
        for ec in extra_cats:
            if ec not in categories_list:
                categories_list.append(ec)
        if args.manufacturer and args.manufacturer not in categories_list:
            categories_list.append(args.manufacturer)
        if args.campaign and args.campaign not in categories_list:
            categories_list.append(args.campaign)

        # Asset destination
        dest_img_filename = f"{img_base}.{args.format.lower()}"
        dest_img_rel = f"assets/images/minis/{folder}/{dest_img_filename}"
        dest_img_abs = os.path.join(REPO_ROOT, dest_img_rel)

        # Post destination
        post_filename = f"{args.date}-{slug}.md"
        post_rel = f"_posts/{folder}/{post_filename}"
        post_abs = os.path.join(REPO_ROOT, post_rel)

        # Post content
        cat_str = ", ".join(categories_list)
        post_content = f"""---
title:  "{title}"
metadate: "hide"
categories: [ {cat_str} ]
image: "/{dest_img_rel}"
visit: "{args.visit}"
---
From the {args.manufacturer} {args.campaign.replace('DnL-', 'Dungeons & Lasers: ')} Campaign.
"""

        plan.append({
            "src_path": file_path,
            "title": title,
            "folder": folder,
            "dest_img_abs": dest_img_abs,
            "dest_img_rel": dest_img_rel,
            "post_abs": post_abs,
            "post_rel": post_rel,
            "post_content": post_content,
        })

    print("\n=== Execution Plan ===")
    for item in plan:
        print(f"\n[{item['title']}]")
        print(f"  Source:     {item['src_path']}")
        print(f"  Target Img: {item['dest_img_rel']}")
        print(f"  Target Post: {item['post_rel']}")

    if args.dry_run:
        print("\n[DRY RUN] Finished preview. No changes made.")
        return

    # Execute plan
    print("\n=== Processing Images & Creating Posts ===")
    t_start = time.time()
    created_posts = []

    for item in plan:
        src = item["src_path"]
        dest_img = item["dest_img_abs"]
        dest_post = item["post_abs"]

        os.makedirs(os.path.dirname(dest_img), exist_ok=True)
        os.makedirs(os.path.dirname(dest_post), exist_ok=True)

        if args.skip_knockout:
            shutil.copy2(src, dest_img)
            print(f"Copied '{os.path.basename(src)}' -> '{item['dest_img_rel']}'")
        else:
            print(f"Knocking out background for '{os.path.basename(src)}'...")
            process_image(
                src,
                dest_img,
                margin=args.margin,
                out_format=args.format,
            )

        with open(dest_post, "w", encoding="utf-8") as f:
            f.write(item["post_content"])
        print(f"Created post '{item['post_rel']}'")
        created_posts.append(dest_post)

        # Remove from ingress if inside ingress directory
        if os.path.abspath(os.path.dirname(src)) == os.path.abspath(args.ingress_dir):
            os.remove(src)
            print(f"Removed source '{os.path.basename(src)}' from ingress.")

    # Ensure .gitkeep in ingress
    gitkeep_path = os.path.join(args.ingress_dir, ".gitkeep")
    if os.path.exists(args.ingress_dir) and not os.path.exists(gitkeep_path):
        with open(gitkeep_path, "w") as f:
            pass

    print(f"\nAll operations completed in {time.time() - t_start:.2f}s.")

    # Run validation
    if validate_posts:
        print("\n=== Running Validation Checks ===")
        checked, errors, warnings = validate_posts(created_posts)
        ingress_issues = check_ingress() if check_ingress else []
        if not errors and not ingress_issues:
            print(f"[OK] Validation passed: {checked} posts verified successfully!")
        else:
            print(f"[WARN] Validation found {len(errors) + len(ingress_issues)} issues:")
            for e in errors + ingress_issues:
                print(f"  - {e}")

    # Commit and push if requested
    if args.push and not args.dry_run:
        import subprocess
        print("\n=== Committing and Pushing to Git ===")
        titles = sorted(list(set(item["title"] for item in plan)))
        msg = f"Add {', '.join(titles)} miniatures and posts"
        try:
            subprocess.check_call(["git", "add", ".agents", "_posts", "assets", "ingress"], cwd=REPO_ROOT)
            subprocess.check_call(["git", "commit", "-m", msg], cwd=REPO_ROOT)
            subprocess.check_call(["git", "push"], cwd=REPO_ROOT)
            print(f"[OK] Successfully committed and pushed to git: {msg}")
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"Git push failed with error: {e}\n")


if __name__ == "__main__":
    main()
