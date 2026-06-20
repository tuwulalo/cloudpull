// CloudPull content script: injects a one-click download button (our icon) into
// the SoundCloud track action bar, next to like / repost / share. The actual
// download is done by the background worker (CORS), this just drives the UI.

(function () {
  const ICON = chrome.runtime.getURL("icons/icon48.png");

  // Inject the button styles once.
  const style = document.createElement("style");
  style.textContent = `
    .cloudpull-dl{display:inline-flex;align-items:center;justify-content:center;
      cursor:pointer;border:0;background:transparent;padding:0 6px;height:100%;
      vertical-align:middle}
    .cloudpull-dl img{width:16px;height:16px;display:block;
      transition:transform .15s ease;opacity:.85}
    .cloudpull-dl:hover img{opacity:1;transform:scale(1.12)}
    .cloudpull-dl.cp-loading img{animation:cp-spin .8s linear infinite}
    .cloudpull-dl.cp-ok img{filter:none}
    @keyframes cp-spin{to{transform:rotate(360deg)}}
  `;
  document.documentElement.appendChild(style);

  function trackUrl() {
    // The permalink of the track/set being viewed: /artist/track or /artist/sets/x
    const path = location.pathname;
    if (!/^\/[^/]+\/[^/]+/.test(path)) return null;
    return location.origin + path;
  }

  function makeButton() {
    const btn = document.createElement("button");
    btn.className = "cloudpull-dl sc-button";
    btn.type = "button";
    btn.title = "Download with CloudPull";
    const img = document.createElement("img");
    img.src = ICON;
    img.alt = "Download";
    btn.appendChild(img);
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const url = trackUrl();
      if (!url) {
        flash(btn, "Open a track page first");
        return;
      }
      btn.classList.remove("cp-ok");
      btn.classList.add("cp-loading");
      btn.title = "Starting...";
      chrome.runtime.sendMessage({ type: "cp-download", url, format: "mp3" });
    });
    return btn;
  }

  function flash(btn, text) {
    btn.title = text;
  }

  // Inject next to the share button of the MAIN track (not list items). The main
  // engagement bar is the first share button inside the listen/hero area.
  function inject() {
    const main =
      document.querySelector(
        ".listenEngagement .sc-button-share, .l-listen-hero .sc-button-share, .fullListenHero .sc-button-share, .sound__soundActions .sc-button-share"
      ) || document.querySelector(".sc-button-share");
    if (!main) return;
    const group = main.closest(".sc-button-group") || main.parentElement;
    if (!group || group.querySelector(".cloudpull-dl")) return;
    group.appendChild(makeButton());
  }

  // SoundCloud is a SPA; re-inject as the DOM changes.
  const observer = new MutationObserver(() => inject());
  observer.observe(document.body, { childList: true, subtree: true });
  inject();

  // Reflect background progress on the button.
  chrome.runtime.onMessage.addListener((msg) => {
    if (!msg || msg.type !== "cp-status") return;
    const btn =
      document.querySelector(".cloudpull-dl.cp-loading") ||
      document.querySelector(".cloudpull-dl");
    if (!btn) return;
    if (msg.status === "progress") {
      btn.title = "Downloading " + msg.percent + "%";
    } else if (msg.status === "done") {
      btn.classList.remove("cp-loading");
      btn.classList.add("cp-ok");
      btn.title = "Saved to your device";
      setTimeout(() => btn.classList.remove("cp-ok"), 2500);
    } else if (msg.status === "error") {
      btn.classList.remove("cp-loading");
      btn.title = msg.message || "Download failed";
    }
  });
})();
