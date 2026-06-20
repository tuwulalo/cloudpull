// Single source of truth for site-wide SEO constants.
// Set NEXT_PUBLIC_SITE_URL to your real domain before deploying so that
// canonical URLs, the sitemap, robots.txt and Open Graph images are absolute.

export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"
).replace(/\/$/, "");

// Where the source repo lives. Set NEXT_PUBLIC_REPO_URL when it exists.
export const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL || "";

// Telegram bot link.
export const TELEGRAM_URL =
  process.env.NEXT_PUBLIC_TELEGRAM_URL || "https://t.me/cloudpullbot";

// Last meaningful content change. Surfaced as a visible "Updated" note and as
// `dateModified` in structured data, a freshness signal for Google and AI
// engines. Bump this (YYYY-MM-DD) whenever the page copy materially changes.
export const SITE_UPDATED = "2026-06-20";
export const SITE_PUBLISHED = "2026-06-01";

export const SITE = {
  name: "CloudPull",
  shortName: "CloudPull",
  url: SITE_URL,
  // 51 chars. Primary keyword "SoundCloud Downloader" first, brand last.
  title: "SoundCloud Downloader - MP3, FLAC & WAV | CloudPull",
  // 157 chars. Action verb first, primary + secondary keywords, a concrete
  // number (320 kbps) for AI citability, soft CTA at the end.
  description:
    "Download any SoundCloud track or playlist to MP3, FLAC, WAV, M4A or Opus at up to 320 kbps. Free, no account, cover art and tags embedded. Just paste a link.",
  tagline: "Pull any SoundCloud track offline, in seconds.",
  // Answer-first, definition-pattern sentence reused in the hero and in the
  // structured-data description so the visible text and schema never drift.
  definition:
    "CloudPull is a free, open-source SoundCloud downloader that converts any track or set to MP3, M4A, Opus, FLAC or WAV, with cover art and tags embedded.",
  keywords: [
    "soundcloud downloader",
    "download soundcloud",
    "soundcloud to mp3",
    "soundcloud mp3 downloader",
    "soundcloud to flac",
    "soundcloud flac downloader",
    "download soundcloud playlist",
    "soundcloud set downloader",
    "soundcloud to wav",
    "soundcloud to opus",
    "free soundcloud downloader",
    "soundcloud downloader online",
  ],
  locale: "en_US",
  themeColor: "#ff5500",
} as const;
