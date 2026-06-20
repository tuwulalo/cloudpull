# CloudPull Chrome extension

A small Manifest V3 extension that downloads SoundCloud tracks and sets through
the CloudPull backend at `https://cloudpull.cloud`. It is a thin client: the
heavy lifting (yt-dlp + ffmpeg) happens on the server, the extension just talks
to the public API.

## Load it (developer mode)

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and select this `extension/` folder
   (e.g. `D:\claude\igx\scsaver\extension`).
4. The CloudPull icon appears in the toolbar. Pin it if you like.

## Use it

1. Open a SoundCloud track or set (or copy its link).
2. Click the CloudPull icon. If you are on a SoundCloud page, the link is
   filled in automatically; otherwise paste it.
3. Pick a format (mp3 / m4a / flac / wav / opus) and press **Download**.
4. Watch the progress; the file saves through Chrome's download manager when
   it is ready.

Keep the popup open until it says "Saved to your device". A single track takes
a few seconds; a whole set takes longer, so for big sets the web app
(`cloudpull.cloud`) is more convenient.

### On-page button

On a SoundCloud track or set page the extension also adds a small CloudPull
icon to the action bar (next to like / repost / share). Click it to download
the current track as mp3 in one click, without opening the popup. The button
spins while it works and stops when the file is saved. For other formats use
the popup. (If you reload the extension you may need to refresh the SoundCloud
tab for the button to appear.)

## How it works

- `POST /api/download` starts a job, `GET /api/progress/{id}` streams progress,
  `GET /api/file/{id}` returns the finished file.
- `host_permissions` for `https://cloudpull.cloud/*` let the popup call the API
  across origins; `downloads` lets it save the file.
- No data is collected by the extension; it only sends the link you choose.

## Publishing to the Chrome Web Store (optional)

1. Zip the contents of this folder (not the folder itself).
2. Create a developer account at the Chrome Web Store Developer Dashboard
   (one-time fee) and upload the zip.
3. Fill in the listing (description, screenshots, the 128px icon) and submit
   for review.

## Personal use

For personal use only. Respect copyright and the SoundCloud terms of use.
CloudPull is not affiliated with SoundCloud.
