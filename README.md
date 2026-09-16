# fmhy-skill

Agent skill for **finding vetted free media sources using the FMHY catalogue**
([fmhy.net](https://fmhy.net/)). Ships a self-contained offline mirror of the
FMHY wiki so an agent can discover movies, TV, anime, music, books, games,
software, and more — without touching the live site unless freshness demands
it.

## What's inside

- `SKILL.md` — the skill: atlas-first lookup workflow, a per-category guide to
  the best vetted sources (streaming, downloading, torrents, books, games,
  AI tools, non-English), unsafe-site / malware avoidance, and video
  release-quality checks (CAM/TS/XviD/x265 flags).
- `references/atlas/` — **FMHY-Atlas**: a verbatim offline mirror of the FMHY
  wiki catalogue — 13 main pages (`references/atlas/references/wiki/`), plus
  tools, changelogs, FAQ, and an Unsafe Sites blocklist. One markdown file
  per FMHY page, headings + link lines preserved. Greppable, no network
  required, and refreshable from upstream with the included `build.py`.

## Scope

This skill is **source discovery and vetting only**. It does not operate
torrent clients, manage downloads, or post-process files — pair it with your
own download workflow.

## Install

Clone into your agent's skills directory:

```bash
git clone https://github.com/gwyntel/fmhy-skill <YOUR_SKILLS_DIR>/fmhy-skill
```

## Refreshing the atlas

```bash
cd <YOUR_SKILLS_DIR>/fmhy-skill/references/atlas
python3 build.py
```

Re-fetches the FMHY wiki from upstream and rebuilds the mirror in place.

## Attribution

FMHY wiki text in `references/atlas/` is indexed for identification only;
FMHY hosts no files itself. See `references/atlas/LICENSE` for the atlas
code licence (CC0) and the exact upstream attribution terms.
