[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/gwyntel/fmhy-skill)

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
  wiki catalogue — 13 main pages (`references/atlas/references/wiki/` in the
  repository; `references/wiki/` relative to the atlas directory), plus tools,
  changelogs, FAQ, and an Unsafe Sites blocklist. One markdown file
  per FMHY page, headings + link lines preserved. Greppable, no network
  required, and refreshable from upstream with the included `build.py`.

## Scope

This skill is **source discovery and vetting only**. It does not operate
torrent clients, manage downloads, or post-process files — pair it with your
own download workflow.

## Install with Vercel skills CLI

This repository publishes one skill at the root (`SKILL.md`). The canonical source is <https://github.com/gwyntel/fmhy-skill>.

```bash
npx skills add gwyntel/fmhy-skill --skill fmhy-skill --agent hermes-agent -g -y
```

Choose another supported agent with `--agent <agent>` or omit `-g` to install into the current project. To inspect what the repository exposes before installing:

```bash
npx skills add gwyntel/fmhy-skill --list
```

The skill uses its bundled offline atlas by default. In an agent that supports skills, ask for vetted FMHY sources for the requested media category; the skill instructions require consulting the matching atlas page and checking the Unsafe Sites list. It only discovers and vets sources; it does not operate download clients.

Update an installed skill with:

```bash
npx skills update fmhy-skill
```

For a manual checkout instead, clone the repository into your agent's skills directory:

```bash
git clone https://github.com/gwyntel/fmhy-skill <YOUR_SKILLS_DIR>/fmhy-skill
```

To refresh the bundled atlas from FMHY upstream (separate from updating this skill repository):

## Refreshing the atlas

```bash
cd <YOUR_SKILLS_DIR>/fmhy-skill/references/atlas
python3 build.py
```

Re-fetches the FMHY wiki from upstream and rebuilds the mirror in place.

## Troubleshooting

- If the CLI cannot find the skill, confirm the repository URL/name and use `--list`; this repository's skill is the root `SKILL.md` named `fmhy-skill`.
- If installation reports invalid or missing frontmatter, check that `SKILL.md` begins with YAML frontmatter containing lowercase `name` and a concise `description`.
- If the skill does not appear in the target agent, verify the selected `--agent` and whether you intended a global (`-g`) or project installation; ensure the target skills directory is writable.
- If `npx` is unavailable, install/use Node.js and npm, or use the manual clone method above.
- If updating the skill does not refresh the offline atlas, run the atlas refresh command separately; skill updates and atlas ingestion are distinct operations.

## Attribution

FMHY wiki text in `references/atlas/` is indexed for identification only;
FMHY hosts no files itself. See `references/atlas/LICENSE` for the atlas
code licence (CC0) and the exact upstream attribution terms.
