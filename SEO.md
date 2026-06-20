# CloudPull SEO & GEO guide

This is how search and AI-answer-engine optimization is wired into CloudPull,
what was deliberately left out (and why), and the off-site steps only you can do.
Every decision here follows the SEO skill pack in `seo-skills.zip`
(`_project-seo-docs/seo-checklist.md`, `seo-schema`, `geo-citability`,
`seo-meta-optimizer`, `core-web-vitals`).

The guiding rule from the checklist: **rank in Google AND get cited by AI engines
(ChatGPT, Perplexity, Gemini, Claude, AI Overviews).** Both matter in 2026.

---

## 1. Where everything lives (single source of truth)

SEO content is centralized so the visible page and the structured data can never
drift apart - that drift is the #1 cause of schema penalties.

| File | What it controls |
|---|---|
| `web/lib/site.ts` | Title, meta description, keywords, the reusable "definition" sentence, `SITE_UPDATED` freshness date |
| `web/lib/content.ts` | FAQ Q&A and the "How it works" steps (fed to both the page and JSON-LD) |
| `web/lib/jsonld.ts` | The `@graph` structured-data block (Organization, WebSite, WebApplication, WebPage, BreadcrumbList, FAQPage) |
| `web/app/layout.tsx` | `<head>` metadata: title template, OpenGraph, Twitter, robots, canonical |
| `web/app/robots.ts` | `robots.txt` - which crawlers (incl. AI bots) are allowed |
| `web/app/sitemap.ts` | `sitemap.xml` |
| `web/app/opengraph-image.tsx` | The 1200x630 social share image (auto-generated) |
| `web/app/page.tsx` | The visible landing copy, the answer-first "What is CloudPull" section, the formats table |

---

## 2. What was configured (mapped to the skills)

### On-page metadata (`seo-meta-optimizer`)
- **Title** rewritten keyword-first: `SoundCloud Downloader - MP3, FLAC & WAV | CloudPull`
  (51 chars; primary keyword in the first 21 chars; brand last). The old title
  ("CloudPull: pull any SoundCloud track offline") buried the keyword and never
  used the exact phrase people search for.
- **Meta description** (157 chars): action verb first, primary + secondary
  keywords, a concrete number (320 kbps) for AI citability, soft CTA at the end.
- **Canonical** is self-referencing on every page (`/` and `/privacy`).
- **Keywords** expanded to the real query variants (to flac, to wav, to opus,
  "online", playlist/set downloader).

### Structured data (`seo-schema`, May 2026 status)
- **Removed `HowTo`.** Its Google rich result died in September 2023 - it adds no
  SERP or ranking value, so shipping it was dead weight.
- **Kept `FAQPage`.** Google retired FAQ rich results for all sites on 7 May 2026,
  but the markup still helps AI Mode / AI Overviews extract Q&A and resolve the
  entity. Per the skill, this is an "Info", not a problem - keep it.
- **Enriched `Organization`** with `sameAs` (GitHub + Telegram), a logo
  `ImageObject` (128x128), description and slogan. `sameAs` is the single
  strongest "this is the same entity" signal for both Google's Knowledge Graph
  and LLM entity resolution.
- **Added `WebPage` + `BreadcrumbList`** nodes, linked by `@id`, with
  `datePublished` / `dateModified` (freshness) and a `mentions` link to the
  SoundCloud entity (association).
- All nodes live in one `@graph`, server-rendered into the initial HTML (not
  injected late by JS), which the skill flags as important for reliable parsing.

### GEO / AI citability (`geo-citability`, checklist section 10)
The Princeton/Georgia-Tech/IIT-Delhi research baked into the skill: AI engines
preferentially quote passages that are **self-contained, answer-first,
fact-rich (numbers), and 130-170 words.** Applied:
- New **"What is CloudPull?" section** high on the page (right after the hero, so
  AI extracts it first). It opens with a definition pattern ("CloudPull is a
  free, open-source SoundCloud downloader that...") and uses **question-based H2/H3
  headings** ("How does CloudPull download SoundCloud tracks?", "Which audio
  format should I choose?") with the answer in the first sentence.
- The **hero subhead** now leads with the exact primary keyword + definition, so
  "SoundCloud downloader" appears in the first 100 words and in the LCP region.
- A **stat strip** with concrete numbers (5 formats, 320 kbps, 2 lossless, $0) -
  specific figures are what gets extracted and cited.
- The **formats list is now a real `<table>`** with `<th scope="row">` per format.
  AI engines extract tables with high accuracy, and it's more accessible. The
  visual design is unchanged.

### Crawler access (`geo-crawlers`, checklist section 10)
`robots.txt` explicitly allows every relevant bot - blocking them means zero AI
citations:
- Retrieval/answer bots: OAI-SearchBot, ChatGPT-User, PerplexityBot,
  Perplexity-User, Claude-Web, Claude-User, Applebot, Bingbot.
- Training/index bots: GPTBot, ClaudeBot, Google-Extended, Applebot-Extended,
  CCBot. (Being in the model weights helps brand-entity association.)
- `Sitemap:` and `Host:` are declared.

### Freshness
`SITE_UPDATED` in `web/lib/site.ts` drives both the visible "Updated <month year>"
note in the footer and `dateModified` in the schema. **Bump it whenever you change
page copy** - a real freshness signal, not a fake daily timestamp.

---

## 3. What was deliberately NOT done (and why)

These are conscious calls from your own checklist, not omissions. Generic SEO
advice would tell you to do some of them; the skill pack says don't.

- **No `llms.txt`.** Checklist section 10 is explicit: 0.001% of AI citations
  reference it (study of 94k URLs), Google Search doesn't use it, zero ROI for a
  site like this. It's only worth it for developer documentation aimed at coding
  agents. CloudPull is not that, so adding it would be cargo-cult.
- **No `aggregateRating` / `Review` schema.** The skill forbids self-authored or
  fake reviews (manual-action risk). Add it only if you collect real, crawlable
  reviews.
- **No `HowTo` / `SearchAction` / FAQ-for-SERP.** All three lost their rich
  results; chasing them is wasted effort.
- **Not chasing a Lighthouse 100.** Below the Core Web Vitals thresholds there's
  no further ranking gain. CloudPull already passes: self-hosted fonts with
  `display: swap`, a text hero (so no LCP image to preload), tiny CSS, no
  render-blocking JS.

---

## 4. Deploy these changes to the live site

These are web (Next.js) changes, so the live site must be rebuilt and restarted.
On the VPS:

```powershell
cd C:\cloudpull
git pull
# build + restart all services (this script wipes .next and restarts web)
powershell -ExecutionPolicy Bypass -File .\deploy\update.ps1
```

`update.ps1` already does: stop web, `npm ci`, remove `.next`, `npm run build`,
restart the `cloudpull-web` scheduled task. No Caddy reload is needed for these
changes (no `Caddyfile` change here).

Verify after deploy:
- `https://cloudpull.cloud/robots.txt` lists the AI bots and your real domain.
- `https://cloudpull.cloud/sitemap.xml` lists `/` and `/privacy`.
- View source on the homepage: one `<script type="application/ld+json">`, title
  and canonical use `https://cloudpull.cloud` (not localhost).

---

## 5. Off-site steps only you can do (highest ROI first)

The on-page work is done. Rankings now depend on these, which need your accounts:

1. **Google Search Console** - add the `cloudpull.cloud` property, verify (DNS TXT
   on Spaceship is cleanest, or the HTML-file method), then **submit the sitemap**
   (`https://cloudpull.cloud/sitemap.xml`) and "Request indexing" for the homepage.
   This is the single most important off-site step.
2. **Bing Webmaster Tools** - add the site, submit the same sitemap. Bing also
   feeds ChatGPT and Copilot, so this doubles as AI visibility.
3. **Strengthen `sameAs` / entity signals** - the more owned, crawlable profiles
   that point back to the site, the better Google and LLMs understand the brand.
   Good free ones for a tool like this: a Product Hunt launch, a GitHub repo with
   the homepage URL in the About, an AlternativeTo listing, a few directory
   listings. Each new profile can be added to `sameAs` in `jsonld.ts`.
4. **Backlinks** (`seo-backlinks`) - a Reddit/Hacker-News/Product-Hunt mention,
   a blog post, or a "free SoundCloud downloader" listicle inclusion. Quality over
   quantity; a few relevant links beat dozens of spam ones.
5. **Re-run a citability/audit pass** in a month - point the `geo-citability` or
   `seo-audit` skill at the live URL to find the next round of improvements once
   there's real Search Console data to act on.

---

## 6. Maintenance checklist (when you edit the page)

- [ ] Changed copy? Bump `SITE_UPDATED` in `web/lib/site.ts`.
- [ ] New FAQ? Add it to `web/lib/content.ts` only - the page and FAQPage schema
      both read from there.
- [ ] New page/route? Give it its own `metadata` with a unique title + description
      + `alternates.canonical`, and add it to `web/app/sitemap.ts`.
- [ ] Keep one `<h1>` per page, with the keyword, and question-phrased `<h2>`s.
- [ ] Lead each section with a self-contained, fact-first sentence (AI citability).
- [ ] Validate structured data at https://search.google.com/test/rich-results
      and https://validator.schema.org after schema changes.
- [ ] New owned profile/social account? Add its URL to `sameAs` in `jsonld.ts`.
