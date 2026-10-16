(function () {
  "use strict";

  function init() {
    var page = document.querySelector("[data-archive-page]");
    if (!page) return;

    var input = page.querySelector("[data-archive-search]");
    var filters = page.querySelector("[data-archive-filters]");
    var status = page.querySelector("[data-archive-status]");
    var items = Array.prototype.slice.call(page.querySelectorAll("[data-archive-item]"));
    var months = Array.prototype.slice.call(page.querySelectorAll("[data-archive-month]"));

    var index = [];
    var indexEl = document.querySelector("[data-archive-index]");
    if (indexEl) {
      try {
        index = JSON.parse(indexEl.textContent || "[]");
      } catch (e) {
        console.warn("archive index parse failed", e);
      }
    }

    // Map url → text from index
    var textByUrl = {};
    index.forEach(function (row) {
      textByUrl[row.url] = ((row.title || "") + " " + (row.text || "")).toLowerCase();
    });

    var state = { topic: "all", query: "" };

    function apply() {
      var q = state.query.trim().toLowerCase();
      var visible = 0;
      items.forEach(function (item) {
        var topic = item.getAttribute("data-topic");
        var href = item.querySelector("a") && item.querySelector("a").getAttribute("href");
        var hay = textByUrl[href] || (item.textContent || "").toLowerCase();
        var topicOk = state.topic === "all" || topic === state.topic;
        var queryOk = !q || hay.indexOf(q) !== -1;
        var show = topicOk && queryOk;
        item.hidden = !show;
        if (show) visible += 1;
      });

      months.forEach(function (month) {
        var any = Array.prototype.some.call(month.querySelectorAll("[data-archive-item]"), function (it) {
          return !it.hidden;
        });
        month.hidden = !any;
      });

      if (status) {
        if (q || state.topic !== "all") {
          status.hidden = false;
          status.textContent = visible + (visible === 1 ? " issue" : " issues") + " matched";
        } else {
          status.hidden = true;
        }
      }
    }

    if (input) {
      input.addEventListener("input", function () {
        state.query = input.value || "";
        apply();
      });
    }

    if (filters) {
      filters.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-topic-filter]");
        if (!btn) return;
        state.topic = btn.getAttribute("data-topic-filter");
        filters.querySelectorAll(".archive-filter").forEach(function (b) {
          b.classList.toggle("archive-filter--active", b === btn);
        });
        apply();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
