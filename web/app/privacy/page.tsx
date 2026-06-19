import type { CSSProperties, ReactNode } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import CloudLogo from "@/components/CloudLogo";
import SiteFooter from "@/components/SiteFooter";

const SPACE = "var(--font-space-grotesk)";

export const metadata: Metadata = {
  title: "Privacy & Acceptable Use",
  description:
    "How CloudPull handles your data, and the rules for using it: a free, open-source tool for downloading SoundCloud tracks for lawful, personal use only.",
  alternates: { canonical: "/privacy" },
};

const LAST_UPDATED = "20 June 2026";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={{ marginTop: 36 }}>
      <h2
        style={{
          fontFamily: SPACE,
          fontWeight: 600,
          fontSize: 22,
          letterSpacing: "-.01em",
          margin: "0 0 12px",
          color: "#16161a",
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

const p: CSSProperties = {
  margin: "0 0 12px",
  fontSize: 16,
  lineHeight: 1.65,
  color: "#41414a",
};

const li: CSSProperties = {
  fontSize: 16,
  lineHeight: 1.6,
  color: "#41414a",
  marginBottom: 8,
};

export default function PrivacyPage() {
  return (
    <div style={{ fontFamily: "var(--font-hanken-grotesk)", color: "#16161a", background: "#ffffff", overflowX: "hidden" }}>
      {/* header */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: "rgba(255,255,255,.82)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          borderBottom: "1px solid #ededea",
        }}
      >
        <div
          style={{
            maxWidth: 1140,
            margin: "0 auto",
            padding: "0 28px",
            height: 66,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 9, textDecoration: "none", color: "#16161a" }}>
            <CloudLogo size={26} />
            <span style={{ fontFamily: SPACE, fontWeight: 600, fontSize: 19, letterSpacing: "-.01em" }}>
              CloudPull
            </span>
          </Link>
          <Link href="/" className="cp-navlink" style={{ fontSize: 14, fontWeight: 500, textDecoration: "none" }}>
            Back to home
          </Link>
        </div>
      </header>

      {/* content */}
      <main style={{ maxWidth: 760, margin: "0 auto", padding: "64px 28px 80px" }}>
        <div style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: ".14em", textTransform: "uppercase", color: "#ff5500", marginBottom: 14 }}>
          Privacy &amp; Acceptable Use
        </div>
        <h1
          style={{
            fontFamily: SPACE,
            fontWeight: 600,
            fontSize: "clamp(32px, 6vw, 44px)",
            letterSpacing: "-.02em",
            lineHeight: 1.05,
            margin: "0 0 14px",
          }}
        >
          Your privacy, and how to use CloudPull
        </h1>
        <p style={{ ...p, color: "#6b6b73" }}>Last updated: {LAST_UPDATED}</p>

        <p style={{ ...p, marginTop: 24 }}>
          CloudPull is a free, open-source tool that makes it convenient to save
          SoundCloud tracks and sets to your own device for personal use. This
          page explains, in plain language, how we handle your data and the
          rules for using CloudPull.
        </p>

        <Section title="1. What CloudPull is for">
          <p style={p}>
            CloudPull exists so you can conveniently keep SoundCloud audio you
            are entitled to listen to offline, for your own personal use. It is a
            personal utility, not a commercial music service, and we operate it
            within the law.
          </p>
        </Section>

        <Section title="2. Lawful, personal use only">
          <ul style={{ paddingLeft: 22, margin: 0 }}>
            <li style={li}>
              Use CloudPull only for content you are legally allowed to download,
              such as your own uploads, royalty-free or Creative Commons tracks,
              or audio the rights holder permits you to save.
            </li>
            <li style={li}>
              Respect copyright law and SoundCloud&apos;s Terms of Use. You are
              responsible for how you use the files you download.
            </li>
            <li style={li}>
              Do not use CloudPull to redistribute, sell, or publicly share
              copyrighted material.
            </li>
            <li style={li}>
              CloudPull is not affiliated with, endorsed by, or connected to
              SoundCloud in any way.
            </li>
          </ul>
        </Section>

        <Section title="3. The data we collect">
          <p style={p}>CloudPull is built to need as little of your data as possible:</p>
          <ul style={{ paddingLeft: 22, margin: 0 }}>
            <li style={li}>No account, no sign-up and no login.</li>
            <li style={li}>We never ask for your name, email or payment details.</li>
            <li style={li}>
              Downloaded files are sent straight to your device. We do not keep
              copies of the audio you download.
            </li>
            <li style={li}>
              Conversion happens on the server only for as long as your download
              takes; the temporary files are then deleted.
            </li>
          </ul>
        </Section>

        <Section title="4. Server logs">
          <p style={p}>
            Like most websites, our server may automatically record standard
            technical information for security and reliability, such as your IP
            address, browser type and the time of a request. These logs are kept
            only as long as needed and are not used to identify you or build a
            profile.
          </p>
        </Section>

        <Section title="5. Cookies and tracking">
          <p style={p}>
            The site uses no advertising cookies and no third-party analytics or
            tracking. We are not interested in following you around the web.
          </p>
        </Section>

        <Section title="6. Third parties">
          <p style={p}>
            CloudPull fetches audio from SoundCloud using the open-source yt-dlp
            tool. We do not sell or share your data with anyone.
          </p>
        </Section>

        <Section title="7. Your choices">
          <p style={p}>
            Because we do not hold accounts or profiles, there is no personal
            data of yours to access, change or delete. If you have a question
            about this policy, you can reach the maintainer through the project
            on GitHub.
          </p>
        </Section>

        <Section title="8. Changes to this policy">
          <p style={p}>
            We may update this page as the project evolves. The &quot;last
            updated&quot; date at the top always reflects the current version.
          </p>
        </Section>
      </main>

      <SiteFooter />
    </div>
  );
}
