(function () {
  "use strict";

  var header = document.querySelector(".site-header");
  if (!header) return;

  var lastY = window.scrollY || 0;
  var ticking = false;
  var delta = 0;
  var HIDE_AFTER = 12;
  var SHOW_AFTER = 8;

  function setOffset() {
    var hidden = header.classList.contains("site-header--hidden");
    var h = hidden ? 0 : header.offsetHeight;
    document.documentElement.style.setProperty("--header-offset", h + "px");
  }

  function onScroll() {
    var y = window.scrollY || 0;
    var diff = y - lastY;
    delta += diff;

    if (y <= 8) {
      header.classList.remove("site-header--hidden");
      delta = 0;
    } else if (diff > 0 && delta > HIDE_AFTER && y > header.offsetHeight) {
      header.classList.add("site-header--hidden");
      delta = 0;
    } else if (diff < 0 && delta < -SHOW_AFTER) {
      header.classList.remove("site-header--hidden");
      delta = 0;
    }

    if ((diff > 0 && delta > 0) || (diff < 0 && delta < 0)) {
      /* keep accumulating in same direction */
    } else if (Math.sign(diff) !== Math.sign(delta) && diff !== 0) {
      delta = diff;
    }

    lastY = y;
    setOffset();
    ticking = false;
  }

  window.addEventListener(
    "scroll",
    function () {
      if (!ticking) {
        window.requestAnimationFrame(onScroll);
        ticking = true;
      }
    },
    { passive: true }
  );

  window.addEventListener("resize", setOffset, { passive: true });
  setOffset();
})();
