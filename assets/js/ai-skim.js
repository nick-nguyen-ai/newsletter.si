(function () {
  "use strict";

  // Both legacy headings ("Claude Code and Codex", "Other coding agents…")
  // map to one section id so they merge at render time.
  var SECTION_CHIPS = [
    {
      match: /claude\s*code|codex|coding agents|dev tools/i,
      id: "coding-agents",
      label: "AI coding agents",
      mergeHeading: "AI coding agents",
    },
    { match: /evaluat|validat/i, id: "eval", label: "Eval & validation" },
    { match: /agent frameworks|open-?source agent/i, id: "frameworks", label: "Agent frameworks" },
    { match: /big ai compan/i, id: "big-cos", label: "Big AI cos" },
    { match: /general ai news/i, id: "general", label: "General" },
    { match: /trending on x/i, id: "x", label: "Trending on X", kind: "x" },
    { match: /papers/i, id: "papers", label: "Papers", kind: "papers" },
    { match: /repos|github/i, id: "repos", label: "Repos", kind: "repos" },
  ];

  // Longer / more specific names first so "Claude Code" wins over a bare "Claude".
  var AGENT_TAGS = [
    { name: "Claude Code", re: /\bclaude\s*code\b/i },
    { name: "Codex", re: /\bcodex\b/i },
    { name: "Cursor", re: /\bcursor\b/i },
    { name: "Copilot", re: /\b(?:github\s+)?copilot\b/i },
    { name: "Gemini CLI", re: /\bgemini\s*cli\b/i },
    { name: "OpenCode", re: /\bopencode\b/i },
    { name: "Windsurf", re: /\bwindsurf\b/i },
    { name: "Cline", re: /\bcline\b/i },
    { name: "Aider", re: /\baider\b/i },
    { name: "Devin", re: /\bdevin\b/i },
    { name: "Grok", re: /\bgrok\b/i },
    { name: "Continue", re: /\bcontinue\.dev\b|\bcontinue\b(?=\s+(?:agent|extension|IDE))/i },
    { name: "Amp", re: /\bamp\b(?=\s+(?:code|agent|CLI|harness))?/i },
    { name: "Goose", re: /\bgoose\b/i },
    { name: "Pi", re: /\bpi\b(?=\s|v\d|[./:'"]|$)|\/pi\b|\bpi\s+v\d/i },
  ];

  function slugify(text) {
    return String(text || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function chipForHeading(headingText) {
    for (var i = 0; i < SECTION_CHIPS.length; i++) {
      if (SECTION_CHIPS[i].match.test(headingText)) return SECTION_CHIPS[i];
    }
    return {
      id: slugify(headingText),
      label: headingText.replace(/^\d+\.\s*/, "").trim(),
      kind: "cards",
    };
  }

  function firstSentence(text) {
    var t = (text || "").replace(/\s+/g, " ").trim();
    if (!t) return "";
    var m = t.match(/^(.+?[.!?])(?:\s|$)/);
    return m ? m[1] : t;
  }

  function extractDomain(url) {
    try {
      return new URL(url, window.location.href).hostname.replace(/^www\./, "");
    } catch (e) {
      return "";
    }
  }

  function isUnconfirmed(text) {
    return /\bunconfirmed\b/i.test(text || "");
  }

  function detectAgents(item) {
    var hay = [item.title || "", item.summary || "", item.forYou || "", item.takeaway || ""];
    (item.links || []).forEach(function (l) {
      hay.push(l.text || "", l.href || "", l.domain || "");
    });
    if (item.bodyEl) hay.push(textOf(item.bodyEl));
    var blob = hay.join(" \n ");
    var found = [];
    var seen = {};
    AGENT_TAGS.forEach(function (agent) {
      if (seen[agent.name]) return;
      if (agent.re.test(blob)) {
        seen[agent.name] = true;
        found.push(agent.name);
      }
    });
    return found;
  }

  function textOf(el) {
    return (el && el.textContent) || "";
  }

  function cloneChildren(from, to) {
    Array.prototype.forEach.call(from.childNodes, function (n) {
      to.appendChild(n.cloneNode(true));
    });
  }

  function parseLinksFromEl(el) {
    var links = [];
    if (!el) return links;
    el.querySelectorAll("a[href]").forEach(function (a) {
      links.push({ href: a.href, text: (a.textContent || "").trim(), domain: extractDomain(a.href) });
    });
    return links;
  }

  function splitForYou(text) {
    var m = text.match(/^(.*?)(?:\n|\s)For you:\s*([\s\S]*)$/i);
    if (!m) {
      // same-line "For you:" after sentence
      m = text.match(/^(.*?)\s+For you:\s*([\s\S]*)$/i);
    }
    if (!m) return { summary: text.trim(), forYou: "" };
    return { summary: m[1].trim(), forYou: m[2].trim() };
  }

  function parseCardFromParagraph(p, section) {
    var strong = p.querySelector("strong");
    if (!strong) return null;
    // Title is the first strong if it starts the paragraph
    var full = textOf(p).replace(/\s+/g, " ").trim();
    var title = textOf(strong).trim();
    if (!title || full.indexOf(title) > 20) return null;

    var rest = full.slice(full.indexOf(title) + title.length).trim();
    var parts = splitForYou(rest);
    var takeaway = parts.forYou ? firstSentence(parts.forYou) : firstSentence(parts.summary);
    if (parts.forYou && takeaway.indexOf("For you:") === 0) {
      takeaway = takeaway.replace(/^For you:\s*/i, "");
    }

    var links = parseLinksFromEl(p);
    // Body HTML for expand: keep original paragraph content
    var body = document.createElement("div");
    body.className = "ai-card__full";
    body.appendChild(p.cloneNode(true));

    var item = {
      kind: "card",
      sectionId: section.id,
      sectionLabel: section.label,
      title: title,
      takeaway: takeaway,
      summary: parts.summary,
      forYou: parts.forYou,
      links: links,
      unconfirmed: isUnconfirmed(title) || isUnconfirmed(full),
      bodyEl: body,
      agents: [],
    };
    item.agents = detectAgents(item);
    return item;
  }

  function parseXItem(li, section) {
    var text = textOf(li).replace(/\s+/g, " ").trim();
    var links = parseLinksFromEl(li);
    var title = links.length ? links[0].text : text.slice(0, 80);
    var takeaway = text;
    // Prefer text after the link / colon
    var colon = text.indexOf("):");
    if (colon > 0) takeaway = text.slice(colon + 2).trim();
    else {
      var c2 = text.indexOf("):");
      if (c2 < 0) {
        var m = text.match(/:\s*(.+)$/);
        if (m) takeaway = m[1];
      }
    }
    var body = document.createElement("div");
    body.className = "ai-card__full";
    body.appendChild(li.cloneNode(true));
    return {
      kind: "card",
      sectionId: section.id,
      sectionLabel: section.label,
      title: title,
      takeaway: firstSentence(takeaway),
      summary: takeaway,
      forYou: "",
      links: links,
      unconfirmed: isUnconfirmed(text),
      bodyEl: body,
    };
  }

  function parsePaperItem(p, section) {
    var card = parseCardFromParagraph(p, section);
    if (!card) return null;
    card.kind = "paper";
    return card;
  }

  function parseRepoItem(li, section) {
    var text = textOf(li).replace(/\s+/g, " ").trim();
    var links = parseLinksFromEl(li);
    var name = links.length ? links[0].text : text.split(",")[0];
    var rest = text;
    if (links.length) {
      var idx = text.indexOf(links[0].text);
      rest = text.slice(idx + links[0].text.length).replace(/^[\s,]+/, "");
    }
    var stars = "";
    var starMatch = rest.match(/\(([\d,]+)\s*(?:stars?\s*)?today/i) || rest.match(/\(([\d,]+)\s*today/i);
    if (starMatch) stars = starMatch[1];

    // one-liner: strip leading "an/a" description before paren stars
    var oneLiner = rest.replace(/\s*\([^)]*today[^)]*\)\.?\s*$/i, "").replace(/\s*\(still #[^)]*\)\.?\s*$/i, "").trim();
    if (oneLiner.charAt(oneLiner.length - 1) === ",") oneLiner = oneLiner.slice(0, -1);

    var body = document.createElement("div");
    body.className = "ai-card__full";
    body.appendChild(li.cloneNode(true));

    return {
      kind: "repo",
      sectionId: section.id,
      sectionLabel: section.label,
      title: name,
      takeaway: oneLiner,
      stars: stars,
      links: links,
      unconfirmed: false,
      bodyEl: body,
    };
  }

  function parseBody(root) {
    var biggest = "";
    var biggestEl = null;
    var sections = [];
    var current = null;
    var preamble = [];

    Array.prototype.forEach.call(root.children, function (el) {
      var tag = el.tagName;

      if (tag === "H1") {
        preamble.push(el);
        return;
      }

      if (tag === "P" && /biggest story today/i.test(textOf(el))) {
        biggestEl = el;
        var t = textOf(el).replace(/\s+/g, " ").trim();
        biggest = t.replace(/^.*biggest story today:\s*/i, "");
        return;
      }

      if (tag === "H2") {
        var chip = chipForHeading(textOf(el));
        current = {
          id: chip.id,
          label: chip.label,
          kind: chip.kind || "cards",
          headingText: chip.mergeHeading || textOf(el).trim(),
          headingEl: el,
          mergeHeading: chip.mergeHeading || null,
          items: [],
          extras: [],
        };
        sections.push(current);
        return;
      }

      if (!current) {
        preamble.push(el);
        return;
      }

      if (current.kind === "x" && (tag === "UL" || tag === "OL")) {
        Array.prototype.forEach.call(el.children, function (li) {
          if (li.tagName === "LI") current.items.push(parseXItem(li, current));
        });
        return;
      }

      if (current.kind === "repos" && (tag === "OL" || tag === "UL")) {
        Array.prototype.forEach.call(el.children, function (li) {
          if (li.tagName === "LI") current.items.push(parseRepoItem(li, current));
        });
        return;
      }

      if (current.kind === "repos" && tag === "P") {
        // intro line like "All ten are from today's…"
        current.extras.push(el);
        return;
      }

      if ((current.kind === "papers" || current.kind === "cards") && tag === "P") {
        var strong = el.querySelector(":scope > strong, strong");
        if (strong && textOf(el).trim().indexOf(textOf(strong).trim()) === 0) {
          var item =
            current.kind === "papers"
              ? parsePaperItem(el, current)
              : parseCardFromParagraph(el, current);
          if (item) {
            current.items.push(item);
            return;
          }
        }
        // Rumour check / misc paragraph → attach to previous card or extras
        if (current.items.length) {
          var last = current.items[current.items.length - 1];
          last.bodyEl.appendChild(el.cloneNode(true));
          if (isUnconfirmed(textOf(el))) last.unconfirmed = true;
          parseLinksFromEl(el).forEach(function (l) {
            last.links.push(l);
          });
        } else {
          current.extras.push(el);
        }
        return;
      }

      // Anything else stays in section extras (full fidelity)
      current.extras.push(el);
    });

    sections = mergeSectionsById(sections);
    return { biggest: biggest, biggestEl: biggestEl, sections: sections, preamble: preamble };
  }

  function mergeSectionsById(sections) {
    var order = [];
    var byId = {};
    sections.forEach(function (sec) {
      if (!byId[sec.id]) {
        byId[sec.id] = {
          id: sec.id,
          label: sec.label,
          kind: sec.kind,
          headingText: sec.mergeHeading || sec.label || sec.headingText,
          headingEl: sec.headingEl,
          items: [],
          extras: [],
          mergeHeading: sec.mergeHeading,
        };
        // Prefer canonical merge heading when chip defines one
        var chip = SECTION_CHIPS.filter(function (c) {
          return c.id === sec.id;
        })[0];
        if (chip && chip.mergeHeading) {
          byId[sec.id].headingText = chip.mergeHeading;
          byId[sec.id].label = chip.label;
        }
        order.push(sec.id);
      }
      var target = byId[sec.id];
      sec.items.forEach(function (it) {
        it.sectionId = target.id;
        it.sectionLabel = target.label;
        if (!it.agents || !it.agents.length) it.agents = detectAgents(it);
        target.items.push(it);
      });
      sec.extras.forEach(function (ex) {
        target.extras.push(ex);
      });
    });
    return order.map(function (id) {
      return byId[id];
    });
  }

  function sourceChips(links) {
    var seen = {};
    var domains = [];
    links.forEach(function (l) {
      if (!l.domain || seen[l.domain]) return;
      seen[l.domain] = true;
      domains.push(l.domain);
    });
    return domains.slice(0, 4);
  }

  function el(tag, className, html) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (html != null) node.innerHTML = html;
    return node;
  }

  function buildCard(item) {
    var details = el("details", "ai-card");
    details.setAttribute("data-section", item.sectionId);

    var summary = el("summary", "ai-card__summary");
    var titleRow = el("div", "ai-card__title-row");
    var title = el("span", "ai-card__title");
    title.textContent = item.title;
    titleRow.appendChild(title);
    summary.appendChild(titleRow);

    var takeaway = el("p", "ai-card__takeaway");
    takeaway.textContent = item.takeaway;
    summary.appendChild(takeaway);

    var meta = el("div", "ai-card__meta");
    if (item.sectionId === "coding-agents" && item.agents && item.agents.length) {
      item.agents.forEach(function (name) {
        var agentTag = el("span", "ai-tag ai-tag--agent");
        agentTag.textContent = name;
        meta.appendChild(agentTag);
      });
    } else {
      var tag = el("span", "ai-tag");
      tag.textContent = item.sectionLabel;
      meta.appendChild(tag);
    }
    if (item.unconfirmed) {
      var badge = el("span", "badge badge--unconfirmed");
      badge.textContent = "unconfirmed";
      meta.appendChild(badge);
    }
    sourceChips(item.links).forEach(function (domain) {
      var d = el("span", "ai-domain");
      d.textContent = domain;
      meta.appendChild(d);
    });
    summary.appendChild(meta);
    details.appendChild(summary);

    var body = el("div", "ai-card__body");
    // Full original block (summary, For you, links) — nothing dropped
    body.appendChild(item.bodyEl);
    details.appendChild(body);
    return details;
  }

  function buildDenseTable(items, kind) {
    var wrap = el("div", "ai-dense");
    var table = document.createElement("table");
    table.className = "ai-dense__table";
    var thead = document.createElement("thead");
    var hr = document.createElement("tr");
    if (kind === "repos") {
      ["Repo", "One-liner", "Stars"].forEach(function (h) {
        var th = document.createElement("th");
        th.textContent = h;
        hr.appendChild(th);
      });
    } else {
      ["Paper", "Takeaway", "Links"].forEach(function (h) {
        var th = document.createElement("th");
        th.textContent = h;
        hr.appendChild(th);
      });
    }
    thead.appendChild(hr);
    table.appendChild(thead);
    var tbody = document.createElement("tbody");

    items.forEach(function (item) {
      var tr = document.createElement("tr");
      tr.setAttribute("data-section", item.sectionId);

      var tdName = document.createElement("td");
      tdName.className = "ai-dense__name";
      if (item.links.length) {
        var a = document.createElement("a");
        a.href = item.links[0].href;
        a.textContent = item.title;
        a.rel = "noopener noreferrer";
        tdName.appendChild(a);
      } else {
        tdName.textContent = item.title;
      }
      tr.appendChild(tdName);

      var tdTake = document.createElement("td");
      tdTake.className = "ai-dense__takeaway";
      var details = el("details", "ai-dense__details");
      var sum = el("summary", "ai-dense__summary");
      sum.textContent = item.takeaway || "Details";
      details.appendChild(sum);
      var full = el("div", "ai-dense__full");
      full.appendChild(item.bodyEl);
      details.appendChild(full);
      tdTake.appendChild(details);
      tr.appendChild(tdTake);

      var tdMeta = document.createElement("td");
      tdMeta.className = "ai-dense__meta";
      if (kind === "repos") {
        tdMeta.textContent = item.stars ? item.stars : "—";
      } else {
        item.links.slice(0, 2).forEach(function (l, i) {
          if (i) tdMeta.appendChild(document.createTextNode(" · "));
          var a = document.createElement("a");
          a.href = l.href;
          a.textContent = l.domain || l.text;
          a.rel = "noopener noreferrer";
          tdMeta.appendChild(a);
        });
      }
      tr.appendChild(tdMeta);
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    return wrap;
  }

  function buildSkim(parsed) {
    var root = el("div", "ai-skim");

    // Today in 30 seconds
    var strip = el("section", "ai-30");
    strip.setAttribute("aria-label", "Today in 30 seconds");
    var stripLabel = el("p", "ai-30__label");
    stripLabel.textContent = "Today in 30 seconds";
    strip.appendChild(stripLabel);

    if (parsed.biggest) {
      var big = el("p", "ai-30__biggest");
      var bigLabel = el("strong", null);
      bigLabel.textContent = "Biggest story: ";
      big.appendChild(bigLabel);
      big.appendChild(document.createTextNode(parsed.biggest));
      strip.appendChild(big);
    }

    var topItems = [];
    parsed.sections.forEach(function (sec) {
      if (sec.kind === "x" || sec.kind === "papers" || sec.kind === "repos") return;
      sec.items.forEach(function (it) {
        if (topItems.length < 5) topItems.push(it);
      });
    });

    if (topItems.length) {
      var ol = el("ol", "ai-30__list");
      topItems.forEach(function (it) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = "#ai-section-" + it.sectionId;
        a.textContent = it.title;
        li.appendChild(a);
        if (it.takeaway) {
          li.appendChild(document.createTextNode(" — " + it.takeaway));
        }
        ol.appendChild(li);
      });
      strip.appendChild(ol);
    }
    root.appendChild(strip);

    // Filter chips
    var chips = el("nav", "ai-chips");
    chips.setAttribute("aria-label", "AI section filters");
    var allBtn = el("button", "ai-chip ai-chip--active");
    allBtn.type = "button";
    allBtn.textContent = "All";
    allBtn.setAttribute("data-filter", "all");
    chips.appendChild(allBtn);

    parsed.sections.forEach(function (sec) {
      if (!sec.items.length && !sec.extras.length) return;
      var btn = el("button", "ai-chip");
      btn.type = "button";
      btn.textContent = sec.label;
      btn.setAttribute("data-filter", sec.id);
      btn.setAttribute("data-jump", "ai-section-" + sec.id);
      chips.appendChild(btn);
    });
    root.appendChild(chips);

    // Sections
    parsed.sections.forEach(function (sec) {
      var section = el("section", "ai-section");
      section.id = "ai-section-" + sec.id;
      section.setAttribute("data-section", sec.id);

      var h = el("h2", "ai-section__title");
      h.textContent = sec.headingText;
      section.appendChild(h);

      sec.extras.forEach(function (extra) {
        section.appendChild(extra.cloneNode(true));
      });

      if (sec.kind === "papers" || sec.kind === "repos") {
        if (sec.items.length) section.appendChild(buildDenseTable(sec.items, sec.kind));
      } else {
        var list = el("div", "ai-card-list");
        sec.items.forEach(function (item) {
          list.appendChild(buildCard(item));
        });
        section.appendChild(list);
      }

      root.appendChild(section);
    });

    // Wire filters
    chips.addEventListener("click", function (e) {
      var btn = e.target.closest(".ai-chip");
      if (!btn) return;
      var filter = btn.getAttribute("data-filter");
      chips.querySelectorAll(".ai-chip").forEach(function (b) {
        b.classList.toggle("ai-chip--active", b === btn);
      });
      root.querySelectorAll(".ai-section").forEach(function (sec) {
        var id = sec.getAttribute("data-section");
        var show = filter === "all" || id === filter;
        sec.hidden = !show;
      });
      if (filter !== "all") {
        var jump = btn.getAttribute("data-jump");
        var target = jump && document.getElementById(jump);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });

    return root;
  }

  function enhance(panelOrBody) {
    var body = panelOrBody.matches && panelOrBody.matches("[data-ai-body]")
      ? panelOrBody
      : panelOrBody.querySelector("[data-ai-body]");
    if (!body || body.getAttribute("data-ai-skimmed") === "1") return;

    var toc = (panelOrBody.querySelector && panelOrBody.querySelector(".ai-toc")) || null;
    if (toc) toc.hidden = true;

    var parsed = parseBody(body);
    if (!parsed.sections.length) return;

    var skim = buildSkim(parsed);

    // Keep original for no-JS consumers already saw it; replace with skim UI
    var original = el("div", "ai-skim__original");
    original.hidden = true;
    while (body.firstChild) original.appendChild(body.firstChild);

    // Fallback toggle
    var fallback = el("p", "ai-skim__fallback");
    var fbBtn = document.createElement("button");
    fbBtn.type = "button";
    fbBtn.className = "ai-skim__fallback-btn";
    fbBtn.textContent = "View original Markdown layout";
    fbBtn.addEventListener("click", function () {
      var showing = !original.hidden;
      original.hidden = showing;
      skim.hidden = !showing;
      fbBtn.textContent = showing ? "View original Markdown layout" : "View skimmable layout";
    });
    fallback.appendChild(fbBtn);

    body.appendChild(skim);
    body.appendChild(fallback);
    body.appendChild(original);
    body.setAttribute("data-ai-skimmed", "1");
  }

  function run() {
    document.querySelectorAll("[data-ai-body]").forEach(function (body) {
      enhance(body);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
