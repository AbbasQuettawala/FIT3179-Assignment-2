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

const palettes = {
  ocean: {
    colours: {
      ink: "#172a3a", paper: "#f4f7fb", "paper-deep": "#e6edf4",
      primary: "#235b87", "primary-light": "#9ac8e2", accent: "#a84b14",
      "accent-light": "#efb779", highlight: "#e7b864", muted: "#526476",
      comparison: "#007b80", low: "#edf3fa", neutral: "#dce4ec", slate: "#68798b",
    },
    growth: ["#c6dcec", "#88b4d3", "#4784b1", "#174d77"],
    fall: ["#843a13", "#b86527", "#dda065", "#f3d7b5"],
  },
  editorial: {
    colours: {
      ink: "#262a31", paper: "#faf6ef", "paper-deep": "#efe8de",
      primary: "#3e5266", "primary-light": "#b1c6d6", accent: "#ab4036",
      "accent-light": "#f0a499", highlight: "#dba86d", muted: "#69615b",
      comparison: "#277b7c", low: "#eef1f4", neutral: "#dfe2e5", slate: "#74787d",
    },
    growth: ["#d1dce6", "#a1b4c7", "#6c87a1", "#374f67"],
    fall: ["#87382f", "#bb594c", "#df998d", "#f4d2c8"],
  },
  plum: {
    colours: {
      ink: "#302339", paper: "#f8f4fa", "paper-deep": "#ede5f0",
      primary: "#704681", "primary-light": "#ceb2dc", accent: "#925908",
      "accent-light": "#efc779", highlight: "#d7ae55", muted: "#6b5d72",
      comparison: "#286e85", low: "#f2edf5", neutral: "#e4dce8", slate: "#817287",
    },
    growth: ["#dfd0e8", "#bc9ccf", "#9672ad", "#623b78"],
    fall: ["#79500c", "#a87922", "#d2ac5f", "#f0dfb3"],
  },
  original: {
    colours: {
      ink: "#10231f", paper: "#f7f3e8", "paper-deep": "#eee8d8",
      primary: "#1f6f5b", "primary-light": "#84cdb2", accent: "#d94d72",
      "accent-light": "#f2a5b9", highlight: "#e5c45b", muted: "#596964",
      comparison: "#5279be", low: "#edf5ef", neutral: "#dfe7df", slate: "#63736f",
    },
    growth: ["#bcd8ca", "#79ad99", "#40856f", "#155641"],
    fall: ["#942c4d", "#b44062", "#d9859e", "#f0c3d0"],
  },
};
let activePalette = "ocean";

function colourChart(specification) {
  if (activePalette === "original") return specification;
  const palette = palettes[activePalette];
  const colours = palette.colours;
  const replacements = {
    "#10231f": colours.ink, "#f7f3e8": colours.paper,
    "#1f6f5b": colours.primary, "#84cdb2": colours["primary-light"],
    "#d94d72": colours.accent, "#5279be": colours.comparison,
    "#63736f": colours.slate, "#edf5ef": colours.low, "#eef1ec": colours.low,
    "#dfe7df": colours.neutral, "#d8ded8": colours.neutral,
    "#d9ded8": colours.neutral, "#a8b3ad": colours.slate,
    "#bbc9bf": colours.neutral, "#e5ebe5": colours.neutral,
    "#b9c7be": colours.slate,
  };
  for (const direction of ["growth", "fall"]) {
    palettes.original[direction].forEach((colour, index) => {
      replacements[colour] = palette[direction][index];
    });
  }
  const recolour = (value) => {
    if (typeof value === "string") return replacements[value] ?? value;
    if (Array.isArray(value)) return value.map(recolour);
    if (value && typeof value === "object") {
      return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, recolour(child)]));
    }
    return value;
  };
  return recolour(specification);
}

function setPalette(name) {
  if (!Object.hasOwn(palettes, name)) return;
  activePalette = name;
  const root = document.documentElement;
  root.dataset.palette = name;
  for (const [token, colour] of Object.entries(palettes[name].colours)) {
    root.style.setProperty(`--${token}`, colour);
  }
  document.querySelector('meta[name="theme-color"]').content = palettes[name].colours.ink;
  document.getElementById("palette-choice").value = name;
  try {
    localStorage.setItem("different-feeds-palette", name);
  } catch {}
  document.querySelectorAll('.chart[data-status="ready"]').forEach(refreshChartLayout);
}

function initialisePalettes() {
  let preferred = activePalette;
  try {
    const saved = localStorage.getItem("different-feeds-palette");
    if (Object.hasOwn(palettes, saved)) preferred = saved;
  } catch {}
  setPalette(preferred);
  document.getElementById("palette-choice").addEventListener("change", (event) => {
    setPalette(event.target.value);
  });
}

function refreshChartLayout(element) {
  if (element.dataset.status !== "ready") return;
  if (element.dataset.compact === String(element.clientWidth < 560)
      && element.dataset.palette === activePalette) return;
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
  element.innerHTML = '<span class="chart-loading">Loading chart…</span>';
  try {
    if (!chartSpecifications.has(element.id)) {
      const response = await fetch(`specs/${element.id}.json`, { cache: "no-cache" });
      if (!response.ok) throw new Error(`Specification returned ${response.status}`);
      chartSpecifications.set(element.id, await response.json());
    }
    const specification = colourChart(structuredClone(chartSpecifications.get(element.id)));
    element.dataset.palette = activePalette;
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
      specification.config.axis.labelFontSize = 11;
      specification.config.axis.titleFontSize = 11;
      specification.config.legend.labelFontSize = 11;
      specification.config.legend.titleFontSize = 11;
      const compact = (node) => {
        if (!node || typeof node !== "object") return;
        if (node.legend && typeof node.legend === "object") {
          if (node.legend.columns) node.legend.columns = 2;
        }
        if (node.encoding?.x?.field === "age" && node.encoding.x.axis) {
          node.encoding.x.axis.labelAngle = -45;
        }
        if (node.field === "label" && node.axis) node.axis.labelLimit = 125;
        if (node.mark?.type === "text" && node.name !== "callout_text" && !node.name?.startsWith("hero_")) node.mark.fontSize = 11;
        Object.values(node).forEach(compact);
      };
      compact(specification);
      if (element.id === "news-age") {
        specification.encoding.x.axis.title = "Used in past 6 months (%)";
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
    message.textContent = "This chart could not load. Check your internet connection, then try again. If you opened a downloaded file, use the website link instead. ";
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
  initialisePalettes();
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
