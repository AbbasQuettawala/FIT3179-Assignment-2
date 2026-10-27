#!/usr/bin/env python3
"""Generate the readable Vega-Lite specifications used by the webpage."""

from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

from spec_notes import add_spec_notes


ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
SCHEMA = "https://vega.github.io/schema/vega-lite/v6.json"

INK = "#10231f"
CREAM = "#f7f3e8"
GREEN = "#1f6f5b"
MINT = "#84cdb2"
MAGENTA = "#d94d72"
ORANGE = "#ed8750"
YELLOW = "#e5c45b"
BLUE = "#5279be"
SLATE = "#63736f"
PALE = "#dfe7df"
CATEGORICAL = ["#23658b", "#b05d25", "#267b75", "#a65c86", "#947026", "#4c8ca8", "#78639a", "#454d56"]
SERVICE_ORDER = ["YouTube", "Netflix", "Prime Video", "Disney+", "TikTok", "Stan", "Kayo", "Binge"]
DEVICE_ORDER = ["Smart TV", "Mobile phone", "Computer", "Tablet", "Chromecast / Google TV", "Games console", "Apple TV"]

AGE_ORDER = ["18–24", "25–34", "35–44", "45–54", "55–64", "65–74", "75+"]
MEDIA_ORDER = ["Paid video", "Short-form video", "Music streaming", "Podcasts", "Free-to-air TV", "FM radio"]
AUDIO_ORDER = ["Music streaming", "Podcasts", "Internet radio", "DAB+ radio", "FM radio", "AM radio"]


# WHAT: Define fonts, colours and axis/legend styling shared by charts.
# WHY: Consistent presentation reduces clutter and keeps the emphasis on comparisons.
def config():
    return {
        "background": None,
        "view": {"stroke": None},
        "axis": {
            "domain": False,
            "gridColor": "#d9ded8",
            "gridOpacity": 0.65,
            "labelColor": INK,
            "labelFont": "Inter",
            "labelFontSize": 14,
            "labelPadding": 7,
            "tickColor": "#a8b3ad",
            "titleColor": INK,
            "titleFont": "Inter",
            "titleFontSize": 12,
            "titleFontWeight": 650,
            "titlePadding": 12,
        },
        "legend": {
            "labelColor": INK,
            "labelFont": "Inter",
            "labelFontSize": 13,
            "symbolStrokeWidth": 3,
            "titleColor": INK,
            "titleFont": "Inter",
            "titleFontSize": 11,
        },
        "header": {
            "labelColor": INK,
            "labelFont": "Inter",
            "titleColor": INK,
            "titleFont": "Inter",
        },
    }


# WHAT: Create the common responsive chart settings.
# WHY: Each chart starts with the same sizing and styling conventions.
def base(height: int = 320):
    return {
        "$schema": SCHEMA,
        "width": "container",
        "height": height,
        "autosize": {"type": "fit", "contains": "padding"},
        "config": config(),
    }


# WHAT: Add map focus, parse CSV numbers, explain the spec and save its numbered JSON file.
# WHY: The generated file stays valid, readable and linked to its position on the website.
def write(name: str, spec: dict, number: int):
    if name.startswith(("adii-", "radio-")):
        spec.setdefault("params", []).append({"name": "stateFocus", "value": "All"})
        layers = spec.get("layer", [spec])
        for layer in layers:
            if "encoding" in layer and not layer.get("name", "").startswith(("callout_", "context_")):
                layer["encoding"]["opacity"] = {
                    "condition": {"test": "stateFocus === 'All' || datum.state === stateFocus", "value": 1},
                    "value": 0.22,
                }

    # WHAT: Find numeric CSV columns and declare their parse types.
    # WHY: Calculations need numbers rather than text; this is parsing, not normalisation.
    def explicit_csv_types(node):
        if isinstance(node, dict):
            if str(node.get("url", "")).endswith(".csv"):
                with (ROOT / node["url"]).open(encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                numeric_fields = {}
                for field in rows[0]:
                    try:
                        for row in rows:
                            float(row[field])
                    except ValueError:
                        continue
                    numeric_fields[field] = "number"
                node["format"] = {"type": "csv", "parse": numeric_fields}
            for value in node.values():
                explicit_csv_types(value)
        elif isinstance(node, list):
            for value in node:
                explicit_csv_types(value)

    explicit_csv_types(spec)
    spec = add_spec_notes(name, spec, number)
    filename = f"{number}.{name.replace('-', '_')}.json"
    with (SPECS / filename).open("w", encoding="utf-8") as handle:
        # WHAT: Put the chart number, name and type on the very first line.
        # WHY: Readers can identify the plot immediately while the file stays valid JSON.
        handle.write('{"description": ' + json.dumps(spec["description"], ensure_ascii=False) + ',\n')
        remaining = {key: value for key, value in spec.items() if key != "description"}
        handle.write(json.dumps(remaining, indent=2, ensure_ascii=False)[2:])
        handle.write("\n")
    return filename


# WHAT: Wrap the explanatory note into short lines.
# WHY: A short connector associates the unnumbered explanation with the data point.
def callout_text(message):
    return json.dumps("\n".join(textwrap.wrap(message, width=30)), ensure_ascii=False)


# WHAT: Layer a connector, background, outline marker and explanatory text onto a chart.
# WHY: A close, readable note connects the pattern to its meaning rather than repeating a value.
def add_callout(spec, message, transforms, anchor, alternate=None):
    spec.setdefault("params", []).append({"name": "compactLayout", "value": False})
    spec.setdefault("usermeta", {})["callout"] = True
    spec["config"]["axisX"] = {"grid": False}
    expression = callout_text(message)
    if alternate:
        condition, other_message = alternate
        expression = f"({condition}) ? ({callout_text(other_message)}) : ({expression})"

    # WHAT: Convert an anchor's data coordinate into a display coordinate.
    # WHY: Annotation connectors need pixel positions; band categories also need their cell centre.
    def position(channel):
        definition = anchor[channel]
        field = json.dumps(definition["field"])
        if definition.get("scale", {}) is None:
            return f"datum[{field}]"
        offset = f" + bandwidth('{channel}') / 2" if definition.get("type") in {"ordinal", "nominal"} else ""
        return f"scale('{channel}', datum[{field}]){offset}"

    anchor_x, anchor_y = position("x"), position("y")
    chart_id = spec["usermeta"]["chart"]
    right_side = chart_id in {"streaming-fta-connected", "age-parallel-profile", "video-hours-bullet", "metro-regional", "adii-cartogram"}
    horizontal = "+ 18" if right_side else "- 247"
    box_height = f"12 + 15 * length(split(({expression}), '\\n'))"
    box_x = f"clamp(({anchor_x}) {horizontal}, 4, max(4, width - 206))"
    box_y = f"clamp(({anchor_y}) - ({box_height}) - 10, 4, max(4, height - ({box_height}) - 4))"
    if chart_id == "streaming-fta-connected":
        box_y = f"clamp(({anchor_y}) - ({box_height}) - 32, 4, max(4, height - ({box_height}) - 4))"
    spec["layer"].extend([
        {
            "name": "callout_leader", "transform": transforms,
            "mark": {"type": "rule", "color": SLATE, "strokeWidth": 1},
            "encoding": {
                "x": {"value": {"expr": anchor_x}}, "y": {"value": {"expr": anchor_y}},
                "x2": {"value": {"expr": f"clamp(({anchor_x}), ({box_x}), ({box_x}) + 202)"}},
                "y2": {"value": {"expr": f"clamp(({anchor_y}), ({box_y}), ({box_y}) + ({box_height}))"}},
                "opacity": {"value": {"expr": "compactLayout ? 0 : 1"}},
                "tooltip": {"value": None},
            },
        },
        {
            "name": "callout_background", "transform": transforms,
            "mark": {"type": "rect", "color": CREAM, "opacity": 0.96, "cornerRadius": 4},
            "encoding": {
                "x": {"value": {"expr": box_x}}, "y": {"value": {"expr": box_y}},
                "x2": {"value": {"expr": f"({box_x}) + 202"}},
                "y2": {"value": {"expr": f"({box_y}) + ({box_height})"}},
                "opacity": {"value": {"expr": "compactLayout ? 0 : 0.96"}},
                "tooltip": {"value": None},
            },
        },
        {
            "name": "callout_anchor", "transform": transforms,
            "mark": {"type": "point", "shape": "circle", "filled": False, "size": 180,
                     "color": CREAM, "stroke": GREEN, "strokeWidth": 1.5},
            "encoding": {**anchor, "tooltip": {"value": message}},
        },
        {
            "name": "callout_text", "transform": transforms,
            "mark": {"type": "text", "text": {"expr": expression}, "font": "Inter",
                     "fontSize": 11, "lineHeight": 15, "lineBreak": "\n",
                     "align": "left", "baseline": "top", "color": INK},
            "encoding": {
                "x": {"value": {"expr": f"({box_x}) + 7"}},
                "y": {"value": {"expr": f"({box_y}) + 6"}},
                "opacity": {"value": {"expr": "compactLayout ? 0 : 1"}},
                "tooltip": {"value": None},
            },
        },
    ])


# WHAT: Add pinned/hover parameters and conditional opacity, width and shapes.
# WHY: Readers can compare a hovered series with a pinned one without losing the overview.
def add_focus(spec, field, parameter, categories, label, all_value="All"):
    spec.setdefault("params", [])
    spec["params"] = [entry for entry in spec["params"] if entry["name"] != parameter]
    spec["params"].extend([
        {"name": parameter, "value": all_value, "bind": {"input": "select", "options": [all_value, *categories], "name": label}},
        {"name": "hoveredSeries", "value": ""},
    ])
    spec.setdefault("usermeta", {})["focus"] = {
        "field": field, "parameter": parameter, "categories": categories, "all": all_value,
    }
    for layer in spec["layer"]:
        if layer.get("name", "").startswith("callout_"):
            continue
        encoding = layer.get("encoding", {})
        colour = encoding.get("color", {})
        category_field = colour.get("field")
        if category_field != field and not (field == "format" and category_field == "name"):
            continue
        colour["scale"] = {"domain": categories, "range": CATEGORICAL[:len(categories)]}
        focused = f"datum.{category_field} === {parameter} || datum.{category_field} === hoveredSeries"
        overview = f"{parameter} === {json.dumps(all_value)} && hoveredSeries === ''"
        encoding["opacity"] = {"condition": {"test": f"({overview}) || ({focused})", "value": 1}, "value": 0.4}
        mark_type = layer.get("mark", {}).get("type")
        if mark_type == "line":
            encoding["strokeWidth"] = {"condition": {"test": focused, "value": 4.5}, "value": 2.5}
        if mark_type == "point" or layer.get("mark", {}).get("point"):
            encoding["shape"] = {"field": category_field, "type": "nominal",
                                 "scale": {"domain": categories, "range": ["circle", "square", "diamond", "triangle-up", "triangle-down", "cross", "triangle-right", "triangle-left"][:len(categories)]},
                                 "legend": None}
        if mark_type == "text":
            encoding["color"] = {"value": INK}


# WHAT: Waffle chart: one tile represents one in 100 adults.
# WHY: A 100-tile grid makes the rounded share easy to picture, rather than presenting only a large number.
def waffle():
    with (ROOT / "data/headline_metrics.json").open(encoding="utf-8") as handle:
        share = json.load(handle)["online_video_past_six_months"]
    spec = base(340)
    spec.update(
        {
            "description": f"100 video tiles represent Australian adults. {share} filled tiles show the rounded share who used online video in the six months before the 2025 survey. Outlined tiles show the remaining share.",
            "data": {"sequence": {"start": 0, "stop": 100, "step": 1, "as": "cell"}},
            "transform": [
                {"calculate": "datum.cell % 10", "as": "column"},
                {"calculate": "floor(datum.cell / 10)", "as": "row"},
                {"calculate": f"datum.cell < {share} ? 'Used online video' : 'Remaining adults'", "as": "group"},
                {"calculate": f"datum.cell < {share} ? {share} : {100 - share}", "as": "share"},
            ],
            "layer": [
                {
                    "name": "hero_tiles",
                    "mark": {"type": "rect", "cornerRadius": 3, "strokeWidth": 1, "opacity": 1},
                    "encoding": {
                        "x": {"field": "column", "type": "ordinal", "axis": None, "scale": {"type": "band", "padding": 0.15}},
                        "y": {"field": "row", "type": "ordinal", "axis": None, "scale": {"type": "band", "padding": 0.15, "range": [80, {"expr": "height"}]}},
                        "color": {
                            "field": "group", "type": "nominal",
                            "scale": {"domain": ["Used online video", "Remaining adults"], "range": [GREEN, CREAM]},
                            "legend": {"title": "One tile = 1 in 100 adults (rounded)", "titleLimit": 300, "orient": "bottom", "columns": 1, "symbolType": "square", "symbolStrokeColor": SLATE},
                        },
                        "stroke": {"condition": {"test": f"datum.cell < {share}", "value": GREEN}, "value": SLATE},
                        "tooltip": [
                            {"field": "group", "title": "Group"},
                            {"field": "share", "type": "quantitative", "title": "Share of adults (%)", "format": ".0f"},
                        ],
                    },
                },
                {
                    "name": "hero_play_icons",
                    "transform": [{"filter": f"datum.cell < {share}"}],
                    "mark": {"type": "point", "shape": "triangle-right", "filled": True, "color": "white", "opacity": 1, "size": {"expr": "pow(min(width / 35, (height - 80) / 18), 2)"}},
                    "encoding": {
                        "x": {"field": "column", "type": "ordinal"},
                        "y": {"field": "row", "type": "ordinal"},
                        "tooltip": [
                            {"field": "group", "title": "Group"},
                            {"field": "share", "type": "quantitative", "title": "Share of adults (%)", "format": ".0f"},
                        ],
                    },
                },
                {
                    "name": "hero_total",
                    "data": {"values": [{}]},
                    "mark": {"type": "text", "text": f"{share} in 100", "font": "Fraunces", "fontSize": {"expr": "width < 360 ? 20 : 24"}, "fontWeight": 700, "align": "left", "baseline": "top", "color": GREEN},
                    "encoding": {"x": {"value": 0}, "y": {"value": 0}},
                },
                {
                    "name": "hero_context",
                    "data": {"values": [{}]},
                    "mark": {"type": "text", "text": "used online video in the past six months", "font": "Inter", "fontSize": {"expr": "width < 360 ? 11 : 13"}, "align": "left", "baseline": "top", "color": INK},
                    "encoding": {"x": {"value": 0}, "y": {"value": 40}},
                },
            ],
        }
    )
    return spec


# WHAT: Horizon chart: layered area bands show change from the first year of each series.
# WHY: Folding change into 10-point bands lets several trends fit into separate compact rows.
def horizon():
    spec = base(680)
    spec["description"] = "Four rows showing changes in weekly video use. Each darker band adds 10 percentage points; in the legend, + means growth and − means a fall."
    spec["data"] = {"url": "data/horizon_trends.csv"}
    spec["layer"] = []
    for band in [1, 2, 3, 4]:
        spec["layer"].append({
            "transform": [{"filter": f"datum.band === {band}"},
                          {"calculate": "datum.change < 0 ? -datum.band : datum.band", "as": "signed_band"}],
            "mark": {"type": "area", "orient": "vertical"},
            "encoding": {
                "x": {"field": "year", "type": "quantitative", "scale": {"domain": [2017, 2025], "nice": False}, "axis": {"title": None, "format": "d", "tickMinStep": 1, "grid": False}},
                "y": {"field": "y1", "type": "quantitative", "scale": {"domain": [0, 52]}, "axis": None},
                "y2": {"field": "y0"},
                "detail": {"field": "metric"},
                "color": {
                    "field": "signed_band", "type": "ordinal",
                    "scale": {
                        "domain": [-4, -3, -2, -1, 1, 2, 3, 4],
                        "range": ["#942c4d", "#b44062", "#d9859e", "#f0c3d0",
                                  "#bcd8ca", "#79ad99", "#40856f", "#155641"],
                    },
                    "legend": {
                        "title": ["Change since first year shown", "(percentage points)"], "titleLimit": 290,
                        "orient": "top", "columns": 4, "symbolType": "square",
                        "labelExpr": "datum.value < 0 ? format(datum.value * 10, '+d') + ' to ' + format((datum.value + 1) * 10, '+d') : format((datum.value - 1) * 10, '+d') + ' to ' + format(datum.value * 10, '+d')",
                    },
                },
                "tooltip": [
                    {"field": "metric", "title": "Activity"},
                    {"field": "year", "type": "ordinal", "title": "Year"},
                    {"field": "change", "type": "quantitative", "format": "+.1f", "title": "Change (percentage points)"},
                    {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Weekly use (%)"},
                ],
            },
        })
    spec["layer"].append({
        "transform": [
            {"filter": "datum.band === 1"},
            {"calculate": "max(2017, datum.year - 0.5)", "as": "hover_start"},
            {"calculate": "min(2025, datum.year + 0.5)", "as": "hover_end"},
            {"calculate": "datum.y0 + 10", "as": "hover_top"},
        ],
        "mark": {"type": "rect", "opacity": 0},
        "encoding": {
            "x": {"field": "hover_start", "type": "quantitative"},
            "x2": {"field": "hover_end"},
            "y": {"field": "y0", "type": "quantitative"},
            "y2": {"field": "hover_top"},
            "tooltip": [
                {"field": "metric", "title": "Activity"},
                {"field": "year", "type": "ordinal", "title": "Year"},
                {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Weekly use (%)"},
                {"field": "change", "type": "quantitative", "format": "+.1f", "title": "Change (percentage points)"},
            ],
        },
    })
    spec["layer"].append({
        "transform": [{"filter": "datum.year === 2025 && datum.band === 1"}, {"calculate": "datum.y0 + 11.5", "as": "label_y"}, {"calculate": "(datum.metric === 'FTA catch-up' ? 'Catch-up TV' : datum.metric) + ' · ' + format(datum.change, '+.1f') + ' points · since ' + (datum.metric === 'Short-form video' ? '2022' : '2017')", "as": "label"}],
        "mark": {"type": "text", "align": "left", "font": "Inter", "fontSize": 13, "fontWeight": 700, "color": INK},
        "encoding": {"x": {"datum": 2017}, "y": {"field": "label_y", "type": "quantitative"}, "text": {"field": "label"}},
    })
    return spec


# WHAT: Connected scatterplot: x is paid streaming use, y is free-to-air use, and the path follows years.
# WHY: This shows how two measurements move together over time without using two unrelated vertical scales.
def connected_scatter():
    spec = base(560)
    spec.update(
        {
            "description": "A line connecting yearly percentages for paid streaming and free-to-air TV use.",
            "data": {"url": "data/streaming_fta.csv", "format": {"type": "csv", "parse": {"year": "number"}}},
            "layer": [
                {
                    "mark": {"type": "line", "stroke": INK, "strokeWidth": 2.5, "interpolate": "linear"},
                    "encoding": {
                        "x": {"field": "paid_streaming", "type": "quantitative", "scale": {"domain": [25, 83], "zero": False}, "axis": {"title": "Used paid streaming in past 7 days (%)"}},
                        "y": {"field": "free_to_air", "type": "quantitative", "scale": {"zero": False}, "axis": {"title": "Watched free-to-air TV in past 7 days (%)"}},
                        "order": {"field": "year", "type": "ordinal"},
                    },
                },
                {
                    "mark": {"type": "circle", "size": 200, "stroke": CREAM, "strokeWidth": 2},
                    "encoding": {
                        "x": {"field": "paid_streaming", "type": "quantitative"},
                        "y": {"field": "free_to_air", "type": "quantitative"},
                        "color": {"field": "year", "type": "quantitative", "scale": {"range": ["#5d849f", "#174d77"]}, "legend": {"title": "Year", "orient": "top", "format": "d"}},
                        "tooltip": [
                            {"field": "year", "type": "ordinal", "title": "Year"},
                            {"field": "paid_streaming", "type": "quantitative", "format": ".1f", "title": "Paid streaming (%)"},
                            {"field": "free_to_air", "type": "quantitative", "format": ".1f", "title": "Free-to-air TV (%)"},
                        ],
                    },
                },
                {
                    "transform": [{"filter": "datum.year === 2017 || datum.year === 2025"}],
                    "mark": {"type": "text", "font": "Inter", "fontWeight": 700, "dy": -12, "color": INK},
                    "encoding": {
                        "x": {"field": "paid_streaming", "type": "quantitative"},
                        "y": {"field": "free_to_air", "type": "quantitative"},
                        "text": {"field": "year"},
                    },
                },
            ],
        }
    )
    return spec


# WHAT: Video-service heatmap: columns are age groups, rows are services, colour is percentage.
# WHY: A grid makes many age-by-service comparisons easier to scan than dozens of separate charts.
def age_heatmap():
    spec = base(500)
    spec.update(
        {
            "description": "A colour-coded grid showing use of eight video services by age group in the past six months.",
            "data": {"url": "data/video_services_age.csv"},
            "layer": [
                {
                    "mark": {"type": "rect", "cornerRadius": 3},
                    "encoding": {
                        "x": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age", "labelAngle": 0}},
                        "y": {"field": "service", "type": "ordinal", "sort": ["YouTube", "Netflix", "Prime Video", "Disney+", "TikTok", "Stan", "Kayo", "Binge"], "axis": {"title": None}},
                        "color": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100], "range": ["#edf5ef", GREEN]}, "legend": {"title": "Used in past 6 months (%)", "orient": "top"}},
                        "tooltip": [
                            {"field": "age", "title": "Age"},
                            {"field": "service", "title": "Service"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Used (%)"},
                            {"field": "base_n", "type": "quantitative", "title": "Survey participants"},
                        ],
                    },
                },
                {
                    "mark": {"type": "text", "font": "Inter", "fontSize": 13, "fontWeight": 650},
                    "encoding": {
                        "x": {"field": "age", "type": "ordinal", "sort": AGE_ORDER},
                        "y": {"field": "service", "type": "ordinal", "sort": ["YouTube", "Netflix", "Prime Video", "Disney+", "TikTok", "Stan", "Kayo", "Binge"]},
                        "text": {"field": "percent", "type": "quantitative", "format": ".0f"},
                        "color": {"condition": {"test": "contrast('white', scale('color', datum.percent)) > contrast('#000000', scale('color', datum.percent))", "value": "white"}, "value": "#000000"},
                    },
                },
            ],
        }
    )
    return spec


# WHAT: Connected age profiles: each age group's line links its values across media activities.
# WHY: Following one coloured line reveals the media mix for an age group; hover and pin help compare groups.
def parallel_profiles():
    spec = base(520)
    spec.update(
        {
            "description": "Compare age groups across weekly activities. Hover to highlight; click or tap to pin a line.",
            "data": {"url": "data/age_media.csv"},
            "transform": [{"calculate": "indexof(" + json.dumps(MEDIA_ORDER) + ", datum.metric)", "as": "metric_position"}],
            "params": [],
            "layer": [
                {
                    "mark": {"type": "line", "point": {"filled": True, "size": 72}},
                    "encoding": {
                        "x": {"field": "metric", "type": "ordinal", "sort": MEDIA_ORDER, "axis": {"title": None, "labelAngle": -28, "labelLimit": 110}},
                        "y": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100]}, "axis": {"title": "Used in past week (%)"}},
                        "detail": {"field": "age"},
                        "color": {"field": "age", "type": "nominal", "scale": {"domain": AGE_ORDER, "range": CATEGORICAL[:7]}, "legend": {"title": "Age group", "orient": "top", "columns": 4}},
                        "order": {"field": "metric_position", "type": "quantitative"},
                        "tooltip": [
                            {"field": "age", "title": "Age"},
                            {"field": "metric", "title": "Activity"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Used (%)"},
                        ],
                    },
                }
            ],
        }
    )
    return spec


# WHAT: Bullet chart: bars show age-group viewing hours; ticks show the national average for the selected format.
# WHY: A shared reference tick makes it easy to see which groups watch more or less than the national average.
def bullet_hours():
    spec = base(500)
    spec.update(
        {
            "description": "Average weekly viewing hours by age, with short vertical lines showing the national average for the chosen format.",
            "data": {"url": "data/video_hours_age.csv"},
            "params": [{"name": "videoFormat", "value": "Free-to-air TV", "bind": {"input": "select", "options": ["Free-to-air TV", "Paid streaming", "Short-form video", "FTA catch-up", "Pay TV", "Pay-per-view"], "labels": ["Free-to-air TV", "Paid streaming", "Short-form video", "Catch-up TV", "Pay TV", "Pay-per-view"], "name": "Video type  "}}],
            "transform": [{"filter": "datum.metric === videoFormat"}],
            "layer": [
                {
                    "name": "bullet_bars",
                    "mark": {"type": "bar", "cornerRadiusEnd": 4, "height": 32},
                    "encoding": {
                        "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age"}},
                        "x": {"field": "hours", "type": "quantitative", "scale": {"domain": {"expr": "[0, videoFormat === 'Free-to-air TV' ? 20 : videoFormat === 'Paid streaming' ? 10 : videoFormat === 'Short-form video' ? 11 : videoFormat === 'FTA catch-up' ? 6 : videoFormat === 'Pay TV' ? 5 : 0.6]"}}, "axis": {"title": "Average hours in past 7 days"}},
                        "color": {"datum": "Age-group average", "type": "nominal", "scale": {"domain": ["Age-group average", "National average"], "range": [GREEN, MAGENTA]}, "legend": {"title": "Bar length = average hours", "orient": "top", "columns": 1, "symbolType": "square", "labelExpr": "datum.label === 'Age-group average' ? 'Bar: age-group average' : 'Tick: national average'"}},
                        "tooltip": [
                            {"field": "age", "title": "Age"},
                            {"field": "hours", "type": "quantitative", "format": ".1f", "title": "Hours"},
                            {"field": "national_hours", "type": "quantitative", "format": ".1f", "title": "National average (hours)"},
                            {"field": "base_n", "type": "quantitative", "title": "Survey participants"},
                            {"field": "metric", "title": "Video format"},
                        ],
                    },
                },
                {
                    "name": "bullet_average",
                    "mark": {"type": "tick", "color": MAGENTA, "thickness": 3, "size": 40},
                    "encoding": {
                        "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER},
                        "x": {"field": "national_hours", "type": "quantitative"},
                        "color": {"datum": "National average", "type": "nominal"},
                    },
                },
                {
                    "name": "bullet_values",
                    "mark": {"type": "text", "align": "left", "dx": 12, "font": "Inter", "fontWeight": 700, "color": INK},
                    "encoding": {
                        "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER},
                        "x": {"field": "hours", "type": "quantitative"},
                        "text": {"field": "hours", "type": "quantitative", "format": ".1f"},
                    },
                },
            ],
        }
    )
    return spec


# WHAT: Bump chart: each service's line follows its rank through the years.
# WHY: Rank makes changes in relative popularity easy to follow; direct endpoint labels identify services.
def service_bump():
    spec = base(580)
    spec.update(
        {
            "description": "Lines showing the popularity ranking of eight selected video services from 2021 to 2025.",
            "data": {"url": "data/video_services.csv", "format": {"type": "csv", "parse": {"year": "number"}}},
            "transform": [
                {"window": [{"op": "rank", "as": "rank"}], "sort": [{"field": "percent", "order": "descending"}], "groupby": ["year"]},
            ],
            "layer": [
                {
                    "mark": {"type": "line", "point": {"filled": True, "size": 110}, "strokeWidth": 2.6},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal", "axis": {"title": None, "labelAngle": 0}},
                        "y": {"field": "rank", "type": "quantitative", "scale": {"domain": [1, 8], "reverse": True}, "axis": {"title": "Rank among these 8 services", "tickMinStep": 1}},
                        "color": {"field": "service", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": {"title": None, "orient": "top", "columns": 4}},
                        "detail": {"field": "service"},
                        "order": {"field": "year"},
                        "tooltip": [
                            {"field": "year", "title": "Year"},
                            {"field": "service", "title": "Service"},
                            {"field": "rank", "title": "Rank"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Used (%)"},
                        ],
                    },
                },
                {
                    "transform": [{"filter": "datum.year === 2025"}],
                    "mark": {"type": "text", "align": "left", "dx": 7, "dy": -8, "font": "Inter", "fontSize": 13, "fontWeight": 700},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal"},
                        "y": {"field": "rank", "type": "quantitative", "scale": {"reverse": True}},
                        "text": {"field": "service"},
                        "color": {"field": "service", "type": "nominal", "scale": {"range": CATEGORICAL}},
                    },
                },
            ],
        }
    )
    return spec


# WHAT: Slope chart: each device connects its usage percentage in two years.
# WHY: The direction and steepness of each slope help compare increases and decreases.
def device_slope():
    spec = base(540)
    spec.update(
        {
            "description": "Lines comparing devices used to watch online video at home in 2021 and 2025.",
            "data": {"url": "data/video_devices.csv", "format": {"type": "csv", "parse": {"year": "number"}}},
            "layer": [
                {
                    "mark": {"type": "line", "strokeWidth": 2.7},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal", "axis": {"title": None, "labelAngle": 0, "labelFontSize": 13, "labelFontWeight": 700}},
                        "y": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 80]}, "axis": {"title": "Use for online video at home (%)"}},
                        "detail": {"field": "device"},
                        "color": {"field": "device", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                        "tooltip": [
                            {"field": "device", "title": "Device"},
                            {"field": "year", "title": "Year"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Used (%)"},
                        ],
                    },
                },
                {
                    "mark": {"type": "point", "filled": True, "size": 136},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal"},
                        "y": {"field": "percent", "type": "quantitative"},
                        "color": {"field": "device", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                    },
                },
                {
                    "transform": [{"filter": "datum.year === 2025"}, {"calculate": "(datum.device === 'Chromecast / Google TV' ? 'Google TV' : datum.device === 'Games console' ? 'Console' : datum.device) + ' ' + format(datum.percent, '.0f') + '%'", "as": "label"}],
                    "mark": {"type": "text", "align": "left", "dx": 7, "dy": {"expr": "datum.device === 'Games console' ? -5 : datum.device === 'Apple TV' ? 5 : 0"}, "font": "Inter", "fontSize": 13, "fontWeight": 650},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal"},
                        "y": {"field": "percent", "type": "quantitative"},
                        "text": {"field": "label"},
                        "color": {"field": "device", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                    },
                },
            ],
        }
    )
    return spec


# WHAT: Audio heatmap: columns are age groups, rows are audio formats, colour is weekly listening percentage.
# WHY: The grid reveals age patterns, while a second text layer supplies exact rounded readings.
def audio_heatmap():
    spec = base(500)
    spec.update(
        {
            "description": "A colour-coded grid comparing weekly listening habits by age.",
            "data": {"url": "data/audio_age.csv"},
            "mark": {"type": "rect", "cornerRadius": 3},
            "encoding": {
                "x": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age", "labelAngle": 0}},
                "y": {"field": "metric", "type": "ordinal", "sort": AUDIO_ORDER, "axis": {"title": None}},
                "color": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100], "range": ["#edf5ef", GREEN]}, "legend": {"title": "Listened in past week (%)", "orient": "top"}},
                "tooltip": [
                    {"field": "age", "title": "Age"},
                    {"field": "metric", "title": "Format"},
                    {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Used (%)"},
                    {"field": "base_n", "type": "quantitative", "title": "Survey participants"},
                ],
            },
        }
    )
    tile = {"name": "heatmap_tiles", "mark": spec.pop("mark"), "encoding": spec.pop("encoding")}
    spec["layer"] = [tile, {
        "name": "heatmap_values",
        "mark": {"type": "text", "font": "Inter", "fontSize": 13, "fontWeight": 650},
        "encoding": {
            "x": tile["encoding"]["x"], "y": tile["encoding"]["y"],
            "text": {"field": "percent", "type": "quantitative", "format": ".0f"},
            "color": {"condition": {"test": "contrast('white', scale('color', datum.percent)) > contrast('#000000', scale('color', datum.percent))", "value": "white"}, "value": "#000000"},
        },
    }]
    return spec


# WHAT: Listening network: left nodes are audio formats, right nodes are locations, and link thickness is percentage.
# WHY: Links make format-to-location relationships visible; thickness expresses the strength of each relationship.
def audio_network():
    formats = [
        {"name": name, "y": index, "x": 0.14}
        for index, name in enumerate(AUDIO_ORDER)
    ]
    locations = [
        {"name": "Home", "y": 0.7, "x": 0.86},
        {"name": "In transit", "y": 2.5, "x": 0.86},
        {"name": "Elsewhere", "y": 4.3, "x": 0.86},
    ]
    spec = base(540)
    spec.update(
        {
            "description": "Lines linking six types of audio to three listening locations. Thicker lines mean more of that format's listeners use it there.",
            "data": {"url": "data/audio_locations.csv"},
            "params": [{"name": "audioFocus", "value": "All formats", "bind": {
                "input": "select", "options": ["All formats", *AUDIO_ORDER], "name": "Choose audio  ",
            }}],
            "transform": [
                {"calculate": "indexof(['Music streaming','Podcasts','Internet radio','DAB+ radio','FM radio','AM radio'], datum.format)", "as": "format_y"},
                {"calculate": "datum.location === 'Home' ? 0.7 : datum.location === 'In transit' ? 2.5 : 4.3", "as": "location_y"},
            ],
            "layer": [
                {
                    "name": "audio_links",
                    "mark": {"type": "rule", "strokeCap": "round"},
                    "encoding": {
                        "x": {"datum": 0.16, "type": "quantitative", "scale": {"domain": [0, 1]}, "axis": None},
                        "x2": {"datum": 0.84},
                        "y": {"field": "format_y", "type": "quantitative", "scale": {"domain": [-0.5, 5.5]}, "axis": None},
                        "y2": {"field": "location_y"},
                        "color": {"field": "format", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                        "opacity": {"condition": [
                            {"test": "audioFocus === 'All formats'", "value": 0.5},
                            {"test": "datum.format === audioFocus", "value": 0.95},
                        ], "value": 0.06},
                        "strokeWidth": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100], "range": [0, 12]}, "legend": {"title": "Listened there (%)", "orient": "top", "values": [25, 50, 75]}},
                        "tooltip": [
                            {"field": "format", "title": "Format"},
                            {"field": "location", "title": "Location"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Used (%)"},
                            {"field": "base_n", "type": "quantitative", "title": "Survey participants"},
                        ],
                    },
                },
                {
                    "data": {"values": formats},
                    "mark": {"type": "circle", "size": 248, "stroke": CREAM, "strokeWidth": 2},
                    "encoding": {
                        "x": {"field": "x", "type": "quantitative"},
                        "y": {"field": "y", "type": "quantitative"},
                        "color": {"field": "name", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                        "opacity": {"condition": {"test": "audioFocus === 'All formats' || datum.name === audioFocus", "value": 1}, "value": 0.25},
                    },
                },
                {
                    "data": {"values": formats},
                    "mark": {"type": "text", "align": "right", "dx": -10, "font": "Inter", "fontSize": 13, "fontWeight": 650, "color": INK},
                    "encoding": {"x": {"field": "x", "type": "quantitative"}, "y": {"field": "y", "type": "quantitative"}, "text": {"field": "name"}},
                },
                {
                    "data": {"values": locations},
                    "mark": {"type": "circle", "size": 288, "color": INK, "stroke": CREAM, "strokeWidth": 2},
                    "encoding": {"x": {"field": "x", "type": "quantitative"}, "y": {"field": "y", "type": "quantitative"}},
                },
                {
                    "data": {"values": locations},
                    "mark": {"type": "text", "align": "left", "dx": 10, "font": "Inter", "fontSize": 13, "fontWeight": 700, "color": INK},
                    "encoding": {"x": {"field": "x", "type": "quantitative"}, "y": {"field": "y", "type": "quantitative"}, "text": {"field": "name"}},
                },
                {
                    "name": "audio_readout",
                    "transform": [{"filter": "datum.format === (hoveredSeries !== '' ? hoveredSeries : audioFocus)"},
                                  {"calculate": "format(datum.percent, '.1f') + '%'", "as": "reading"}],
                    "mark": {"type": "text", "align": "left", "dx": 10, "dy": 16,
                             "font": "Inter", "fontSize": 13, "fontWeight": 700, "color": GREEN},
                    "encoding": {
                        "x": {"datum": 0.86}, "y": {"field": "location_y", "type": "quantitative"},
                        "text": {"field": "reading"},
                    },
                },
            ],
        }
    )
    return spec


# WHAT: News dot plot: each dot shows online news and information use for one age group.
# WHY: Aligned positions make small differences easier to compare than differently sized areas.
def news_age():
    spec = base(480)
    spec.update({
        "description": "Dots showing the percentage of each age group that used online news and information in the past six months, in 2025.",
        "data": {"url": "data/news_age.csv"},
        "encoding": {
            "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age"}},
            "x": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100]},
                  "axis": {"title": "Used online news and information (%)"}},
            "tooltip": [
                {"field": "age", "title": "Age"},
                {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Used in past 6 months (%)"},
                {"field": "base_n", "type": "quantitative", "title": "Survey participants"},
            ],
        },
        "layer": [
            {"mark": {"type": "circle", "size": 200, "color": GREEN, "opacity": 1}},
            {"mark": {"type": "text", "dx": -12, "align": "right", "font": "Inter", "color": INK},
             "encoding": {"text": {"field": "percent", "type": "quantitative", "format": ".1f"}}},
        ],
    })
    return spec


# WHAT: Dumbbell chart: two points per activity compare city and regional use, joined by a rule.
# WHY: The connecting segment makes the direction and size of the city-regional difference visible.
def metro_regional():
    spec = base(520)
    spec.update({
        "description": "Pairs of dots comparing weekly media use in ACMA's city and regional groups in 2025.",
        "data": {"url": "data/metro_regional.csv"},
        "encoding": {
            "y": {"field": "metric", "type": "nominal", "sort": MEDIA_ORDER, "axis": {"title": None}},
            "x": {"type": "quantitative", "scale": {"domain": [0, 100]}, "axis": {"title": "Used in past week (%)"}},
        },
        "layer": [
            {"mark": {"type": "rule", "strokeWidth": 3, "color": "#bbc9bf"},
             "encoding": {"x": {"field": "metro"}, "x2": {"field": "regional"}}},
            {"transform": [{"fold": ["metro", "regional"], "as": ["region", "percent"]}],
             "mark": {"type": "point", "filled": True, "size": 160, "opacity": 1},
             "encoding": {
                 "x": {"field": "percent"},
                 "color": {"field": "region", "type": "nominal",
                           "scale": {"domain": ["metro", "regional"], "range": [BLUE, MAGENTA]},
                           "legend": {"title": "Location", "orient": "top", "labelExpr": "datum.label === 'metro' ? 'City (metro)' : 'Regional'"}},
                 "shape": {"field": "region", "type": "nominal",
                           "scale": {"domain": ["metro", "regional"], "range": ["circle", "diamond"]}},
                 "tooltip": [
                     {"field": "metric", "title": "Activity"},
                     {"field": "metro", "format": ".1f", "type": "quantitative", "title": "City (metro) (%)"},
                     {"field": "regional", "format": ".1f", "type": "quantitative", "title": "Regional (%)"},
                     {"field": "gap", "format": "+.1f", "type": "quantitative", "title": "Regional minus city (percentage points)"},
                     {"field": "metro_base_n", "title": "City survey participants"},
                     {"field": "regional_base_n", "title": "Regional survey participants"},
                 ],
             }},
        ],
    })
    return spec


# WHAT: Draw state labels, halos and an offset ACT pointer.
# WHY: Small regions need readable labels without covering nearby marks.
def state_label_layers():
    labels = {
        "data": {"url": "data/adii_states.csv"},
        "transform": [
            {"calculate": "datum.state === 'ACT' ? 153.2 : datum.longitude", "as": "label_longitude"},
            {"calculate": "datum.state === 'ACT' ? -35.9 : datum.latitude", "as": "label_latitude"},
        ],
        "encoding": {
            "longitude": {"field": "label_longitude", "type": "quantitative"},
            "latitude": {"field": "label_latitude", "type": "quantitative"},
            "text": {"field": "state"},
            "tooltip": [{"field": "state_name", "title": "State / territory"}],
        },
    }
    halo = {
        **labels, "name": "state_label_halos",
        "mark": {"type": "text", "font": "Inter", "fontSize": 11, "fontWeight": 700,
                 "stroke": CREAM, "strokeWidth": 3, "color": CREAM},
    }
    foreground = {
        **labels, "name": "state_labels",
        "mark": {"type": "text", "font": "Inter", "fontSize": 11, "fontWeight": 700, "color": INK},
    }
    pointer = {
        "name": "state_label_pointer",
        "data": {"url": "data/adii_states.csv"},
        "transform": [{"filter": "datum.state === 'ACT'"}],
        "mark": {"type": "rule", "strokeWidth": 0.8, "color": INK},
        "encoding": {
            "longitude": {"field": "longitude", "type": "quantitative"},
            "latitude": {"field": "latitude", "type": "quantitative"},
            "longitude2": {"datum": 151.9}, "latitude2": {"datum": -35.9},
        },
    }
    return [pointer, halo, foreground]


# WHAT: Choropleth: state shapes are coloured by digital inclusion score.
# WHY: Keeping geographic outlines supports regional comparison and helps viewers locate familiar states.
def state_choropleth():
    spec = base(720)
    spec.update(
        {
            "description": "A shaded map of digital inclusion scores by state and territory. Darker shading means a higher score.",
            "data": {"url": "data/au_states.topojson", "format": {"type": "topojson", "feature": "states"}},
            "transform": [
                {
                    "lookup": "properties.state_name",
                    "from": {"data": {"url": "data/adii_states.csv"}, "key": "state_name", "fields": ["score", "state", "gap"]},
                }
            ],
            "projection": {"type": "conicEqualArea", "parallels": [-18, -36], "rotate": [-134, 0, 0], "center": [0, -28]},
            "mark": {"type": "geoshape", "stroke": CREAM, "strokeWidth": 1.2},
            "encoding": {
                "color": {"field": "score", "type": "quantitative", "scale": {"domain": [68, 80], "range": ["#edf5ef", GREEN]}, "legend": {"title": "Digital inclusion score", "orient": "top"}},
                "tooltip": [
                    {"field": "state", "title": "State / territory"},
                    {"field": "score", "type": "quantitative", "format": ".1f", "title": "Digital inclusion score"},
                    {"field": "gap", "type": "quantitative", "format": "+.1f", "title": "Above/below national score (points)"},
                ],
            },
        }
    )
    geometry = {key: spec.pop(key) for key in ["data", "transform", "mark", "encoding"]}
    spec["layer"] = [geometry, *state_label_layers()]
    return spec


# WHAT: Build a radio-site map with either equal-sized dots or count-scaled circles.
# WHY: The AM/FM version emphasises distribution; the digital-radio version also shows records per site.
def radio_map(digital=False):
    spec = base(580)
    spec.update({
        "description": "Digital-radio sites, with larger circles showing more issued licence records." if digital else "One dot for each registered site with an issued AM or FM radio licence.",
        "params": [{"name": "mapRegion", "value": "Australia", "bind": {
            "input": "select", "options": ["Australia", "Sydney", "Melbourne", "Brisbane", "Perth"],
            "name": "Show area  ",
        }}],
        "projection": {
            "type": "conicEqualArea", "parallels": [-18, -36],
            "rotate": {"expr": "mapRegion === 'Sydney' ? [-151,0,0] : mapRegion === 'Melbourne' ? [-145,0,0] : mapRegion === 'Brisbane' ? [-153,0,0] : mapRegion === 'Perth' ? [-116,0,0] : [-134,0,0]"},
            "center": {"expr": "mapRegion === 'Sydney' ? [0,-33.8] : mapRegion === 'Melbourne' ? [0,-37.8] : mapRegion === 'Brisbane' ? [0,-27.4] : mapRegion === 'Perth' ? [0,-31.9] : [0,-28]"},
            "scale": {"expr": "mapRegion === 'Australia' ? min(width * 1.38, height * 1.45) : min(width,height) * 27"},
            "translate": {"expr": "[width/2,height/2]"},
        },
        "layer": [
            {"data": {"url": "data/au_states.topojson", "format": {"type": "topojson", "feature": "states"}},
             "mark": {"type": "geoshape", "clip": True, "fill": "#cbdce3", "stroke": "#526476", "strokeWidth": 1.5}},
            {
                "data": {"url": "data/digital_radio_sites.csv" if digital else "data/radio_sites.csv"},
                "mark": {"type": "circle", "clip": True, "stroke": CREAM, "strokeWidth": 0.7, "size": 36},
                "encoding": {
                    "longitude": {"field": "longitude", "type": "quantitative"},
                    "latitude": {"field": "latitude", "type": "quantitative"},
                    "tooltip": [
                        {"field": "name", "title": "Licensed site"},
                        {"field": "site_id", "title": "ACMA site ID"},
                        {"field": "state", "title": "State"},
                        {"field": "dr" if digital else "am", "type": "quantitative", "title": "Digital-radio records" if digital else "AM licence records"},
                        *([] if digital else [{"field": "fm", "type": "quantitative", "title": "FM licence records"}]),
                    ],
                },
            },
        ],
    })
    marks = spec["layer"][1]["encoding"]
    if digital:
        marks["size"] = {"field": "dr", "type": "quantitative", "scale": {"domain": [0, 3], "range": [0, 960]},
                         "legend": {"title": "Licence records per site", "orient": "top", "values": [1, 2, 3], "format": "d"}}
        marks["color"] = {"value": GREEN}
    else:
        marks["color"] = {"field": "technology", "type": "nominal",
                          "scale": {"domain": ["AM", "FM", "AM + FM"], "range": [MAGENTA, BLUE, GREEN]},
                          "legend": {"title": "One dot = one site", "orient": "top"}}
    for layer in state_label_layers():
        layer.setdefault("transform", []).append({"filter": "mapRegion === 'Australia'"})
        spec["layer"].append(layer)
    spec["layer"].append({
        "name": "context_city_label",
        "data": {"values": [{}]},
        "transform": [{"filter": "mapRegion !== 'Australia'"}],
        "mark": {"type": "text", "font": "Inter", "fontSize": 14, "fontWeight": 700,
                 "align": "left", "baseline": "top", "color": INK,
                 "text": {"expr": "mapRegion + ' area · licensed sites'"}},
        "encoding": {"x": {"value": 6}, "y": {"value": 6}},
    })
    return spec


# WHAT: Dorling cartogram: circle area represents population and colour represents inclusion score.
# WHY: Replacing land area with population reduces the visual dominance of large, sparsely populated states.
def state_cartogram():
    with (ROOT / "data/population_cartogram.csv").open(encoding="utf-8") as handle:
        sample = next(csv.DictReader(handle))
    extent_x, extent_y = float(sample["extent_x"]), float(sample["extent_y"])
    scale = f"min(width / {extent_x}, (height - 185) / {extent_y})"
    spec = base(900)
    spec.update({
        "description": "A map of population circles: area shows March 2026 residents, while colour shows digital inclusion based on 2024 data.",
        "data": {"url": "data/population_cartogram.csv"},
        "transform": [
            {"calculate": f"datum.cartogram_x * {scale} + (width - datum.extent_x * {scale}) / 2", "as": "pixel_x"},
            {"calculate": f"100 + datum.cartogram_y * {scale} + (height - 185 - datum.extent_y * {scale}) / 2", "as": "pixel_y"},
            {"calculate": f"4 * pow(datum.radius * {scale}, 2)", "as": "symbol_size"},
        ],
        "encoding": {
            "x": {"field": "pixel_x", "type": "quantitative", "scale": None, "axis": None},
            "y": {"field": "pixel_y", "type": "quantitative", "scale": None, "axis": None},
        },
        "layer": [
            {"name": "cartogram_states",
             "mark": {"type": "circle", "stroke": CREAM, "strokeWidth": 1.5},
             "encoding": {
                 "size": {"field": "symbol_size", "type": "quantitative", "scale": None},
                 "color": {"field": "score", "type": "quantitative",
                           "scale": {"domain": [68, 80], "range": ["#edf5ef", GREEN]},
                           "legend": {"title": "Digital inclusion score", "orient": "top"}},
                 "tooltip": [
                     {"field": "state_name", "title": "State / territory"},
                     {"field": "population", "type": "quantitative", "format": ",.0f", "title": "Residents (March 2026 estimate)"},
                     {"field": "score", "type": "quantitative", "format": ".1f", "title": "Digital inclusion score (out of 100)"},
                 ],
             }},
            {"mark": {"type": "text", "font": "Inter", "fontSize": 14, "fontWeight": 750},
             "encoding": {"text": {"field": "state"},
                          "color": {"condition": {"test": "contrast('white', scale('color', datum.score)) > contrast('#000000', scale('color', datum.score))", "value": "white"}, "value": "#000000"}}},
            {"name": "context_population_key",
             "transform": [{"filter": "datum.state === 'NSW'"}],
             "mark": {"type": "circle", "fill": "transparent", "stroke": INK, "strokeWidth": 1.2},
             "encoding": {
                 "x": {"value": {"expr": "width / 2 - 80"}},
                 "y": {"value": {"expr": "height - 42"}},
                 "size": {"value": {"expr": f"4 * pow(20 * {scale}, 2)"}},
                 "tooltip": {"value": "This circle represents one million residents"},
             }},
            {"name": "context_population_label",
             "transform": [{"filter": "datum.state === 'NSW'"}],
             "mark": {"type": "text", "text": ["1 million residents", "Circle size · March 2026"],
                      "align": "left", "font": "Inter", "fontSize": 13, "lineHeight": 15, "color": INK},
             "encoding": {
                 "x": {"value": {"expr": f"width / 2 - 68 + 20 * {scale}"}},
                 "y": {"value": {"expr": "height - 48"}},
                 "tooltip": {"value": None},
             }},
        ],
    })
    return spec


# WHAT: Compare the three trust findings from their own survey on one percentage scale.
# WHY: Aligned bar lengths are easier to compare than separate large-number cards.
def news_trust():
    spec = base(230)
    spec.update({
        "description": "Trust in three types of news, from a separate 2026 survey of Australian news consumers.",
        "data": {"url": "data/news_indicators.csv"},
        "transform": [
            {"filter": "datum.topic === 'Trust'"},
            {"calculate": "datum.group === 'News I use' ? 'News they use' : datum.group", "as": "label"},
            {"calculate": "format(datum.percent, '.0f') + '%'", "as": "value_label"},
        ],
        "encoding": {
            "y": {"field": "group", "type": "ordinal", "axis": None,
                  "sort": ["News I use", "News on social media", "News from AI chatbots"]},
            "tooltip": [{"field": "label", "title": "Type of news"},
                        {"field": "percent", "type": "quantitative", "format": ".0f", "title": "Trust (%)"},
                        {"field": "source", "title": "Separate survey"}],
        },
        "layer": [
            {"name": "trust_bars", "mark": {"type": "bar", "color": GREEN, "size": 18},
             "encoding": {"x": {"field": "percent", "type": "quantitative",
                                "scale": {"domain": [0, 100], "nice": False},
                                "axis": {"title": "Trust (%)", "values": [0, 25, 50, 75, 100]}}}},
            {"name": "trust_labels", "mark": {"type": "text", "align": "left", "dy": -21,
                                               "font": "Inter", "fontSize": 14, "color": INK},
             "encoding": {"x": {"value": 0}, "text": {"field": "label"}}},
            {"name": "trust_values", "mark": {"type": "text", "align": "left", "dx": 7,
                                               "font": "Inter", "fontSize": 14, "fontWeight": 700, "color": INK},
             "encoding": {"x": {"field": "percent", "type": "quantitative"},
                          "text": {"field": "value_label"}}},
        ],
    })
    return spec


# WHAT: Build the charts with stable file numbers and attach annotations and interactions.
# WHY: One generator keeps the numbered specifications and manifest consistent.
def main():
    SPECS.mkdir(exist_ok=True)
    charts = {
        "hero-waffle": waffle(),
        "media-horizon": horizon(),
        "streaming-fta-connected": connected_scatter(),
        "age-media-heatmap": age_heatmap(),
        "age-parallel-profile": parallel_profiles(),
        "video-hours-bullet": bullet_hours(),
        "video-service-bump": service_bump(),
        "device-slope": device_slope(),
        "audio-age-heatmap": audio_heatmap(),
        "audio-location-network": audio_network(),
        "news-age": news_age(),
        "adii-choropleth": state_choropleth(),
        "adii-cartogram": state_cartogram(),
        "metro-regional": metro_regional(),
        "radio-symbol-map": radio_map(digital=True),
        "radio-dot-map": radio_map(),
        "news-trust": news_trust(),
    }
    for chart_id, specification in charts.items():
        specification.setdefault("usermeta", {})["chart"] = chart_id
    add_callout(
        charts["streaming-fta-connected"],
        "Free-to-air TV use rose again in 2025. Streaming's growth does not mean everyone has left TV behind.",
        [{"filter": "datum.year === 2025"}],
        {"x": {"field": "paid_streaming", "type": "quantitative"},
         "y": {"field": "free_to_air", "type": "quantitative"}},
    )
    add_callout(
        charts["age-parallel-profile"],
        "Paid video leads here. Other formats still have users; the mix is not all online.",
        [{"filter": "datum.age === (hoveredSeries !== '' ? hoveredSeries : selectedAge === 'All' ? '75+' : selectedAge)"},
         {"window": [{"op": "row_number", "as": "callout_rank"}], "sort": [{"field": "percent", "order": "descending"}]},
         {"filter": "datum.callout_rank === 1"}],
        {"x": {"field": "metric", "type": "ordinal", "sort": MEDIA_ORDER},
         "y": {"field": "percent", "type": "quantitative"}},
        alternate=("datum.metric === 'Free-to-air TV'",
                   "Free-to-air TV leads here, but online media still reaches many in this age group."),
    )
    add_callout(
        charts["video-hours-bullet"],
        "Beyond the tick means more hours than the national mean, not more viewers.",
        [{"window": [{"op": "row_number", "as": "callout_rank"}], "sort": [{"field": "hours", "order": "descending"}]},
         {"filter": "datum.callout_rank === 1"}],
        {"x": {"field": "hours", "type": "quantitative"},
         "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER}},
        alternate=("videoFormat === 'Free-to-air TV'",
                   "Older adults spend longer watching TV. Viewer counts alone miss this difference."),
    )
    add_callout(
        charts["device-slope"],
        "Smart-TV use grew more than phone use. Streaming is part of watching TV at home, not just on the go.",
        [{"filter": "datum.year === 2025 && datum.device === 'Smart TV'"}],
        {"x": {"field": "year", "type": "ordinal"},
         "y": {"field": "percent", "type": "quantitative"}},
    )
    add_callout(
        charts["news-age"],
        "Most older adults use online news and information too. Using it does not tell us whether they trust it.",
        [{"filter": "datum.age === '75+'"}],
        {"x": {"field": "percent", "type": "quantitative"},
         "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER}},
    )
    add_callout(
        charts["metro-regional"],
        "Regional groups use more FM radio and free-to-air TV. Similar podcast use shows they are not simply offline.",
        [{"filter": "datum.metric === 'FM radio'"}],
        {"x": {"field": "regional", "type": "quantitative"},
         "y": {"field": "metric", "type": "nominal", "sort": MEDIA_ORDER}},
    )
    add_callout(
        charts["adii-cartogram"],
        "NSW stands out when size shows people rather than land. Colour shows digital inclusion, not how many people use media.",
        [{"filter": "datum.state === 'NSW'"},
         {"calculate": "datum.pixel_y - sqrt(datum.symbol_size) / 2", "as": "callout_edge_y"}],
        {"x": {"field": "pixel_x", "type": "quantitative", "scale": None, "axis": None},
         "y": {"field": "callout_edge_y", "type": "quantitative", "scale": None, "axis": None}},
    )
    add_focus(charts["age-parallel-profile"], "age", "selectedAge", AGE_ORDER, "Pin age group  ")
    add_focus(charts["video-service-bump"], "service", "selectedService", SERVICE_ORDER, "Pin service  ")
    add_focus(charts["device-slope"], "device", "selectedDevice", DEVICE_ORDER, "Pin device  ")
    add_focus(charts["audio-location-network"], "format", "audioFocus", AUDIO_ORDER, "Pin audio format  ", "All formats")
    manifest = []
    for number, (name, spec) in enumerate(charts.items(), start=1):
        filename = write(name, spec, number)
        manifest.append({"number": number, "id": name, "file": filename})
    with (SPECS / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(f"Built {len(charts)} Vega-Lite specifications in {SPECS}")


if __name__ == "__main__":
    main()
