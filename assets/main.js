const charts = [
  "hero-waffle",
  "media-horizon",
  "streaming-fta-connected",
  "age-media-heatmap",
  "age-parallel-profile",
  "video-hours-bullet",
  "video-service-bump",
  "device-slope",
  "audio-age-heatmap",
  "audio-location-network",
  "news-age",
  "metro-regional",
  "adii-choropleth",
  "adii-cartogram",
  "radio-symbol-map",
  "radio-dot-map",
];

const embedOptions = {
  actions: { export: true, source: true, compiled: false, editor: false },
  renderer: "svg",
  tooltip: { theme: "light" },
  downloadFileName: "different-feeds-chart",
};

const chartViews = new Map();
const chartSpecifications = new Map();

function refreshChartLayout(element) {
  if (element.dataset.status !== "ready") return;
  if (element.dataset.compact === String(element.clientWidth < 560)) return;
  delete element.dataset.rendered;
  renderChart(element);
}

const chartResizeObserver = typeof ResizeObserver === "function"
  ? new ResizeObserver((entries) => entries.forEach(({ target }) => refreshChartLayout(target)))
  : null;

async function renderChart(element) {
  if (element.dataset.rendered) return;
  element.dataset.rendered = "true";
  element.dataset.status = "loading";
  element.innerHTML = '<span class="chart-loading">Loading interactive chart…</span>';
  try {
    if (!chartSpecifications.has(element.id)) {
      const response = await fetch(`specs/${element.id}.json`);
      if (!response.ok) throw new Error(`Specification returned ${response.status}`);
      chartSpecifications.set(element.id, await response.json());
    }
    const specification = structuredClone(chartSpecifications.get(element.id));
    const previousView = chartViews.get(element.id);
    if (previousView) {
      for (const parameter of specification.params || []) {
        parameter.value = previousView.signal(parameter.name);
      }
      previousView.finalize();
      chartViews.delete(element.id);
    }
    element.replaceChildren();
    if (specification.params?.some((parameter) => parameter.name === "stateFocus")) {
      specification.params.find((parameter) => parameter.name === "stateFocus").value =
        document.getElementById("state-focus").value;
    }
    const compactLayout = element.clientWidth < 560;
    element.dataset.compact = String(compactLayout);
    if (compactLayout) {
      specification.config.axis.labelFontSize = 10;
      specification.config.axis.titleFontSize = 10;
      specification.config.legend.labelFontSize = 10;
      specification.config.legend.titleFontSize = 10;
      const compact = (node) => {
        if (!node || typeof node !== "object") return;
        if (node.legend && typeof node.legend === "object") {
          if (node.legend.columns) node.legend.columns = 2;
        }
        if (node.encoding?.x?.field === "age" && node.encoding.x.axis) {
          node.encoding.x.axis.labelAngle = -45;
        }
        if (node.field === "label" && node.axis) node.axis.labelLimit = 125;
        if (node.mark?.type === "text" && node.name !== "callout_text") node.mark.fontSize = 10;
        Object.values(node).forEach(compact);
      };
      compact(specification);
      if (element.id === "news-age") {
        specification.encoding.x.axis.title = "Six-month reach (%)";
      }
      if (element.id === "device-slope") {
        specification.layer.forEach((layer) => {
          if (layer.name === "callout_text") return;
          layer.encoding.x = {
            field: "year", type: "quantitative",
            scale: { domain: [2020, 2029], nice: false },
            axis: { title: null, values: [2021, 2025], format: "d", grid: false },
          };
        });
      }
      if (element.id === "audio-location-network") {
        specification.layer[2].data.values.forEach((row) => {
          row.short_name = row.name === "Music streaming" ? "Streaming" : row.name;
        });
        specification.layer[2].encoding.text = { field: "short_name" };
        specification.layer[2].mark.align = "left";
        specification.layer[2].mark.dx = -65;
        specification.layer[0].encoding.x.scale.domain = [-0.15, 1.05];
      }
    }
    const result = await vegaEmbed(element, specification, embedOptions);
    chartViews.set(element.id, result.view);
    element.dataset.status = "ready";
    refreshChartLayout(element);
  } catch (error) {
    element.dataset.status = "error";
    element.replaceChildren();
    const message = document.createElement("p");
    message.className = "chart-error";
    message.textContent = "This chart could not load. Check your connection and open the page through a local web server or GitHub Pages. ";
    const retry = document.createElement("button");
    retry.textContent = "Retry chart";
    retry.addEventListener("click", () => {
      delete element.dataset.rendered;
      renderChart(element);
    });
    message.append(retry);
    element.append(message);
    console.error(`Chart ${element.id}:`, error);
  }
}

function initialiseCharts() {
  const elements = charts.map((id) => document.getElementById(id)).filter(Boolean);
  elements.forEach((element) => chartResizeObserver?.observe(element));
  if (!("IntersectionObserver" in window)) {
    elements.forEach(renderChart);
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        renderChart(entry.target);
        observer.unobserve(entry.target);
      });
    },
    { rootMargin: "700px 0px" },
  );
  elements.forEach((element) => observer.observe(element));
}

function initialiseReveals() {
  const elements = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window)) {
    elements.forEach((element) => element.classList.add("is-visible"));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.08 },
  );
  elements.forEach((element) => observer.observe(element));
}

function updateReadingProgress() {
  const documentHeight = document.documentElement.scrollHeight - window.innerHeight;
  const progress = documentHeight > 0 ? (window.scrollY / documentHeight) * 100 : 0;
  document.querySelector(".reading-progress span").style.width = `${Math.min(100, progress)}%`;
}

window.addEventListener("DOMContentLoaded", async () => {
  await document.fonts.ready;
  initialiseCharts();
  initialiseReveals();
  updateReadingProgress();
  document.getElementById("state-focus").addEventListener("change", (event) => {
    for (const [name, view] of chartViews) {
      if (name.startsWith("adii-") || name.startsWith("radio-")) {
        view.signal("stateFocus", event.target.value).runAsync();
      }
    }
  });
});
window.addEventListener("scroll", updateReadingProgress, { passive: true });
