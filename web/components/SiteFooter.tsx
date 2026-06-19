import Link from "next/link";
import CloudLogo from "@/components/CloudLogo";
import { REPO_URL } from "@/lib/site";

const linkStyle = {
  fontSize: 13,
  fontWeight: 500,
  color: "#56565e",
  textDecoration: "none",
};

export default function SiteFooter() {
  return (
    <footer style={{ borderTop: "1px solid #ededea", background: "#ffffff" }}>
      <div
        style={{
          maxWidth: 1140,
          margin: "0 auto",
          padding: "40px 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 20,
          flexWrap: "wrap",
        }}
      >
        <Link
          href="/"
          style={{ display: "flex", alignItems: "center", gap: 9, textDecoration: "none", color: "#16161a" }}
        >
          <CloudLogo size={22} />
          <span style={{ fontFamily: "var(--font-space-grotesk)", fontWeight: 600, fontSize: 16 }}>
            CloudPull
          </span>
        </Link>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 10 }}>
          <nav style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <Link href="/privacy" className="cp-navlink" style={linkStyle}>
              Privacy
            </Link>
            {REPO_URL ? (
              <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="cp-navlink" style={linkStyle}>
                GitHub
              </a>
            ) : null}
          </nav>
          <p style={{ margin: 0, fontSize: 12.5, color: "#9a9aa0", maxWidth: 460, textAlign: "right" }}>
            For personal use. Respect copyright and the SoundCloud terms of use.
            CloudPull is not affiliated with SoundCloud.
          </p>
        </div>
      </div>
    </footer>
  );
}
