---
name: fmhy-skill
description: Find vetted free media sources using the FMHY catalogue. Ships an offline greppable mirror of the FMHY wiki (references/atlas) with per-category source picks, unsafe-site avoidance, and release-quality checks. Source discovery only — no torrent-client operation or transcoding.
trigger: user requests free or pirated media (movies, TV, anime, music, books, manga, comics, audiobooks, games, ROMs, software, apps, courses) or asks where to find/watch/download something.
---

# FMHY Source Discovery

## Overview

**FMHY** ("FreeMediaHeckYeah", `https://fmhy.net/`, mirrors also at `fmhy.net` variants and `r/FREEMEDIAHECKYEAH`) is a community-maintained, curated link catalogue of free and grey-area sources for media, software, learning, and tools. It is an **index, not a host** — it hosts no files, and every entry links out to a third-party site. Its value is that entries are *vetted and labelled*: FMHY marks trusted picks with `⭐`, notes popup/redirect ad behaviour, tags login/sign-up/invite requirements, and maintains an explicit **Unsafe Sites** page for malware-flagged or untrustworthy operators.

Two ways to consume it, in order of preference:

1. **Offline atlas mirror (default — fast, stable, greppable).** This skill ships a verbatim offline mirror of FMHY's wiki at `references/atlas/`. One file per FMHY page, headings + link lines preserved in source order. Use this first: it is local, needs no network, cannot be rate-limited, and is exactly the page structure an agent needs to navigate. Prefer it whenever the question is "which sources exist for X".
2. **Live `https://fmhy.net/<slug>` (fallback for freshness).** Browse the live site only when the atlas is stale (check `references/atlas/manifest.json` → `generated_at` / `sources.upstream_commit`), when you need a specific site's current status, or when the user asks what's on FMHY *right now*. Live pages carry ads/popups — a full adblocker is required to read them comfortably.

**Working rule: consult the matching atlas page before proposing any source.** Do not invent source recommendations from memory; FMHY's catalogue is the ground truth for this skill, and stale memory of "the site that used to work" is the most common failure mode.

## Using the atlas mirror

Layout:

```
references/atlas/
  README.md                 what the mirror is, source selection, licence/attribution notes
  manifest.json             per-page records + taxonomy + build provenance (generated_at, upstream_commit)
  links.jsonl               one JSON record per link occurrence — cheapest thing to grep
  build.py                  re-runnable ingestion entry point (see "Refreshing the atlas")
  references/
    wiki/        13 pages — the main catalogue (video, audio, gaming, reading, …)
    tools/        9 pages — developer/file/gaming/image/internet/social/system/text/video tools
    posts/       52 pages — monthly changelogs + announcements
    other/        5 pages — FAQ, backups, contributing, selfhosting, wallpapers
    more/         2 pages — unsafe.md (blocklist), storage.md (misc resources)
    beginners-guide/  1 page — onboarding/setup advice for new users
    site/         4 pages — index, feedback, sandbox, startpage
```

### Navigate a page by section, don't read it whole

Wiki pages are large (the biggest are ~180 KB). Every page starts with YAML frontmatter (`page`, `source_title`, `slug`, `source_class`, `source_url`, `upstream_path`, `upstream_commit`, `captured_at`, `link_count`) then FMHY's own heading tree:

- `# Page title`
- `# ► Top-level section` (e.g. `► Streaming Sites`, `► Download Sites`)
- `## ▷ Subsection` (e.g. `▷ Stream Aggregators`, `▷ Anime Streaming`)

Recommended moves:

```bash
# 1. See a page's section map without reading the body
grep -n '^#' references/atlas/references/wiki/video.md

# 2. Read only the section you need (headings + entries until the next ▼/►)
sed -n '/^## ▷ Anime Downloading/,/^## ▷/p' references/atlas/references/wiki/video.md

# 3. Find which page owns a topic across the whole wiki
grep -rn 'Streaming Sites\|Torrent Sites' references/atlas/references/wiki/*.md | head

# 4. Structured lookups — the cheapest path when you want links, not prose
grep -i '"link_text":"[^"]*Bandcamp' references/atlas/links.jsonl
python3 -c "import json;[print(o['slug'],o['section'],o['subsection'],o['link_text'],o['url']) for o in map(json.loads,open('references/atlas/links.jsonl')) if 'anime' in (o['subsection'] or '').lower()]"
```

Entry-line grammar (worth knowing so you can parse results):

- `⭐` = FMHY's own trusted/notable pick. Prefer these when the user has no other preference.
- `🌐` = a *meta* resource: an index, aggregator, or mega-list (e.g. a piracy index) rather than a single service.
- `↪️` = a cross-reference to another section/page — follow the link rather than treating it as a source.
- Trailing `/`-separated annotations are the vetting notes: `Sign-Up`, `Requires Invite`, `PW: \`x\``, `Use Adblock`, `Use Translator`, `Geoblocked`, `Requires UK VPN`, `Auto-Next`, `4K`, `Sub`/`Dub`, `Low Upload`, `Slow`, mirrors `[2] [3]`, and `[Discord]`/`[Subreddit]`/`[GitHub]` support links.
- Multiple `[2]`, `[3]` after a name are mirror domains for the same service — when one is down or geoblocked, try the next before concluding the source is dead.

## Category playbook

Each section below maps to one atlas page. Read that page's section map first, then pick sources.

### Movies / TV / Anime — `references/wiki/video.md`

Covers: streaming sites (aggregators, P-Stream forks, dedicated-server, multi-server, free-with-ads, video streaming), streaming apps (Android/iOS/Smart TV/Firestick), specialty streaming (anime, cartoons, TV, drama, classics/public-domain, film archives), live TV/sports + IPTV tools and players, download sites (incl. Telegram channels, anime downloading), torrent apps (Stremio tools), torrent sites (incl. anime torrenting), tracking/databases, subtitles, and player/server/sync tools.

Best entry points:

- **Streaming (watch in-browser):** `⭐ Stream Aggregators` for one-stop catalogues; `⭐ Dedicated-Server` subsections are the most consistent and least mislabelled; `P-Stream Forks` are forkable and let you add extra sources via an extension.
- **Anime:** dedicated `▷ Anime Streaming` / `▷ Anime Streaming Apps` / `▷ Anime Downloading` / `▷ Anime Torrenting` subsections; pair with the anime-specific trackers under `▷ Anime Tracking / Databases`.
- **Downloading:** `► Download Sites` (incl. Telegram channels) and `► Torrent Sites`. `▷ Film Archives` and `▷ Classics / Public Domain` are the fully-legal options.
- **Live sport/TV:** `► Live TV / Sports` incl. `▷ Sports Replays` and `▷ IPTV Tools`.

Before using anything here:

- An adblocker (full version of a mainstream content blocker) is **mandatory** — most streaming sites run popups/redirects, and some hide the toggle in settings. FMHY publishes per-site popup/redirect grading; check it rather than guessing.
- Aggregator streams vary in quality and can be mislabelled. For consistency, prefer dedicated-server sites and then verify the stream actually resolves to the title/episode requested.
- Live/IPTV sites behave worst without a VPN; use a throwaway email or alias when a sign-up is required.
- **Release-name quality check — do this before downloading video.** Read the release name as a set of claims and confirm each one:
  - *Source tier, best→worst for a re-encode:* `BluRay`/`REMUX` > `WEB-DL` > `WEBRip` > `HDTV` > `DVDRip` > cam/`HDTS`. Prefer WEB-DL/BluRay for modern content; DVDRip only when the request explicitly wants it (rare older TV rips are DVD-only).
  - *Resolution/codec:* `2160p`/`4K`, `1080p`, `720p`; `x265`/`HEVC`/`AV1` = smaller but needs decode support, `x264`/`H.264` = widest compatibility. Flag HEVC/AV1 to the user if their target device/app may not handle it.
  - *Audio:* `5.1`/`Atmos`/`DTS-HD` vs plain stereo; `DUAL`/`MULTI` means multiple audio tracks.
  - *Subtitles:* bare `SUB`/`MULTISUB` = soft subtitle tracks (good). **`SWESUB`, `NLSUB`, `FREESUB`, `PLSUB` etc. mean hardcoded/burned-in subtitles in that language** — always flag this, since burned subs are baked into the frames and unusable for clean clips/GIFs.
  - *Trust signals:* known scene/P2P groups, `REPACK`/`PROPER` (fixes to a previous bad release), `COMPLETE`/season packs for TV. Watch for `Sample/`, `.nfo`, and fake "download" buttons.
  - *Suspicious:* names with padded keywords, absurd size for the resolution, or a mismatch between claimed and actual runtime — verify with a media probe before trusting.
  - Torrent downloads normally arrive as a **directory** containing the video plus extras; search *inside* it for the actual `.mkv`/`.mp4` and exclude sampler files.

### Music / Podcasts / Radio — `references/wiki/audio.md`

Covers: audio streaming (apps, sites, genre-specific, YouTube-Music tools), specialty streaming (concerts/live shows, podcasts, ambient/relaxation), internet radio (directories, genre, lofi), Spotify tools + playlist tools, audio ripping (sites, tools, Telegram bots, download sites, genre-specific), audio torrenting, royalty-free music, soundtracks (incl. game OSTs), tracking/discovery databases (Last.fm tools), players/servers/metadata/album art/song ID/lyrics/karaoke/sheet music/spectrum analyzers, audio editing (editors, browser synths, plugins, SFX/samples), and platform-specific audio sections.

Best entry points:

- **Streaming:** YouTube-Music front-ends/clients are the workhorse; lossless browser players and user-uploaded platforms (SoundCloud-style, with privacy front-ends) for anything not on the big services. Unreleased material often lives in dedicated community trackers.
- **Concert recordings:** dedicated live-music torrent trackers and bootleg archives — legal grey area but long-established and well-seeded.
- **Radio:** large free radio directories; a few big broadcasters are **UK-VPN-gated** and have their own downloaders. Hi-fi/lofi stations are free and unlimited.
- **Ripping:** dedicated ripping sites/tools + Telegram bots; use redirect-bypassers for link shorteners.
- **Ambient/study:** free customisable noise mixers and rain/drone stations.

Before using anything here: get a VPN before torrenting and bind it to the client where supported; ripping sites are ad-heavy, so pair with an adblocker and a redirect bypasser.

### Books / Comics / Manga / Audiobooks — `references/wiki/reading.md`

Covers: ebooks (public domain, PDF search, Calibre libraries, ebook readers, browser readers, e-reader/Kindle tools), special interest (light novels, fanfiction, newspapers), audiobooks (download/stream/tools), visual media (comics, manga, magazines), educational books (textbooks, STEM, history, poetry, programming, academic papers, manuals), documents/articles (incl. declassified documents), esoteric/cultural texts, book/comic/manga tracking databases, curated recommendation lists, and reader apps.

Best entry points:

- **Books:** the shadow-library search engines (Anna's Archive, Library Genesis, Z-Library) lead the page and have many mirror domains — if one is blocked, move to the next mirror rather than declaring failure. Dedicated ebook forums cover audiobooks/magazines/newspapers/comics in one place. A private book tracker exists but is **invite-only**.
- **Public domain:** Project Gutenberg and national Gutenberg branches, plus open-access lending platforms — fully legal, no VPN, best default when the title qualifies.
- **Audiobooks:** forum + tracker sources; streaming via the same platforms.
- **Comics/Manga:** dedicated comic/manga sites with their own trackers; light novels have a separate subsection.
- **Textbooks/papers:** the `Educational Books` subsections (textbooks, academic papers) are the correct target rather than the general ebook section.
- **Readers:** cross-platform readers (KOReader, Koodo, Readest, SumatraPDF) and Kindle-specific tooling (converter, downloader, app installer) for device workflows.

Before using anything here: check the *mirror list* on each shadow-library entry — the canonical domain rotates; several "mirrors" circulating elsewhere are phishing clones. E-reader-specific tools assume a specific device (Kindle/Kobo); confirm the user's device before recommending.

### Gaming / Emulation — `references/wiki/gaming.md`

Covers: game downloads (repacks, pre-installed, GOG-only, multiplayer/online-fix, and per-OS Linux/Mac sections), special interest (VR, indie, abandonware/retro, decompilations/ports, remakes, revival projects), emulation/ROMs (emulators, ROM resources, ROM sites, Nintendo/PlayStation ROMs, browser emulators), puzzle games, tabletop (chess, cards, D&D), browser games (dozens of subgenres), and gaming tools.

Best entry points:

- **PC game downloads:** `⭐` repack/piracy-index entries lead the page. Aggregated mega-indexes (subreddit/forum megathreads) are the right first stop for "where do I get X", then the per-site star entries. Repack sites with a strong reputation are the safest single-site option. GOG-only mirrors exist for DRM-free classics. Multiplayer-capable releases live in a separate "online fix" subsection.
- **Abandonware/retro:** several long-running abandonware archives; ideal for out-of-print titles with no legitimate vendor.
- **ROMs:** `Emulation / ROMs` — emulator projects first, then ROM resources organised by console family (Nintendo, PlayStation) plus in-browser retro emulators for zero-install play.
- **Indie:** itch.io (free/featured) plus its downloader tools.

Before using anything here — **this category has the highest malware risk on FMHY**:

- File hosts increasingly serve **fake download buttons that redirect to malicious pages**. A content blocker helps but is not sufficient. FMHY's rule: *real downloads happen on the same page as the file host; avoid download pages that open a new tab or redirect you.* There is a linked guide showing what the fake pages look like — read it if the user is new to this.
- **Never take games or software from a general torrent site/aggregator** unless the uploader is a highly trusted, named group. Use the dedicated game sections instead.
- Check the Unsafe list before using any game site the user names from elsewhere (see *Source vetting* below) — fake clones of popular repack sites are a recurring problem, and several formerly-popular sites are explicitly flagged for malware, click-hijack ads, or doxxing.
- Repacks are self-extracting installers: run them in a sandboxed/VM environment if the user is cautious, and scan with an online multi-engine scanner first.

### Software / Apps — `references/wiki/downloading.md`

Covers: software sites (FOSS sites, freeware sites, per-OS Linux/Mac software sections), download directories (open directories), download sites (multi-site search engines, plus cross-links to video/anime/educational/game/audio), Usenet (indexers, providers, downloaders), debrid/leech services, IRC tools, and download managers.

Best entry points:

- **Multi-site search engines** (Virgil-style software search, CSEs) first — they search across the vetted sites, which avoids picking a single untrusted vendor.
- **FOSS:** official project repos, FOSS-specific sites, plus "is it really FOSS" checkers to verify a claim of open source.
- **Windows freeware:** established repack/portal sites with published download guides; several are non-English and require a translator.
- **Forums:** two long-running software forums require sign-up and use rank systems to signal trusted uploaders — check the linked rank notes before downloading from an unfamiliar poster.
- **Store-front alternatives:** tools for fetching Microsoft Store apps, and open-directory crawlers for public file servers.
- **Soulseek/Nicotine+** for peer-to-peer file sharing (useful for rare music/ebooks).
- **Usenet:** guide + automation stack (indexer + provider + client), plus browser extensions to push NZBs to the client. Paid; a debrid service (paid, sign-up) covers torrent/usenet fetching without local seeding.
- **Open directories:** some track IPs — **always use a VPN or Tor**.

Before using anything here:

- **Scan every downloaded binary with an online multi-engine malware scanner before installing, and prefer a sandboxed/triage environment for first run.** Fake download buttons on file hosts are pervasive; install a full content blocker.
- **Never use general DDL/aggregator sites for software or games** — they mix sources with unpredictable provenance. Use the dedicated per-category sections.
- Avoid entries whose name implies a downloader/installer wrapping a known app — "apps with fake names are generally not worth using".

### AI Tools — `references/wiki/ai.md`

Covers: AI chatbots (official model sites, multi-model sites, specialised chatbots, local frontends, self-hosting tools, roleplay chatbots), AI coding tools (cross-linked), video generation, image generation (+ local frontends, guides, restoration/upscaling), audio generation (TTS, voice change/clone, voice removal/separation), AI agents, AI tools, prompt libraries, AI indexes, and benchmarks (general, specialised, coding).

Best entry points:

- **Chat:** official free tiers of the major labs lead the page; multi-model aggregators give access to several frontier models in one place with daily caps; specialised chatbots exist for document Q&A/note-taking, research search, and text transforms.
- **Local/self-hosted:** a full stack of desktop apps and web UIs (LM Studio, Jan, Open WebUI, text-generation UIs), the canonical local inference engine, its GUI+API wrapper, and fine-tuning tooling. Use these when the user wants privacy, offline operation, or no rate limits.
- **Roleplay/character chat:** dedicated front-ends plus zero-sign-up web options.
- **Image/video/audio generation:** hosted generators plus local diffusion front-ends; separate subsections for TTS, voice cloning, and stem/voice separation.
- **Benchmarks:** use the benchmark sections when the user wants to compare models rather than just pick one.

Before using anything here: almost every hosted chatbot in this section is **sign-up gated** (a lot of entries carry `Sign-Up`) — tell the user up front. Free tiers have rate/daily limits that FMHY often documents inline; check the entry's annotations (`Unlimited`, `Up To N Daily`, `Traffic-Based`) before promising capacity. Local front-ends require adequate hardware — check the model size/quantisation against the user's machine before recommending a local route.

### Education / Courses / Research — `references/wiki/educational.md`

Covers: documentaries, courses (streaming/downloading), learning sites, virtual tours, science & math (physics/math/engineering/chemistry/periodic tables/biology/med school), space (astronomy/spacecraft), aerospace (rocketry/drones/simulators), history (tech/military/mythology), humanities (world data, geography, flags, economics, philosophy), skills & hobbies (music, art, chess, Go, D&D, LEGO), language learning (15+ languages incl. sign and constructed languages), developer learning (tutorials, languages, web dev, CS, data science, UI/UX, cybersecurity, game dev, AI/ML), exam prep (SAT, JEE/NEET), and educational tooling (study/research, flashcards, calculators, dictionaries, encyclopedias, Wikipedia tools).

Best entry points:

- **Courses:** the big open-courseware providers (MIT OCW, edX, Khan Academy) plus course-search engines that index many platforms; a course-download community exists behind Telegram. Use redirect bypassers on the download routes.
- **Documentaries:** several free documentary streamers; watermarks can be removed with community filter lists or hidden via picture-in-picture.
- **Reference/learning:** interactive simulations (PhET-style), explainer communities, and subject-specific reference sites per subsection — these are the highest-signal picks and are almost all free and legal.
- **Developer learning:** this is a large, well-covered block — route coding questions here rather than to the software page.
- **Language learning:** per-language subsections with the standard free platforms plus exchange partners.

Before using anything here: this page is overwhelmingly **legal/free** — don't route a request for a textbook or course to the piracy sections without checking whether an open-access version is listed here first. Language-specific resources sometimes assume a script/RTL support or a specific keyboard tool.

### Linux / macOS — `references/wiki/linux-macos.md`

Covers: Linux guides (incl. CLI cheat sheets), communities, distros, Linux apps (software sites, system, video, audio, image, productivity/calendars, gaming), Linux tools (adblock/privacy, internet, server/self-hosting, file tools, Android-on-Linux, terminal/shell, Raspberry Pi), customisation (desktop environments, window managers, themes), macOS apps (software sites, video/audio/image/gaming), macOS tools (adblock/privacy, internet, system, file tools), and Unix-like systems.

Best entry points:

- **Windows apps on Linux:** the Wine ecosystem (compatibility database, GUIs, container managers, fix scripts) is the core block — start at the compatibility database when a user asks "will this Windows app run on Linux".
- **Guides:** the Arch wiki is the canonical Linux guide regardless of distro; a searchable command index for one-liners.
- **Distros:** FMHY does **not** curate individual distros — it lists chooser tools and indexes. Consult each distro's own docs (or DistroWatch) for install guides.
- **Per-OS app blocks:** Linux and Mac sections mirror the video/audio/image/gaming categories with platform-native picks — use these instead of the Windows/flatpak-agnostic entries.
- **System/self-hosting:** terminal tools, resource monitors, snapshot/backup tools, remote desktop, and server/self-host sections.

Before using anything here: some software sources are non-English and need a translator; note `Kapital Sin`-style forum sources require sign-up. Verify architecture (ARM vs x86_64) and package format (AppImage vs deb vs flatpak) before recommending an install route.

### Android / iOS — `references/wiki/mobile.md`

Covers: Android APKs (modded, Telegram channels, FOSS, untouched, launchers, APK tools, ReVanced/Morphe patchers, social apps, Telegram clients), Android device (optimisation, customisation, battery, keyboards, screen, SIM/SMS, root/flash, root managers, alternative OSes), camera (image tools/galleries), Android tools (utilities, adblocking, privacy, browsers, RSS, file/text/notes/to-do/notifications/date-time/productivity/maps/weather), emulators (on Android, Android-on-Windows, Linux-on-Android), Android torrenting, reading (incl. manga), audio (players, YouTube-Music clients, podcasts/radio, relaxation), streaming (video players, anime, live TV, YouTube apps), iOS tools (jailbreaking, sideloading, adblocking, privacy), iOS iPAs (Telegram channels, social apps), iOS audio, iOS streaming (anime, YouTube apps), and iOS reading.

Best entry points:

- **Modded APKs:** established modding forums/portals and Telegram channels; a couple of major ones require sign-up and translation. Signing/installing modded APKs has pitfalls — the section notes split/bundled format merging (APKM/APKX → APK) and patcher tooling (Lucky Patcher-class tools with compatibility guides).
- **FOSS apps:** FOSS-declared stores and simple-app collections; the FOSS app installer (Droid-ify-class) is the cleanest route.
- **Untouched APKs:** APK mirror sites and store-front alternatives; a Google-Play alternative client exists (with its own risk warnings — read them).
- **ReVanced/Morphe:** official patcher sites only; **fake ReVanced sites are an explicit malware vector** (see Unsafe list). Never fetch a patched APK from a search result.
- **Launchers/root/ROMs:** launcher subsections, root/flash tools, root managers, and alternative Android OSes.
- **iOS:** jailbreaking and sideloading tools; iOS IPA sources are mostly Telegram channels. Expect Apple-side friction (sideload limits, certificate revocation).

Before using anything here: sideloaded/modded apps carry real risk — check the Unsafe list for the app and the source; note that some listed messaging clients have been caught logging phone numbers or tokens. APK tools and modding assume the user knows their device architecture (arm64 vs armeabi) and Android version.

### Adblocking / Privacy / VPN — `references/wiki/privacy.md`

Covers: adblocking (filters, DNS adblocking, DNS filter lists, per-platform sections), antivirus/anti-malware (file scanners, site legitimacy checks), privacy/security (privacy guide indexes, network security, per-platform), web privacy (browser privacy, passwords/2FA, encrypted messengers, email privacy, data-breach monitoring, fingerprinting/tracking, search engines), VPN (servers, tools), and proxy (servers, clients, anti-censorship, proxy sites).

Best entry points:

- **Adblocking:** a mainstream content blocker (full version of the primary extension, or the MV3 lite variant where required) + SponsorBlock for in-video sponsor segments. **Do not run two general adblockers at once** — it causes breakage; combining an adblocker with SponsorBlock is fine.
- **DNS-level blocking:** self-hosted DNS blockers (Pi-hole, AdGuard Home) + aggregated blocklists; the recommended modern blocklist collections are named on the page.
- **Site-trust checks:** the FMHY SafeGuard extension (flags trusted/untrusted sites in-browser) and the FMHY filterlist for adblockers — plus URL scanners (VirusTotal, URLVoid, URLScan, site-safety raters) and online sandboxes for files.
- **VPN:** use a paid VPN for privacy/speed; free VPNs are mostly only good for unblocking regions. **Bind the VPN to the torrent client** to avoid ISP notices. Note that some VPN brands share ownership with adware distributors (flagged in the Unsafe list).
- **Browser privacy:** privacy-hardened browsers, 2FA/password managers, encrypted messengers, breach monitoring, anti-fingerprinting, privacy-respecting search engines.

Before using anything here: keep OS-level real-time protection on; for pirated patches, use "Allow on device" or targeted exclusions rather than disabling protection wholesale. This page is also the right destination when a user asks "is this download safe" — go to the scanners, don't guess.

### Non-English Sources — `references/wiki/non-english.md`

Covers: a per-language catalogue — Arabic, Bangla, Bulgarian, Chinese, Czech, Filipino, Finnish, French, German, Greek, Hebrew, Hungarian, Indian languages, Indonesian, Italian, Japanese, Korean, Persian, Polish (and further languages continuing down the page). Each language typically has `Downloading`, `Torrenting`, `Streaming`, and `Reading` subsections; Chinese additionally has `Great Firewall`, `Light Novels`, and `Manga`.

Best entry points:

- Use this page only when the request is explicitly **language- or region-specific** — for English/any-language media, the main English sections are better vetted and more current.
- Per-language streaming/download sites are often the only route to **hard-subbed or dubbed** releases in that language, and often the only listings for regional cinema that never appears in English-language catalogues.
- Typing/input tools appear here for non-Latin scripts (e.g. keyboard tools for Bangla, romanisation helper).

Before using anything here:

- **Use this section for media only** (movies, music, books). For installing software, games, or APKs, prefer the English sections unless the source is a highly trusted named uploader. This is FMHY's own rule and applies especially to the non-English software mirrors.
- Many entries are **geoblocked** — a VPN in the right country is often required, and some are only reachable from within the region.
- Several entries require sign-up, are non-English-UI (use a translator), or need a redirect bypasser for download links.
- **Great Firewall caveat:** many "GFW-bypass" VPNs are operated by state-linked agencies to collect user data — avoid generic ones and stick to the VPNs listed in the privacy page.
- Regional ISP blocking is common (e.g. Brazil, parts of the EU) — if a listed site won't load, try a VPN before concluding it's dead.

### Unsafe Sites — `references/more/unsafe.md`

The explicit blocklist. Read it *before* recommending a site the user names from a search result, a chat message, or their own memory. Structure:

- **Game sites:** a longer "untrusted sites / untrusted uploaders" community list, a fake-clone tracker for popular repack brands, and named sites flagged for malware, click-hijack ads, adware installers, or demotion on major trackers for malware.
- **Software/app sites:** a very long list of named vendors "caught with malware" (with VirusTotal/Triage evidence links), plus fake patcher-site trackers for the big YouTube/Spotify patching projects.
- **Torrent sites/clients:** a named site caught with malware, a long-standing client considered adware, a client associated with adware, and fake mirrors of a major tracker.
- **Software/apps (behavioural flags):** antivirus vendors that sell user data or are outright scams, a security suite with constant upsell popups, a chat mod with a spam/spying history, a messaging app with a predator/scammer ecosystem, an app that remotely enables a monetisation service, a launcher with shady practices, a shader mod that can trigger unwanted reboots, and messaging clients caught logging phone numbers or auth tokens.
- **Fake-site trackers:** fake shadow-library sites (Z-Lib and Anna's Archive clones), and fake Windows activators.

How to apply it:

1. `grep -i '<site-or-brand>' references/atlas/references/more/unsafe.md` before use.
2. If flagged → do not use it, say why, and offer the FMHY-list alternative instead. Malware flags include evidence links; cite the reason rather than a vague "it's unsafe".
3. If the user is already using a flagged site, tell them plainly and recommend a scanner pass over anything already downloaded.
4. Use the SafeGuard extension or the FMHY filterlist as an ongoing guard rather than relying on manual checks.
5. Fake-clone awareness: **always navigate to the domain listed in the atlas**, never to a similar-looking domain from a search engine. Clone sites are the single most common attack vector in this space.

## Source vetting checklist

Run this before handing a user a link:

1. **Is it on an FMHY list?** If the source came from somewhere else (search engine, social post, forum), find it in the atlas first. Not listed ≠ unsafe, but unlisted means unvetted — say so.
2. **Is it on the unsafe list?** (`references/more/unsafe.md`) If yes, stop and offer the vetted alternative.
3. **Is it a `⭐` entry?** Prefer those; they're FMHY's own picks.
4. **Are the gating conditions acceptable?** `Sign-Up` / `Requires Invite` / `Requires Sign-Up`, `Geoblocked`, `Requires UK VPN`, `PW: \`x\``, `Use Translator`, `Use Adblock`, `Slow` / `Low Upload`. Surface these to the user before they commit.
5. **Mirrors:** for shadow libraries and shadow-streaming sites, the canonical domain rotates and clones are common — use the atlas-listed mirrors and move to the next when one fails.
6. **Counterfeit check:** for software/games/APKs, verify you're on the official project domain; fake patcher and fake repack sites are a documented, ongoing problem.
7. **Scan before running:** binaries → online multi-engine scanner + sandbox/triage; archives → scan before extraction; and for pirated packages expect antivirus false positives on patches (use targeted exclusions, don't disable protection globally).
8. **Network hygiene:** use a VPN for torrents and open directories (binding it to the client where supported), and a throwaway email/alias for sign-ups.
9. **For video, run the release-name quality check** (above) so the user knows exactly what tier, codec, audio and subtitle situation they're getting.
10. **Be honest when sources are dead.** After a few failed attempts across the listed mirrors, say the specific source type appears unavailable and offer alternatives (different source tier, a legitimate/free option, physical media, or asking in the community). Don't keep re-searching the same dead swarms.

## Refreshing the atlas

The mirror is a snapshot, not a live feed. Check staleness with `manifest.json` (`generated_at`, `sources.upstream_commit`) and refresh when it matters:

```bash
cd references/atlas
python3 build.py                # rebuild; refetch upstream only if cache older than 24h
python3 build.py --refresh      # force refetch of the upstream snapshot
python3 build.py --offline      # rebuild from cache only, fail if no cache
python3 build.py --ttl 0        # treat any cache as stale
python3 build.py --with-prose   # also emit non-link prose (heavier; see licence note)
python3 build.py --verify-single-page   # cross-check against FMHY's single-page mirror
```

Requirements: Python 3.10+ and `git`, no third-party packages. `references/`, `manifest.json` and `links.jsonl` are rewritten from scratch, idempotently. Raw snapshots cache under `data/raw/` (gitignored) — a second run in a row makes **zero** network requests. `build.py` fetches FMHY's content over a single shallow `git clone` of the upstream wiki repo plus `robots.txt`/`sitemap.xml` over HTTP, throttled to ≤1 request/second, and **never** requests any third-party site FMHY links to. Keep it that way: don't point this skill at the linked sites in bulk.

## Related atlas pages

- `references/tools/` — nine pages (`developer-tools`, `file-tools`, `gaming-tools`, `image-tools`, `internet-tools`, `social-media-tools`, `system-tools`, `text-tools`, `video-tools`). Use these for *tooling* questions (converters, download managers, redirect bypassers, players, editors) that the media pages cross-link out to.
- `references/posts/` — 52 monthly changelog/announcement posts plus one-off notices. Read these to answer "what changed / what died recently" and to judge whether an atlas entry may already be stale.
- `references/other/` — FAQ, backups, contributing, selfhosting, wallpapers. The FAQ is the right source for "what is FMHY / is this allowed" questions; `backups.md` documents FMHY's own full-wiki backups and mirror list.
- `references/beginners-guide/` — onboarding and setup advice (adblocking first, then safe habits). Point users who are new to this space here rather than walking them through it ad hoc.
- `references/more/storage.md` — miscellaneous resource lists, mirror/backup catalogs, and archive tooling.
- `references/site/` — `index`, `feedback`, `sandbox`, `startpage`. Index pages are the only sensible cross-category entry when a request doesn't map to a single page.

## Out of scope

This skill is **source discovery + vetting guidance**. It does not operate torrent clients, manage downloads, or cover file post-processing (transcoding, remuxing, clipping, tagging). Route those to the appropriate tooling section of the atlas (`references/tools/video-tools.md`, `file-tools.md`) or the user's own media pipeline. FMHY hosts no files — never imply otherwise, and always attribute the catalogue to FMHY (`https://fmhy.net/`) when presenting its picks.
