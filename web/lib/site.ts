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

export const SITE = {
  name: "CloudPull",
  shortName: "CloudPull",
  url: SITE_URL,
  // ~57 chars, primary keyword first.
  title: "CloudPull: pull any SoundCloud track offline",
  // ~155 chars, with a soft call to action.
  description:
    "Paste a SoundCloud track or set link and download the audio in mp3, m4a, flac, wav or opus, with cover art and tags embedded. Free, no account, open source.",
  tagline: "Pull any SoundCloud track offline, in seconds.",
  keywords: [
    "soundcloud downloader",
    "download soundcloud",
    "soundcloud to mp3",
    "soundcloud mp3 downloader",
    "soundcloud flac",
    "download soundcloud playlist",
    "soundcloud set downloader",
    "soundcloud to wav",
    "free soundcloud downloader",
  ],
  locale: "en_US",
  themeColor: "#ff5500",
} as const;
