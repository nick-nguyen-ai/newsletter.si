(function () {
  "use strict";

  if (typeof Chart === "undefined") return;

  var MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  var WEEKLY_THRESHOLD = 200; // downsample when more points than this

  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  function theme() {
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return {
      dark: dark,
      text: cssVar("--text-muted", dark ? "#a3a3a3" : "#5c5c5c"),
      grid: cssVar("--border", dark ? "#2e2e2e" : "#e6e4df"),
      accent: cssVar("--accent", dark ? "#5cb8b8" : "#0d6e6e"),
      accentFill: dark ? "rgba(92, 184, 184, 0.12)" : "rgba(13, 110, 110, 0.10)",
      marker: dark ? "#c4a882" : "#8a6a4a",
      band: dark ? "rgba(92, 184, 184, 0.08)" : "rgba(13, 110, 110, 0.06)",
      bandAlt: dark ? "rgba(196, 168, 130, 0.10)" : "rgba(138, 106, 74, 0.07)",
    };
  }

  function parseDate(s) {
    if (!s) return null;
    var p = String(s).split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }

  function fmtDate(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  function addMonths(d, n) {
    var x = new Date(d.getTime());
    x.setMonth(x.getMonth() + n);
    return x;
  }

  function lastNonNull(values, labels) {
    for (var i = values.length - 1; i >= 0; i--) {
      if (values[i] != null && !isNaN(values[i])) return { value: values[i], date: labels[i], index: i };
    }
    return null;
  }

  function valueOnOrBefore(labels, values, targetDate) {
    var target = fmtDate(targetDate);
    var best = null;
    for (var i = 0; i < labels.length; i++) {
      if (labels[i] <= target && values[i] != null && !isNaN(values[i])) {
        best = { value: values[i], date: labels[i] };
      }
      if (labels[i] > target) break;
    }
    return best;
  }

  function downsampleWeekly(labels, values) {
    if (labels.length <= WEEKLY_THRESHOLD) return { labels: labels, values: values };
    var outL = [];
    var outV = [];
    var bucket = null;
    var lastL = null;
    var lastV = null;
    function flush() {
      if (lastL != null) {
        outL.push(lastL);
        outV.push(lastV);
      }
      lastL = null;
      lastV = null;
    }
    for (var i = 0; i < labels.length; i++) {
      var d = parseDate(labels[i]);
      // ISO week-ish: year + week number via Thursday trick
      var t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
      t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
      var yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
      var week = Math.ceil(((t - yearStart) / 86400000 + 1) / 7);
      var key = t.getUTCFullYear() + "-W" + week;
      if (bucket !== null && key !== bucket) flush();
      bucket = key;
      if (values[i] != null && !isNaN(values[i])) {
        lastL = labels[i];
        lastV = values[i];
      } else if (lastL == null) {
        lastL = labels[i];
        lastV = null;
      }
    }
    flush();
    return { labels: outL, values: outV };
  }

  function sliceRange(labels, values, range, warStart) {
    if (!labels.length) return { labels: labels, values: values };
    var latest = parseDate(labels[labels.length - 1]);
    var start = null;
    if (range === "1M") start = addMonths(latest, -1);
    else if (range === "6M") start = addMonths(latest, -6);
    else if (range === "1Y") start = addMonths(latest, -12);
    else if (range === "war") start = parseDate(warStart || "2026-02-28");
    else start = parseDate("2020-01-01"); // 2020-now

    var startStr = fmtDate(start);
    var sL = [];
    var sV = [];
    for (var i = 0; i < labels.length; i++) {
      if (labels[i] < startStr) continue;
      sL.push(labels[i]);
      sV.push(values[i]);
    }
    return downsampleWeekly(sL, sV);
  }

  function xPosForDate(chart, labels, dateStr) {
    var meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data || !meta.data.length) return null;
    var idx = -1;
    for (var i = 0; i < labels.length; i++) {
      if (labels[i] >= dateStr) {
        idx = i;
        break;
      }
    }
    if (idx < 0) idx = labels.length - 1;
    var pt = meta.data[idx];
    return pt ? pt.x : null;
  }

  function erasPlugin(payload, colors) {
    return {
      id: "erasOverlay",
      afterDraw: function (chart) {
        var labels = chart.data.labels || [];
        if (!labels.length) return;
        var area = chart.chartArea;
        var ctx = chart.ctx;
        var bands = payload.bands || [];
        var markers = payload.markers || [];

        ctx.save();

        bands.forEach(function (band, bi) {
          var x0 = xPosForDate(chart, labels, band.start);
          var end = band.end || labels[labels.length - 1];
          var x1 = xPosForDate(chart, labels, end);
          if (x0 == null || x1 == null) return;
          if (x1 < area.left || x0 > area.right) return;
          x0 = Math.max(x0, area.left);
          x1 = Math.min(x1, area.right);
          ctx.fillStyle = bi % 2 === 0 ? colors.band : colors.bandAlt;
          ctx.fillRect(x0, area.top, Math.max(1, x1 - x0), area.bottom - area.top);
          ctx.fillStyle = colors.text;
          ctx.font = '600 9px "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif';
          ctx.textAlign = "left";
          var labelX = x0 + 4;
          if (labelX + 40 < area.right) {
            ctx.fillText(band.label || "", labelX, area.bottom - 6);
          }
        });

        markers.forEach(function (m) {
          var x = xPosForDate(chart, labels, m.date);
          if (x == null || x < area.left || x > area.right) return;
          ctx.beginPath();
          ctx.setLineDash([3, 3]);
          ctx.strokeStyle = colors.marker;
          ctx.lineWidth = 1;
          ctx.moveTo(x, area.top);
          ctx.lineTo(x, area.bottom);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = colors.marker;
          ctx.font = '600 9px "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif';
          ctx.textAlign = "left";
          var tx = x + 3;
          if (tx > area.right - 36) {
            ctx.textAlign = "right";
            tx = x - 3;
          }
          ctx.fillText(m.label || "", tx, area.top + 11);
        });

        ctx.restore();
      },
    };
  }

  function parsePayload(el) {
    var raw = el.getAttribute("data-chart");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      console.warn("chart: bad JSON", e);
      return null;
    }
  }

  function formatNum(n, unit) {
    if (n == null || isNaN(n)) return "—";
    var s = Math.abs(n) >= 1000 ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : n.toFixed(2);
    return s + (unit ? " " + unit : "");
  }

  function updateStats(figure, fullLabels, fullValues, unit) {
    var statsEl = figure.querySelector("[data-chart-stats]");
    if (!statsEl) return;
    var latest = lastNonNull(fullValues, fullLabels);
    if (!latest) {
      statsEl.textContent = "";
      return;
    }
    var yoYDate = addMonths(parseDate(latest.date), -12);
    var yoY = valueOnOrBefore(fullLabels, fullValues, yoYDate);
    var html = '<span class="chart__stat-latest"><strong>' + formatNum(latest.value, unit) + "</strong></span>";
    if (yoY && yoY.value) {
      var chg = latest.value - yoY.value;
      var pct = (chg / yoY.value) * 100;
      var cls = chg >= 0 ? "chart__stat-up" : "chart__stat-down";
      var sign = chg >= 0 ? "+" : "";
      html +=
        ' <span class="chart__stat-yoy ' +
        cls +
        '">' +
        sign +
        formatNum(chg, unit) +
        " (" +
        sign +
        pct.toFixed(1) +
        "%) vs a year ago</span>";
    } else {
      html += ' <span class="chart__stat-yoy">YoY n/a</span>';
    }
    statsEl.innerHTML = html;
  }

  function isNarrow() {
    return window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
  }

  function buildChart(canvas, payload, colors, view) {
    var type = payload.type || "line";
    var labels = view.labels;
    var values = view.values;
    var narrow = isNarrow();
    var tickSize = narrow ? 11 : 10;

    var dataset = {
      label: payload.label || "",
      data: values,
      borderColor: colors.accent,
      backgroundColor: colors.accentFill,
      borderWidth: 1.5,
      pointRadius: 0,
      pointHoverRadius: narrow ? 5 : 3,
      pointHitRadius: narrow ? 18 : 8,
      tension: 0.15,
      spanGaps: false,
      fill: type === "line",
    };

    return new Chart(canvas.getContext("2d"), {
      type: type,
      data: { labels: labels, datasets: [dataset] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        layout: {
          padding: { top: 4, right: narrow ? 4 : 8, bottom: 0, left: 0 },
        },
        interaction: { mode: "nearest", intersect: false, axis: "x" },
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: true,
            displayColors: false,
            padding: narrow ? 10 : 8,
            titleFont: { size: narrow ? 13 : 12, weight: "600" },
            bodyFont: { size: narrow ? 13 : 12 },
            caretSize: 6,
            caretPadding: 8,
            callbacks: {
              title: function (items) {
                if (!items.length) return "";
                var label = items[0].label || "";
                if (/^\d{4}-\d{2}-\d{2}$/.test(label)) {
                  var p = label.split("-");
                  return MONTHS[+p[1] - 1] + " " + (+p[2]) + ", " + p[0];
                }
                return label;
              },
              label: function (ctx) {
                var v = ctx.parsed.y;
                if (v === null || v === undefined) return (ctx.dataset.label || "") + ": —";
                var unit = payload.unit ? " " + payload.unit : "";
                return (ctx.dataset.label ? ctx.dataset.label + ": " : "") + v + unit;
              },
            },
          },
        },
        scales: {
          x: {
            ticks: {
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: narrow ? 4 : 6,
              color: colors.text,
              font: { size: tickSize },
              callback: function (val) {
                var label = this.getLabelForValue(val);
                if (/^\d{4}-\d{2}-\d{2}$/.test(label)) {
                  var parts = label.split("-");
                  return MONTHS[+parts[1] - 1] + " " + parts[0].slice(2);
                }
                return label;
              },
            },
            grid: { color: colors.grid, drawBorder: false },
          },
          y: {
            ticks: {
              color: colors.text,
              font: { size: tickSize },
              maxTicksLimit: narrow ? 5 : 8,
              padding: 4,
            },
            grid: { color: colors.grid, drawBorder: false },
            title: payload.y_label
              ? {
                  display: !narrow,
                  text: payload.y_label,
                  color: colors.text,
                  font: { size: 10, weight: "600" },
                }
              : undefined,
          },
        },
      },
      plugins: [erasPlugin(payload, colors)],
    });
  }

  function mountFigure(figure, colors) {
    var canvas = figure.querySelector("canvas[data-chart]");
    if (!canvas) return null;
    var payload = parsePayload(canvas);
    if (!payload) return null;

    var fullLabels = payload.labels || [];
    var fullValues = (payload.values || []).map(function (v) {
      if (v === null || v === undefined || v === "") return null;
      var n = Number(v);
      return isNaN(n) ? null : n;
    });

    updateStats(figure, fullLabels, fullValues, payload.unit);

    var state = { chart: null, range: "2020" };

    function redraw(range) {
      state.range = range || state.range;
      var view = sliceRange(fullLabels, fullValues, state.range, payload.war_start);
      if (state.chart) state.chart.destroy();
      // eras overlay uses sliced labels — markers outside range simply won't draw
      var viewPayload = Object.assign({}, payload, { labels: view.labels, values: view.values });
      state.chart = buildChart(canvas, viewPayload, colors, view);
    }

    var ranges = figure.querySelector("[data-chart-ranges]");
    if (ranges) {
      ranges.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-range]");
        if (!btn) return;
        ranges.querySelectorAll(".chart__range").forEach(function (b) {
          b.classList.toggle("chart__range--active", b === btn);
        });
        redraw(btn.getAttribute("data-range"));
      });
    }

    redraw("2020");
    return state;
  }

  var mounted = [];

  function mountAll() {
    mounted.forEach(function (s) {
      if (s && s.chart) s.chart.destroy();
    });
    mounted = [];
    var colors = theme();
    document.querySelectorAll("figure.chart").forEach(function (figure) {
      var s = mountFigure(figure, colors);
      if (s) mounted.push(s);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountAll);
  } else {
    mountAll();
  }

  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", mountAll);
  }

  // Markets Morning/Close tabs: charts in a newly shown panel measured 0×0 while
  // hidden — resize (or remount) when the tab becomes visible.
  window.addEventListener("mk-tab-shown", function (ev) {
    var panel = ev && ev.detail && ev.detail.panel;
    if (!panel) return;
    panel.querySelectorAll("figure.chart").forEach(function (figure) {
      var canvas = figure.querySelector("canvas[data-chart]");
      if (!canvas) return;
      var existing = null;
      try {
        if (typeof Chart !== "undefined" && Chart.getChart) {
          existing = Chart.getChart(canvas);
        }
      } catch (e) {
        existing = null;
      }
      if (existing) {
        existing.resize();
        return;
      }
      var colors = theme();
      var s = mountFigure(figure, colors);
      if (s) mounted.push(s);
    });
  });
})();
