#!/usr/bin/env python3
"""Exercise hover previews, pinned comparisons, touch and changing benchmarks."""

import argparse
import csv
from pathlib import Path

from playwright.sync_api import sync_playwright


FOCUS_CHARTS = [
    ("age-parallel-profile", "age", "selectedAge", "18–24", "75+", "All"),
    ("video-service-bump", "service", "selectedService", "YouTube", "Netflix", "All"),
    ("device-slope", "device", "selectedDevice", "Smart TV", "Mobile phone", "All"),
    ("audio-location-network", "name", "audioFocus", "FM radio", "Music streaming", "All formats"),
]


def ready(page, chart_id):
    page.locator(f"#{chart_id}").scroll_into_view_if_needed()
    page.wait_for_selector(f'#{chart_id}[data-status="ready"]')


def signal(page, chart_id, name, value):
    page.wait_for_function(
        "([chart, name, value]) => chartViews.get(chart).signal(name) === value",
        arg=[chart_id, name, value],
    )


def point(page, chart_id, field, value):
    marks = page.locator(f"#{chart_id} .mark-symbol.role-mark path")
    index = marks.evaluate_all("""(marks, [field, value]) => marks.findIndex(mark =>
        mark.__data__?.datum?.[field] === value &&
        !mark.closest('[class*="callout_"]'))""", [field, value])
    assert index >= 0, (chart_id, field, value)
    return marks.nth(index)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path(".cache/critique/interactions"))
    options = parser.parse_args()
    options.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.goto(options.url, wait_until="networkidle")
        for chart_id, field, parameter, first, second, all_value in FOCUS_CHARTS:
            ready(page, chart_id)
            signal(page, chart_id, parameter, all_value)
            point(page, chart_id, field, first).hover()
            signal(page, chart_id, "hoveredSeries", first)
            point(page, chart_id, field, first).click()
            signal(page, chart_id, parameter, first)
            page.mouse.move(1, 1)
            signal(page, chart_id, "hoveredSeries", "")
            point(page, chart_id, field, second).hover()
            signal(page, chart_id, "hoveredSeries", second)
            signal(page, chart_id, parameter, first)
            page.wait_for_function("""([chart, first, second]) => {
                const text = document.querySelector('#' + chart + ' .chart-detail').textContent;
                return text.includes(first) && text.includes(second);
            }""", arg=[chart_id, first, second])
            assert page.locator(f"#{chart_id} .chart-focus-status").text_content().startswith(f"Pinned: {first}")
            page.locator(f"#{chart_id}").screenshot(path=str(options.output / f"{chart_id}-comparison.png"))
            page.mouse.move(1, 1)
            signal(page, chart_id, "hoveredSeries", "")
            signal(page, chart_id, parameter, first)
            point(page, chart_id, field, first).click()
            signal(page, chart_id, parameter, all_value)
            selector = page.locator(f"#{chart_id} select")
            selector.focus()
            page.keyboard.press("Home")
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Tab")
            chosen = selector.input_value()
            assert chosen != all_value
            signal(page, chart_id, parameter, chosen)
            page.get_by_role("button", name="Clear pinned line").and_(page.locator(f"#{chart_id} button")).click()
            signal(page, chart_id, parameter, all_value)
            selector.select_option(first)
            print(f"{chart_id}: real hover, pin, simultaneous comparison, unpin, keyboard and clear passed.")
        for chart in page.locator(".chart").all():
            ready(page, chart.get_attribute("id"))
        colours = page.evaluate("Object.fromEntries(['age-parallel-profile','video-service-bump','device-slope','audio-location-network'].map(name => [name, chartViews.get(name).scale('color').range()]))")
        assert page.locator("#palette-choice").count() == 0
        assert page.locator("html").get_attribute("data-palette") == "ocean"
        for width in [390, 1024, 320, 1366]:
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_function("""() => [...document.querySelectorAll('.chart')].every(chart =>
                chart.dataset.status === 'ready' && chart.dataset.compact === String(chart.clientWidth < 560))""")
            for chart_id, field, parameter, first, second, all_value in FOCUS_CHARTS:
                signal(page, chart_id, parameter, first)
                signal(page, chart_id, "hoveredSeries", "")
            assert page.evaluate("expected => Object.entries(expected).every(([name, colours]) => JSON.stringify(chartViews.get(name).scale('color').range()) === JSON.stringify(colours))", colours)
        root = Path(__file__).resolve().parents[1]
        with (root / "data/video_hours_age.csv").open() as source:
            rows = list(csv.DictReader(source))
        for video_format in dict.fromkeys(row["metric"] for row in rows):
            page.locator("#video-hours-bullet select").select_option(video_format)
            signal(page, "video-hours-bullet", "videoFormat", video_format)
            group = [row for row in rows if row["metric"] == video_format]
            longest = max(group, key=lambda row: float(row["hours"]))
            label = "Catch-up TV" if video_format == "FTA catch-up" else video_format
            page.wait_for_function("""([label, age]) => {
                const text = document.querySelector('#video-hours-explanation').textContent;
                return text.startsWith(label + ':') && text.includes('aged ' + age);
            }""", arg=[label, longest["age"]])
            text = page.locator("#video-hours-explanation").text_content()
            assert f"{float(longest['hours']):.1f} hours" in text
            assert f"{float(longest['national_hours']):.1f} hours" in text
            assert page.locator("#video-hours-bullet .bullet_bars_marks path").count() == 7
            assert page.locator("#video-hours-bullet .bullet_average_marks path").count() == 7
            page.locator("#video-hours-bullet").screenshot(path=str(options.output / f"hours-{video_format.replace(' ', '-')}.png"))
        assert not failures, failures
        page.close()
        page = browser.new_page(viewport={"width": 390, "height": 900}, has_touch=True, is_mobile=True)
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.goto(options.url, wait_until="networkidle")
        for chart_id, field, parameter, first, second, all_value in FOCUS_CHARTS:
            ready(page, chart_id)
            point(page, chart_id, field, first).tap()
            signal(page, chart_id, parameter, first)
            point(page, chart_id, field, first).tap()
            signal(page, chart_id, parameter, all_value)
        assert not failures, failures
        browser.close()
        print("The fixed ocean palette, resizing, all six video formats and real touch pin/unpin passed.")


if __name__ == "__main__":
    main()
