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
        for width in [1366, 1024, 768, 390, 320]:
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
            assert page.locator('.chart[data-status="ready"]').count() == 17, page.locator(".chart-error").all_text_contents()
            assert not failures, failures
            expected_sections = {
                'shift': ['media-horizon', 'streaming-fta-connected'],
                'generations': ['age-media-heatmap', 'age-parallel-profile', 'video-hours-bullet',
                                'video-service-bump', 'device-slope'],
                'ears-eyes': ['audio-age-heatmap', 'audio-location-network', 'news-age', 'news-trust'],
                'access': ['metro-regional', 'adii-choropleth', 'adii-cartogram',
                           'radio-symbol-map', 'radio-dot-map'],
            }
            for section, expected in expected_sections.items():
                actual = page.locator(f'#{section} .chart').evaluate_all('charts => charts.map(chart => chart.id)')
                assert actual == expected, f'Chart order breaks the story in {section}: {actual}'
            assert page.locator('.chart-summary').evaluate_all("""summaries => summaries.every(summary => {
                const box = summary.getBoundingClientRect();
                const title = summary.parentElement.querySelector('h3').getBoundingClientRect();
                return Math.abs(box.left - title.left) < 2 && box.top >= title.bottom;
            })"""), 'Key findings should sit below their chart titles, aligned left'
            assert page.locator('#palette-choice').count() == 0
            assert page.locator('#news-trust .trust_values_marks text').all_text_contents() == ['54%', '21%', '19%']
            assert page.locator('#news-trust .trust_bars_marks path').count() == 3
            assert page.locator('#news-trust .trust_bars_marks path').evaluate_all("""bars => {
                const widths = bars.map(bar => bar.getBBox().width);
                return Math.abs(widths[1] / widths[0] - 21 / 54) < 0.001 &&
                    Math.abs(widths[2] / widths[0] - 19 / 54) < 0.001;
            }""")
            assert page.locator('h1, .chapter-heading h2, .closing h2, .pull-quote p').evaluate_all("""headings =>
                headings.every(heading => getComputedStyle(heading).fontFamily.startsWith('Inter') &&
                    !heading.textContent.trim().endsWith('.') &&
                    getComputedStyle(heading).color === 'rgb(23, 42, 58)')""")
            assert page.locator('html').get_attribute('data-palette') == 'ocean'
            assert page.locator('#hero-waffle .hero_tiles_marks path').count() == 100
            assert page.locator('#hero-waffle .hero_play_icons_marks path').count() == 95
            assert page.locator('#hero-waffle .hero_total_marks text').text_content() == '95 in 100'
            assert page.locator('#hero-waffle .hero_tiles_marks path').evaluate_all("""tiles => {
                const counts = new Map();
                for (const tile of tiles) {
                    const fill = tile.getAttribute('fill');
                    counts.set(fill, (counts.get(fill) || 0) + 1);
                }
                return JSON.stringify([...counts.values()].sort((left, right) => left - right)) === '[5,95]';
            }""")
            assert page.evaluate("""() => {
                const size = selector => parseFloat(getComputedStyle(document.querySelector(selector)).fontSize);
                return size('h1') >= 30 && size('h1') <= 44 && size('.chapter-heading h2') <= 28 && size('.viz-heading h3') >= 22 && size('.viz-heading h3') <= 26 &&
                    size('.chart-source') < size('.annotation');
            }"""), 'Headings or sources overwhelm the chart narrative'
            assert page.locator('.annotation').evaluate_all("""notes => notes.every(note => {
                const style = getComputedStyle(note);
                return style.backgroundColor === 'rgba(0, 0, 0, 0)' && style.borderLeftWidth === '0px' &&
                    style.fontWeight === '400' && style.color === 'rgb(23, 42, 58)' &&
                    style.fontSize === '16px' && !note.querySelector('span, strong, b');
            })"""), 'Explanations should be plain dark paragraphs'
            assert page.locator('.viz-card, .hero-visual').evaluate_all("""cards => cards.every(card => {
                const style = getComputedStyle(card);
                return style.borderRadius === '0px' && style.boxShadow === 'none';
            })"""), 'Chart panels should be flat with square corners'
            assert page.locator('#media-horizon svg.marks').bounding_box()['height'] >= 680
            assert abs(page.locator('#hero-waffle svg.marks').bounding_box()['height'] - 340) <= 1
            if width >= 1024:
                hero_ratio = page.locator('.hero-visual').bounding_box()['width'] / page.locator('.hero-copy').bounding_box()['width']
                assert 1.45 <= hero_ratio <= 1.55
                assert page.locator('h1').evaluate('heading => parseFloat(getComputedStyle(heading).fontSize)') > 32
                assert page.locator('.hero').bounding_box()['width'] <= 1200
                assert page.locator('.annotation').evaluate_all("notes => notes.every(note => note.clientWidth <= 850)")
                assert page.locator('.chapter-heading').evaluate_all("headings => headings.every(heading => getComputedStyle(heading).gridTemplateColumns.split(' ').length === 1)")
                assert page.locator('#video-hours-bullet .bullet_bars_marks path').evaluate_all(
                    "bars => bars.every(bar => bar.getBBox().height >= 32)"
                )
                assert page.locator('#age-media-heatmap .mark-text.role-mark text').evaluate_all(
                    "labels => labels.every(label => parseFloat(getComputedStyle(label).fontSize) >= 13)"
                )
            areas = page.locator('#media-horizon .mark-area path').evaluate_all(
                "paths => paths.filter(path => path.getBBox().height > 1 && path.getBBox().width > 1).length"
            )
            assert areas >= 8, f"Horizon has only {areas} visible bands"
            assert "Catch-up TV" in page.locator("#media-horizon svg.marks").text_content()
            overflow = page.evaluate("""() => [...document.querySelectorAll('.chart svg')]
                .filter(svg => svg.closest('.vega-embed') && svg.getBoundingClientRect().width > 50)
                .filter(svg => svg.getBoundingClientRect().right > innerWidth + 2)
                .map(svg => svg.closest('.chart').id)""")
            assert not overflow, f"Clipped chart at {width}px: {overflow}"
            clipped_labels = page.evaluate("""() => [...document.querySelectorAll('.chart text')]
                .filter(text => {
                    if (!text.getClientRects().length) return false;
                    const bounds = text.getBoundingClientRect();
                    const frame = text.closest('.chart').getBoundingClientRect();
                    return bounds.left < frame.left - 2 || bounds.right > frame.right + 2;
                }).map(text => text.closest('.chart').id + ': ' + text.textContent)""")
            assert not clipped_labels, f"Clipped labels at {width}px: {clipped_labels}"
            for heatmap, count in [('age-media-heatmap', 56), ('audio-age-heatmap', 42)]:
                assert page.locator(f'#{heatmap} .mark-text.role-mark text').count() == count
            assert page.locator('#video-hours-bullet .bullet_bars_marks path').count() == 7
            assert page.locator('#video-hours-bullet .bullet_average_marks path').count() == 7
            assert "Bar length = average hours" in page.locator('#video-hours-bullet svg.marks').text_content()
            assert "Tick: national average" in page.locator('#video-hours-bullet svg.marks').text_content()
            for map_id in ['radio-symbol-map', 'radio-dot-map']:
                assert 300 <= page.locator(f'#{map_id} svg.marks').bounding_box()['height'] <= 580
            assert page.locator('.chart-reading').count() == 16
            assert page.locator('.annotation').evaluate_all("notes => notes.every(note => note.textContent.trim().split(/\\s+/).length >= 45)")
            annotated = ["streaming-fta-connected", "age-parallel-profile", "video-hours-bullet",
                         "device-slope", "news-age", "metro-regional", "adii-cartogram"]
            for chart_id in annotated:
                callout = page.locator(f"#{chart_id} .callout_text_marks text")
                assert callout.count() == 1, f"Missing or duplicated annotation: {chart_id}"
                assert not callout.text_content().lstrip().startswith('1.'), chart_id
                assert page.locator(f'#{chart_id} .callout_number_marks').count() == 0
                assert len(callout.text_content()) > 60, f"Non-explanatory annotation: {chart_id}"
                assert page.locator(f"#{chart_id} .callout_leader_marks line[stroke-dasharray]").count() == 0
                if width <= 390:
                    assert page.locator(f"#{chart_id}").locator('xpath=..').locator('.annotation').is_visible()
            assert page.locator('.chart-callout-note').count() == 0, 'Do not duplicate the main explanation on mobile'
            assert page.locator('.viz-card').evaluate_all("""cards => cards.every(card => {
                const plot = card.querySelector(':scope > .chart');
                const explanation = card.querySelector(':scope > .annotation');
                return !plot || !explanation || explanation.getBoundingClientRect().top >= plot.getBoundingClientRect().bottom;
            })"""), 'Main chart explanations must follow the chart, not sit beside it'
            assert "Free-to-air TV leads here" in page.locator("#age-parallel-profile .callout_text_marks").text_content()
            page.locator('#age-parallel-profile select').select_option("75+")
            assert page.evaluate("chartViews.get('age-parallel-profile').signal('selectedAge')") == "75+"
            page.wait_for_function("document.querySelector('#age-parallel-profile .callout_text_marks').textContent.includes('Free-to-air TV leads')")
            assert page.locator('#video-hours-bullet option[value="FTA catch-up"]').inner_text() == "Catch-up TV"
            page.locator('#video-hours-bullet select').select_option("FTA catch-up")
            assert page.evaluate("chartViews.get('video-hours-bullet').signal('videoFormat')") == "FTA catch-up"
            page.locator('#video-hours-bullet select').select_option("Paid streaming")
            assert page.evaluate("chartViews.get('video-hours-bullet').signal('videoFormat')") == "Paid streaming"
            page.wait_for_function("document.querySelector('#video-hours-bullet .callout_text_marks').textContent.includes('Beyond the tick')")
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
            page.locator('#age-parallel-profile select').select_option("All")
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
                        if (!text.getClientRects().length) return true;
                        const bounds = text.getBoundingClientRect();
                        const frame = text.closest('.chart').getBoundingClientRect();
                        return bounds.left >= frame.left - 2 && bounds.right <= frame.right + 2;
                    })"""), f"Labels clipped after live resize to {resized_width}"
                assert not failures, failures
                print("Live desktop/mobile resizing preserves age, video, audio, state and city selections without clipped labels.")
            print(f"{width}px: 17 charts including trust bars, seven explanatory callouts, dynamic age/format text, eight states and all controls passed; cartogram areas/collisions and radio marks checked; no clipping or page errors")
            page.close()
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        page.route("**/specs/1.hero_waffle.json", lambda route: route.fulfill(status=503, body="Temporary failure"))
        page.goto(options.url, wait_until="networkidle")
        page.wait_for_selector('#hero-waffle[data-status="error"]')
        assert page.locator('#hero-waffle button').inner_text() == "Retry chart"
        assert page.locator('#hero-title').is_visible()
        page.unroute("**/specs/1.hero_waffle.json")
        page.locator('#hero-waffle button').click()
        page.wait_for_selector('#hero-waffle[data-status="ready"]')
        print("Failed chart retains narrative and recovers through Retry chart.")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
