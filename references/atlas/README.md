# FMHY Atlas

A machine-readable reference of FMHY's public wiki, built so that an AI agent can
understand FMHY's pages and its link catalogue without crawling rendered HTML.

connected to FMHY, `github.com/fmhy`, or `r/FREEMEDIAHECKYEAH`.** All wiki
content referenced here is FMHY's; see [Attribution and licence](#attribution-and-licence).

This repository is an **index of FMHY's public catalogue**. It contains no media,
no acquisition tooling, and no per-site playbooks. It never fetches anything from
the third-party sites FMHY links out to.

## What is in here

```
references/<source-class>/<page>.md   one file per FMHY page: title, provenance,
                                      source structure and every link line, verbatim
manifest.json                         one record per page + build provenance
links.jsonl                           one JSON record per link occurrence
build.py                              the single re-runnable entry point
data/raw/                             cached raw snapshot (gitignored)
```

Each `references/<source-class>/<page>.md` starts with YAML frontmatter:

| field | meaning |
| --- | --- |
| `page` | FMHY's own name for the page (sidebar/nav label, else the page's own `title:`, else its first heading) |
| `source_title` | the page's own first heading in the wiki source, when it differs |
| `slug` | the page's path on fmhy.net without a leading slash, e.g. `audio`, `other/FAQ`, `posts/sept-2026` |
| `source_class` | the taxonomy bucket (see below) |
| `source_url` | the public URL on fmhy.net |
| `upstream_path` | file path inside `github.com/fmhy/edit` |
| `upstream_blob` | permalink to that file at the exact commit captured |
| `upstream_commit` | the pinned upstream commit |
| `captured_at` | when the snapshot was taken (UTC) |
| `link_count` | number of link occurrences in this file |

The body is FMHY's own structure: headings reproduced verbatim at their original
levels, and every line that carries a link reproduced verbatim, in source order,
under the heading it sits beneath. A single `# <page>` title line is added at the
top so each file is self-describing. FMHY's `***` separators are dropped.

`links.jsonl` is the same information flattened, one JSON object per link
occurrence — the cheapest thing for an agent to grep or stream:

```json
{"page":"Music / Podcasts / Radio","slug":"audio","source_class":"wiki",
 "source_url":"https://fmhy.net/audio","section":"► Audio Streaming",
 "subsection":"▷ Streaming Apps","subsubsection":null,
 "link_text":"Limusic","url":"https://simohypers.github.io/limusic/",
 "line":"* ⭐ **[Limusic](https://simohypers.github.io/limusic/)** - YouTube Music Client"}
```

## Source selection

FMHY publishes three machine-readable surfaces. We use the first two, and use the
third only as an optional cross-check:

1. **`github.com/fmhy/edit` — the wiki source. Chosen as the content source of record.**
   Its `docs/*.md` files *are* the wiki pages, one file per page. They give clean
   per-page separation, the source's own headings, and each link on the line it
   lives on with its label and description intact.
   `scripts/generate-single-page.js` in that repo concatenates a fixed list of
   these files to build the single-page view, which proves the repo is upstream
   of the API.
2. **`https://fmhy.net/sitemap.xml` — the canonical page list.** 87 URLs. Used to
   decide which pages exist and what their public slugs are. robots.txt allows it.
3. **`https://api.fmhy.net/single-page`** returns the whole wiki as one 1.95 MB
   Markdown blob. It is a *concatenation* of the same `docs/*.md` files, so it
   cannot separate pages — it is strictly worse for this job. `build.py
   --verify-single-page` will fetch it, cache it, and check it against our pinned
   snapshot.

`build.py` fetches FMHY's content over **git** (a single clone/fetch of a public
repo) and fetches only `robots.txt` and `sitemap.xml` over HTTP. It never
requests a rendered wiki page.

## Taxonomy — how `<source-class>` is derived

`<source-class>` is **FMHY's own top-level taxonomy**, read at build time from
`docs/.vitepress/shared.ts`, the file that defines FMHY's sidebar. Nothing here is
hand-written; rerun `build.py` and re-derive it.

The rule:

- a sidebar **group** names a class (`wiki`, `tools`, `more`);
- a **standalone** sidebar entry names a class after the first segment of its own
  path (so `/beginners-guide` → `beginners-guide` and `/posts` → `posts`);
- a page **inherits the class of its nearest indexed ancestor**, so
  `/posts/sept-2026` lands in `posts` and `/other/FAQ` in `other`;
- pages FMHY never lists in its sidebar or nav fall back to `site`.

Result, as captured:

| class | pages | contents |
| --- | --- | --- |
| `wiki` | 13 | FMHY's "Wiki" sidebar group (privacy, ai, video, audio, gaming, …) |
| `tools` | 9 | FMHY's "Tools" sidebar group |
| `more` | 2 | FMHY's "More" group (unsafe, storage) |
| `posts` | 52 | the "Posts" entry and every changelog/announcement post |
| `other` | 5 | FAQ, backups, contributing, selfhosting, wallpapers |
| `beginners-guide` | 1 | FMHY's "Beginners Guide" |
| `site` | 4 | pages FMHY lists in neither sidebar nor nav: `index`, `feedback`, `sandbox`, `startpage` |

If this interpretation needs to change, change `parse_taxonomy`,
`build_class_map` and `resolve_class` in `build.py`, then rerun it. `manifest.json`
also carries the raw `taxonomy` array it derived, so you can diff FMHY's structure
between captures without re-cloning.

## Coverage

87 URLs are listed in FMHY's sitemap. 86 are present under `references/`.

| page | reason |
| --- | --- |
| `/recently-removed` | **Excluded.** It has no upstream Markdown source — it is generated at build time by FMHY's `scripts/generate-removed.js` from a removed-links data set. It is not a link catalogue page and has no per-page source file to preserve. It is recorded under `excluded_from_sitemap` in `manifest.json` on every build. |

Four pages have upstream sources that FMHY deliberately keeps out of the published
site (`index`, `feedback`, `sandbox`, `startpage` — see `excluded` in
`shared.ts`). They are indexed anyway so the repo is complete, and are flagged in
`manifest.json` with `excluded_from_site: true`. `posts` and `startpage` are
component-driven and legitimately contain zero links.

## Rebuilding

Requires Python 3.10+ and `git`. No third-party packages.

```bash
python3 build.py                # build; refetch only if the cache is older than 24h
python3 build.py --refresh      # force a refetch of the upstream snapshot
python3 build.py --offline      # build from cache, fail if there is no cache
python3 build.py --ttl 0        # treat any cache as stale
python3 build.py --with-prose   # also include non-link prose (see licence note)
python3 build.py --verify-single-page   # cross-check against api.fmhy.net mirror
```

`references/`, `manifest.json` and `links.jsonl` are rewritten from scratch each
run; the script is idempotent.

### Caching

`build.py` caches its raw snapshot under `data/raw/`, which is **gitignored**:

```
data/raw/fmhy-edit/     a shallow clone of fmhy/edit at the captured commit
data/raw/sitemap.xml    the captured sitemap
data/raw/robots.txt     the captured robots policy
data/raw/snapshot.json  commit, timestamps, what was fetched
```

- Deleting `data/raw/` and re-running refetches everything from FMHY.
- Running `build.py` twice in a row makes **zero** network requests the second
  time — the second run prints `cache hit -- no network requests`.
- Pass `--refresh` (or `--ttl 0`) to go back to the network before the TTL expires.

Re-runs therefore cost FMHY nothing until the cache actually goes stale.

### Politeness

- `robots.txt` is fetched first and **obeyed** for every HTTP request to FMHY's
  hosts (longest-match wins, with `*` and `$` support). If the sitemap were ever
  disallowed, the build aborts.
- HTTP requests are throttled to at most **one per second**. The wiki content
  itself arrives over a single `git clone --depth 1` (~1 network operation), not
  a crawl.
- The User-Agent names this project:
  `FMHY-Atlas/0.1 (non-commercial reference indexer; indexes FMHY's public link
  catalogue; +https://github.com/GwynTel/fmhy-skill)`.
- Nothing is ever requested from the third-party sites FMHY links to.

## Provenance

Every page records the upstream commit, the upstream file path, a permalink to that
file at that commit, the public URL, and the capture timestamp. `manifest.json`
carries the same for the whole build under `sources`, plus page and link counts
and the derived taxonomy.

| | |
| --- | --- |
| content source | `https://github.com/fmhy/edit` |
| captured commit | `f14105db2c0c0422ec6587d769919164716e45f6` (see `manifest.json.sources.upstream_commit` for the current build) |
| page list | `https://fmhy.net/sitemap.xml` (87 URLs) |
| taxonomy | `docs/.vitepress/shared.ts` |
| rebuild | `python3 build.py` |

Verify any page against FMHY directly: the `upstream_blob` permalink in each file's
frontmatter is the exact source revision the file was rendered from.

## Attribution and licence

FMHY's wiki is FMHY's work. Attribution belongs to FMHY and its contributors:
<https://fmhy.net/> · <https://github.com/fmhy/edit> · <https://reddit.com/r/FREEMEDIAHECKYEAH>

### What we found in the upstream sources

- **The site's code is Apache-2.0.** `fmhy/edit/.licenserc.json` applies this
  header to `**/*.ts` and `**/*.css`:

  > `Copyright (c) 2025 taskylizard. Apache License 2.0.`
  > `Licensed under the Apache License, Version 2.0 (the "License"); you may not`
  > `use this file except in compliance with the License. [...] distributed on an`
  > `"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express`
  > `or implied. See the License for the specific language governing permissions`
  > `and limitations under the License.`

  `fmhy/edit/docs/.vitepress/LICENSE` says the same — `Copyright (c) taskylizard.
  Apache License 2.0` — and `docs/.vitepress/README.md` states: *"This is the
  website source code to be used with VitePress. Licensed under the Apache License
  v2.0, see LICENSE for more information."*
- **There is no LICENSE file at the root of `fmhy/edit`** (404), and no content
  licence anywhere else. The Apache-2.0 grant covers the **site build code**
  (`*.ts`, `*.css`, `docs/.vitepress/`), **not** the wiki text in `docs/*.md`.
- **The wiki content therefore carries no stated licence.** FMHY's footer reads
  `Made with ❤ (rev: …) © 2026, Estd 2018. This site does not host any files.`
  with no further grant.
- **FMHY clearly intends copies to exist.** `docs/other/backups.md` links "Markdown
  Files — Raw .zip Archive" and "Markdown Page — Entire Markdown on Single Page",
  alongside an official self-hosting guide and ~20 listed mirrors. That is strong
  evidence redistribution is welcome — but it is not a licence grant, and it is
  not a waiver of attribution.

### What FMHY Atlas therefore does

Because the content licence is unstated rather than open, this repo is deliberately
**not a full mirror of FMHY's text**:

- ✅ Committed: page structure, headings, **link lines** (the catalogue entry — the
  link, its label and its one-line description, verbatim), and full provenance.
- ❌ Not committed: non-link prose — the free-standing explanatory paragraphs,
  warnings and notes that are not part of a catalogue entry. These are recorded as
  prose blocks internally and omitted from the published files.

Be aware of the size of that reservation: much of FMHY's editorial writing sits
*inside* its catalogue entries ("* [Tool](url) — what it does / caveat / mirror"),
so including prose only grows the tree by a few per cent. This repo should still
be read as a faithful index of FMHY's catalogue with attribution, not as a licence
to reprint the wiki.

If you are an FMHY maintainer and would like this changed in either direction —
more fidelity or less — open an issue and it will be honoured.

This repository's own code (`build.py`, `README.md`, the structure and the
manifest) is offered under **CC0-1.0** with no warranty, so the shape of the index
can be reused freely. The FMHY content it indexes is **not** covered by that and
remains FMHY's.

## Deliberately out of scope

- No `skill.md` (that is a separate piece of work).
- No agent that browses the sites FMHY links to, and no per-site acquisition
  playbook.
- No tooling that fetches or downloads media from third parties.
