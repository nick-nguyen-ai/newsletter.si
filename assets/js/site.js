(function () {
  "use strict";

  function markUnconfirmed(root) {
    if (!root) return;

    // **Unconfirmed** → muted badge
    root.querySelectorAll("strong").forEach(function (el) {
      var text = (el.textContent || "").trim();
      if (/^unconfirmed$/i.test(text)) {
        el.classList.add("badge", "badge--unconfirmed");
      }
    });

    // (unconfirmed) / [unconfirmed] in text → muted badge (keep links intact)
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(function (node) {
      var value = node.nodeValue;
      if (!value || !/[\[(]unconfirmed[\])]/i.test(value)) return;

      var span = document.createElement("span");
      span.innerHTML = value.replace(
        /[\[(]unconfirmed[\])]/gi,
        '<span class="badge badge--unconfirmed">unconfirmed</span>'
      );
      var parent = node.parentNode;
      while (span.firstChild) {
        parent.insertBefore(span.firstChild, node);
      }
      parent.removeChild(node);
    });
  }

  function buildAiToc() {
    document.querySelectorAll("[data-ai-toc]").forEach(function (list) {
      var panel = list.closest("#ai") || list.closest(".day-panel");
      if (!panel) return;
      var body = panel.querySelector("[data-ai-body]");
      if (!body) return;

      list.innerHTML = "";
      body.querySelectorAll("h2").forEach(function (heading) {
        if (!heading.id) {
          heading.id = heading.textContent
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-|-$/g, "");
        }
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = "#" + heading.id;
        a.textContent = heading.textContent;
        li.appendChild(a);
        list.appendChild(li);
      });

      if (!list.children.length) {
        var toc = list.closest(".ai-toc");
        if (toc) toc.hidden = true;
      }
    });
  }

  document.querySelectorAll(".issue-body").forEach(markUnconfirmed);
  buildAiToc();
})();
