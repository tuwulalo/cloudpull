// Builds the JSON-LD structured-data graph for the landing page:
// Organization, WebSite, WebApplication, HowTo and FAQPage. One @graph keeps
// the entities linked by @id, which search and AI engines reward.

import { REPO_URL, SITE, SITE_URL } from "@/lib/site";
import { FAQ, HOW_STEPS } from "@/lib/content";

export function buildJsonLd() {
  const orgId = `${SITE_URL}/#org`;

  const organization = {
    "@type": "Organization",
    "@id": orgId,
    name: SITE.name,
    url: SITE_URL,
    logo: `${SITE_URL}/icon.svg`,
    ...(REPO_URL ? { sameAs: [REPO_URL] } : {}),
  };

  const website = {
    "@type": "WebSite",
    "@id": `${SITE_URL}/#website`,
    url: SITE_URL,
    name: SITE.name,
    description: SITE.description,
    inLanguage: "en",
    publisher: { "@id": orgId },
  };

  const application = {
    "@type": "WebApplication",
    "@id": `${SITE_URL}/#app`,
    name: SITE.name,
    url: SITE_URL,
    description: SITE.description,
    applicationCategory: "MultimediaApplication",
    operatingSystem: "Web, Windows, macOS, Linux",
    browserRequirements: "Requires JavaScript and a local CloudPull backend.",
    isAccessibleForFree: true,
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    featureList: [
      "Download SoundCloud tracks and full sets",
      "Output to mp3, m4a, flac, wav or opus",
      "Embedded cover art and metadata tags",
      "Live download and conversion progress",
      "Runs locally with no account required",
    ],
    publisher: { "@id": orgId },
  };

  const howTo = {
    "@type": "HowTo",
    name: "How to download a track from SoundCloud with CloudPull",
    description:
      "Download any SoundCloud track or set as mp3, m4a, flac, wav or opus in three steps.",
    totalTime: "PT1M",
    step: HOW_STEPS.map((s, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: s.title,
      text: s.body,
    })),
  };

  const faqPage = {
    "@type": "FAQPage",
    "@id": `${SITE_URL}/#faq`,
    mainEntity: FAQ.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };

  return {
    "@context": "https://schema.org",
    "@graph": [organization, website, application, howTo, faqPage],
  };
}
