// CloudPull background service worker. The on-page button (content.js) cannot
// call the API directly (CORS from soundcloud.com), so it asks the worker, which
// has host access to cloudpull.cloud, to run the download and save the file.

const API = "https://cloudpull.cloud";

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg && msg.type === "cp-download") {
    handleDownload(msg.url, msg.format || "mp3", sender.tab && sender.tab.id);
  }
  // no async response needed; progress is pushed back via tabs.sendMessage
});

function notify(tabId, status, extra) {
  if (tabId == null) return;
  chrome.tabs.sendMessage(tabId, { type: "cp-status", status, ...extra }).catch(() => {});
}

async function handleDownload(url, format, tabId) {
  try {
    const res = await fetch(API + "/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, format, quality: "320", embed_thumbnail: true }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error " + res.status);
    }
    const { job_id } = await res.json();

    // Read the SSE progress stream manually (service workers have no EventSource).
    const stream = await fetch(API + "/api/progress/" + job_id);
    const reader = stream.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep;
      while ((sep = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const line = block.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const d = JSON.parse(line.slice(5).trim());
        if (d.status === "downloading") {
          notify(tabId, "progress", { percent: Math.round(d.percent || 0) });
        } else if (d.status === "processing") {
          notify(tabId, "progress", { percent: 100 });
        } else if (d.status === "done") {
          chrome.downloads.download({ url: API + "/api/file/" + job_id });
          notify(tabId, "done", {});
          return;
        } else if (d.status === "error") {
          notify(tabId, "error", { message: d.error || "Download failed" });
          return;
        }
      }
    }
    notify(tabId, "error", { message: "Connection ended" });
  } catch (e) {
    notify(tabId, "error", { message: (e && e.message) || "Could not download" });
  }
}
