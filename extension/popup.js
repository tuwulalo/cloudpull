// CloudPull Chrome extension popup. A thin client over the public API at
// cloudpull.cloud (host_permissions in the manifest let it call cross-origin).

const API = "https://cloudpull.cloud";
const SC = /soundcloud\.com/i;

let format = "mp3";
let es = null;

const $ = (id) => document.getElementById(id);

function setStatus(text, cls) {
  const el = $("status");
  el.className = "status " + (cls || "");
  el.textContent = text;
}

// Prefill the link from the active tab if it is a SoundCloud page.
chrome.tabs
  .query({ active: true, currentWindow: true })
  .then(([tab]) => {
    if (tab && tab.url && SC.test(tab.url)) {
      $("url").value = tab.url;
    }
  })
  .catch(() => {});

// Format pills.
document.querySelectorAll(".pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    format = pill.dataset.fmt;
    document
      .querySelectorAll(".pill")
      .forEach((p) => p.classList.toggle("active", p === pill));
    $("dlbtn").textContent = "Download " + format;
  });
});

async function download() {
  const url = $("url").value.trim();
  if (!SC.test(url)) {
    setStatus("Paste a SoundCloud link first.", "err");
    return;
  }
  $("dlbtn").disabled = true;
  setStatus("Starting...", "");

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

    if (es) es.close();
    es = new EventSource(API + "/api/progress/" + job_id);
    let finished = false;

    es.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      if (d.status === "downloading") {
        setStatus("Downloading " + Math.round(d.percent || 0) + "%", "");
      } else if (d.status === "processing") {
        setStatus("Converting...", "");
      } else if (d.status === "done") {
        finished = true;
        es.close();
        chrome.downloads.download({ url: API + "/api/file/" + job_id });
        setStatus("Saved to your device", "ok");
        $("dlbtn").disabled = false;
      } else if (d.status === "error") {
        finished = true;
        es.close();
        setStatus(d.error || "Download failed", "err");
        $("dlbtn").disabled = false;
      }
    };

    es.onerror = () => {
      if (finished) return;
      es.close();
      setStatus("Lost connection. Try again.", "err");
      $("dlbtn").disabled = false;
    };
  } catch (e) {
    setStatus(e.message || "Could not start the download", "err");
    $("dlbtn").disabled = false;
  }
}

$("dlbtn").addEventListener("click", download);
$("url").addEventListener("keydown", (e) => {
  if (e.key === "Enter") download();
});
