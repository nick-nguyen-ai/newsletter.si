(function () {
  "use strict";

  function sydneyParts(d) {
    // en-CA gives YYYY-MM-DD; hour/minute from Australia/Sydney
    var date = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Australia/Sydney",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(d);
    var parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Australia/Sydney",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).formatToParts(d);
    var hour = 0;
    var minute = 0;
    parts.forEach(function (p) {
      if (p.type === "hour") hour = parseInt(p.value, 10);
      if (p.type === "minute") minute = parseInt(p.value, 10);
    });
    return { date: date, minutes: hour * 60 + minute };
  }

  function defaultTab(postDate) {
    var hash = (window.location.hash || "").replace(/^#/, "").toLowerCase();
    if (hash === "morning" || hash === "close") return hash;
    // Section hashes belong to a tab; leave default logic for bare morning/close only.
    var now = sydneyParts(new Date());
    if (postDate < now.date) return "close";
    if (postDate === now.date && now.minutes >= 16 * 60 + 30) return "close";
    return "morning";
  }

  function resizeCharts(panel) {
    if (!panel) return;
    panel.querySelectorAll("canvas").forEach(function (canvas) {
      try {
        if (typeof Chart !== "undefined" && Chart.getChart) {
          var ch = Chart.getChart(canvas);
          if (ch) ch.resize();
        }
      } catch (e) {
        /* ignore */
      }
    });
    // Let charts.js remount if it listens
    try {
      window.dispatchEvent(
        new CustomEvent("mk-tab-shown", { detail: { panel: panel } })
      );
    } catch (e2) {
      /* ignore */
    }
  }

  function setTab(root, name, opts) {
    opts = opts || {};
    var tabs = root.querySelectorAll("[data-mk-tab]");
    var panels = root.querySelectorAll("[data-mk-panel]");
    tabs.forEach(function (tab) {
      var on = tab.getAttribute("data-mk-tab") === name;
      tab.setAttribute("aria-selected", on ? "true" : "false");
      tab.tabIndex = on ? 0 : -1;
      tab.classList.toggle("mk-tab--active", on);
    });
    var shown = null;
    panels.forEach(function (panel) {
      var on = panel.getAttribute("data-mk-panel") === name;
      if (on) {
        panel.hidden = false;
        shown = panel;
      } else {
        panel.hidden = true;
      }
    });
    // Sync outer layout sidebar: prefer the active panel's inline nav.
    var outer = document.querySelector(".site-shell > [data-section-nav]");
    if (outer) outer.hidden = true;

    if (opts.updateHash !== false) {
      var url = new URL(window.location.href);
      url.hash = name;
      history.replaceState(null, "", url.pathname + url.search + "#" + name);
    }
    // Charts in a newly shown panel need a resize (they measured 0×0 while hidden).
    if (shown) {
      requestAnimationFrame(function () {
        resizeCharts(shown);
      });
    }
  }

  function bindKeyboard(tablist, root) {
    tablist.addEventListener("keydown", function (e) {
      var tabs = Array.prototype.slice.call(
        tablist.querySelectorAll('[role="tab"]')
      );
      var i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      var next = i;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        next = (i + 1) % tabs.length;
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        next = (i - 1 + tabs.length) % tabs.length;
      } else if (e.key === "Home") {
        next = 0;
      } else if (e.key === "End") {
        next = tabs.length - 1;
      } else {
        return;
      }
      e.preventDefault();
      tabs[next].focus();
      setTab(root, tabs[next].getAttribute("data-mk-tab"));
    });
  }

  function initOne(root) {
    var postDate = root.getAttribute("data-post-date") || "";
    var tablist = root.querySelector('[role="tablist"]');
    if (!tablist) return;

    tablist.addEventListener("click", function (e) {
      var tab = e.target.closest("[data-mk-tab]");
      if (!tab || !tablist.contains(tab)) return;
      setTab(root, tab.getAttribute("data-mk-tab"));
    });
    bindKeyboard(tablist, root);

    window.addEventListener("hashchange", function () {
      var h = (window.location.hash || "").replace(/^#/, "").toLowerCase();
      if (h === "morning" || h === "close") setTab(root, h, { updateHash: false });
    });

    setTab(root, defaultTab(postDate), { updateHash: true });
  }

  function init() {
    document.querySelectorAll("[data-mk-tabs]").forEach(initOne);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
