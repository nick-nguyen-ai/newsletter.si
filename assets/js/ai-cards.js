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

  function initReport(report) {
    var select = report.querySelector("[data-ai-sec-select]");
    var side = report.querySelector("[data-ai-sec-side]");
    var sections = Array.prototype.slice.call(
      report.querySelectorAll("[data-ai-section]")
    );
    var cur = "all";

    function show(secId, opts) {
      opts = opts || {};
      cur = secId || "all";
      sections.forEach(function (sec) {
        var id = sec.getAttribute("data-ai-section");
        var on = cur === "all" || id === cur;
        sec.hidden = !on;
      });
      if (select) select.value = cur;
      if (side) {
        side.querySelectorAll("[data-ai-sec]").forEach(function (a) {
          a.classList.toggle("is-active", a.getAttribute("data-ai-sec") === cur);
        });
      }
      if (opts.updateHash) {
        var url = new URL(window.location.href);
        if (cur === "all") {
          url.hash = "";
          history.replaceState(null, "", url.pathname + url.search);
        } else {
          url.hash = "section-" + cur;
          history.replaceState(null, "", url.pathname + url.search + url.hash);
        }
      }
    }

    function openCard(id, scroll) {
      var card = report.querySelector("#" + CSS.escape(id));
      if (!card) return null;
      var sec = card.getAttribute("data-ai-card-sec");
      if (sec) show(sec, { updateHash: false });
      card.classList.add("is-open");
      var btn = card.querySelector("[data-ai-card-toggle]");
      var det = card.querySelector(".ai-card__det");
      if (btn) btn.setAttribute("aria-expanded", "true");
      if (det) det.hidden = false;
      if (scroll) {
        var header = document.querySelector(".site-header");
        var offset = (header ? header.offsetHeight : 0) + 12;
        var top = card.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top: top, behavior: "smooth" });
        card.classList.add("is-flash");
        setTimeout(function () {
          card.classList.remove("is-flash");
        }, 1500);
      }
      return card;
    }

    if (select) {
      select.addEventListener("change", function () {
        show(select.value, { updateHash: true });
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    if (side) {
      side.addEventListener("click", function (e) {
        var a = e.target.closest("[data-ai-sec]");
        if (!a) return;
        e.preventDefault();
        show(a.getAttribute("data-ai-sec"), { updateHash: true });
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    report.addEventListener("click", function (e) {
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
        var det = card.querySelector(".ai-card__det");
        if (det) det.hidden = !open;
      }
    });

    // Initial filter from hash
    var hash = (window.location.hash || "").replace(/^#/, "");
    if (hash.indexOf("section-") === 0) {
      show(hash.replace(/^section-/, ""), { updateHash: false });
    } else if (hash && report.querySelector("#" + CSS.escape(hash) + "[data-ai-card]")) {
      openCard(hash, true);
    } else {
      show("all", { updateHash: false });
    }

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
