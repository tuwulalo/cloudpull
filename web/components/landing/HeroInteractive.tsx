"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import {
  MediaInfo,
  Progress,
  fetchInfo,
  fileUrl,
  progressUrl,
  startDownload,
} from "@/lib/api";
import { formatDuration } from "@/lib/format";

const SPACE = "var(--font-space-grotesk)";
const HANKEN = "var(--font-hanken-grotesk)";

type Fmt = "mp3" | "m4a" | "flac" | "wav";
const FORMATS: Fmt[] = ["mp3", "m4a", "flac", "wav"];

type Phase =
  | "idle"
  | "loading"
  | "ready"
  | "downloading"
  | "processing"
  | "done"
  | "error";

const supportedChip: CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "#56565e",
  fontFamily: SPACE,
  background: "#fff",
  border: "1px solid #e7e7e3",
  padding: "3px 9px",
  borderRadius: 6,
};

function cardPill(active: boolean, disabled: boolean): CSSProperties {
  return {
    flex: 1,
    textAlign: "center",
    padding: "9px 0",
    borderRadius: 9,
    fontSize: 13,
    fontWeight: active ? 700 : 600,
    fontFamily: SPACE,
    cursor: disabled ? "default" : "pointer",
    background: active ? "#fff5ef" : "#fafafa",
    border: active ? "1.5px solid #ff5500" : "1.5px solid #ececec",
    color: active ? "#ff5500" : "#8a8a92",
    transition: "all 0.12s ease",
  };
}

export default function HeroInteractive() {
  const [url, setUrl] = useState("");
  const [info, setInfo] = useState<MediaInfo | null>(null);
  const [format, setFormat] = useState<Fmt>("mp3");
  const [phase, setPhase] = useState<Phase>("idle");
  const [percent, setPercent] = useState(0);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [doneName, setDoneName] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const finishedRef = useRef(false);
  const downloadedRef = useRef<string | null>(null);

  useEffect(() => () => esRef.current?.close(), []);

  const closeStream = () => {
    esRef.current?.close();
    esRef.current = null;
  };

  const onUrlChange = (value: string) => {
    setUrl(value);
    if (info || phase !== "idle") {
      closeStream();
      setInfo(null);
      setPhase("idle");
      setPercent(0);
      setErrMsg(null);
      setJobId(null);
      setDoneName(null);
    }
  };

  const find = useCallback(async () => {
    const value = url.trim();
    if (!value) return;
    closeStream();
    setErrMsg(null);
    setPercent(0);
    setJobId(null);
    setDoneName(null);
    setPhase("loading");
    try {
      const data = await fetchInfo(value);
      setInfo(data);
      setPhase("ready");
    } catch (e) {
      setInfo(null);
      setErrMsg(e instanceof Error ? e.message : "Could not read this link");
      setPhase("error");
    }
  }, [url]);

  const triggerBrowserDownload = (id: string) => {
    if (downloadedRef.current === id) return;
    downloadedRef.current = id;
    const a = document.createElement("a");
    a.href = fileUrl(id);
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const download = useCallback(async () => {
    if (!info) {
      find();
      return;
    }
    closeStream();
    finishedRef.current = false;
    downloadedRef.current = null;
    setErrMsg(null);
    setPercent(0);
    setPhase("downloading");
    try {
      const { job_id } = await startDownload({
        url: url.trim(),
        format,
        quality: "320",
        embed_thumbnail: true,
      });
      setJobId(job_id);

      const es = new EventSource(progressUrl(job_id));
      esRef.current = es;
      es.onmessage = (ev) => {
        const d = JSON.parse(ev.data) as Progress;
        if (d.status === "downloading") {
          setPhase("downloading");
          setPercent(d.percent || 0);
        } else if (d.status === "processing") {
          setPhase("processing");
          setPercent(100);
        } else if (d.status === "done") {
          finishedRef.current = true;
          setPhase("done");
          setPercent(100);
          setDoneName(d.filename || null);
          closeStream();
          triggerBrowserDownload(job_id);
        } else if (d.status === "error") {
          finishedRef.current = true;
          setErrMsg(d.error || "Download failed");
          setPhase("error");
          closeStream();
        }
      };
      es.onerror = () => {
        if (finishedRef.current) return;
        finishedRef.current = true;
        closeStream();
        setErrMsg("Lost connection to the server");
        setPhase("error");
      };
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "Could not start the download");
      setPhase("error");
    }
  }, [info, url, format, find]);

  const reset = () => {
    closeStream();
    finishedRef.current = false;
    downloadedRef.current = null;
    setPercent(0);
    setErrMsg(null);
    setJobId(null);
    setDoneName(null);
    setPhase(info ? "ready" : "idle");
  };

  const busy = phase === "downloading" || phase === "processing";
  const isPlaylist = info?.type === "playlist";
  const pct = Math.round(percent);

  return (
    <>
      {/* paste bar */}
      <div style={{ maxWidth: 620, margin: "0 auto" }}>
        <div
          style={{
            display: "flex",
            gap: 10,
            background: "#fff",
            border: "1px solid #e4e4e0",
            borderRadius: 14,
            padding: 8,
            boxShadow: "0 4px 24px rgba(20,20,26,.05)",
          }}
        >
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "0 12px",
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#a6a6ac"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1" />
              <path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1" />
            </svg>
            <input
              value={url}
              onChange={(e) => onUrlChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") find();
              }}
              spellCheck={false}
              aria-label="SoundCloud link"
              placeholder="Paste a SoundCloud track or set link"
              style={{
                width: "100%",
                border: "none",
                outline: "none",
                background: "transparent",
                fontFamily: HANKEN,
                fontSize: 15,
                color: "#16161a",
                padding: "11px 0",
              }}
            />
          </div>
          <button
            type="button"
            onClick={find}
            disabled={phase === "loading" || !url.trim()}
            className="cp-orange"
            style={{
              flex: "none",
              display: "flex",
              alignItems: "center",
              gap: 8,
              border: "none",
              cursor: phase === "loading" || !url.trim() ? "default" : "pointer",
              opacity: phase === "loading" || !url.trim() ? 0.65 : 1,
              color: "#fff",
              fontFamily: HANKEN,
              fontWeight: 600,
              fontSize: 15,
              padding: "0 22px",
              borderRadius: 9,
            }}
          >
            {phase === "loading" ? (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" className="cp-spin">
                <circle cx="12" cy="12" r="9" stroke="#fff" strokeOpacity="0.35" strokeWidth="2.6" />
                <path d="M21 12a9 9 0 0 0-9-9" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
              </svg>
            ) : (
              <svg
                width="17"
                height="17"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#fff"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="m21 21-4.3-4.3" />
              </svg>
            )}
            Find
          </button>
        </div>

        {/* supported formats */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            marginTop: 16,
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontSize: 12, color: "#9a9aa0", fontWeight: 500 }}>
            Supported:
          </span>
          {["mp3", "m4a", "flac", "wav", "opus"].map((f) => (
            <span key={f} style={supportedChip}>
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* product card (live) */}
      <div
        style={{
          maxWidth: 560,
          margin: "46px auto 0",
          transform: "translateY(1px)",
        }}
      >
        <div
          style={{
            background: "#fff",
            border: "1px solid #e7e7e3",
            borderRadius: "18px 18px 0 0",
            borderBottom: "none",
            boxShadow: "0 -2px 40px rgba(20,20,26,.06)",
            overflow: "hidden",
            textAlign: "left",
          }}
        >
          <div style={{ padding: 28 }}>
            {/* track row */}
            <div style={{ display: "flex", alignItems: "center", gap: 15 }}>
              {info?.thumbnail ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={info.thumbnail}
                  alt={info.title ?? "cover"}
                  style={{
                    width: 64,
                    height: 64,
                    flex: "none",
                    borderRadius: 11,
                    objectFit: "cover",
                  }}
                />
              ) : (
                <div
                  style={{
                    width: 64,
                    height: 64,
                    flex: "none",
                    borderRadius: 11,
                    background:
                      "linear-gradient(140deg,#ff7a3c,#ff2d6b 70%,#7b2dff)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="#fff">
                    <path
                      d="M9 18V6l10-2v12"
                      stroke="#fff"
                      strokeWidth="2"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <circle cx="6" cy="18" r="3" />
                    <circle cx="16" cy="16" r="3" />
                  </svg>
                </div>
              )}
              <div style={{ minWidth: 0, flex: 1 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 5,
                  }}
                >
                  <span
                    style={{
                      fontSize: 10.5,
                      fontWeight: 700,
                      letterSpacing: ".06em",
                      textTransform: "uppercase",
                      color: "#ff5500",
                      background: "#fff1e9",
                      padding: "2.5px 8px",
                      borderRadius: 5,
                    }}
                  >
                    {isPlaylist
                      ? `Set · ${info?.type === "playlist" ? info.track_count : 0}`
                      : "Track"}
                  </span>
                  {!isPlaylist && info?.type === "track" && info.duration ? (
                    <span
                      style={{ fontSize: 12, color: "#9a9aa0", fontFamily: SPACE }}
                    >
                      {formatDuration(info.duration)}
                    </span>
                  ) : null}
                </div>
                <div
                  style={{
                    fontFamily: SPACE,
                    fontWeight: 600,
                    fontSize: 16,
                    color: info ? "#16161a" : "#b4b4ba",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {info?.title ?? "Your track will appear here"}
                </div>
                <div style={{ fontSize: 13, color: "#8a8a92" }}>
                  {info?.uploader ?? "Paste a link above and press Find"}
                </div>
              </div>
            </div>

            {/* format pills */}
            <div style={{ display: "flex", gap: 8, marginTop: 18 }}>
              {FORMATS.map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => !busy && setFormat(f)}
                  disabled={busy}
                  style={{ ...cardPill(format === f, busy), border: cardPill(format === f, busy).border }}
                >
                  {f === "mp3" ? "mp3 · 320" : f}
                </button>
              ))}
            </div>

            {/* action zone */}
            {(phase === "idle" || phase === "loading" || phase === "ready") && (
              <button
                type="button"
                onClick={download}
                disabled={phase !== "ready"}
                className={phase === "ready" ? "cp-orange" : undefined}
                style={{
                  marginTop: 14,
                  width: "100%",
                  border: "none",
                  cursor: phase === "ready" ? "pointer" : "default",
                  background: phase === "ready" ? "#ff5500" : "#f0f0ec",
                  color: phase === "ready" ? "#fff" : "#b4b4ba",
                  fontFamily: HANKEN,
                  fontWeight: 600,
                  fontSize: 15,
                  padding: "13px 0",
                  borderRadius: 10,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 9,
                }}
              >
                <svg
                  width="17"
                  height="17"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke={phase === "ready" ? "#fff" : "#b4b4ba"}
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 4v12" />
                  <path d="m7 11 5 5 5-5" />
                  <path d="M5 20h14" />
                </svg>
                {phase === "ready"
                  ? `Download ${format}`
                  : "Find a track to download"}
              </button>
            )}

            {busy && (
              <div style={{ marginTop: 16 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 12.5,
                    marginBottom: 8,
                  }}
                >
                  <span style={{ color: "#56565e", fontWeight: 600 }}>
                    {phase === "processing"
                      ? "Converting…"
                      : "Downloading & converting…"}
                  </span>
                  <span
                    style={{ color: "#ff5500", fontWeight: 700, fontFamily: SPACE }}
                  >
                    {pct}%
                  </span>
                </div>
                <div
                  style={{
                    height: 9,
                    borderRadius: 6,
                    background: "#f0f0ec",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      borderRadius: 6,
                      background: "linear-gradient(90deg,#ff7a3c,#ff5500)",
                      width: `${pct}%`,
                      transition: "width 0.18s linear",
                    }}
                  />
                </div>
              </div>
            )}

            {phase === "done" && (
              <div
                style={{
                  marginTop: 16,
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                  background: "#f1f9f2",
                  border: "1px solid #cdeccf",
                  borderRadius: 14,
                  padding: "18px 20px",
                }}
              >
                <div
                  style={{
                    width: 38,
                    height: 38,
                    flex: "none",
                    borderRadius: "50%",
                    background: "#22a04a",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#fff"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="m5 12 5 5L20 7" />
                  </svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "#1c7a39" }}>
                    Saved to your device
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: "#5b9a6b",
                      fontFamily: SPACE,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {doneName ?? "file saved"}
                  </div>
                </div>
                {jobId ? (
                  <a
                    href={fileUrl(jobId)}
                    style={{
                      flex: "none",
                      color: "#1c7a39",
                      fontSize: 12.5,
                      fontWeight: 600,
                      fontFamily: HANKEN,
                      textDecoration: "underline",
                    }}
                  >
                    Save again
                  </a>
                ) : null}
                <button
                  type="button"
                  onClick={reset}
                  style={{
                    flex: "none",
                    border: "none",
                    cursor: "pointer",
                    background: "transparent",
                    color: "#8a8a92",
                    fontSize: 12.5,
                    fontWeight: 600,
                    fontFamily: HANKEN,
                    textDecoration: "underline",
                  }}
                >
                  Again
                </button>
              </div>
            )}

            {phase === "error" && (
              <div
                style={{
                  marginTop: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  background: "#fdf1f1",
                  border: "1px solid #f3cccc",
                  borderRadius: 10,
                  padding: "12px 14px",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: "#c0392b" }}>
                    Something went wrong
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "#b46b66",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {errMsg ?? "Unknown error"}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={info ? download : find}
                  style={{
                    flex: "none",
                    border: "none",
                    cursor: "pointer",
                    background: "transparent",
                    color: "#c0392b",
                    fontSize: 12.5,
                    fontWeight: 600,
                    fontFamily: HANKEN,
                    textDecoration: "underline",
                  }}
                >
                  Try again
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
