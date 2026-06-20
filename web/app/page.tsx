import type { CSSProperties, ReactNode } from "react";
import CloudLogo from "@/components/CloudLogo";
import AnchorScroll from "@/components/landing/AnchorScroll";
import HeroInteractive from "@/components/landing/HeroInteractive";
import SiteFooter from "@/components/SiteFooter";
import { FAQ, HOW_STEPS } from "@/lib/content";
import { buildJsonLd } from "@/lib/jsonld";
import { REPO_URL, TELEGRAM_URL } from "@/lib/site";

const SPACE = "var(--font-space-grotesk)";

const repoHref = REPO_URL || "#";
const repoProps = REPO_URL
  ? { target: "_blank", rel: "noopener noreferrer" }
  : {};

const container: CSSProperties = {
  maxWidth: 1140,
  margin: "0 auto",
  padding: "0 28px",
};

const eyebrow = (color: string): CSSProperties => ({
  fontSize: 12.5,
  fontWeight: 700,
  letterSpacing: ".14em",
  textTransform: "uppercase",
  color,
  marginBottom: 14,
});

const featureStroke = {
  fill: "none",
  stroke: "#ff7a3c",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const features: { icon: ReactNode; title: string; body: string }[] = [
  {
    icon: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M9 17v-5l3-1v5" />
        <circle cx="8" cy="17" r="1.4" />
        <circle cx="11" cy="16" r="1.4" />
      </>
    ),
    title: "Five formats",
    body: "mp3, m4a, flac, wav and opus. Pick the right trade-off between size and fidelity.",
  },
  {
    icon: <path d="m12 3 9 5-9 5-9-5 9-5Z M3 12l9 5 9-5 M3 17l9 5 9-5" />,
    title: "Whole sets & playlists",
    body: "Hand it a set and get every track, packed into a single zip in one go.",
  },
  {
    icon: (
      <>
        <path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0l-7-7A2 2 0 0 1 3 12.2V5a2 2 0 0 1 2-2h7.2a2 2 0 0 1 1.4.6l7 7a2 2 0 0 1 0 2.8Z" />
        <circle cx="7.5" cy="7.5" r="1.3" />
      </>
    ),
    title: "Cover art + tags",
    body: "Artwork, title and artist are embedded so your library stays clean and organised.",
  },
  {
    icon: <path d="M13 2 3 14h8l-1 8 10-12h-8l1-8Z" />,
    title: "Live progress",
    body: "Real-time download and conversion progress streamed straight to the page, no guessing.",
  },
  {
    icon: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    title: "Runs on your machine",
    body: "No account, no upload to a third party. The files never leave your computer.",
  },
  {
    icon: (
      <>
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </>
    ),
    title: "Open source core",
    body: "A shared core that already powers a web app, with a Telegram bot next. Inspect it, run it, fork it.",
  },
];

const formatRows = [
  { name: "mp3", desc: "Universal. Up to 320 kbps.", lossless: false },
  { name: "m4a", desc: "AAC. Efficient, Apple-friendly.", lossless: false },
  { name: "opus", desc: "Best quality per kilobyte.", lossless: false },
  { name: "flac", desc: "Lossless, compressed.", lossless: true },
  { name: "wav", desc: "Lossless, uncompressed.", lossless: true },
];

// Concrete numbers near the top of the page. Specific, verifiable figures are
// what AI answer engines extract and cite (geo-citability skill).
const stats = [
  { value: "5", label: "Audio formats" },
  { value: "320 kbps", label: "Top MP3 bitrate" },
  { value: "2", label: "Lossless options" },
  { value: "$0", label: "Cost, no account" },
];

// Visually hidden but read by screen readers and crawlers.
const srOnly: CSSProperties = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0,0,0,0)",
  whiteSpace: "nowrap",
  border: 0,
};

function GitHubMark({ size = 16, fill = "#16161a" }: { size?: number; fill?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} aria-hidden>
      <path d="M12 2C6.5 2 2 6.6 2 12.3c0 4.5 2.9 8.3 6.8 9.7.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.4-3.4-1.4-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.6 2.4 1.1 3 .9.1-.7.3-1.1.6-1.4-2.2-.3-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.3-.4-1.3.1-2.7 0 0 .8-.3 2.7 1a9.3 9.3 0 0 1 5 0c1.9-1.3 2.7-1 2.7-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.3 4.7-4.6 5 .4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5A10.3 10.3 0 0 0 22 12.3C22 6.6 17.5 2 12 2Z" />
    </svg>
  );
}

function TelegramMark({ size = 16, fill = "#fff" }: { size?: number; fill?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} aria-hidden>
      <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
    </svg>
  );
}

export default function LandingPage() {
  const jsonLd = buildJsonLd();

  return (
    <div
      style={{
        fontFamily: "var(--font-hanken-grotesk)",
        color: "#16161a",
        background: "#ffffff",
        overflowX: "hidden",
      }}
    >
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <AnchorScroll />

      {/* ============ NAV ============ */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: "rgba(255,255,255,.95)",
          borderBottom: "1px solid #ededea",
        }}
      >
        <div
          style={{
            ...container,
            height: 66,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <a href="#top" style={{ display: "flex", alignItems: "center", gap: 9, textDecoration: "none", color: "#16161a" }}>
            <CloudLogo size={26} />
            <span
              style={{
                fontFamily: SPACE,
                fontWeight: 600,
                fontSize: 19,
                letterSpacing: "-.01em",
              }}
            >
              CloudPull
            </span>
          </a>
          <nav
            style={{ display: "flex", alignItems: "center", gap: 30 }}
            className="cp-nav"
          >
            <a href="#how" className="cp-navlink" style={{ fontSize: 14, textDecoration: "none", fontWeight: 500 }}>
              How it works
            </a>
            <a href="#features" className="cp-navlink" style={{ fontSize: 14, textDecoration: "none", fontWeight: 500 }}>
              Features
            </a>
            <a href="#formats" className="cp-navlink" style={{ fontSize: 14, textDecoration: "none", fontWeight: 500 }}>
              Formats
            </a>
            <a href="#faq" className="cp-navlink" style={{ fontSize: 14, textDecoration: "none", fontWeight: 500 }}>
              FAQ
            </a>
          </nav>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <a
              href={repoHref}
              {...repoProps}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                fontSize: 14,
                color: "#16161a",
                textDecoration: "none",
                fontWeight: 600,
                padding: "8px 12px",
                borderRadius: 9,
                border: "1px solid #e4e4e0",
              }}
            >
              <GitHubMark />
              GitHub
            </a>
            <a
              href={TELEGRAM_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="cp-orange"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                fontSize: 14,
                color: "#fff",
                textDecoration: "none",
                fontWeight: 600,
                padding: "9px 16px",
                borderRadius: 9,
                whiteSpace: "nowrap",
              }}
            >
              <TelegramMark />
              Telegram
            </a>
          </div>
        </div>
      </header>

      {/* ============ HERO ============ */}
      <section
        id="top"
        style={{ background: "linear-gradient(180deg,#f7f7f5 0%,#f7f7f5 56%,#ffffff 100%)" }}
      >
        <div id="get" style={{ ...container, padding: "72px 28px 84px", textAlign: "center" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 13px",
              borderRadius: 999,
              background: "#fff",
              border: "1px solid #e7e7e3",
              fontSize: 12.5,
              fontWeight: 600,
              color: "#56565e",
              marginBottom: 26,
            }}
          >
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#ff5500" }} />
            Free · No account · Open source
          </div>
          <h1
            style={{
              fontFamily: SPACE,
              fontWeight: 600,
              fontSize: "clamp(34px, 8vw, 60px)",
              lineHeight: 1.02,
              letterSpacing: "-.03em",
              margin: "0 auto 22px",
              maxWidth: 760,
            }}
          >
            Pull any SoundCloud track <span style={{ color: "#ff5500" }}>offline</span>, in seconds.
          </h1>
          <p
            style={{
              fontSize: 18,
              lineHeight: 1.55,
              color: "#56565e",
              maxWidth: 580,
              margin: "0 auto 34px",
            }}
          >
            CloudPull is a free SoundCloud downloader. Paste a track or full set
            link and grab the audio in your format of choice (mp3, FLAC and
            more), with cover art and tags baked in.
          </p>

          <HeroInteractive />
        </div>
      </section>

      {/* ============ WHAT IS CLOUDPULL (answer-first, for SEO + AI citation) ============ */}
      <section id="about" style={{ ...container, padding: "80px 28px 8px" }}>
        <div style={{ maxWidth: 820, margin: "0 auto" }}>
          <div style={eyebrow("#ff5500")}>What is CloudPull</div>
          <h2
            style={{
              fontFamily: SPACE,
              fontWeight: 600,
              fontSize: "clamp(26px, 5vw, 36px)",
              letterSpacing: "-.02em",
              margin: "0 0 18px",
            }}
          >
            A free SoundCloud downloader for any format
          </h2>
          <p style={{ margin: "0 0 16px", fontSize: 17, lineHeight: 1.65, color: "#41414a" }}>
            CloudPull is a free, open-source SoundCloud downloader that saves any
            public track or set to your device as MP3, M4A, Opus, FLAC or WAV. It
            runs the download and conversion on the server with yt-dlp and
            ffmpeg, then streams the finished file straight to your browser, with
            no account, no app to install, and nothing uploaded to a third party.
          </p>

          <h3 style={{ fontFamily: SPACE, fontWeight: 600, fontSize: 19, margin: "26px 0 8px" }}>
            How does CloudPull download SoundCloud tracks?
          </h3>
          <p style={{ margin: "0 0 16px", fontSize: 16, lineHeight: 1.65, color: "#41414a" }}>
            Paste a SoundCloud link and CloudPull reads the title, artist,
            artwork and full tracklist, fetches the highest-quality source audio,
            and converts it to your chosen format. A single track arrives as one
            tagged file; a full set or playlist is packed into a single zip. Most
            single tracks finish in a few seconds.
          </p>

          <h3 style={{ fontFamily: SPACE, fontWeight: 600, fontSize: 19, margin: "26px 0 8px" }}>
            Which audio format should I choose?
          </h3>
          <p style={{ margin: "0 0 28px", fontSize: 16, lineHeight: 1.65, color: "#41414a" }}>
            Choose MP3 at up to 320 kbps for small, universal files that play
            everywhere. Pick FLAC or WAV for bit-perfect, lossless audio when
            sound quality matters most. M4A (AAC) and Opus sit in between, giving
            the best quality per megabyte for streaming and mobile.
          </p>

          <dl
            className="cp-grid-4"
            style={{ display: "grid", gap: 14, margin: 0 }}
          >
            {stats.map((s) => (
              <div
                key={s.label}
                style={{
                  background: "#f7f7f5",
                  border: "1px solid #ededea",
                  borderRadius: 14,
                  padding: "20px 18px",
                  textAlign: "center",
                }}
              >
                <dt
                  style={{
                    fontFamily: SPACE,
                    fontWeight: 700,
                    fontSize: 26,
                    color: "#ff5500",
                    lineHeight: 1.1,
                  }}
                >
                  {s.value}
                </dt>
                <dd style={{ margin: "6px 0 0", fontSize: 13.5, color: "#6b6b73", fontWeight: 500 }}>
                  {s.label}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section id="how" style={{ ...container, padding: "88px 28px" }}>
        <div style={{ textAlign: "center", marginBottom: 54 }}>
          <div style={eyebrow("#ff5500")}>How it works</div>
          <h2
            style={{
              fontFamily: SPACE,
              fontWeight: 600,
              fontSize: "clamp(28px, 5.5vw, 40px)",
              letterSpacing: "-.02em",
              margin: 0,
            }}
          >
            Three steps. No clutter.
          </h2>
        </div>
        <div className="cp-grid-3" style={{ display: "grid", gap: 24 }}>
          {HOW_STEPS.map((s) => (
            <div
              key={s.n}
              style={{
                background: "#f7f7f5",
                border: "1px solid #ededea",
                borderRadius: 16,
                padding: 30,
              }}
            >
              <div
                style={{
                  fontFamily: SPACE,
                  fontWeight: 600,
                  fontSize: 15,
                  color: "#ff5500",
                  border: "1.5px solid #ffcdb0",
                  width: 38,
                  height: 38,
                  borderRadius: 10,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 20,
                }}
              >
                {s.n}
              </div>
              <h3 style={{ fontFamily: SPACE, fontWeight: 600, fontSize: 19, margin: "0 0 8px" }}>
                {s.title}
              </h3>
              <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.55, color: "#6b6b73" }}>
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ============ FEATURES ============ */}
      <section id="features" style={{ background: "#16161a", color: "#f6f6f8" }}>
        <div style={{ ...container, padding: "88px 28px" }}>
          <div style={{ marginBottom: 50, maxWidth: 560 }}>
            <div style={eyebrow("#ff7a3c")}>Features</div>
            <h2
              style={{
                fontFamily: SPACE,
                fontWeight: 600,
                fontSize: "clamp(28px, 5.5vw, 40px)",
                letterSpacing: "-.02em",
                margin: "0 0 14px",
                color: "#fff",
              }}
            >
              Everything the rip needs. Nothing it doesn&apos;t.
            </h2>
            <p style={{ margin: 0, fontSize: 16, lineHeight: 1.55, color: "#9b9ba6" }}>
              One shared engine over yt-dlp, wrapped in an interface you can use
              in ten seconds.
            </p>
          </div>
          <div
            className="cp-grid-3"
            style={{
              display: "grid",
              gap: 1,
              background: "#262630",
              border: "1px solid #262630",
              borderRadius: 16,
              overflow: "hidden",
            }}
          >
            {features.map((f) => (
              <div key={f.title} style={{ background: "#1a1a1f", padding: 30 }}>
                <svg width="24" height="24" viewBox="0 0 24 24" {...featureStroke} style={{ marginBottom: 16 }}>
                  {f.icon}
                </svg>
                <h3 style={{ fontFamily: SPACE, fontWeight: 600, fontSize: 17, margin: "0 0 7px", color: "#fff" }}>
                  {f.title}
                </h3>
                <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: "#9b9ba6" }}>
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ FORMATS ============ */}
      <section id="formats" style={{ ...container, padding: "88px 28px" }}>
        <div className="cp-formats" style={{ display: "grid", gap: 48, alignItems: "center" }}>
          <div>
            <div style={eyebrow("#ff5500")}>Formats &amp; quality</div>
            <h2
              style={{
                fontFamily: SPACE,
                fontWeight: 600,
                fontSize: "clamp(28px, 5vw, 38px)",
                letterSpacing: "-.02em",
                margin: "0 0 16px",
              }}
            >
              From quick mp3 to bit-perfect lossless.
            </h2>
            <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6, color: "#6b6b73" }}>
              Choose what fits the moment: a small mp3 for the phone, or
              untouched FLAC for the good speakers. CloudPull converts with
              ffmpeg and embeds the metadata either way.
            </p>
          </div>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 10px" }}>
            <caption style={srOnly}>
              SoundCloud download formats compared by name, description and
              whether the audio is lossless.
            </caption>
            <thead>
              <tr>
                <th scope="col" style={srOnly}>Format</th>
                <th scope="col" style={srOnly}>Description</th>
                <th scope="col" style={srOnly}>Type</th>
              </tr>
            </thead>
            <tbody>
              {formatRows.map((row) => {
                const bColor = row.lossless ? "#ffcdb0" : "#e7e7e3";
                const bWidth = row.lossless ? "1.5px" : "1px";
                const bg = row.lossless ? "#fffaf6" : "transparent";
                const cell: CSSProperties = {
                  borderTop: `${bWidth} solid ${bColor}`,
                  borderBottom: `${bWidth} solid ${bColor}`,
                  background: bg,
                  padding: "16px 0",
                  verticalAlign: "middle",
                };
                return (
                  <tr key={row.name}>
                    <th
                      scope="row"
                      style={{
                        ...cell,
                        borderLeft: `${bWidth} solid ${bColor}`,
                        borderTopLeftRadius: 12,
                        borderBottomLeftRadius: 12,
                        paddingLeft: 20,
                        width: 72,
                        textAlign: "left",
                        fontFamily: SPACE,
                        fontWeight: 700,
                        fontSize: 16,
                        color: "#16161a",
                      }}
                    >
                      {row.name}
                    </th>
                    <td style={{ ...cell, paddingRight: 16, fontSize: 14, color: "#6b6b73" }}>
                      {row.desc}
                    </td>
                    <td
                      style={{
                        ...cell,
                        borderRight: `${bWidth} solid ${bColor}`,
                        borderTopRightRadius: 12,
                        borderBottomRightRadius: 12,
                        paddingRight: 20,
                        textAlign: "right",
                        whiteSpace: "nowrap",
                      }}
                    >
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: row.lossless ? 700 : 600,
                          color: row.lossless ? "#fff" : "#ff5500",
                          background: row.lossless ? "#ff5500" : "#fff1e9",
                          padding: "4px 10px",
                          borderRadius: 6,
                        }}
                      >
                        {row.lossless ? "Lossless" : "Lossy"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* ============ FAQ ============ */}
      <section id="faq" style={{ background: "#f7f7f5", borderTop: "1px solid #ededea", borderBottom: "1px solid #ededea" }}>
        <div style={{ ...container, padding: "88px 28px" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <div style={eyebrow("#ff5500")}>FAQ</div>
            <h2
              style={{
                fontFamily: SPACE,
                fontWeight: 600,
                fontSize: "clamp(28px, 5.5vw, 40px)",
                letterSpacing: "-.02em",
                margin: 0,
              }}
            >
              Questions &amp; answers
            </h2>
          </div>
          <div style={{ maxWidth: 820, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
            {FAQ.map((item) => (
              <div
                key={item.q}
                style={{
                  background: "#fff",
                  border: "1px solid #e7e7e3",
                  borderRadius: 14,
                  padding: "22px 24px",
                }}
              >
                <h3 style={{ fontFamily: SPACE, fontWeight: 600, fontSize: 18, margin: "0 0 8px", color: "#16161a" }}>
                  {item.q}
                </h3>
                <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: "#56565e" }}>
                  {item.a}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ CTA ============ */}
      <section style={{ ...container, margin: "88px auto", padding: "0 28px" }}>
        <div
          style={{
            background: "#ff5500",
            borderRadius: 22,
            padding: "64px 40px",
            textAlign: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(40rem 30rem at 80% -20%,rgba(255,255,255,.22),transparent 60%)",
            }}
          />
          <div style={{ position: "relative" }}>
            <h2
              style={{
                fontFamily: SPACE,
                fontWeight: 600,
                fontSize: "clamp(30px, 6vw, 42px)",
                letterSpacing: "-.02em",
                margin: "0 0 14px",
                color: "#fff",
              }}
            >
              Paste a link. Get the file.
            </h2>
            <p
              style={{
                margin: "0 auto 30px",
                fontSize: 17,
                lineHeight: 1.5,
                color: "rgba(255,255,255,.9)",
                maxWidth: 480,
              }}
            >
              No sign-up, no paywall, no nonsense. Spin up CloudPull locally and
              start pulling tracks.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
              <a
                href="#get"
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: "#ff5500",
                  background: "#fff",
                  textDecoration: "none",
                  padding: "13px 26px",
                  borderRadius: 11,
                }}
              >
                Open the app
              </a>
              <a
                href={repoHref}
                {...repoProps}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 15,
                  fontWeight: 600,
                  color: "#fff",
                  background: "rgba(255,255,255,.14)",
                  textDecoration: "none",
                  padding: "13px 24px",
                  borderRadius: 11,
                  border: "1px solid rgba(255,255,255,.3)",
                }}
              >
                <GitHubMark fill="#fff" size={17} />
                View source
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <SiteFooter />
    </div>
  );
}
