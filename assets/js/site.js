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

  document.querySelectorAll(".issue-body").forEach(markUnconfirmed);
})();
