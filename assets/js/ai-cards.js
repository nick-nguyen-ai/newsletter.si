(function () {
  "use strict";

  function formatInlineCode(root) {
    if (!root) return;
    root.querySelectorAll("[data-ai-md]").forEach(function (el) {
      if (el.getAttribute("data-ai-md-done") === "1") return;
      var text = el.textContent || "";
      if (text.indexOf("`") === -1) {
        el.setAttribute("data-ai-md-done", "1");
        return;
      }
      var parts = text.split("`");
      el.textContent = "";
      parts.forEach(function (part, i) {
        if (i % 2 === 1) {
          var code = document.createElement("code");
          code.textContent = part;
          el.appendChild(code);
        } else {
          el.appendChild(document.createTextNode(part));
        }
      });
      el.setAttribute("data-ai-md-done", "1");
    });
  }

  /** Scroll a chip into view inside the horizontal chip row only — never the page. */
  function scrollChipRowTo(chip) {
    if (!chip) return;
    var row = chip.closest("[data-ai-chip-row]");
    if (!row) return;
    var rowRect = row.getBoundingClientRect();
    var chipRect = chip.getBoundingClientRect();
    var delta =
      chipRect.left -
      rowRect.left -
      (rowRect.width - chipRect.width) / 2;
    row.scrollBy({
      left: delta,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
  }

  function setToggleLabel(btn, open) {
    var label = btn && btn.querySelector("[data-ai-toggle-label]");
    if (label) label.textContent = open ? "Hide details" : "Read details";
  }

  function initReport(report) {
    var side = report.querySelector("[data-ai-sec-side]");
    var chips = report.querySelector("[data-ai-chip-row]");
    var sections = Array.prototype.slice.call(
      report.querySelectorAll("[data-ai-section]")
    );
    var cur = "all";

    function syncNav(secId) {
      if (side) {
        side.querySelectorAll("[data-ai-sec]").forEach(function (a) {
          a.classList.toggle(
            "is-active",
            a.getAttribute("data-ai-sec") === secId
          );
        });
      }
      if (chips) {
        chips.querySelectorAll("[data-ai-sec]").forEach(function (btn) {
          var on = btn.getAttribute("data-ai-sec") === secId;
          btn.classList.toggle("is-active", on);
          if (on) scrollChipRowTo(btn);
        });
      }
    }

    function show(secId, opts) {
      opts = opts || {};
      cur = secId || "all";
      sections.forEach(function (sec) {
        var id = sec.getAttribute("data-ai-section");
        var on = cur === "all" || id === cur;
        sec.hidden = !on;
      });
      syncNav(cur);
      if (opts.updateHash) {
        var url = new URL(window.location.href);
        if (cur === "all") {
          url.hash = "";
          history.pushState(null, "", url.pathname + url.search);
        } else {
          url.hash = "section-" + cur;
          history.pushState(null, "", url.pathname + url.search + url.hash);
        }
      }
    }

    function openCard(id, scroll) {
      var card = report.querySelector("#" + CSS.escape(id));
      if (!card) {
        // Alias: older anchors may omit prefixes; try data-ai-card match
        card = report.querySelector('[data-ai-card][id="' + id + '"]');
      }
      if (!card) return null;
      var sec = card.getAttribute("data-ai-card-sec");
      if (sec) show(sec, { updateHash: false });
      card.classList.add("is-open");
      var btn = card.querySelector("[data-ai-card-toggle]");
      var det = card.querySelector(".ai-card__det");
      if (btn) {
        btn.setAttribute("aria-expanded", "true");
        setToggleLabel(btn, true);
      }
      if (det) det.hidden = false;
      if (scroll) {
        var header = document.querySelector(".site-header");
        var chipsBar = report.querySelector(".ai-report__chips");
        var offset =
          (header ? header.offsetHeight : 0) +
          (chipsBar && getComputedStyle(chipsBar).display !== "none"
            ? chipsBar.offsetHeight
            : 0) +
          12;
        var top = card.getBoundingClientRect().top + window.scrollY - offset;
        var reduce = window.matchMedia("(prefers-reduced-motion: reduce)")
          .matches;
        window.scrollTo({ top: top, behavior: reduce ? "auto" : "smooth" });
        card.classList.add("is-flash");
        setTimeout(function () {
          card.classList.remove("is-flash");
        }, 1400);
      }
      return card;
    }

    function onSecClick(secId) {
      show(secId, { updateHash: true });
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)")
        .matches;
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    }

    if (side) {
      side.addEventListener("click", function (e) {
        var a = e.target.closest("[data-ai-sec]");
        if (!a) return;
        e.preventDefault();
        onSecClick(a.getAttribute("data-ai-sec"));
      });
    }

    if (chips) {
      chips.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-ai-sec]");
        if (!btn) return;
        e.preventDefault();
        onSecClick(btn.getAttribute("data-ai-sec"));
      });
    }

    report.addEventListener("click", function (e) {
      // External source links must never toggle the card
      if (e.target.closest("[data-ai-ext-link], .ai-card__links a, a[href^='http']")) {
        return;
      }

      var jump = e.target.closest("[data-ai-jump]");
      if (jump) {
        e.preventDefault();
        var id = jump.getAttribute("data-ai-jump");
        var sec = jump.getAttribute("data-ai-jump-sec");
        if (sec) show(sec, { updateHash: false });
        openCard(id, true);
        history.replaceState(null, "", "#" + id);
        return;
      }

      var toggle = e.target.closest("[data-ai-card-toggle]");
      if (toggle) {
        var card = toggle.closest(".ai-card");
        if (!card) return;
        var open = !card.classList.contains("is-open");
        card.classList.toggle("is-open", open);
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        setToggleLabel(toggle, open);
        var det = card.querySelector(".ai-card__det");
        if (det) det.hidden = !open;
      }
    });

    // Keyboard: Enter/Space on focused toggle already works for <button>

    function applyHash(hash, scroll) {
      hash = (hash || "").replace(/^#/, "");
      if (!hash || hash === "all") {
        show("all", { updateHash: false });
        return;
      }
      if (hash.indexOf("section-") === 0) {
        show(hash.replace(/^section-/, ""), { updateHash: false });
        return;
      }
      if (report.querySelector("#" + CSS.escape(hash) + "[data-ai-card]")) {
        openCard(hash, scroll !== false);
        return;
      }
      show("all", { updateHash: false });
    }

    applyHash(window.location.hash, true);

    window.addEventListener("hashchange", function () {
      applyHash(window.location.hash, true);
    });

    window.addEventListener("popstate", function () {
      applyHash(window.location.hash, false);
    });

    formatInlineCode(report);
  }

  function init() {
    document.querySelectorAll("[data-ai-report]").forEach(initReport);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
