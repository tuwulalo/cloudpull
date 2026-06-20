// Builds the JSON-LD structured-data graph for the landing page. A single
// @graph keeps the entities linked by @id, which Google and AI answer engines
// reward. Schema choices follow the seo-schema skill (May 2026 status):
//   - Organization + WebSite + WebApplication + WebPage + BreadcrumbList: active.
//   - FAQPage: no SERP rich result since 7 May 2026, but KEPT because it still
//     aids AI Mode / AI Overview entity resolution and Q&A extraction.
//   - HowTo: removed. Its rich result died in Sept 2023 and it adds no SERP or
//     ranking value, so we do not ship dead markup.

import { REPO_URL, SITE, SITE_URL, SITE_PUBLISHED, SITE_UPDATED, TELEGRAM_URL } from "@/lib/site";
import { FAQ } from "@/lib/content";

export function buildJsonLd() {
  const orgId = `${SITE_URL}/#org`;
  const websiteId = `${SITE_URL}/#website`;
  const appId = `${SITE_URL}/#app`;
  const webpageId = `${SITE_URL}/#webpage`;
  const ogImage = `${SITE_URL}/opengraph-image`;

  // sameAs is the strongest "this is the same entity" signal for both Google's
  // Knowledge Graph and LLM entity resolution. List every owned profile.
  const sameAs = [REPO_URL, TELEGRAM_URL].filter(Boolean);

  const organization = {
    "@type": "Organization",
    "@id": orgId,
    name: SITE.name,
    url: SITE_URL,
    description: SITE.definition,
    slogan: SITE.tagline,
    logo: {
      "@type": "ImageObject",
      url: `${SITE_URL}/icon.png`,
      width: 128,
      height: 128,
    },
    ...(sameAs.length ? { sameAs } : {}),
  };

  const website = {
    "@type": "WebSite",
    "@id": websiteId,
    url: SITE_URL,
    name: SITE.name,
    description: SITE.description,
    inLanguage: "en",
    publisher: { "@id": orgId },
  };

  const application = {
    "@type": "WebApplication",
    "@id": appId,
    name: SITE.name,
    url: SITE_URL,
    description: SITE.definition,
    applicationCategory: "MultimediaApplication",
    operatingSystem: "Web, Windows, macOS, Linux, Android, iOS",
    browserRequirements: "Requires a modern browser. No install, no account.",
    inLanguage: "en",
    datePublished: SITE_PUBLISHED,
    dateModified: SITE_UPDATED,
    isAccessibleForFree: true,
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    featureList: [
      "Download SoundCloud tracks and full sets or playlists",
      "Output to mp3 (up to 320 kbps), m4a, opus, flac or wav",
      "Embedded cover art and metadata tags",
      "Live download and conversion progress",
      "No account, no upload to a third party",
    ],
    publisher: { "@id": orgId },
  };

  const breadcrumb = {
    "@type": "BreadcrumbList",
    "@id": `${SITE_URL}/#breadcrumb`,
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: SITE_URL,
      },
    ],
  };

  const webpage = {
    "@type": "WebPage",
    "@id": webpageId,
    url: SITE_URL,
    name: SITE.title,
    description: SITE.description,
    inLanguage: "en",
    isPartOf: { "@id": websiteId },
    about: { "@id": appId },
    primaryImageOfPage: ogImage,
    datePublished: SITE_PUBLISHED,
    dateModified: SITE_UPDATED,
    breadcrumb: { "@id": `${SITE_URL}/#breadcrumb` },
    // Helps engines associate this page with the SoundCloud entity it serves.
    mentions: [
      {
        "@type": "WebSite",
        name: "SoundCloud",
        url: "https://soundcloud.com",
      },
    ],
  };

  const faqPage = {
    "@type": "FAQPage",
    "@id": `${SITE_URL}/#faq`,
    inLanguage: "en",
    isPartOf: { "@id": websiteId },
    mainEntity: FAQ.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };

  return {
    "@context": "https://schema.org",
    "@graph": [organization, website, application, breadcrumb, webpage, faqPage],
  };
}
