// Client for the Python backend (FastAPI). Single source of truth for types and URLs.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export type TrackInfo = {
  id: string | null;
  title: string | null;
  uploader: string | null;
  duration: number | null;
  thumbnail: string | null;
  webpage_url: string | null;
};

export type MediaInfo =
  | ({ type: "track" } & TrackInfo)
  | {
      type: "playlist";
      title: string | null;
      uploader: string | null;
      webpage_url: string | null;
      thumbnail: string | null;
      track_count: number;
      tracks: TrackInfo[];
    };

export type FormatOption = { id: string; lossless: boolean };

export type FormatsResponse = {
  formats: FormatOption[];
  qualities: string[];
};

export type Progress = {
  id: string;
  status: "queued" | "downloading" | "processing" | "done" | "error";
  percent: number;
  speed?: number | null;
  eta?: number | null;
  title?: string | null;
  track_index?: number | null;
  track_total?: number | null;
  filename?: string | null;
  file_count?: number | null;
  error?: string | null;
};

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // body is not JSON, keep the status code
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function fetchFormats(): Promise<FormatsResponse> {
  return fetch(`${API_BASE}/api/formats`).then((r) => {
    if (!r.ok) throw new Error("Failed to load the format list");
    return r.json();
  });
}

export function fetchInfo(url: string): Promise<MediaInfo> {
  return postJson<MediaInfo>("/api/info", { url });
}

export function startDownload(params: {
  url: string;
  format: string;
  quality: string;
  embed_thumbnail: boolean;
}): Promise<{ job_id: string }> {
  return postJson<{ job_id: string }>("/api/download", params);
}

export function recordVisit(): void {
  fetch(`${API_BASE}/api/hit`, { method: "POST", keepalive: true }).catch(() => {
    // analytics is best-effort; never block the page on it
  });
}

export function fileUrl(jobId: string): string {
  return `${API_BASE}/api/file/${jobId}`;
}

export function progressUrl(jobId: string): string {
  return `${API_BASE}/api/progress/${jobId}`;
}
