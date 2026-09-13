/* Chart.js seeding for the leadership insights dashboard.
 * SSR-first: canvases carry data-* attrs; JSON payloads are embedded with
 * Django's json_script. If Chart.js fails to load, the page still works
 * (no-JS fallbacks in the templates).
 */
(function () {
  "use strict";

  if (!window.Chart) return;

  var BLUE = "#2f63e9";
  var GREEN = "#16a34a";
  var AMBER = "#f59e0b";
  var RED = "#dc2626";
  var SLATE_TXT = "#64748b";
  var SLATE_TRACK = "#e2e8f0";

  function payload(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function scoreColor(score) {
    if (score >= 80) return GREEN;
    if (score >= 60) return AMBER;
    return RED;
  }

  Chart.defaults.font.family =
    "Segoe UI, system-ui, -apple-system, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.color = SLATE_TXT;

  /* ----- Readiness doughnut gauge (with threshold tick) ----- */
  var gauge = document.getElementById("readiness-gauge");
  if (gauge && gauge.dataset.score) {
    var gaugeSize = 92;
    gauge.width = gaugeSize;
    gauge.height = gaugeSize;
    var score = parseInt(gauge.dataset.score, 10);
    var threshold = parseInt(gauge.dataset.threshold || "60", 10);

    var thresholdLine = {
      id: "thresholdLine",
      afterDraw: function (chart, _args, opts) {
        var angle = Math.PI / 2 + (opts.threshold / 100) * Math.PI * 2;
        var meta = chart.getDatasetMeta(0);
        if (!meta.data.length) return;
        var el = meta.data[0];
        var r1 = el.innerRadius * 0.85;
        var r2 = el.outerRadius * 1.05;
        var cx = el.x;
        var cy = el.y;
        var ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = "#7c3aed";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(angle) * r1, cy + Math.sin(angle) * r1);
        ctx.lineTo(cx + Math.cos(angle) * r2, cy + Math.sin(angle) * r2);
        ctx.stroke();
        ctx.restore();
      },
    };

    new Chart(gauge, {
      type: "doughnut",
      data: {
        datasets: [
          {
            data: [score, 100 - score],
            backgroundColor: [scoreColor(score), SLATE_TRACK],
            borderWidth: 0,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        cutout: "78%",
        plugins: {
          thresholdLine: { threshold: threshold },
          legend: { display: false },
          tooltip: {
            enabled: true,
            callbacks: {
              label: function (ctx) {
                return ctx.dataIndex === 0 ? "Readiness " + score + "/100" : "";
              },
            },
          },
        },
      },
      plugins: [thresholdLine],
    });
  }

  /* ----- Readiness trend line ----- */
  var trend = document.getElementById("trend-chart");
  var trendData = payload("trend-chart-data");
  if (trend && trendData && trendData.length) {
    new Chart(trend, {
      type: "line",
      data: {
        labels: trendData.map(function (p) {
          return p.label;
        }),
        datasets: [
          {
            data: trendData.map(function (p) {
              return p.score;
            }),
            borderColor: BLUE,
            backgroundColor: "rgba(47, 99, 233, 0.12)",
            fill: true,
            tension: 0.3,
            pointBackgroundColor: trendData.map(function (p) {
              return p.delta == null
                ? BLUE
                : p.delta > 0
                  ? GREEN
                  : p.delta < 0
                    ? RED
                    : SLATE_TXT;
            }),
            pointRadius: 4,
            pointHoverRadius: 5,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: function (ctx) {
                var p = trendData[ctx.dataIndex];
                if (p.delta == null) return "";
                var sign = p.delta > 0 ? "+" : "";
                return "Δ " + sign + p.delta + " vs previous";
              },
            },
          },
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: { stepSize: 20 },
            grid: { color: SLATE_TRACK },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }

  /* ----- Risk matrix: vertical criticality bars ----- */
  var risk = document.getElementById("risk-chart");
  var riskData = payload("risk-chart-data");
  if (risk && riskData && riskData.length) {
    new Chart(risk, {
      type: "bar",
      data: {
        labels: riskData.map(function (r) {
          return r.skill;
        }),
        datasets: [
          {
            data: riskData.map(function (r) {
              return r.score;
            }),
            backgroundColor: riskData.map(function (r) {
              return scoreColor(r.score);
            }),
            borderWidth: 0,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var r = riskData[ctx.dataIndex];
                return "criticality " + r.score + " · " + r.holders + " holder(s)";
              },
            },
          },
        },
        scales: {
          x: {
            min: 0,
            max: 100,
            grid: { color: SLATE_TRACK },
          },
          y: { grid: { display: false } },
        },
      },
    });
  }

  /* ----- Departure what-if: coverage before/after ----- */
  var departure = document.getElementById("departure-chart");
  var depData = payload("departure-chart-data");
  if (departure && depData && depData.length) {
    new Chart(departure, {
      type: "bar",
      data: {
        labels: depData.map(function (d) {
          return d.skill;
        }),
        datasets: [
          {
            label: "Coverage now",
            data: depData.map(function (d) {
              return d.before;
            }),
            backgroundColor: BLUE,
          },
          {
            label: "After departure",
            data: depData.map(function (d) {
              return d.after;
            }),
            backgroundColor: RED,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", align: "end" },
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: { callback: function (v) { return v + "%"; } },
            grid: { color: SLATE_TRACK },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }
/* ----- Readiness by department: radar ----- */
  var radar = document.getElementById("radar-chart");
  var radarData = payload("radar-chart-data");
  if (radar && radarData && radarData.length > 1) {
    new Chart(radar, {
      type: "radar",
      data: {
        labels: radarData.map(function (r) {
          return r.department;
        }),
        datasets: [
          {
            label: "Readiness",
            data: radarData.map(function (r) {
              return r.score;
            }),
            borderColor: BLUE,
            backgroundColor: "rgba(47, 99, 233, 0.18)",
            pointBackgroundColor: radarData.map(function (r) {
              return scoreColor(r.score);
            }),
            pointRadius: 3,
            pointHoverRadius: 4,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { stepSize: 20 },
            grid: { color: SLATE_TRACK },
            angleLines: { color: SLATE_TRACK },
            pointLabels: { color: SLATE_TXT, font: { size: 11 } },
          },
        },
      },
    });
  }

  /* ----- Talent depth by category: stacked horizontal bars ----- */
  var level = document.getElementById("level-chart");
  var levelData = payload("level-chart-data");
  if (level && levelData && levelData.total > 0) {
    var LEVEL_COLORS = ["#94a3b8", "#60a5fa", "#3b82f6", "#6366f1", "#8b5cf6"];
    new Chart(level, {
      type: "bar",
      data: {
        labels: levelData.categories,
        datasets: levelData.datasets.map(function (ds, i) {
          return {
            label: ds.label,
            data: ds.data,
            backgroundColor: LEVEL_COLORS[i % LEVEL_COLORS.length],
          };
        }),
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "top", align: "end" } },
        scales: {
          x: {
            stacked: true,
            grid: { color: SLATE_TRACK },
            ticks: { precision: 0 },
          },
          y: { stacked: true, grid: { display: false } },
        },
      },
    });
  }
})();