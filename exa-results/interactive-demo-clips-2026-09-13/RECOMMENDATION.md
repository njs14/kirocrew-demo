# Free tools for interactive demo clips

Researched with Exa on September 13, 2026. This is a recommendation based on documentation, source repositories and licenses; no recorder was installed or exercised.

## Recommendation for KiroCrew

Use **Recordly → MP4 → a small HTML5 player in the existing presentation**, with **asciinema for the terminal segment**. Use **OBS Studio** as the recording fallback. This captures the actual desktop and dashboard, then lets the presenter or audience control how the recording unfolds.

Use **Lumi Desktop + H5P Interactive Video** if visual authoring of clickable overlays, paused explanations or branching is more important than matching the existing slide design. Reserve **rrweb** for browser-only replay and **ShowKit** for an optional captured walkthrough.

Selection priorities were: actual captured behavior, free local use and export, source availability/license, portability into HTML slides, legible dashboard/terminal detail, and setup burden. Paid hosting and mock data are unnecessary for the recommended path.

## Shortlist

| Tool | Useful capability | Fit and limitation |
| --- | --- | --- |
| [Recordly](https://github.com/webadderallorg/Recordly) | Desktop/window capture, manual and automatic zoom, cursor effects, annotations, trim/speed controls, MP4 export. macOS 14+ supported. | Best first experiment for polished short clips. The project states it is fully free. Its [license](https://github.com/webadderallorg/Recordly/blob/main/LICENSE.md) contains AGPLv3 plus attribution/branding notices. Treat code reuse as a separate choice from using the recorder. Test an actual automated capture before committing to its automatic cursor effects. |
| [OBS Studio](https://github.com/obsproject/obs-studio) | Free screen/window recording, multiple sources/scenes, hotkeys and scripting/plugin APIs. GPLv2-or-later. | Strong fallback for straightforward capture of desktop, terminal and browser activity. Its [feature documentation](https://obsproject.com/) emphasizes capture and compositing; demo zoom editing requires a separate workflow. |
| [Lumi Desktop](https://lumi.education/en/lumi-h5p-offline-desktop-editor/) + [H5P Interactive Video](https://h5p.org/interactive-video) | Free offline authoring with timed text, images, links, pause points, bookmarks and adaptive navigation. Interactive Video's [source](https://github.com/h5p/h5p-interactive-video) is MIT licensed. | Best visual authoring option for interactive overlays on a recording. Lumi's [HTML export](https://help.lumi.education/articles/9460373-html-and-scorm-export) packages playback for local browsers or static hosting. Keep large video files separate. Use the desktop/local path; paid cloud hosting is unnecessary. |
| [asciinema player](https://github.com/asciinema/asciinema-player) | Apache-2.0 HTML player for text-based terminal recordings, with seek, speed, selectable text and [markers that pause or navigate](https://docs.asciinema.org/manual/player/markers/). | Best for the fixed MCP probe and its digest/request IDs. Produces terminal replay, not a desktop or browser recording. Its [quick start](https://docs.asciinema.org/manual/player/quick-start/) supports locally bundled JS/CSS and recording data. |
| [rrweb](https://github.com/rrweb-io/rrweb) | MIT DOM-event recording and replay with cursor activity, seeking and inactivity skipping. | Useful for dashboard changes. [Replay reconstructs the page](https://rrweb.com/use-cases/embedded-replay); it does not run the original app scripts or backend calls. Offline assets, canvas charts and media require additional handling. |
| [ShowKit](https://github.com/hyunghwan/showkit) | MIT captured HTML walkthroughs with hotspots, tooltips, scrolling and step navigation. | Closest to letting viewers click captured controls. Its [architecture](https://github.com/hyunghwan/showkit/blob/main/ARCHITECTURE.md) uses sanitized states and local assets. The [0.2.x compatibility scope](https://github.com/hyunghwan/showkit/blob/main/COMPATIBILITY.md) excludes several complex surfaces, including large canvas, video and cross-origin frames. Pilot one ordinary admin flow first. |

## What interactive would mean

There are three different deliverables:

1. **Controlled video:** the audience can play, pause, jump to a result, repeat a step, or open a receipt. Actions and dashboard values are recorded pixels. This is the recommended default.
2. **Interactive video:** the audience clicks an overlay to reveal an explanation or choose the next prerecorded segment. H5P supports this directly.
3. **Captured product walkthrough:** the audience clicks hotspots and moves between saved UI states. ShowKit provides this style. rrweb instead replays recorded DOM events. Neither operates the real AWS account during playback.

Keeping those distinctions visible helps the clips explain verified behavior without making a recorded dashboard look live. Label footage with its recording time and retain the original capture alongside edited exports. Cursor smoothing, zooms, annotations and speed changes improve presentation but should not imply a different sequence of observed actions.

## A first KiroCrew experiment

Build one 20–40 second clip first, using this proposed structure:

1. Record the agent opening Demo Observability and showing client/server samples.
2. Pause on the relevant values; add a short caption that identifies the measurement and capture time.
3. Place the clip inside the current slide style, with **Play**, **Replay step**, **Jump to result** and **Inspect receipt** controls.
4. Test playback and seeking in the same browser used for the presentation, then expand to the desktop-quit/server-survives sequence and the direct MCP probe.

Use asciinema for the probe so request IDs and output remain readable. Keep native Kiro CLI acceptance labeled pending until a real authenticated run exists. The recommendation does not create new proof or assume the currently deployed environment has been rechecked.

## Integration with the existing deck

The current deck is custom HTML. It does not need to migrate to a slide framework. Native [HTMLMediaElement](https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement) exposes playback controls, current time, playback rate and media events; small JavaScript controls can seek to cue points and coordinate captions.

If a future deck does use [reveal.js](https://revealjs.com/media/), it already documents slide-aware media autoplay/pause, lazy loading, lightboxes and iframe start/stop messages. Those behaviors would need to be added explicitly to this project's current navigation code.

Local source inspection found two concrete integration tasks:

- `scripts/serve-presentation.py` currently serves only the single HTML artifact. A clip edition needs an explicit allowlist for its video/player assets, or deliberately embedded media.
- The generated content policy starts with `default-src 'none'` and currently has no media permission. The clip edition needs narrowly scoped local media permissions, and the runtime must pause playback when changing slides.

For several clips, distribute a folder or ZIP containing the HTML and local media. This avoids putting every video into one large base64 HTML file. Lumi also [documents size/loading limitations](https://help.lumi.education/articles/9460373-html-and-scorm-export) for large embedded videos. Browser playback and offline asset loading still need a real smoke test.

## Options filtered out

- [Screenity](https://screenity.io/): its Chrome recorder remains free/open source, but the current site says the editor, auto-zoom/caption workflow, sharing and associated exports are paid. That does not fit the requested all-free workflow.
- [Demoday](https://github.com/emilankerwiik/demoday): useful for generating an interactive mock-up from source, but its placeholder data would not establish actual piloting or telemetry observations.
- Hosted analytics/session-replay services: unnecessary for a small portable slideshow. rrweb's open-source library can be used independently of paid hosting.

## Research scope and limits

Exa returned 55 search-result slots across capture, interactive playback/authoring, and DOM/guided-replay workstreams. This counts requested results, including duplicates, rather than 55 independently validated sources. Two result URLs in the DOM workstream were truncated and were not used; only identified primary sources informed the recommendation. Follow-up fetches are separate from the result count.

Maintainer documentation and source repositories were used for technical conclusions. Repository metadata and marketing claims were not treated as a hands-on benchmark. No upload, installation, capture, deployment or deck modification was performed. Recordly's behavior with the actual agent input path, Lumi's chosen export package, and dashboard-specific rrweb/ShowKit compatibility remain to be tested.
