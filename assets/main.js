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
  "news-trust",
  "adii-choropleth",
  "adii-cartogram",
  "metro-regional",
  "radio-symbol-map",
  "radio-dot-map",
];

// WHAT: Configure SVG rendering, tooltips and export/source menu actions.
// WHY: vegaEmbed reads these settings; they are not data transformations.
const embedOptions = {
  actions: { export: true, source: true, compiled: false, editor: false },
  renderer: "svg",
  tooltip: { theme: "light" },
  downloadFileName: "different-feeds-chart",
};

// WHAT: Keep references to the running Vega views.
// WHY: JavaScript needs these views to read or update chart signals.
const chartViews = new Map();
// WHAT: Cache the original parsed chart specifications.
// WHY: Recolouring and resizing can reuse them rather than downloading each file repeatedly.
const chartSpecifications = new Map();

const palette = {
  colours: {
    ink: "#172a3a", paper: "#f4f7fb", "paper-deep": "#e6edf4",
    primary: "#235b87", "primary-light": "#9ac8e2", accent: "#a84b14",
    "accent-light": "#efb779", highlight: "#e7b864", muted: "#526476",
    comparison: "#007b80", low: "#edf3fa", neutral: "#dce4ec", slate: "#68798b",
  },
  growth: ["#c6dcec", "#88b4d3", "#4784b1", "#174d77"],
  fall: ["#843a13", "#b86527", "#dda065", "#f3d7b5"],
};
const sourceBands = {
  growth: ["#bcd8ca", "#79ad99", "#40856f", "#155641"],
  fall: ["#942c4d", "#b44062", "#d9859e", "#f0c3d0"],
};
const activePalette = "ocean";

// WHAT: Apply the final ocean-and-amber palette to generated chart colours.
// WHY: Page and chart colours stay consistent without changing the source data.
function colourChart(specification, background = palette.colours.paper) {
  const colours = palette.colours;
  const replacements = {
    "#10231f": colours.ink, "#f7f3e8": background,
    "#1f6f5b": colours.primary, "#84cdb2": colours["primary-light"],
    "#d94d72": colours.accent, "#5279be": colours.comparison,
    "#63736f": colours.slate, "#edf5ef": colours.low, "#eef1ec": colours.low,
    "#dfe7df": colours.neutral, "#d8ded8": colours.neutral,
    "#d9ded8": colours.neutral, "#a8b3ad": colours.slate,
    "#bbc9bf": colours.neutral, "#e5ebe5": colours.neutral,
    "#b9c7be": colours.slate,
  };
  for (const direction of ["growth", "fall"]) {
    sourceBands[direction].forEach((colour, index) => {
      replacements[colour] = palette[direction][index];
    });
  }
  // WHAT: Recursively visit strings, arrays and objects in the specification.
  // WHY: Colours can be nested in marks, scales and configuration, not only at the top level.
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

// WHAT: Apply the final page palette, ignoring older saved theme preferences.
// WHY: Every visitor should see the same reviewed ocean-and-amber design.
function initialisePalette() {
  const root = document.documentElement;
  root.dataset.palette = activePalette;
  for (const [token, colour] of Object.entries(palette.colours)) {
    root.style.setProperty(`--${token}`, colour);
  }
  document.querySelector('meta[name="theme-color"]').content = palette.colours.ink;
}

// WHAT: Calculate a bounded responsive height for radio maps.
// WHY: The national map should remain readable without excessive blank space.
function radioHeight(element) {
  return element.id.startsWith("radio-")
    ? Math.round(Math.min(580, Math.max(300, element.clientWidth * 0.68)))
    : 0;
}

// WHAT: Walk through the Vega scenegraph and collect its rendered items.
// WHY: The explanatory text can read the same data and annotations as the displayed chart.
function sceneItems(view) {
  const items = [];
  // WHAT: Recursively visit each rendered Vega scene item.
  // WHY: Marks and groups form a tree, so deeper items also need to be collected.
  const inspect = (item) => {
    items.push(item);
    item.items?.forEach(inspect);
  };
  inspect(view.scenegraph().root);
  return items;
}

// WHAT: Attach chart-specific hover/click handlers, status text, clear buttons and explanatory paragraphs.
// WHY: The Vega chart and its surrounding HTML explanations should respond together.
function initialiseChartDetails(element, view, specification) {
  const focus = specification.usermeta?.focus;
  let status;
  let clear;
  let details;
  let bullet;
  if (focus) {
    status = document.createElement("p");
    status.className = "chart-focus-status";
    status.setAttribute("role", "status");
    clear = document.createElement("button");
    clear.type = "button";
    clear.textContent = "Clear pinned line";
    // WHAT: Reset the pin to All and clear the hover.
    // WHY: The reader can return to the overview in one action.
    clear.addEventListener("click", () => {
      view.signal(focus.parameter, focus.all).signal("hoveredSeries", "").runAsync();
    });
    details = document.createElement("div");
    details.className = "chart-detail";
    element.append(status, clear, details);
    // WHAT: Find the hovered/clicked item's category, checking parent groups if necessary.
    // WHY: Both legend items and plotted marks should identify a valid series.
    const categoryFor = (item) => {
      for (let depth = 0; item && depth < 6; depth += 1) {
        const datum = item.datum || {};
        const candidate = datum[focus.field] ?? datum.name ?? datum.value;
        if (focus.categories.includes(candidate)) return candidate;
        item = item.mark?.group;
      }
      return "";
    };
    // WHAT: Listen for a mark or legend hover, find its category and update hoveredSeries.
    // WHY: Temporary highlighting should not replace the pinned comparison.
    view.addEventListener("mouseover", (event, item) => {
      if (event.pointerType === "touch") return;
      const category = categoryFor(item);
      if (view.signal("hoveredSeries") !== category) view.signal("hoveredSeries", category).runAsync();
    });
    // WHAT: Clear the temporary hover value when the pointer leaves.
    // WHY: The pinned selection remains active after the temporary comparison ends.
    view.addEventListener("mouseout", () => {
      if (view.signal("hoveredSeries")) view.signal("hoveredSeries", "").runAsync();
    });
    // WHAT: Toggle the clicked category as the pinned selection.
    // WHY: Click or tap provides a persistent focus, including on touchscreens without hover.
    view.addEventListener("click", (event, item) => {
      const category = categoryFor(item);
      if (!category) return;
      // WHAT: Read the current pin and use a ternary condition to toggle it.
      // WHY: Clicking the same series again clears it; clicking another series replaces the pin.
      const pinned = view.signal(focus.parameter) === category ? focus.all : category;
      view.signal(focus.parameter, pinned).signal("hoveredSeries", "").runAsync();
    });
  }
  // WHAT: Create a live explanation for the currently selected video format.
  // WHY: The reader needs context for the bars and national-average ticks after changing the dropdown.
  if (element.id === "video-hours-bullet") {
    bullet = document.getElementById("video-hours-explanation");
    bullet.setAttribute("role", "status");
  }
  // WHAT: Refresh comparison readouts and the single viewing-hours explanation.
  // WHY: The explanations must match what the reader is currently inspecting.
  const update = () => {
    const items = sceneItems(view);
    if (focus) {
      const pinned = view.signal(focus.parameter);
      const hovered = view.signal("hoveredSeries");
      const statusText = pinned === focus.all
        ? "All lines shown. Hover to compare; click or tap to pin."
        : `Pinned: ${pinned}. Hover another line to compare; click the pinned line again to clear.`;
      if (status.textContent !== statusText) status.textContent = statusText;
      clear.disabled = pinned === focus.all;
      details.replaceChildren();
      for (const category of [...new Set([pinned, hovered])].filter(value => focus.categories.includes(value))) {
        const rows = new Map();
        for (const item of items) {
          const datum = item.datum;
          if (datum?.[focus.field] !== category || typeof datum.percent !== "number") continue;
          const key = datum.metric ?? datum.year ?? datum.location;
          if (key !== undefined) rows.set(key, datum.percent);
        }
        const paragraph = document.createElement("p");
        paragraph.textContent = `${category}: ` + [...rows].map(([key, value]) => `${key} ${value.toFixed(1)}%`).join(" · ");
        details.append(paragraph);
      }
    }
    if (bullet) {
      const rows = items.map(item => item.datum).filter(datum => typeof datum?.hours === "number");
      const longest = rows.reduce((best, row) => !best || row.hours > best.hours ? row : best, null);
      if (longest) {
        const format = longest.metric === "FTA catch-up" ? "Catch-up TV" : longest.metric;
        bullet.textContent = `${format}: adults aged ${longest.age} report the most time, averaging ${longest.hours.toFixed(1)} hours in the past week, against a national average of ${longest.national_hours.toFixed(1)} hours. A bar beyond the tick means more time than average. This adds a different perspective from audience size: a format can occupy more of a group’s week even without reaching everyone. The axis rescales with the selected format, and the averages should not be added across formats.`;
      }
    }
  };
  let queued = false;
  // WHAT: Queue at most one explanation update for the next animation frame.
  // WHY: Rapid pointer events should not trigger redundant DOM work.
  const scheduleUpdate = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      if (chartViews.get(element.id) === view) update();
    });
  };
  // WHAT: Listen for parameter signals changing inside the chart.
  // WHY: Dropdown-driven updates need to refresh the surrounding explanatory text as well.
  for (const parameter of specification.params || []) view.addSignalListener(parameter.name, scheduleUpdate);
  update();
}

// WHAT: Re-render only when the chart's layout or palette state has changed.
// WHY: Avoid unnecessary rendering while keeping resized charts readable.
function refreshChartLayout(element) {
  if (element.dataset.status !== "ready") return;
  if (element.dataset.compact === String(element.clientWidth < 560)
      && element.dataset.palette === activePalette
      && element.dataset.radioHeight === String(radioHeight(element))) return;
  delete element.dataset.rendered;
  renderChart(element);
}

// WHAT: Observe changes in chart container dimensions.
// WHY: A browser resize or layout change may require a compact rendering.
const chartResizeObserver = typeof ResizeObserver === "function"
  ? new ResizeObserver((entries) => entries.forEach(({ target }) => refreshChartLayout(target)))
  : null;

// WHAT: Load a chart specification, apply theme/layout settings and embed it.
// WHY: This is the bridge between an HTML container and its Vega-Lite definition.
async function renderChart(element) {
  if (element.dataset.rendered) return;
  element.dataset.rendered = "true";
  element.dataset.status = "loading";
  element.innerHTML = '<span class="chart-loading">Loading chart…</span>';
  try {
    if (!chartSpecifications.has(element.id)) {
      // WHAT: Request the numbered JSON file named by the HTML element's data-spec attribute.
      // WHY: For example, the audio heatmap loads specs/9.audio_age_heatmap.json. await waits within this async function, not by freezing the page.
      const response = await fetch(element.dataset.spec, { cache: "no-cache" });
      if (!response.ok) throw new Error(`Specification returned ${response.status}`);
      // WHAT: Parse the HTTP response body into a JavaScript object and cache it.
      // WHY: vegaEmbed needs the actual specification object rather than unparsed JSON text.
      chartSpecifications.set(element.id, await response.json());
    }
    // WHAT: Make a deep copy and recolour that copy.
    // WHY: Theme changes must not overwrite the cached original specification.
    // WHAT: Match annotation fills and label halos to their section background.
    // WHY: Pale chart details should blend into each section rather than look like white patches.
    const surface = element.closest('.chapter') || document.body;
    const background = getComputedStyle(surface).backgroundColor;
    const specification = colourChart(structuredClone(chartSpecifications.get(element.id)), background);
    element.dataset.palette = activePalette;
    const previousView = chartViews.get(element.id);
    if (previousView) {
      for (const parameter of specification.params || []) {
        if (!["hoveredSeries", "compactLayout"].includes(parameter.name) && !parameter.select) {
          // WHAT: Read an existing parameter value and restore it into the replacement specification.
          // WHY: Pinned selections and dropdown choices should survive a resize.
          parameter.value = previousView.signal(parameter.name);
        }
      }
      // WHAT: Release the previous chart view's resources before replacing it.
      // WHY: Repeated rendering should not leave old listeners and views running.
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
    element.dataset.radioHeight = String(radioHeight(element));
    if (radioHeight(element)) specification.height = radioHeight(element);
    // WHAT: Locate the compactLayout parameter for annotated charts.
    // WHY: Small plots rely on the main explanation below the chart rather than an extra annotation box.
    const compactParameter = specification.params?.find(parameter => parameter.name === "compactLayout");
    if (compactParameter) compactParameter.value = compactLayout;
    if (compactLayout) {
      specification.config.axis.labelFontSize = 11;
      specification.config.axis.titleFontSize = 11;
      specification.config.legend.labelFontSize = 11;
      specification.config.legend.titleFontSize = 11;
      // WHAT: Recursively adjust label, axis and legend settings for a narrow chart.
      // WHY: Mobile text needs to fit without changing the source measurements.
      const compact = (node) => {
        if (!node || typeof node !== "object") return;
        if (node.legend && typeof node.legend === "object") {
          node.legend.columns = node.legend.columns > 1 ? 2 : 1;
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
          if (layer.name?.startsWith("callout_")) return;
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
        specification.layer[2].mark.dx = 0;
        specification.layer[0].encoding.x = { value: 90 };
        specification.layer[0].encoding.x2 = { value: { expr: "width - 68" } };
        specification.layer[1].encoding.x = { value: 90 };
        specification.layer[2].encoding.x = { value: 2 };
        specification.layer[3].encoding.x = { value: { expr: "width - 68" } };
        specification.layer[4].encoding.x = { value: { expr: "width - 68" } };
        specification.layer[5].encoding.x = { value: { expr: "width - 68" } };
      }
    }
    // WHAT: Render the specification into the HTML element and return the running Vega view.
    // WHY: This is the actual step that turns the declarative chart definition into the visible interactive plot.
    const result = await vegaEmbed(element, specification, embedOptions);
    chartViews.set(element.id, result.view);
    element.dataset.status = "ready";
    initialiseChartDetails(element, result.view, specification);
    refreshChartLayout(element);
  // WHAT: Catch a failed chart load and offer a retry button.
  // WHY: A failed network request should produce a useful message rather than an unexplained blank chart.
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

// WHAT: Observe chart containers and load them shortly before they come into view.
// WHY: Lazy loading avoids drawing all 16 charts immediately; unsupported browsers fall back to loading them all.
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

// WHAT: Reveal page sections as they enter the viewport.
// WHY: This is a page presentation effect, separate from chart data or Vega-Lite highlighting.
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

// WHAT: Calculate scroll progress and update the thin bar at the top.
// WHY: The reader can see how far through the long page they are.
function updateReadingProgress() {
  const documentHeight = document.documentElement.scrollHeight - window.innerHeight;
  const progress = documentHeight > 0 ? (window.scrollY / documentHeight) * 100 : 0;
  document.querySelector(".reading-progress span").style.width = `${Math.min(100, progress)}%`;
}

// WHAT: Start once the HTML is ready, then wait for fonts before initialising charts.
// WHY: Containers and font measurements must exist before the charts are laid out.
window.addEventListener("DOMContentLoaded", async () => {
  initialisePalette();
  await document.fonts.ready;
  initialiseCharts();
  initialiseReveals();
  updateReadingProgress();
  document.getElementById("state-focus").addEventListener("change", (event) => {
    for (const [name, view] of chartViews) {
      if (name.startsWith("adii-") || name.startsWith("radio-")) {
        // WHAT: Set the stateFocus signal from the HTML state dropdown, then run the chart update.
        // WHY: All loaded map charts should highlight the same chosen state.
        view.signal("stateFocus", event.target.value).runAsync();
      }
    }
  });
});
window.addEventListener("scroll", updateReadingProgress, { passive: true });
