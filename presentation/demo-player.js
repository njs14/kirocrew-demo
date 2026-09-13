(function () {
  "use strict";
  function initialize() {
    const players = Array.from(document.querySelectorAll(".recorded-demo"));
    if (!players.length) return;
    const pauseAll = () => players.forEach((slide) => slide.querySelector("video").pause());
    players.forEach((slide) => {
      const video = slide.querySelector("video");
      const cues = Array.from(slide.querySelectorAll("[data-cue-time]"));
      const detail = slide.querySelector(".demo-cue-detail");
      const guided = slide.querySelector(".demo-guided");
      const next = slide.querySelector(".demo-next-cue");
      const status = slide.querySelector(".demo-status");
      let previousTime = 0;
      let lastGuidedCue = -1;
      let requestedTime = null;
      video.muted = true;

      function showCue(button) {
        cues.forEach((cue) => {
          if (cue === button) cue.setAttribute("aria-current", "step");
          else cue.removeAttribute("aria-current");
        });
        detail.replaceChildren();
        const heading = document.createElement("strong");
        heading.textContent = button.dataset.cueLabel;
        const paragraph = document.createElement("p");
        paragraph.textContent = button.dataset.cueDetail;
        detail.append(heading, paragraph);
        if (button.dataset.cueEvidence) {
          const link = document.createElement("a");
          link.href = button.dataset.cueEvidence;
          link.textContent = "Open supporting evidence";
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          detail.append(link);
        }
      }
      function seek(time) {
        video.pause();
        requestedTime = time;
        if (video.readyState >= 1) {
          video.currentTime = Math.min(time, video.duration);
          requestedTime = null;
        } else video.load();
        previousTime = time;
        lastGuidedCue = cues.findIndex((cue) => Number(cue.dataset.cueTime) === time);
      }
      cues.forEach((button) => button.addEventListener("click", () => {
        seek(Number(button.dataset.cueTime));
        showCue(button);
        status.textContent = `Paused at ${button.dataset.cueLabel}.`;
      }));
      video.addEventListener("loadedmetadata", () => {
        if (requestedTime !== null) {
          video.currentTime = Math.min(requestedTime, video.duration);
          requestedTime = null;
        }
      });
      video.addEventListener("play", () => {
        if (slide.hidden || document.hidden || document.querySelector("dialog[open]")) video.pause();
        else players.forEach((other) => { if (other !== slide) other.querySelector("video").pause(); });
      });
      video.addEventListener("seeking", () => {
        // Manual seeking starts a new forward interval; it never counts as playback.
        previousTime = video.currentTime;
        lastGuidedCue = -1;
      });
      video.addEventListener("timeupdate", () => {
        const time = video.currentTime;
        if (guided.checked && !video.paused && !video.seeking && time >= previousTime) {
          const index = cues.findIndex((cue, i) => i !== lastGuidedCue &&
            Number(cue.dataset.cueTime) > previousTime + 0.01 && Number(cue.dataset.cueTime) <= time);
          if (index !== -1) {
            const cue = cues[index];
            video.pause();
            video.currentTime = Number(cue.dataset.cueTime);
            lastGuidedCue = index;
            showCue(cue);
            status.textContent = `Guided pause: ${cue.dataset.cueLabel}. Press play to continue.`;
          }
        }
        previousTime = video.currentTime;
        next.disabled = !cues.some((cue) => Number(cue.dataset.cueTime) > video.currentTime + 0.05);
      });
      next.addEventListener("click", () => {
        const cue = cues.find((item) => Number(item.dataset.cueTime) > video.currentTime + 0.05);
        if (cue) cue.click();
      });
      slide.querySelector(".demo-replay").addEventListener("click", () => {
        seek(0);
        if (cues.length) showCue(cues[0]);
        video.play().catch(() => { status.textContent = "Press play in the video controls to start."; });
      });
      video.addEventListener("error", () => {
        status.textContent = "Video could not load. Keep the media folder beside this edition, or use the local preview server.";
      });
      if (cues.length) showCue(cues[0]);
      else next.disabled = true;
    });
    const observer = new MutationObserver(() => {
      if (document.querySelector("dialog[open]")) pauseAll();
      else players.forEach((slide) => { if (slide.hidden) slide.querySelector("video").pause(); });
    });
    document.querySelectorAll(".slide, dialog").forEach((node) => {
      observer.observe(node, { attributes: true, attributeFilter: ["hidden", "open"] });
    });
    document.addEventListener("visibilitychange", () => { if (document.hidden) pauseAll(); });
    window.addEventListener("pagehide", pauseAll);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, { once: true });
  else initialize();
}());
