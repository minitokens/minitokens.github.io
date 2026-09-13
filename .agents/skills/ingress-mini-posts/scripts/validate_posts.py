#!/usr/bin/env python3
"""
validate_posts.py

Validates Jekyll blog posts, image paths, and ingress directory status.

Usage:
    python3 validate_posts.py [--recent-only] [--check-all]
"""

import argparse
import glob
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

def check_ingress():
    ingress_dir = os.path.join(REPO_ROOT, "ingress")
    if not os.path.isdir(ingress_dir):
        return [f"Missing ingress directory: {ingress_dir}"]

    issues = []
    items = [f for f in os.listdir(ingress_dir) if not f.startswith(".")]
    if items:
        issues.append(f"Ingress directory is not clean! Contains unhandled files: {items}")
    return issues


def validate_posts(posts):
    errors = []
    warnings = []
    checked = 0

    for post_path in posts:
        checked += 1
        with open(post_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if not content.startswith("---"):
            errors.append(f"{post_path}: Missing frontmatter opening '---'")
            continue

        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append(f"{post_path}: Malformed frontmatter")
            continue

        fm = parts[1]

        # Check title
        m_title = re.search(r"^title:\s*[\"']?(.*?)[\"']?\s*$", fm, re.MULTILINE)
        if not m_title or not m_title.group(1).strip():
            errors.append(f"{post_path}: Missing or empty 'title'")

        # Check categories
        m_cat = re.search(r"^categories:\s*\[(.*?)\]", fm, re.MULTILINE)
        if not m_cat:
            errors.append(f"{post_path}: Missing 'categories: [...]'")

        # Check image
        m_img = re.search(r"^image:\s*[\"']?(.*?)[\"']?\s*$", fm, re.MULTILINE)
        if not m_img:
            errors.append(f"{post_path}: Missing 'image:' field")
        else:
            rel_img = m_img.group(1).strip().lstrip("/")
            local_img_path = os.path.join(REPO_ROOT, rel_img)
            if not os.path.exists(local_img_path):
                errors.append(f"{post_path}: Referenced image does not exist -> {local_img_path}")
            elif os.path.getsize(local_img_path) == 0:
                errors.append(f"{post_path}: Referenced image is 0 bytes -> {local_img_path}")

    return checked, errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate Jekyll mini posts and image assets.")
    parser.add_argument("--recent-only", action="store_true", help="Only validate posts added/modified in git working tree")
    args = parser.parse_args()

    print("=== Validating Ingress Directory ===")
    ingress_issues = check_ingress()
    for issue in ingress_issues:
        print(f"  [ERROR] {issue}")
    if not ingress_issues:
        print("  [OK] Ingress directory is clean and ready.")

    print("\n=== Validating Jekyll Posts & Assets ===")
    if args.recent_only:
        # Get untracked or modified posts
        import subprocess
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT).decode("utf-8")
        posts = []
        for line in out.splitlines():
            path = line[3:].strip()
            if path.startswith("_posts/") and path.endswith(".md"):
                posts.append(os.path.join(REPO_ROOT, path))
    else:
        posts = sorted(glob.glob(os.path.join(REPO_ROOT, "_posts", "**", "*.md"), recursive=True))

    checked, errors, warnings = validate_posts(posts)
    print(f"Checked {checked} post(s).")

    for w in warnings:
        print(f"  [WARN] {w}")
    for e in errors:
        print(f"  [ERROR] {e}")

    if not errors and not ingress_issues:
        print("  [OK] All checked posts and asset references are valid!")
        sys.exit(0)
    else:
        print(f"\nValidation failed with {len(errors) + len(ingress_issues)} issue(s).")
        sys.exit(1)


if __name__ == "__main__":
    main()
