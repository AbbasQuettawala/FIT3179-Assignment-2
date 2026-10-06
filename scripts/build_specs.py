#!/usr/bin/env python3
"""Generate the readable Vega-Lite specifications used by the webpage."""

from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path


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
CATEGORICAL = ["#24665a", "#914859", "#355f91", "#854689", "#946218", "#496a31", "#9f4329", "#536069"]

AGE_ORDER = ["18–24", "25–34", "35–44", "45–54", "55–64", "65–74", "75+"]
MEDIA_ORDER = ["Paid video", "Short-form video", "Music streaming", "Podcasts", "Free-to-air TV", "FM radio"]
AUDIO_ORDER = ["Music streaming", "Podcasts", "Internet radio", "DAB+ radio", "FM radio", "AM radio"]


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
            "labelFontSize": 12,
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
            "labelFontSize": 11,
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


def base(height: int = 320):
    return {
        "$schema": SCHEMA,
        "width": "container",
        "height": height,
        "autosize": {"type": "fit", "contains": "padding"},
        "config": config(),
    }


def write(name: str, spec: dict):
    if name.startswith(("adii-", "radio-")):
        spec.setdefault("params", []).append({"name": "stateFocus", "value": "All"})
        layers = spec.get("layer", [spec])
        for layer in layers:
            if "encoding" in layer and not layer.get("name", "").startswith(("callout_", "context_")):
                layer["encoding"]["opacity"] = {
                    "condition": {"test": "stateFocus === 'All' || datum.state === stateFocus", "value": 1},
                    "value": 0.22,
                }

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
    with (SPECS / f"{name}.json").open("w", encoding="utf-8") as handle:
        json.dump(spec, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def callout_text(message):
    wide = json.dumps("\n".join(textwrap.wrap(message, width=58)), ensure_ascii=False)
    narrow = json.dumps("\n".join(textwrap.wrap(message, width=29)), ensure_ascii=False)
    return f"width < 360 ? {narrow} : {wide}"


def add_callout(spec, message, transforms, anchor, alternate=None, reserve=True):
    spec["config"]["axisX"] = {"grid": False}
    if reserve:
        spec["height"] += 100

        def reserve_header(node):
            if isinstance(node, dict):
                vertical = node.get("encoding", {}).get("y")
                if vertical is not None and "field" in vertical:
                    scale = vertical.setdefault("scale", {})
                    if scale is not None:
                        scale["range"] = [100, {"expr": "height"}] if vertical.get("type") in {"nominal", "ordinal"} else [{"expr": "height"}, 100]
                for value in node.values():
                    reserve_header(value)
            elif isinstance(node, list):
                for value in node:
                    reserve_header(value)

        reserve_header(spec)
    expression = callout_text(message)
    if alternate:
        condition, other_message = alternate
        expression = f"({condition}) ? ({callout_text(other_message)}) : ({expression})"
    spec["layer"].extend([
        {
            "name": "callout_leader",
            "transform": transforms,
            "mark": {"type": "rule", "color": SLATE, "strokeWidth": 1, "strokeDash": [3, 3]},
            "encoding": {
                **anchor, "x2": {"value": {"expr": "min(width * 0.8, 280)"}},
                "y2": {"value": {"expr": f"10 + 15 * length(split(({expression}), '\\n'))"}},
                "tooltip": {"value": None},
            },
        },
        {
            "name": "callout_text",
            "transform": transforms,
            "mark": {
                "type": "text", "text": {"expr": expression}, "font": "Inter",
                "fontSize": 11, "lineHeight": 15, "lineBreak": "\n",
                "align": "left", "baseline": "top", "color": INK,
            },
            "encoding": {"x": {"value": 4}, "y": {"value": 5}, "tooltip": {"value": None}},
        },
    ])


def waffle():
    spec = base(210)
    spec.update(
        {
            "description": "A 100-cell waffle showing online video reach in Australia in 2025.",
            "data": {"sequence": {"start": 0, "stop": 100, "step": 1, "as": "cell"}},
            "transform": [
                {"calculate": "datum.cell % 10", "as": "column"},
                {"calculate": "9 - floor(datum.cell / 10)", "as": "row"},
            ],
            "mark": {"type": "square", "filled": True, "size": 310, "cornerRadius": 2},
            "encoding": {
                "x": {"field": "column", "type": "ordinal", "axis": None},
                "y": {"field": "row", "type": "ordinal", "axis": None},
                "color": {
                    "condition": {"test": "datum.cell < 95", "value": GREEN},
                    "value": "#d8ded8",
                    "legend": None,
                },
                "tooltip": {"value": "95 in every 100 Australians used online video in the past six months"},
            },
        }
    )
    return spec


def horizon():
    spec = base(370)
    spec["description"] = "Four horizon rows with 10-percentage-point bands folded onto a shared baseline."
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
                        "title": ["Change vs first measured year", "(percentage points)"], "titleLimit": 290,
                        "orient": "top", "columns": 4, "symbolType": "square",
                        "labelExpr": "datum.value < 0 ? format(datum.value * 10, '+d') + ' to ' + format((datum.value + 1) * 10, '+d') : format((datum.value - 1) * 10, '+d') + ' to ' + format(datum.value * 10, '+d')",
                    },
                },
                "tooltip": [
                    {"field": "metric", "title": "Medium"},
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
                {"field": "metric", "title": "Medium"},
                {"field": "year", "type": "ordinal", "title": "Year"},
                {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Weekly use (%)"},
                {"field": "change", "type": "quantitative", "format": "+.1f", "title": "Change (percentage points)"},
            ],
        },
    })
    spec["layer"].append({
        "transform": [{"filter": "datum.year === 2025 && datum.band === 1"}, {"calculate": "datum.y0 + 11.5", "as": "label_y"}, {"calculate": "datum.metric + '  ' + format(datum.change, '+.1f') + ' pp · since ' + (datum.metric === 'Short-form video' ? '2022' : '2017')", "as": "label"}],
        "mark": {"type": "text", "align": "left", "font": "Inter", "fontSize": 11, "fontWeight": 700, "color": INK},
        "encoding": {"x": {"datum": 2017}, "y": {"field": "label_y", "type": "quantitative"}, "text": {"field": "label"}},
    })
    return spec


def connected_scatter():
    spec = base(390)
    spec.update(
        {
            "description": "A connected scatterplot contrasting paid streaming and free-to-air viewing.",
            "data": {"url": "data/streaming_fta.csv", "format": {"type": "csv", "parse": {"year": "number"}}},
            "layer": [
                {
                    "mark": {"type": "line", "stroke": INK, "strokeWidth": 2.5, "interpolate": "linear"},
                    "encoding": {
                        "x": {"field": "paid_streaming", "type": "quantitative", "scale": {"zero": False}, "axis": {"title": "Used paid streaming in past 7 days (%)"}},
                        "y": {"field": "free_to_air", "type": "quantitative", "scale": {"zero": False}, "axis": {"title": "Watched free-to-air TV in past 7 days (%)"}},
                        "order": {"field": "year", "type": "ordinal"},
                    },
                },
                {
                    "mark": {"type": "circle", "size": 125, "stroke": CREAM, "strokeWidth": 2},
                    "encoding": {
                        "x": {"field": "paid_streaming", "type": "quantitative"},
                        "y": {"field": "free_to_air", "type": "quantitative"},
                        "color": {"field": "year", "type": "quantitative", "scale": {"scheme": "viridis"}, "legend": {"title": "Year", "orient": "top", "format": "d"}},
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


def age_heatmap():
    spec = base(330)
    spec.update(
        {
            "description": "Six-month reach of eight selected video services across seven age groups.",
            "data": {"url": "data/video_services_age.csv"},
            "layer": [
                {
                    "mark": {"type": "rect", "cornerRadius": 3},
                    "encoding": {
                        "x": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age", "labelAngle": 0}},
                        "y": {"field": "service", "type": "ordinal", "sort": ["YouTube", "Netflix", "Prime Video", "Disney+", "TikTok", "Stan", "Kayo", "Binge"], "axis": {"title": None}},
                        "color": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100], "range": ["#edf5ef", GREEN]}, "legend": {"title": "% over six months", "orient": "top"}},
                        "tooltip": [
                            {"field": "age", "title": "Age"},
                            {"field": "service", "title": "Service"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Share (%)"},
                            {"field": "base_n", "type": "quantitative", "title": "Base n"},
                        ],
                    },
                },
                {
                    "mark": {"type": "text", "font": "Inter", "fontSize": 10, "fontWeight": 650},
                    "encoding": {
                        "x": {"field": "age", "type": "ordinal", "sort": AGE_ORDER},
                        "y": {"field": "service", "type": "ordinal", "sort": ["YouTube", "Netflix", "Prime Video", "Disney+", "TikTok", "Stan", "Kayo", "Binge"]},
                        "text": {"field": "percent", "type": "quantitative", "format": ".0f"},
                        "color": {"condition": {"test": "datum.percent > 86", "value": "white"}, "value": "#000000"},
                    },
                },
            ],
        }
    )
    return spec


def parallel_profiles():
    spec = base(360)
    spec.update(
        {
            "description": "Interactive parallel coordinates showing each age group's cross-media profile.",
            "data": {"url": "data/age_media.csv"},
            "transform": [{"calculate": "indexof(" + json.dumps(MEDIA_ORDER) + ", datum.metric)", "as": "metric_position"}],
            "params": [{"name": "selectedAge", "value": "18–24", "bind": {"input": "select", "options": AGE_ORDER, "name": "Highlight age  "}}],
            "layer": [
                {
                    "mark": {"type": "line", "point": {"filled": True, "size": 45}},
                    "encoding": {
                        "x": {"field": "metric", "type": "ordinal", "sort": MEDIA_ORDER, "axis": {"title": None, "labelAngle": -28, "labelLimit": 110}},
                        "y": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100]}, "axis": {"title": "Past-week use (%)"}},
                        "detail": {"field": "age"},
                        "color": {"condition": {"test": "datum.age === selectedAge", "value": MAGENTA}, "value": SLATE},
                        "opacity": {"condition": {"test": "datum.age === selectedAge", "value": 1}, "value": 0.16},
                        "strokeWidth": {"condition": {"test": "datum.age === selectedAge", "value": 4}, "value": 1.2},
                        "order": {"field": "metric_position", "type": "quantitative"},
                        "tooltip": [
                            {"field": "age", "title": "Age"},
                            {"field": "metric", "title": "Medium"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Share (%)"},
                        ],
                    },
                }
            ],
        }
    )
    return spec


def bullet_hours():
    spec = base(330)
    spec.update(
        {
            "description": "Bullet bars comparing reported weekly video hours by age with the national benchmark.",
            "data": {"url": "data/video_hours_age.csv"},
            "params": [{"name": "videoFormat", "value": "Free-to-air TV", "bind": {"input": "select", "options": ["Free-to-air TV", "Paid streaming", "Short-form video", "FTA catch-up", "Pay TV", "Pay-per-view"], "name": "Compare format  "}}],
            "transform": [{"filter": "datum.metric === videoFormat"}],
            "layer": [
                {
                    "mark": {"type": "bar", "height": 30, "color": PALE},
                    "encoding": {
                        "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER},
                        "x": {"field": "national_hours", "type": "quantitative"},
                    },
                },
                {
                    "mark": {"type": "bar", "cornerRadiusEnd": 4, "height": 22},
                    "encoding": {
                        "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age"}},
                        "x": {"field": "hours", "type": "quantitative", "scale": {"domain": [0, 16]}, "axis": {"title": "Average hours in past 7 days"}},
                        "color": {"condition": {"test": "datum.hours >= datum.national_hours", "value": GREEN}, "value": MINT},
                        "tooltip": [
                            {"field": "age", "title": "Age"},
                            {"field": "hours", "type": "quantitative", "format": ".1f", "title": "Hours"},
                            {"field": "national_hours", "type": "quantitative", "format": ".1f", "title": "National"},
                            {"field": "base_n", "type": "quantitative", "title": "Respondents (base n)"},
                            {"field": "metric", "title": "Video format"},
                        ],
                    },
                },
                {
                    "mark": {"type": "tick", "color": MAGENTA, "thickness": 3, "size": 28},
                    "encoding": {
                        "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER},
                        "x": {"field": "national_hours", "type": "quantitative"},
                    },
                },
                {
                    "mark": {"type": "text", "align": "left", "dx": 6, "font": "Inter", "fontWeight": 700, "color": INK},
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


def service_bump():
    spec = base(390)
    spec.update(
        {
            "description": "Ranks within eight selected video services, all measured from 2021 to 2025.",
            "data": {"url": "data/video_services.csv", "format": {"type": "csv", "parse": {"year": "number"}}},
            "transform": [
                {"window": [{"op": "rank", "as": "rank"}], "sort": [{"field": "percent", "order": "descending"}], "groupby": ["year"]},
            ],
            "layer": [
                {
                    "mark": {"type": "line", "point": {"filled": True, "size": 68}, "strokeWidth": 2.6},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal", "axis": {"title": None, "labelAngle": 0}},
                        "y": {"field": "rank", "type": "quantitative", "scale": {"domain": [1, 8], "reverse": True}, "axis": {"title": "Rank among selected services", "tickMinStep": 1}},
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
                    "mark": {"type": "text", "align": "left", "dx": 7, "dy": -8, "font": "Inter", "fontSize": 10, "fontWeight": 700},
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


def device_slope():
    spec = base(370)
    spec.update(
        {
            "description": "A slopegraph showing how online video devices changed between 2021 and 2025.",
            "data": {"url": "data/video_devices.csv", "format": {"type": "csv", "parse": {"year": "number"}}},
            "layer": [
                {
                    "mark": {"type": "line", "strokeWidth": 2.7},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal", "axis": {"title": None, "labelAngle": 0, "labelFontSize": 13, "labelFontWeight": 700}},
                        "y": {"field": "percent", "type": "quantitative", "axis": {"title": "Use for online video at home (%)"}},
                        "detail": {"field": "device"},
                        "color": {"field": "device", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                        "tooltip": [
                            {"field": "device", "title": "Device"},
                            {"field": "year", "title": "Year"},
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Share (%)"},
                        ],
                    },
                },
                {
                    "mark": {"type": "point", "filled": True, "size": 85},
                    "encoding": {
                        "x": {"field": "year", "type": "ordinal"},
                        "y": {"field": "percent", "type": "quantitative"},
                        "color": {"field": "device", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                    },
                },
                {
                    "transform": [{"filter": "datum.year === 2025"}, {"calculate": "(datum.device === 'Chromecast / Google TV' ? 'Google TV' : datum.device === 'Games console' ? 'Console' : datum.device) + ' ' + format(datum.percent, '.0f') + '%'", "as": "label"}],
                    "mark": {"type": "text", "align": "left", "dx": 7, "dy": {"expr": "datum.device === 'Games console' ? -5 : datum.device === 'Apple TV' ? 5 : 0"}, "font": "Inter", "fontSize": 11, "fontWeight": 650},
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


def audio_heatmap():
    spec = base(320)
    spec.update(
        {
            "description": "A heatmap of weekly audio format use by age.",
            "data": {"url": "data/audio_age.csv"},
            "mark": {"type": "rect", "cornerRadius": 3},
            "encoding": {
                "x": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age", "labelAngle": 0}},
                "y": {"field": "metric", "type": "ordinal", "sort": AUDIO_ORDER, "axis": {"title": None}},
                "color": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 80], "range": ["#eef1ec", MINT, GREEN]}, "legend": {"title": "% in past week", "orient": "top"}},
                "tooltip": [
                    {"field": "age", "title": "Age"},
                    {"field": "metric", "title": "Format"},
                    {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Share (%)"},
                    {"field": "base_n", "type": "quantitative", "title": "Base n"},
                ],
            },
        }
    )
    return spec


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
    spec = base(350)
    spec.update(
        {
            "description": "A bipartite network linking audio formats to the places Australians listen.",
            "data": {"url": "data/audio_locations.csv"},
            "params": [{"name": "audioFocus", "value": "All formats", "bind": {
                "input": "select", "options": ["All formats", *AUDIO_ORDER], "name": "Trace a format  ",
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
                            {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Share (%)"},
                            {"field": "base_n", "type": "quantitative", "title": "Base n"},
                        ],
                    },
                },
                {
                    "data": {"values": formats},
                    "mark": {"type": "circle", "size": 155, "stroke": CREAM, "strokeWidth": 2},
                    "encoding": {
                        "x": {"field": "x", "type": "quantitative"},
                        "y": {"field": "y", "type": "quantitative"},
                        "color": {"field": "name", "type": "nominal", "scale": {"range": CATEGORICAL}, "legend": None},
                        "opacity": {"condition": {"test": "audioFocus === 'All formats' || datum.name === audioFocus", "value": 1}, "value": 0.25},
                    },
                },
                {
                    "data": {"values": formats},
                    "mark": {"type": "text", "align": "right", "dx": -10, "font": "Inter", "fontSize": 11, "fontWeight": 650, "color": INK},
                    "encoding": {"x": {"field": "x", "type": "quantitative"}, "y": {"field": "y", "type": "quantitative"}, "text": {"field": "name"}},
                },
                {
                    "data": {"values": locations},
                    "mark": {"type": "circle", "size": 180, "color": INK, "stroke": CREAM, "strokeWidth": 2},
                    "encoding": {"x": {"field": "x", "type": "quantitative"}, "y": {"field": "y", "type": "quantitative"}},
                },
                {
                    "data": {"values": locations},
                    "mark": {"type": "text", "align": "left", "dx": 10, "font": "Inter", "fontSize": 11, "fontWeight": 700, "color": INK},
                    "encoding": {"x": {"field": "x", "type": "quantitative"}, "y": {"field": "y", "type": "quantitative"}, "text": {"field": "name"}},
                },
                {
                    "name": "audio_readout",
                    "transform": [{"filter": "datum.format === audioFocus"},
                                  {"calculate": "format(datum.percent, '.1f') + '%'", "as": "reading"}],
                    "mark": {"type": "text", "align": "left", "dx": 10, "dy": 16,
                             "font": "Inter", "fontSize": 11, "fontWeight": 700, "color": GREEN},
                    "encoding": {
                        "x": {"datum": 0.86}, "y": {"field": "location_y", "type": "quantitative"},
                        "text": {"field": "reading"},
                    },
                },
            ],
        }
    )
    return spec


def news_age():
    spec = base(300)
    spec.update({
        "description": "Six-month online news and information reach among ACMA survey age groups, 2025.",
        "data": {"url": "data/news_age.csv"},
        "encoding": {
            "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER, "axis": {"title": "Age"}},
            "x": {"field": "percent", "type": "quantitative", "scale": {"domain": [0, 100]},
                  "axis": {"title": "Accessed news and information online (%)"}},
            "tooltip": [
                {"field": "age", "title": "Age"},
                {"field": "percent", "type": "quantitative", "format": ".1f", "title": "Six-month reach (%)"},
                {"field": "base_n", "type": "quantitative", "title": "Respondent base"},
            ],
        },
        "layer": [
            {"mark": {"type": "circle", "size": 125, "color": GREEN, "opacity": 1}},
            {"mark": {"type": "text", "dx": -12, "align": "right", "font": "Inter", "color": INK},
             "encoding": {"text": {"field": "percent", "type": "quantitative", "format": ".1f"}}},
        ],
    })
    return spec


def metro_regional():
    spec = base(340)
    spec.update({
        "description": "Paired weekly media-use estimates for metro and regional respondents in 2025.",
        "data": {"url": "data/metro_regional.csv"},
        "encoding": {
            "y": {"field": "metric", "type": "nominal", "sort": MEDIA_ORDER, "axis": {"title": None}},
            "x": {"type": "quantitative", "scale": {"domain": [0, 100]}, "axis": {"title": "Past-week use (%)"}},
        },
        "layer": [
            {"mark": {"type": "rule", "strokeWidth": 3, "color": "#bbc9bf"},
             "encoding": {"x": {"field": "metro"}, "x2": {"field": "regional"}}},
            {"transform": [{"fold": ["metro", "regional"], "as": ["region", "percent"]}],
             "mark": {"type": "point", "filled": True, "size": 100, "opacity": 1},
             "encoding": {
                 "x": {"field": "percent"},
                 "color": {"field": "region", "type": "nominal",
                           "scale": {"domain": ["metro", "regional"], "range": [BLUE, MAGENTA]},
                           "legend": {"title": "Location", "orient": "top"}},
                 "shape": {"field": "region", "type": "nominal",
                           "scale": {"domain": ["metro", "regional"], "range": ["circle", "diamond"]}},
                 "tooltip": [
                     {"field": "metric", "title": "Weekly behaviour"},
                     {"field": "metro", "format": ".1f", "type": "quantitative", "title": "Metro (%)"},
                     {"field": "regional", "format": ".1f", "type": "quantitative", "title": "Regional (%)"},
                     {"field": "gap", "format": "+.1f", "type": "quantitative", "title": "Regional minus metro (points)"},
                     {"field": "metro_base_n", "title": "Metro base"},
                     {"field": "regional_base_n", "title": "Regional base"},
                 ],
             }},
        ],
    })
    return spec


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


def state_choropleth():
    spec = base(420)
    spec.update(
        {
            "description": "A state choropleth of Australian Digital Inclusion Index scores.",
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
                "color": {"field": "score", "type": "quantitative", "scale": {"domain": [68, 80], "range": ["#edf5ef", GREEN]}, "legend": {"title": "ADII score", "orient": "top"}},
                "tooltip": [
                    {"field": "state", "title": "State / territory"},
                    {"field": "score", "type": "quantitative", "format": ".1f", "title": "ADII score"},
                    {"field": "gap", "type": "quantitative", "format": "+.1f", "title": "vs national"},
                ],
            },
        }
    )
    geometry = {key: spec.pop(key) for key in ["data", "transform", "mark", "encoding"]}
    spec["layer"] = [geometry, *state_label_layers()]
    return spec


def radio_map(digital=False):
    spec = base(470)
    spec.update({
        "description": "Issued digital-radio licence records per site." if digital else "Unique physical sites with issued AM and/or FM licences.",
        "params": [{"name": "mapRegion", "value": "Australia", "bind": {
            "input": "select", "options": ["Australia", "Sydney", "Melbourne", "Brisbane", "Perth"],
            "name": "Map view  ",
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
             "mark": {"type": "geoshape", "clip": True, "fill": "#e5ebe5", "stroke": "#b9c7be", "strokeWidth": 1}},
            {
                "data": {"url": "data/digital_radio_sites.csv" if digital else "data/radio_sites.csv"},
                "mark": {"type": "circle", "clip": True, "stroke": CREAM, "strokeWidth": 0.7, "size": 22},
                "encoding": {
                    "longitude": {"field": "longitude", "type": "quantitative"},
                    "latitude": {"field": "latitude", "type": "quantitative"},
                    "tooltip": [
                        {"field": "name", "title": "Licensed site"},
                        {"field": "site_id", "title": "ACMA site ID"},
                        {"field": "state", "title": "State"},
                        {"field": "dr" if digital else "am", "type": "quantitative", "title": "Digital-radio records" if digital else "AM assignments"},
                        *([] if digital else [{"field": "fm", "type": "quantitative", "title": "FM assignments"}]),
                    ],
                },
            },
        ],
    })
    marks = spec["layer"][1]["encoding"]
    if digital:
        marks["size"] = {"field": "dr", "type": "quantitative", "scale": {"domain": [0, 3], "range": [0, 600]},
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
        "mark": {"type": "text", "font": "Inter", "fontSize": 12, "fontWeight": 700,
                 "align": "left", "baseline": "top", "color": INK,
                 "text": {"expr": "mapRegion + ' area · licensed sites'"}},
        "encoding": {"x": {"value": 6}, "y": {"value": 6}},
    })
    return spec


def state_cartogram():
    with (ROOT / "data/population_cartogram.csv").open(encoding="utf-8") as handle:
        sample = next(csv.DictReader(handle))
    extent_x, extent_y = float(sample["extent_x"]), float(sample["extent_y"])
    scale = f"min(width / {extent_x}, (height - 185) / {extent_y})"
    spec = base(615)
    spec.update({
        "description": "Dorling cartogram: area represents March 2026 residents; colour separately represents ADII 2024 fieldwork.",
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
                           "legend": {"title": "ADII score", "orient": "top"}},
                 "tooltip": [
                     {"field": "state_name", "title": "State / territory"},
                     {"field": "population", "type": "quantitative", "format": ",.0f", "title": "Residents (March 2026 estimate)"},
                     {"field": "score", "type": "quantitative", "format": ".1f", "title": "ADII index score"},
                 ],
             }},
            {"mark": {"type": "text", "font": "Inter", "fontSize": 12, "fontWeight": 750},
             "encoding": {"text": {"field": "state"},
                          "color": {"condition": {"test": "datum.score >= 75", "value": "white"}, "value": INK}}},
            {"name": "context_population_key",
             "transform": [{"filter": "datum.state === 'NSW'"}],
             "mark": {"type": "circle", "fill": "transparent", "stroke": INK, "strokeWidth": 1.2},
             "encoding": {
                 "x": {"value": {"expr": "width / 2 - 80"}},
                 "y": {"value": {"expr": "height - 42"}},
                 "size": {"value": {"expr": f"4 * pow(20 * {scale}, 2)"}},
                 "tooltip": {"value": "Area reference: one million residents"},
             }},
            {"name": "context_population_label",
             "transform": [{"filter": "datum.state === 'NSW'"}],
             "mark": {"type": "text", "text": ["1 million residents", "Area key · March 2026"],
                      "align": "left", "font": "Inter", "fontSize": 11, "lineHeight": 15, "color": INK},
             "encoding": {
                 "x": {"value": {"expr": f"width / 2 - 68 + 20 * {scale}"}},
                 "y": {"value": {"expr": "height - 48"}},
                 "tooltip": {"value": None},
             }},
        ],
    })
    return spec


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
        "metro-regional": metro_regional(),
        "adii-choropleth": state_choropleth(),
        "adii-cartogram": state_cartogram(),
        "radio-symbol-map": radio_map(digital=True),
        "radio-dot-map": radio_map(),
    }
    add_callout(
        charts["streaming-fta-connected"],
        "The FTA rebound interrupts the longer shift towards streaming: broadcast viewing has not simply disappeared.",
        [{"filter": "datum.year === 2025"}],
        {"x": {"field": "paid_streaming", "type": "quantitative"},
         "y": {"field": "free_to_air", "type": "quantitative"}},
    )
    add_callout(
        charts["age-parallel-profile"],
        "Paid video leads this age profile, but broadcast formats still reach part of the group. Media habits overlap.",
        [{"filter": "datum.age === selectedAge"},
         {"window": [{"op": "row_number", "as": "callout_rank"}], "sort": [{"field": "percent", "order": "descending"}]},
         {"filter": "datum.callout_rank === 1"}],
        {"x": {"field": "metric", "type": "ordinal", "sort": MEDIA_ORDER},
         "y": {"field": "percent", "type": "quantitative"}},
        alternate=("datum.metric === 'Free-to-air TV'",
                   "Free-to-air leads this age profile, yet digital formats still reach some of the same age group. Habits overlap."),
    )
    add_callout(
        charts["video-hours-bullet"],
        "The longest bar shows heavier viewing, not a larger audience: hours are averaged across each age-group base.",
        [{"window": [{"op": "row_number", "as": "callout_rank"}], "sort": [{"field": "hours", "order": "descending"}]},
         {"filter": "datum.callout_rank === 1"}],
        {"x": {"field": "hours", "type": "quantitative"},
         "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER}},
        alternate=("videoFormat === 'Free-to-air TV'",
                   "Older adults spend longer with broadcast TV. Reach alone misses how much viewing time this medium occupies."),
    )
    add_callout(
        charts["device-slope"],
        "Smart TVs gain more than phones here: online video is also a living-room habit, not just a mobile one.",
        [{"filter": "datum.year === 2025 && datum.device === 'Smart TV'"}],
        {"x": {"field": "year", "type": "ordinal"},
         "y": {"field": "percent", "type": "quantitative"}},
    )
    add_callout(
        charts["news-age"],
        "Older respondents still report broad online reach. This question measures news and information access, not trust.",
        [{"filter": "datum.age === '75+'"}],
        {"x": {"field": "percent", "type": "quantitative"},
         "y": {"field": "age", "type": "ordinal", "sort": AGE_ORDER}},
    )
    news_leader = charts["news-age"]["layer"][-2]
    elbow = {
        **news_leader,
        "name": "callout_elbow",
        "encoding": {
            **news_leader["encoding"],
            "x": {"value": {"expr": "width - 2"}},
            "x2": {"value": {"expr": "width - 2"}},
        },
    }
    news_leader["encoding"]["x2"] = {"value": {"expr": "width - 2"}}
    news_leader["encoding"]["y2"] = {"field": "age"}
    charts["news-age"]["layer"].append(elbow)
    add_callout(
        charts["metro-regional"],
        "Regional audiences lean more towards FM and broadcast TV; the tiny podcast gap challenges a simple online/offline divide.",
        [{"filter": "datum.metric === 'FM radio'"}],
        {"x": {"field": "regional", "type": "quantitative"},
         "y": {"field": "metric", "type": "nominal", "sort": MEDIA_ORDER}},
    )
    add_callout(
        charts["adii-cartogram"],
        "NSW gains visual weight when residents, not land, determine area. Colour still measures inclusion, not audience size.",
        [{"filter": "datum.state === 'NSW'"},
         {"calculate": "datum.pixel_y - sqrt(datum.symbol_size) / 2", "as": "callout_edge_y"}],
        {"x": {"field": "pixel_x", "type": "quantitative", "scale": None, "axis": None},
         "y": {"field": "callout_edge_y", "type": "quantitative", "scale": None, "axis": None}},
        reserve=False,
    )
    for name, spec in charts.items():
        write(name, spec)
    with (SPECS / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(list(charts), handle, indent=2)
        handle.write("\n")
    print(f"Built {len(charts)} Vega-Lite specifications in {SPECS}")


if __name__ == "__main__":
    main()
