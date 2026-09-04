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

## Workflow Procedure

### 1. Ingress & Identification
1. Check the `ingress/` folder at the repository root for new image files (`.png`, `.jpg`, `.webp`).
2. Identify the D&D monster name from the image filename or user instructions.
3. Determine the monster's 5e type (e.g., via `5e.tools` search or web search):
   - **Beast**: Category folder `beasts` (Frontmatter category: `Beasts`)
   - **Monstrosity**: Category folder `monstrosity` (Frontmatter category: `Monstrocities`)
   - **Elemental**: Category folder `elementals` (Frontmatter category: `Elementals`)
   - **Dragon**: Category folder `dragons` (Frontmatter category: `Dragons`)
   - **Humanoid / Gnome**: Category folder `humanoid/gnomes` (Frontmatter category: `Gnomes`)
4. **Clarification on Missing Information**:
   - If key metadata or details required for a complete post are missing or unknown (such as miniature manufacturer, campaign/set name, or ambiguous monster identity), ask the user for clarification before finalizing post creation.

### 2. Move Image Assets
1. Move the image files from `ingress/` to `assets/images/minis/<category_folder>/`.
2. Ensure the `ingress/` folder is retained with `.gitkeep` so it remains available for subsequent uploads.

### 3. Generate Jekyll Markdown Posts
1. Use today's date in `YYYY-MM-DD` format for post filenames.
2. Follow slug naming: `_posts/<category_folder>/YYYY-MM-DD-<slug>.md` (append `-2`, `-3`, etc., for multiple images of the same monster type).
3. Standard Frontmatter Template:

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

*Example for Archon-Studio Deuslair miniatures:*
```yaml
---
title:  "Purple Worm"
metadate: "hide"
categories: [ Monstrocities, Archon-Studio, DnL-Deuslair ]
image: "/assets/images/minis/monstrosity/PurpleWorm.png"
visit: "https://archon-studio.com/"
---
From the Archon-Studio Dungeons & Lasers: Deuslair Campaign.
```

### 4. Quality Control & Verification
1. Inspect created markdown posts to ensure `image:` path matches the target image exactly.
2. Confirm category spelling aligns with existing posts in `_posts/<category_folder>/`.
3. Check `git status` to verify untracked and modified files.
