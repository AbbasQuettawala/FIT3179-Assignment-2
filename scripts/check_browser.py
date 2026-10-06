#!/usr/bin/env python3
"""Check the served page with Playwright and capture review screenshots."""

import argparse
import csv
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path(".cache/browser-review"))
    options = parser.parse_args()
    options.output.mkdir(parents=True, exist_ok=True)
    with (Path(__file__).resolve().parents[1] / "data/population_cartogram.csv").open() as source:
        populations = [int(row["population"]) for row in csv.DictReader(source)]
    with (Path(__file__).resolve().parents[1] / "data/audio_locations.csv").open() as source:
        audio_locations = list(csv.DictReader(source))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width in [1366, 1024, 390]:
            page = browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
            failures = []
            page.on("pageerror", lambda error: failures.append(str(error)))
            page.goto(options.url, wait_until="networkidle")
            for chart in page.locator(".chart").all():
                chart.scroll_into_view_if_needed()
                page.wait_for_function(
                    "element => ['ready','error'].includes(element.dataset.status)",
                    arg=chart.element_handle(),
                )
            assert page.locator('.chart[data-status="ready"]').count() == 16, page.locator(".chart-error").all_text_contents()
            assert not failures, failures
            areas = page.locator('#media-horizon .mark-area path').evaluate_all(
                "paths => paths.filter(path => path.getBBox().height > 1 && path.getBBox().width > 1).length"
            )
            assert areas >= 8, f"Horizon has only {areas} visible bands"
            overflow = page.evaluate("""() => [...document.querySelectorAll('.chart svg')]
                .filter(svg => svg.closest('.vega-embed') && svg.getBoundingClientRect().width > 50)
                .filter(svg => svg.getBoundingClientRect().right > innerWidth + 2)
                .map(svg => svg.closest('.chart').id)""")
            assert not overflow, f"Clipped chart at {width}px: {overflow}"
            clipped_labels = page.evaluate("""() => [...document.querySelectorAll('.chart text')]
                .filter(text => {
                    const bounds = text.getBoundingClientRect();
                    const frame = text.closest('.chart').getBoundingClientRect();
                    return bounds.left < frame.left - 2 || bounds.right > frame.right + 2;
                }).map(text => text.closest('.chart').id + ': ' + text.textContent)""")
            assert not clipped_labels, f"Clipped labels at {width}px: {clipped_labels}"
            annotated = ["streaming-fta-connected", "age-parallel-profile", "video-hours-bullet",
                         "device-slope", "news-age", "metro-regional", "adii-cartogram"]
            for chart_id in annotated:
                callout = page.locator(f"#{chart_id} .callout_text_marks text")
                assert callout.count() == 1, f"Missing or duplicated annotation: {chart_id}"
                assert len(callout.text_content()) > 60, f"Non-explanatory annotation: {chart_id}"
            assert "Paid video leads" in page.locator("#age-parallel-profile .callout_text_marks").text_content()
            page.locator('#age-parallel-profile select').select_option("75+")
            assert page.evaluate("chartViews.get('age-parallel-profile').signal('selectedAge')") == "75+"
            page.wait_for_function("document.querySelector('#age-parallel-profile .callout_text_marks').textContent.includes('Free-to-air leads')")
            page.locator('#video-hours-bullet select').select_option("Paid streaming")
            assert page.evaluate("chartViews.get('video-hours-bullet').signal('videoFormat')") == "Paid streaming"
            page.wait_for_function("document.querySelector('#video-hours-bullet .callout_text_marks').textContent.includes('longest bar')")
            for audio_format in dict.fromkeys(row["format"] for row in audio_locations):
                page.locator("#audio-location-network select").select_option(audio_format)
                page.wait_for_function("format => chartViews.get('audio-location-network').signal('audioFocus') === format", arg=audio_format)
                expected = sorted(float(row["percent"]) for row in audio_locations if row["format"] == audio_format)
                readings = page.locator("#audio-location-network .audio_readout_marks text").all_text_contents()
                assert len(readings) == 3 and all(value.endswith("%") for value in readings)
                actual = sorted(float(value[:-1]) for value in readings)
                assert all(abs(displayed - source) <= 0.051 for displayed, source in zip(actual, expected)), (audio_format, actual, expected)
                if audio_format == "FM radio":
                    page.locator("#audio-location-network").screenshot(path=str(options.output / f"audio-network-traced-{width}.png"))
            page.locator("#audio-location-network select").select_option("All formats")
            assert page.locator("#audio-location-network .audio_readout_marks text").count() == 0
            page.locator('#state-focus').select_option("TAS")
            page.wait_for_function("['adii-choropleth','adii-cartogram','radio-symbol-map','radio-dot-map'].every(name => chartViews.get(name).signal('stateFocus') === 'TAS')")
            page.locator('#state-focus').select_option("All")
            for map_id in ["radio-symbol-map", "radio-dot-map"]:
                assert page.locator(f"#{map_id} .state_labels_marks text").count() == 8
                for region in ["Sydney", "Melbourne", "Brisbane", "Perth"]:
                    page.locator(f'#{map_id} select').select_option(region)
                    page.wait_for_function("([name, region]) => chartViews.get(name).signal('mapRegion') === region", arg=[map_id, region])
                    assert page.locator(f"#{map_id} .state_labels_marks text").count() == 0
                    assert region in page.locator(f"#{map_id} .context_city_label_marks").text_content()
                    if width == 1366:
                        page.locator(f'#{map_id}').screenshot(path=str(options.output / f"{map_id}-{region}.png"))
                page.locator(f'#{map_id} select').select_option("Australia")
            circles = page.locator('#adii-cartogram .cartogram_states_marks path').evaluate_all(
                "paths => paths.map(path => {const box = path.getBoundingClientRect(); return {x: box.x + box.width/2, y: box.y + box.height/2, radius: box.width/2};})"
            )
            assert len(circles) == 8, f"Expected 8 cartogram circles, found {len(circles)}"
            for index, left in enumerate(circles):
                for right in circles[index + 1:]:
                    distance = ((left["x"] - right["x"]) ** 2 + (left["y"] - right["y"]) ** 2) ** 0.5
                    assert distance >= left["radius"] + right["radius"] - 1, "Cartogram overlap"
            area_ratio = (max(circle["radius"] for circle in circles) / min(circle["radius"] for circle in circles)) ** 2
            assert abs(area_ratio - max(populations) / min(populations)) < 0.1, "Circle areas do not represent population"
            key_radius = page.locator("#adii-cartogram .context_population_key_marks path").evaluate("path => path.getBoundingClientRect().width / 2")
            assert abs((max(circle["radius"] for circle in circles) / key_radius) ** 2 - max(populations) / 1_000_000) < 0.05, "Population area key uses a different scale"
            assert page.locator("#adii-choropleth .state_labels_marks text").count() == 8
            assert page.locator('#radio-dot-map .mark-symbol.role-mark path').count() == 1574
            assert page.locator('#radio-symbol-map .mark-symbol.role-mark path').count() == 29
            state_shapes = page.locator('#adii-choropleth .mark-shape.role-mark path')
            assert state_shapes.count() == 8, "A state disappeared during geometry cleaning"
            assert state_shapes.evaluate_all("paths => paths.every(path => path.getBBox().width > 0 && path.getBBox().height > 0)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.locator('.source-notes li[id]').count() == 7
            page.locator('#age-parallel-profile select').select_option("18–24")
            page.locator('#video-hours-bullet select').select_option("Free-to-air TV")
            page.screenshot(path=str(options.output / f"page-{width}.png"), full_page=True)
            for chart in page.locator(".chart").all():
                chart.screenshot(path=str(options.output / f"{chart.get_attribute('id')}-{width}.png"))
            if width == 1366:
                page.locator("#age-parallel-profile select").select_option("75+")
                page.locator("#video-hours-bullet select").select_option("Paid streaming")
                page.locator("#audio-location-network select").select_option("FM radio")
                page.locator("#state-focus").select_option("TAS")
                page.locator("#radio-dot-map select").select_option("Sydney")
                for resized_width in [390, 1024]:
                    page.set_viewport_size({"width": resized_width, "height": 900})
                    page.wait_for_function("""() => [...document.querySelectorAll('.chart')].every(
                        element => element.dataset.status === 'ready' &&
                        element.dataset.compact === String(element.clientWidth < 560))""")
                    assert page.evaluate("chartViews.get('age-parallel-profile').signal('selectedAge')") == "75+"
                    assert page.evaluate("chartViews.get('video-hours-bullet').signal('videoFormat')") == "Paid streaming"
                    assert page.evaluate("chartViews.get('audio-location-network').signal('audioFocus')") == "FM radio"
                    assert page.evaluate("chartViews.get('radio-dot-map').signal('mapRegion')") == "Sydney"
                    assert page.evaluate("chartViews.get('adii-cartogram').signal('stateFocus')") == "TAS"
                    assert page.evaluate("""() => [...document.querySelectorAll('.chart text')].every(text => {
                        const bounds = text.getBoundingClientRect();
                        const frame = text.closest('.chart').getBoundingClientRect();
                        return bounds.left >= frame.left - 2 && bounds.right <= frame.right + 2;
                    })"""), f"Labels clipped after live resize to {resized_width}"
                assert not failures, failures
                print("Live desktop/mobile resizing preserves age, video, audio, state and city selections without clipped labels.")
            print(f"{width}px: 16 charts, seven explanatory callouts, dynamic age/format text, eight states and all controls passed; cartogram areas/collisions and radio marks checked; no clipping or page errors")
            page.close()
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        page.route("**/specs/hero-waffle.json", lambda route: route.fulfill(status=503, body="Temporary failure"))
        page.goto(options.url, wait_until="networkidle")
        page.wait_for_selector('#hero-waffle[data-status="error"]')
        assert page.locator('#hero-waffle button').inner_text() == "Retry chart"
        assert page.locator('#hero-title').is_visible()
        page.unroute("**/specs/hero-waffle.json")
        page.locator('#hero-waffle button').click()
        page.wait_for_selector('#hero-waffle[data-status="ready"]')
        print("Failed chart retains narrative and recovers through Retry chart.")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
