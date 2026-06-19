// Landing copy that is also fed into structured data (HowTo + FAQPage),
// kept in one place so the visible text and the schema never drift apart.

export const HOW_STEPS = [
  {
    n: "01",
    title: "Paste a link",
    body: "Drop in a single track or a whole set. CloudPull reads the title, artist, artwork and full tracklist.",
  },
  {
    n: "02",
    title: "Pick format & quality",
    body: "mp3 up to 320 kbps, or go lossless with FLAC and WAV. Cover art and tags are embedded automatically.",
  },
  {
    n: "03",
    title: "Download",
    body: "Watch live progress as it converts. A single track lands as one file; a set arrives as a tidy zip.",
  },
];

// Question-phrased, concise (40-60 word) answers: good for featured snippets,
// voice search and AI answer engines (AEO), and for FAQPage structured data.
export const FAQ = [
  {
    q: "Is CloudPull free?",
    a: "Yes. CloudPull is completely free and open source. There is no paywall, no subscription and no account to create. It runs locally on your own machine, so there are no usage limits, watermarks or hidden costs.",
  },
  {
    q: "Which audio formats does CloudPull support?",
    a: "CloudPull downloads SoundCloud audio as mp3 (up to 320 kbps), m4a, opus, and lossless FLAC or WAV. Choose mp3 for small, universal files, or FLAC and WAV when you want bit-perfect, lossless quality for good speakers.",
  },
  {
    q: "Can I download a whole SoundCloud set or playlist?",
    a: "Yes. Paste a set or playlist link and CloudPull fetches every track, converts each one to your chosen format, and packs them into a single zip file. A single track simply downloads as one audio file.",
  },
  {
    q: "Do I need a SoundCloud account?",
    a: "No. CloudPull needs no SoundCloud account, login or API key. Just paste a public track or set link, pick a format, and download. Nothing is uploaded to a third-party service in the process.",
  },
  {
    q: "Does CloudPull keep cover art and tags?",
    a: "Yes. CloudPull embeds the cover artwork, title and artist into every downloaded file automatically, so your music library stays clean and organised without any manual tagging afterwards.",
  },
  {
    q: "Where are the downloaded files saved?",
    a: "Files are saved straight to your device through your browser's normal download flow. CloudPull runs locally with ffmpeg, so the audio never leaves your computer or passes through an external server.",
  },
];
