(function () {
  "use strict";

  function initialize() {
    const deck = document.getElementById("deck");
    if (!deck) return;

    const slides = Array.from(deck.querySelectorAll(".slide"));
    if (!slides.length) return;

    const byId = (id) => document.getElementById(id);
    const previous = byId("previous");
    const next = byId("next");
    const slideCount = byId("slide-count");
    const sectionLabel = byId("section-label");
    const progress = byId("progress");
    const status = byId("status");
    const overview = byId("overview-dialog");
    const overviewList = byId("overview-list");
    const notes = byId("notes-dialog");
    const imageDialog = byId("image-dialog");
    const fullscreenButton = byId("fullscreen-button");
    const dialogOpeners = new WeakMap();
    const overviewItems = [];
    let currentIndex = -1;
    let gesture = null;

    const interactiveSelector = [
      "a[href]", "button", "input", "select", "textarea", "summary",
      "audio[controls]", "video[controls]", "iframe",
      '[contenteditable]:not([contenteditable="false"])',
      '[tabindex]:not([tabindex="-1"]):not(#deck)',
      '[role="button"]', '[role="link"]', '[role="checkbox"]',
      '[role="combobox"]', '[role="listbox"]', '[role="menuitem"]',
      '[role="option"]', '[role="radio"]', '[role="scrollbar"]',
      '[role="searchbox"]', '[role="slider"]', '[role="spinbutton"]',
      '[role="switch"]', '[role="tab"]', '[role="textbox"]', '[role="treeitem"]'
    ].join(",");

    function report(message) {
      if (status) status.textContent = message;
    }

    function modalOpen() {
      return Boolean(document.querySelector("dialog[open]"));
    }

    function interactiveEvent(event) {
      const path = typeof event.composedPath === "function"
        ? event.composedPath() : [event.target];
      return path.some((node) => node instanceof Element && node.closest(interactiveSelector));
    }

    function titleOf(slide, index) {
      return slide.dataset.title || `Slide ${index + 1}`;
    }

    function focusElement(element) {
      if (!element || !element.isConnected || element.closest("[hidden]") ||
          element.matches(":disabled")) return false;
      element.focus({ preventScroll: true });
      return document.activeElement === element;
    }

    function focusCurrentSlide() {
      const target = slides[currentIndex].querySelector("h1, h2, [data-slide-focus]") || deck;
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      focusElement(target);
    }

    function hashIndex() {
      const match = /^#slide-([1-9]\d*)$/.exec(window.location.hash);
      if (!match) return null;
      const index = Number(match[1]) - 1;
      return Number.isSafeInteger(index) && index >= 0 && index < slides.length ? index : null;
    }

    function writeHash(index) {
      const hash = `#slide-${index + 1}`;
      if (window.location.hash === hash) return;
      // Replace the fragment without scrolling or adding one history entry per slide.
      window.history.replaceState(window.history.state, "", hash);
    }

    function goTo(index, announce = true) {
      if (!Number.isInteger(index)) return false;
      index = Math.max(0, Math.min(slides.length - 1, index));
      if (index === currentIndex) {
        writeHash(index);
        return false;
      }

      const outgoing = slides[currentIndex];
      const focused = document.activeElement;
      currentIndex = index;
      slides.forEach((slide, position) => {
        slide.hidden = position !== currentIndex;
        slide.setAttribute("aria-hidden", String(slide.hidden));
      });
      if (previous) previous.disabled = currentIndex === 0;
      if (next) next.disabled = currentIndex === slides.length - 1;
      if (slideCount) {
        slideCount.textContent = `${currentIndex + 1} / ${slides.length}`;
        slideCount.setAttribute("aria-label", `Slide ${currentIndex + 1} of ${slides.length}`);
      }
      if (sectionLabel) sectionLabel.textContent = slides[currentIndex].dataset.section || "";
      if (progress) {
        progress.style.width = `${((currentIndex + 1) / slides.length) * 100}%`;
        progress.setAttribute("role", "progressbar");
        progress.setAttribute("aria-label", "Slide progress");
        progress.setAttribute("aria-valuemin", "0");
        progress.setAttribute("aria-valuemax", String(slides.length));
        progress.setAttribute("aria-valuenow", String(currentIndex + 1));
      }
      overviewItems.forEach((button, position) => {
        if (position === currentIndex) button.setAttribute("aria-current", "true");
        else button.removeAttribute("aria-current");
      });
      writeHash(currentIndex);
      if (announce) report(`Slide ${currentIndex + 1} of ${slides.length}. ${titleOf(slides[currentIndex], currentIndex)}`);

      // Keep persistent controls focused. Only recover focus that became unusable.
      if (!modalOpen() && (outgoing?.contains(focused) ||
          (focused === previous && previous.disabled) || (focused === next && next.disabled))) {
        focusCurrentSlide();
      }
      // A long mobile slide must not leave the next headline above the viewport.
      if (window.matchMedia("(max-width: 760px)").matches) {
        window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      }
      return true;
    }

    function openDialog(dialog, preferredFocus) {
      if (!dialog || modalOpen()) return false;
      if (typeof dialog.showModal !== "function") {
        report("Dialogs are unavailable in this browser.");
        return false;
      }
      dialogOpeners.set(dialog, document.activeElement);
      gesture = null;
      dialog.showModal();
      if (preferredFocus) focusElement(preferredFocus);
      return true;
    }

    [overview, notes, byId("help-dialog"), imageDialog].filter(Boolean).forEach((dialog) => {
      dialog.querySelectorAll("button[data-close]").forEach((button) => {
        button.addEventListener("click", () => dialog.close());
      });
      // The native dialog supplies Escape handling and focus containment.
      dialog.addEventListener("close", () => {
        if (modalOpen()) return;
        const opener = dialogOpeners.get(dialog);
        // focusElement uses preventScroll, preserving a slide change's mobile reset.
        if (!focusElement(opener)) focusCurrentSlide();
      });
    });

    if (overviewList) {
      const items = document.createDocumentFragment();
      slides.forEach((slide, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "overview-item";
        button.textContent = `${String(index + 1).padStart(2, "0")} · ${titleOf(slide, index)}`;
        button.addEventListener("click", () => {
          overview.close();
          goTo(index);
        });
        overviewItems.push(button);
        items.append(button);
      });
      overviewList.replaceChildren(items);
    }

    function showOverview() {
      openDialog(overview, overviewItems[currentIndex]);
    }

    function showNotes() {
      if (modalOpen()) return;
      const source = slides[currentIndex].querySelector(".speaker-notes");
      const content = byId("notes-content");
      const title = byId("notes-title");
      if (title) title.textContent = `${currentIndex + 1}. ${titleOf(slides[currentIndex], currentIndex)}`;
      if (content) {
        if (source) content.replaceChildren(...Array.from(source.childNodes, (node) => node.cloneNode(true)));
        else content.textContent = "No speaker notes for this slide.";
      }
      openDialog(notes);
    }

    function updateFullscreen() {
      if (!fullscreenButton) return;
      const active = Boolean(document.fullscreenElement);
      fullscreenButton.setAttribute("aria-pressed", String(active));
      fullscreenButton.setAttribute("aria-label", active ? "Exit fullscreen" : "Enter fullscreen");
      fullscreenButton.title = active ? "Exit fullscreen" : "Enter fullscreen";
    }

    function toggleFullscreen() {
      if (modalOpen()) return;
      const leaving = Boolean(document.fullscreenElement);
      const request = leaving ? document.exitFullscreen : document.documentElement.requestFullscreen;
      if (typeof request !== "function") {
        report("Fullscreen is unavailable in this browser.");
        return;
      }
      try {
        const result = request.call(leaving ? document : document.documentElement);
        Promise.resolve(result).catch(() => report("Fullscreen could not be changed. Use the browser’s fullscreen control."));
      } catch (_) {
        report("Fullscreen could not be changed. Use the browser’s fullscreen control.");
      }
    }

    function onClick(id, callback) {
      const button = byId(id);
      if (button) button.addEventListener("click", callback);
    }

    onClick("previous", () => goTo(currentIndex - 1));
    onClick("next", () => goTo(currentIndex + 1));
    onClick("overview-button", showOverview);
    onClick("notes-button", showNotes);
    onClick("fullscreen-button", toggleFullscreen);
    onClick("help-button", () => openDialog(byId("help-dialog")));
    onClick("print-button", () => window.print());

    deck.addEventListener("click", (event) => {
      const button = event.target instanceof Element ? event.target.closest("button[data-image]") : null;
      if (!button || !deck.contains(button) || button.closest("[hidden]") || modalOpen()) return;
      const source = button.dataset.image || "";
      const expanded = byId("expanded-image");
      const caption = button.dataset.caption || "Slide image";
      // The standalone deck expands embedded assets; it never fetches a remote image.
      if (!/^data:image\//i.test(source) && !source.startsWith("blob:")) {
        report("This image is not embedded in the presentation.");
        return;
      }
      if (!expanded) return;
      expanded.src = source;
      expanded.alt = caption;
      if (byId("image-caption")) byId("image-caption").textContent = caption;
      openDialog(imageDialog);
    });

    document.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey ||
          event.altKey || modalOpen() || interactiveEvent(event)) return;
      const key = event.key.toLowerCase();
      let action;
      if (["arrowright", "arrowdown", "pagedown", " ", "spacebar"].includes(key)) action = () => goTo(currentIndex + 1);
      else if (["arrowleft", "arrowup", "pageup"].includes(key)) action = () => goTo(currentIndex - 1);
      else if (key === "home") action = () => goTo(0);
      else if (key === "end") action = () => goTo(slides.length - 1);
      else if (!event.repeat && key === "o") action = showOverview;
      else if (!event.repeat && key === "n") action = showNotes;
      else if (!event.repeat && key === "f") action = toggleFullscreen;
      else if (!event.repeat && key === "?") action = () => openDialog(byId("help-dialog"));
      if (action) {
        event.preventDefault();
        action();
      }
    });

    deck.addEventListener("touchstart", (event) => {
      gesture = null;
      if (event.touches.length !== 1 || modalOpen() || interactiveEvent(event)) return;
      const touch = event.touches[0];
      gesture = { id: touch.identifier, x: touch.clientX, y: touch.clientY, at: event.timeStamp };
    }, { passive: true });
    deck.addEventListener("touchmove", (event) => {
      if (!gesture) return;
      if (event.touches.length !== 1 || modalOpen()) {
        gesture = null;
        return;
      }
      const touch = event.touches[0];
      const dx = Math.abs(touch.clientX - gesture.x);
      const dy = Math.abs(touch.clientY - gesture.y);
      if (touch.identifier !== gesture.id || (dy > 16 && dy > dx)) gesture = null;
    }, { passive: true });
    deck.addEventListener("touchcancel", () => { gesture = null; }, { passive: true });
    deck.addEventListener("touchend", (event) => {
      const start = gesture;
      gesture = null;
      if (!start || event.touches.length || modalOpen() || interactiveEvent(event)) return;
      const touch = Array.from(event.changedTouches).find((item) => item.identifier === start.id);
      if (!touch) return;
      const dx = touch.clientX - start.x;
      const dy = Math.abs(touch.clientY - start.y);
      if (event.timeStamp - start.at > 900 || Math.abs(dx) < 60 || Math.abs(dx) < dy * 1.5) return;
      event.preventDefault();
      goTo(currentIndex + (dx < 0 ? 1 : -1));
    }, { passive: false });

    window.addEventListener("hashchange", () => goTo(hashIndex() ?? 0));
    document.addEventListener("fullscreenchange", () => {
      updateFullscreen();
      report(document.fullscreenElement ? "Fullscreen enabled." : "Fullscreen exited.");
    });
    document.addEventListener("fullscreenerror", () => report("Fullscreen is unavailable for this presentation."));

    goTo(hashIndex() ?? 0, false);
    updateFullscreen();
    window.presentationApi = Object.freeze({
      goTo: (index) => goTo(index),
      current: () => currentIndex,
      count: slides.length
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
}());
