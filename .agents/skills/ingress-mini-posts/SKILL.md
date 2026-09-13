---
name: ingress-mini-posts
description: >-
  Use this skill when processing miniature token images placed in the ingress folder or assets/images/minis/,
  identifying their D&D 5e monster type (via 5e.tools), moving image files to the appropriate category subfolder,
  generating Jekyll blog post markdown files in _posts with standard frontmatter, and preserving the ingress directory.
---

# Ingress Mini Post Generator Skill

This skill defines the standard workflow for ingesting miniature images, categorizing D&D monsters, moving asset files, and creating blog post markdown entries for the minitokens.github.io site.

---

## Automation Scripts

The skill includes dedicated Python automation scripts in `scripts/` backed by a local 5e monster cache (`resources/5e_monsters.json`):

| Script | Purpose |
|---|---|
| [`process_ingress.py`](file://scripts/process_ingress.py) | **All-in-one pipeline**: knocks out backgrounds, categorizes monsters, moves assets, creates Jekyll markdown posts, cleans `ingress/`, and runs validation. |
| [`knockout_background.py`](file://scripts/knockout_background.py) | Standalone background knockout using `rembg` (u2net model), alpha transparency generation, and tight bounding box cropping with configurable padding. |
| [`categorize.py`](file://scripts/categorize.py) | Categorization tool mapping miniature filenames to 5e types, category folders, Jekyll tags, post slugs, and titles. |
| [`validate_posts.py`](file://scripts/validate_posts.py) | Quality control validator checking that all post image links exist, frontmatter is intact, and `ingress/` is clean. |

---

## Prerequisites
Install the required background removal and image manipulation packages:
```bash
pip install "rembg[cpu]" pillow
```

---

## Quickstart: All-In-One Automated Workflow

To process all miniatures currently in `ingress/`:
```bash
# 1. Preview changes (dry-run)
python3 .agents/skills/ingress-mini-posts/scripts/process_ingress.py --dry-run --manufacturer Archon-Studio --campaign DnL-Deuslair

# 2. Execute end-to-end processing
python3 .agents/skills/ingress-mini-posts/scripts/process_ingress.py --manufacturer Archon-Studio --campaign DnL-Deuslair --visit "https://archon-studio.com/"
```

Common options:
- `--dry-run`: Preview planned categorization, destination image paths, and post contents without altering files.
- `--skip-knockout`: Use if input files are already transparent PNGs.
- `--format png|webp`: Output format (default: `png`).
- `--manufacturer <Name>`: Mini manufacturer (e.g. `Archon-Studio`, `Northstar`, `Loot-Studios`). Default: `Archon-Studio`.
- `--campaign <Name>`: Campaign or box name (e.g. `DnL-Deuslair`, `Frostgrave`). Default: `DnL-Deuslair`.
- `--visit <URL>`: Manufacturer or campaign website.

---

## Step-by-Step Manual Workflow

If you prefer to run steps individually:

### 1. Ingress & Identification
1. Check `ingress/` for new image files (`.png`, `.jpg`, `.webp`).
2. Run `categorize.py` to inspect monster classification and category mapping:
   ```bash
   python3 .agents/skills/ingress-mini-posts/scripts/categorize.py BlackDrake1 BlueDrake2 DrakeHandler
   ```

### 2. Background Removal & Knockout
When raw photos or non-transparent images are placed into `ingress/`, knockout backgrounds and crop to subject bounding box:
```bash
python3 .agents/skills/ingress-mini-posts/scripts/knockout_background.py --input-dir ingress/ --output-dir ingress/ --format png --margin 10
```

### 3. Move Image Assets
1. Move the processed transparent image files (`.png` / `.webp`) to `assets/images/minis/<category_folder>/`.
2. Delete raw input photos from `ingress/`.
3. Ensure `ingress/` retains `.gitkeep`.

### 4. Generate Jekyll Markdown Posts
1. Post filename convention: `_posts/<category_folder>/YYYY-MM-DD-<slug>.md` (append `-2`, `-3`, etc., for multiple angles).
2. Standard Frontmatter Template:
   ```yaml
   ---
   title:  "<Monster Name>"
   metadate: "hide"
   categories: [ <PrimaryCategory>, <Manufacturer>, <Campaign> ]
   image: "/assets/images/minis/<category_folder>/<ImageFilename>"
   visit: "<ManufacturerURL>"
   ---
   From the <Manufacturer> <Campaign> Campaign.
   ```

### 5. Quality Control & Verification
Run the validation script to verify that all posts point to valid images and that `ingress/` is clean:
```bash
python3 .agents/skills/ingress-mini-posts/scripts/validate_posts.py
```
Check `git status` to verify staged, untracked, and modified files.

### 6. Commit & Push Changes
Stage all modified and created files, commit with a descriptive message naming the added miniatures, and push to GitHub:
```bash
git add .agents _posts assets ingress
git commit -m "Add <Monster Names> miniatures and posts"
git push origin main
```
