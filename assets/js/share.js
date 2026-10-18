(function () {
  "use strict";

  var toastTimer = null;

  function pageShareEl() {
    return (
      document.querySelector(".share-fab[data-share]") ||
      document.querySelector(".share-btn--header[data-share]") ||
      document.querySelector("[data-share]")
    );
  }

  function shareUrl(fromEl) {
    var el = fromEl || pageShareEl();
    var base =
      (el && el.getAttribute("data-share-url")) ||
      (document.querySelector('link[rel="canonical"]') &&
        document.querySelector('link[rel="canonical"]').href) ||
      location.href.split("#")[0];
    try {
      var url = new URL(base, location.origin);
      var section = el && el.getAttribute("data-share-section");
      if (section && section !== "all") {
        url.hash = section;
      } else if (!section) {
        url.hash = location.hash || "";
      } else {
        url.hash = "";
      }
      return url.toString();
    } catch (e) {
      return location.href;
    }
  }

  function showToast(msg) {
    var toast = document.querySelector("[data-share-toast]");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "share-toast";
      toast.setAttribute("data-share-toast", "");
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add("share-toast--visible");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove("share-toast--visible");
    }, 2200);
  }

  function copyLink(url) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(url).then(function () {
        showToast("Link copied");
      });
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = url;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
        showToast("Link copied");
        resolve();
      } catch (e) {
        reject(e);
      } finally {
        document.body.removeChild(ta);
      }
    });
  }

  function ensureFallback() {
    var panel = document.querySelector("[data-share-fallback]");
    if (panel) return panel;
    panel = document.createElement("div");
    panel.className = "share-fallback";
    panel.setAttribute("data-share-fallback", "");
    panel.hidden = true;
    panel.innerHTML =
      '<div class="share-fallback__sheet" role="dialog" aria-label="Share this page">' +
      '<p class="share-fallback__title">Share</p>' +
      '<button type="button" class="share-fallback__btn" data-share-copy>Copy link</button>' +
      '<a class="share-fallback__btn" data-share-wa target="_blank" rel="noopener noreferrer">WhatsApp</a>' +
      '<a class="share-fallback__btn" data-share-x target="_blank" rel="noopener noreferrer">X</a>' +
      '<a class="share-fallback__btn" data-share-mail>Email</a>' +
      '<button type="button" class="share-fallback__close" data-share-close>Close</button>' +
      "</div>";
    document.body.appendChild(panel);

    panel.addEventListener("click", function (e) {
      if (e.target === panel || e.target.closest("[data-share-close]")) {
        panel.hidden = true;
      }
    });
    panel.querySelector("[data-share-copy]").addEventListener("click", function () {
      var btn = panel._shareSource || null;
      copyLink(shareUrl(btn)).then(function () {
        panel.hidden = true;
      });
    });
    return panel;
  }

  function showFallback(url, sourceEl) {
    var panel = ensureFallback();
    panel._shareSource = sourceEl || null;
    var enc = encodeURIComponent;
    // URL only — never prepend titles containing a bare "signaletter.si" token
    // (messaging apps auto-link it to the unrelated Slovenian site).
    panel.querySelector("[data-share-wa]").href = "https://wa.me/?text=" + enc(url);
    panel.querySelector("[data-share-x]").href =
      "https://twitter.com/intent/tweet?url=" + enc(url);
    panel.querySelector("[data-share-mail]").href = "mailto:?body=" + enc(url);
    panel.hidden = false;
  }

  function doShare(fromEl) {
    var url = shareUrl(fromEl);
    if (typeof navigator.share === "function") {
      navigator
        .share({ url: url })
        .catch(function (err) {
          if (err && err.name === "AbortError") return;
          showFallback(url, fromEl);
        });
      return;
    }
    showFallback(url, fromEl);
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-share]");
    if (!btn) return;
    e.preventDefault();
    doShare(btn);
  });

  function decorateSections() {
    var root = document.querySelector("[data-topic-body]");
    if (!root) return false;
    var hasSections = root.querySelector(".topic-section, .ai-section");
    if (!hasSections) return false;

    var pageEl = pageShareEl();
    var pageUrl =
      (pageEl && pageEl.getAttribute("data-share-url")) ||
      location.href.split("#")[0];

    root.querySelectorAll(".topic-section, .ai-section").forEach(function (sec) {
      if (sec.querySelector("[data-share-section]")) return;
      var id =
        sec.getAttribute("data-section-id") ||
        sec.getAttribute("data-section") ||
        (sec.id || "").replace(/^(section-|ai-section-)/, "");
      if (!id) return;
      var titleEl =
        sec.querySelector(".topic-section__title, .ai-section__title") ||
        sec.querySelector("h2, h3");
      if (!titleEl) return;
      titleEl.classList.add("share-section-heading");
      var label = (titleEl.textContent || id).trim();
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "share-btn share-btn--inline";
      btn.setAttribute("data-share", "");
      btn.setAttribute("data-share-section", id);
      btn.setAttribute("data-share-url", pageUrl);
      btn.setAttribute("aria-label", "Share " + label + " section");
      btn.innerHTML =
        '<svg class="share-btn__icon" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/></svg>';
      titleEl.appendChild(btn);
    });
    return true;
  }

  function startDecorate() {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      if (decorateSections() || tries > 40) clearInterval(timer);
    }, 50);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startDecorate);
  } else {
    startDecorate();
  }
})();
