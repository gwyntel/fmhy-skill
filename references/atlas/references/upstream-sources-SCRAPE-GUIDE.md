---
name: fmhy-upstream-sources
description: How to read FMHY's wiki as structured data (upstream layout, which source to use, parser gotchas, licence position). Use before writing any code that ingests, indexes or summarises FMHY in the FMHY Atlas repo.
---

# FMHY upstream sources

Everything here was verified by hand against the live sources. The FMHY Atlas
ingestion layer (`/home/team/shared/fmhy-atlas/build.py`) already implements all of
it — read that first and copy its helpers rather than re-deriving them.

## Which source to use

| Source | Use it for | Notes |
| --- | --- | --- |
| `git clone https://github.com/fmhy/edit` | **content of record** | `docs/*.md` *are* the wiki pages, one file per page, with headings + links in context. 86 pages. |
| `https://fmhy.net/sitemap.xml` | canonical page list + public slugs | 87 URLs. robots.txt allows it. |
| `docs/.vitepress/shared.ts` | FMHY's **own taxonomy** and page names | `export const sidebar` and `export const nav`. |
| `https://api.fmhy.net/single-page` | cross-check only | `text/markdown`, ~1.95 MB, **not JSON**. It is a plain concatenation of 25 fixed `docs/*.md` files (see `scripts/generate-single-page.js`), so it cannot separate pages. Don't use it as the primary source. |

`fmhy.net/single-page` (no `api.` subdomain) is a 404. `github.com/fmhy/FMHY` is just
a README + `fmhy.md` pointer — not a content mirror.

## Parser gotchas (all cost real debugging time)

- **`api.fmhy.net/single-page` returns Markdown, not JSON.** Inspect content-type
  before assuming a schema.
- **Inline SVG contains `xmlns="http://www.w3.org/2000/svg"`.** A naive bare-URL
  regex harvests it as a link. Exclude the `http://www.w3.org/` namespace, and treat
  lines starting with `<` as markup unless they carry a markdown link.
  Worst offender: `docs/index.md`, which is almost entirely a Vue component.
- **FMHY sprinkles U+2060 (word joiner) and U+200B inside link text** as a rendering
  workaround. Strip them when comparing or matching; keep them in verbatim output.
- **`docs/posts/*.md` and `docs/posts.md` carry VitePress frontmatter with a real
  `title:`.** That is a far better page name than anything derivable from the body
  (the bodies are prose announcements with no H1). Always parse frontmatter first.
- **Page names live in three places, in this order:** frontmatter `title:`, then the
  sidebar/nav label in `shared.ts` (emoji wrapped in `<span class="i-twemoji:…">`),
  then the page's own first heading. A page's first H1 is usually a *section*
  heading ("► Audio Streaming"), not the page title.
- **Heading levels run 1–6, and `######` is real** (`docs/posts/support-ia.md`).
  Do not plan on demoting headings by one level to make room for a title.
- **`***` on its own line is FMHY's separator**, not a heading or a hr.
- **Custom components**: `<Post`, `<WallpaperCard`, `<StartPage`, `<Index`. Six files
  are component-driven and legitimately contain 0–1 links.
- **Do not expect `docs/.vitepress/shared.ts` to be valid JSON-ish.** `sidebar` and
  `nav` are TS arrays containing a ternary (`meta.build.nsfw ? {...} : {}`). A
  brace-matching scanner that skips string literals is enough; a JSON parser is not.

## Taxonomy

FMHY's sidebar (`shared.ts`) is the authoritative top-level taxonomy:
groups `Wiki`, `Tools`, `More`, plus standalone entries `Beginners Guide`, `Posts`,
`Contribute`. `/audio` and `/educational` appear in both `Wiki` and `Tools`, but the
second appearance is an **anchor** (`/audio#audio-tools`) — anchor-strip before
mapping, and let the first assignment win. Pages inherit their nearest indexed
ancestor, so `posts/sept-2026` → `posts` and `other/FAQ` → `other`. Four pages
(`index`, `feedback`, `sandbox`, `startpage`) are in neither sidebar nor nav.

## Coverage and exclusions

`/recently-removed` is in the sitemap but has **no upstream Markdown** — it is
generated at build time by `scripts/generate-removed.js`. Exclude it and say why.
`shared.ts` also declares `excluded = [readme.md, single-page, feedback.md,
index.md, sandbox.md, startpage.md]`: these exist upstream but FMHY keeps them out
of the published site. Index them anyway and flag them.

## Licence position (read before redistributing)

- **Site code is Apache-2.0**, `Copyright (c) taskylizard` — see `.licenserc.json`
  (applies to `**/*.ts` and `**/*.css`) and `docs/.vitepress/LICENSE`.
- **There is no LICENSE at the repo root (404) and no content licence anywhere.**
  The wiki text in `docs/*.md` is **unlicensed**, i.e. all rights reserved by
- FMHY clearly *wants* copies to exist — `docs/other/backups.md` publishes a raw
  `.zip` of the markdown, a single-page markdown link, a self-hosting guide and
  ~20 mirrors — but that is evidence of intent, **not a licence grant**.
- Consequence for this team: reproduce structure, headings and **link lines** (the
  catalogue) with full attribution, and keep non-link prose out of anything
  committed. `build.py --with-prose` exists for private use; do not commit its output.

## Politeness

robots.txt is permissive (`Allow: /`; only `/assets/`, `*.png$`, `*.svg$`, `*.ico$`
disallowed). Content comes over one `git clone --depth 1`, not a crawl. Throttle any
HTTP to ≤1 req/s and send a User-Agent naming the project. Cache the raw snapshot
under `data/raw/` (gitignored) so re-runs cost FMHY nothing.
