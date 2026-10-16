(function () {
  "use strict";

  if (typeof Chart === "undefined") return;

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
      accentFill: dark ? "rgba(92, 184, 184, 0.15)" : "rgba(13, 110, 110, 0.12)",
      marker: dark ? "#c4a882" : "#8a6a4a",
    };
  }

  function warLinePlugin(markerDate, markerLabel, colors) {
    return {
      id: "warMarker",
      afterDraw: function (chart) {
        if (!markerDate) return;
        var xScale = chart.scales.x;
        var meta = chart.getDatasetMeta(0);
        if (!meta || !meta.data || !meta.data.length) return;

        var labels = chart.data.labels || [];
        var idx = -1;
        for (var i = 0; i < labels.length; i++) {
          if (labels[i] >= markerDate) {
            idx = i;
            break;
          }
        }
        if (idx < 0) return;

        var pt = meta.data[idx];
        if (!pt) return;
        var x = pt.x;
        var ctx = chart.ctx;
        var top = chart.chartArea.top;
        var bottom = chart.chartArea.bottom;

        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = colors.marker;
        ctx.lineWidth = 1;
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = colors.marker;
        ctx.font = '600 10px "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif';
        ctx.textAlign = "left";
        ctx.fillText(markerLabel || "War begins", x + 4, top + 12);
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

  function buildChart(canvas, payload, colors) {
    var type = payload.type || "line";
    var labels = payload.labels || [];
    var values = (payload.values || []).map(function (v) {
      if (v === null || v === undefined || v === "") return null;
      var n = Number(v);
      return isNaN(n) ? null : n;
    });

    var datasets = payload.datasets || [
      {
        label: payload.label || "",
        data: values,
        borderColor: colors.accent,
        backgroundColor: type === "bar" ? colors.accentFill : colors.accentFill,
        borderWidth: type === "bar" ? 0 : 1.75,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.15,
        spanGaps: false,
        fill: type === "line",
      },
    ];

    if (payload.datasets) {
      datasets = payload.datasets.map(function (ds, i) {
        return Object.assign(
          {
            borderColor: colors.accent,
            backgroundColor: colors.accentFill,
            borderWidth: type === "bar" ? 0 : 1.75,
            pointRadius: 0,
            tension: 0.15,
            spanGaps: false,
            fill: type === "line" && i === 0,
          },
          ds
        );
      });
    }

    var plugins = [];
    if (payload.marker_date) {
      plugins.push(warLinePlugin(payload.marker_date, payload.marker_label, colors));
    }

    return new Chart(canvas.getContext("2d"), {
      type: type,
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: !!(payload.legend || (payload.datasets && payload.datasets.length > 1)) },
          tooltip: {
            callbacks: {
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
              maxTicksLimit: 6,
              color: colors.text,
              font: { size: 10 },
              callback: function (val, i) {
                var label = this.getLabelForValue(val);
                // Show as d Mon or YYYY-MM
                if (/^\d{4}-\d{2}-\d{2}$/.test(label)) {
                  var parts = label.split("-");
                  return parts[2] + " " + ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][+parts[1]-1];
                }
                return label;
              },
            },
            grid: { color: colors.grid, drawBorder: false },
          },
          y: {
            ticks: { color: colors.text, font: { size: 10 } },
            grid: { color: colors.grid, drawBorder: false },
            title: payload.y_label
              ? { display: true, text: payload.y_label, color: colors.text, font: { size: 10, weight: "600" } }
              : undefined,
          },
        },
      },
      plugins: plugins,
    });
  }

  var charts = [];

  function mountAll() {
    charts.forEach(function (c) { c.destroy(); });
    charts = [];
    var colors = theme();
    document.querySelectorAll("canvas[data-chart]").forEach(function (canvas) {
      var payload = parsePayload(canvas);
      if (!payload) return;
      charts.push(buildChart(canvas, payload, colors));
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
})();
