(function () {
  "use strict";

  var MARKETS_SECTIONS = [
    { id: "big-picture", label: "Big picture", match: /^big picture$/i },
    { id: "macro", label: "Macro & geopolitics", match: /^macro/i },
    { id: "charts", label: "Charts", match: null },
    { id: "analysts", label: "Analysts", match: /analysts differ|where analysts/i },
    { id: "watchlist", label: "Watchlist", match: /watchlist/i },
    { id: "what-to-watch", label: "What to watch", match: /^what to watch$/i },
  ];

  function el(tag, className) {
    var n = document.createElement(tag);
    if (className) n.className = className;
    return n;
  }

  function textOf(node) {
    return (node && node.textContent || "").replace(/\s+/g, " ").trim();
  }

  function marketsHeadingId(strongText) {
    for (var i = 0; i < MARKETS_SECTIONS.length; i++) {
      var s = MARKETS_SECTIONS[i];
      if (s.match && s.match.test(strongText)) return s;
    }
    return null;
  }

  function wrapMarketsSections(body) {
    if (body.getAttribute("data-markets-sectioned") === "1") return;
    var children = Array.prototype.slice.call(body.childNodes);
    var fragment = document.createDocumentFragment();
    var current = null;
    var chartSection = null;

    function startSection(def, headingText) {
      current = el("section", "topic-section");
      current.id = "section-" + def.id;
      current.setAttribute("data-section-id", def.id);
      var h = el("h2", "topic-section__title");
      h.textContent = def.label || headingText;
      current.appendChild(h);
      fragment.appendChild(current);
      return current;
    }

    children.forEach(function (node) {
      if (node.nodeType !== 1) {
        if (current) current.appendChild(node);
        else fragment.appendChild(node);
        return;
      }

      // Chart figures → Charts section
      if (node.matches && node.matches("figure.chart")) {
        if (!chartSection) {
          chartSection = startSection(MARKETS_SECTIONS[2], "Charts");
        }
        chartSection.appendChild(node);
        current = chartSection;
        return;
      }

      var strong = node.tagName === "P" ? node.querySelector("strong") : null;
      var strongText = strong ? textOf(strong) : "";
      var isHeading =
        strong &&
        textOf(node).indexOf(strongText) === 0 &&
        strongText.length < 80 &&
        (textOf(node) === strongText || textOf(node).length > strongText.length);

      if (isHeading) {
        var def = marketsHeadingId(strongText);
        if (def && def.id !== "charts") {
          current = startSection(def, strongText);
          // Keep the original paragraph (has the body text after the bold title)
          current.appendChild(node);
          return;
        }
      }

      if (!current) {
        // Preamble before first heading — put in Big picture bucket if needed
        current = startSection(MARKETS_SECTIONS[0], "Big picture");
      }
      current.appendChild(node);
    });

    body.innerHTML = "";
    body.appendChild(fragment);
    body.setAttribute("data-markets-sectioned", "1");
  }

  function collectSections(body) {
    var sections = [];
    // Prefer AI skim sections
    var aiSecs = body.querySelectorAll(".ai-section");
    if (aiSecs.length) {
      aiSecs.forEach(function (sec) {
        sections.push({
          id: sec.getAttribute("data-section") || sec.id.replace(/^ai-section-/, ""),
          label: textOf(sec.querySelector(".ai-section__title")) || sec.id,
          el: sec,
        });
      });
      return sections;
    }

    var topicSecs = body.querySelectorAll(".topic-section");
    topicSecs.forEach(function (sec) {
      sections.push({
        id: sec.getAttribute("data-section-id") || sec.id.replace(/^section-/, ""),
        label: textOf(sec.querySelector(".topic-section__title")) || sec.id,
        el: sec,
      });
    });
    return sections;
  }

  function buildNav(listEl, sections) {
    listEl.innerHTML = "";
    var allBtn = el("button", "section-nav__item section-nav__item--active");
    allBtn.type = "button";
    allBtn.setAttribute("data-section-filter", "all");
    allBtn.textContent = "All";
    listEl.appendChild(allBtn);

    sections.forEach(function (sec) {
      var btn = el("button", "section-nav__item");
      btn.type = "button";
      btn.setAttribute("data-section-filter", sec.id);
      btn.textContent = sec.label.replace(/^\d+\.\s*/, "");
      listEl.appendChild(btn);
    });
  }

  function applyFilter(sections, filterId) {
    sections.forEach(function (sec) {
      var show = filterId === "all" || sec.id === filterId;
      sec.el.hidden = !show;
    });
    // Also hide AI 30s / chips when a single section is selected
    var skim = document.querySelector(".ai-skim");
    if (skim) {
      var strip = skim.querySelector(".ai-30");
      var chips = skim.querySelector(".ai-chips");
      if (strip) strip.hidden = filterId !== "all";
      if (chips) chips.hidden = true; // sidebar replaces chips
    }
  }

  function setActive(listEl, filterId) {
    listEl.querySelectorAll(".section-nav__item").forEach(function (btn) {
      btn.classList.toggle(
        "section-nav__item--active",
        btn.getAttribute("data-section-filter") === filterId
      );
    });
  }

  function updateHash(filterId) {
    var url = new URL(window.location.href);
    if (!filterId || filterId === "all") {
      url.hash = "";
      history.replaceState(null, "", url.pathname + url.search);
    } else {
      url.hash = filterId;
      history.replaceState(null, "", url.pathname + url.search + "#" + filterId);
    }
  }

  function init() {
    var nav = document.querySelector("[data-section-nav]");
    var body = document.querySelector("[data-topic-body]");
    if (!nav || !body) return;

    var listEl = nav.querySelector("[data-section-nav-list]");
    if (!listEl) return;

    var topic = body.getAttribute("data-topic-section");

    // Wait a tick so ai-skim can transform AI bodies first
    function run() {
      if (topic === "markets") wrapMarketsSections(body);
      var sections = collectSections(body);
      if (!sections.length) {
        nav.hidden = true;
        return;
      }
      buildNav(listEl, sections);

      function select(filterId, scroll) {
        applyFilter(sections, filterId);
        setActive(listEl, filterId);
        updateHash(filterId);
        if (scroll && filterId !== "all") {
          var target = sections.filter(function (s) {
            return s.id === filterId;
          })[0];
          if (target) target.el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }

      listEl.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-section-filter]");
        if (!btn) return;
        select(btn.getAttribute("data-section-filter"), true);
      });

      var hash = (window.location.hash || "").replace(/^#/, "");
      if (hash && sections.some(function (s) { return s.id === hash; })) {
        select(hash, false);
      } else {
        select("all", false);
      }

      window.addEventListener("hashchange", function () {
        var h = (window.location.hash || "").replace(/^#/, "") || "all";
        if (h === "all" || sections.some(function (s) { return s.id === h; })) {
          select(h, false);
        }
      });
    }

    // AI skim runs on DOMContentLoaded; give it a frame
    if (topic === "ai" && !body.querySelector(".ai-section")) {
      var tries = 0;
      var timer = setInterval(function () {
        tries += 1;
        if (body.querySelector(".ai-section") || tries > 20) {
          clearInterval(timer);
          run();
        }
      }, 50);
    } else {
      run();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
