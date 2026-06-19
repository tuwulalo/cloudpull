import { ImageResponse } from "next/og";

export const alt = "CloudPull: pull any SoundCloud track offline";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          background: "linear-gradient(140deg, #ff8636 0%, #ff5500 55%, #ee4800 100%)",
          color: "#ffffff",
          fontFamily: "sans-serif",
        }}
      >
        {/* brand row */}
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: 20,
              background: "rgba(255,255,255,0.16)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 44,
            }}
          >
            ☁
          </div>
          <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: -1 }}>
            CloudPull
          </div>
        </div>

        {/* headline */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 78, fontWeight: 800, lineHeight: 1.05, letterSpacing: -2 }}>
            Pull any SoundCloud
          </div>
          <div style={{ fontSize: 78, fontWeight: 800, lineHeight: 1.05, letterSpacing: -2 }}>
            track offline.
          </div>
        </div>

        {/* footer chips */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {["mp3", "m4a", "flac", "wav", "opus"].map((f) => (
            <div
              key={f}
              style={{
                display: "flex",
                fontSize: 28,
                fontWeight: 700,
                padding: "8px 22px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.18)",
              }}
            >
              {f}
            </div>
          ))}
          <div style={{ display: "flex", fontSize: 28, fontWeight: 600, marginLeft: 8 }}>
            Free · No account
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
