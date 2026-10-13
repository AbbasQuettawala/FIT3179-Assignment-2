#!/usr/bin/env python3
"""Check palette switching, chart contrast and saved preferences in a browser."""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def wait_for_palette(page, palette):
    page.wait_for_function("""palette => [...document.querySelectorAll('.chart')].every(
        element => element.dataset.status === 'ready' && element.dataset.palette === palette &&
        element.dataset.compact === String(element.clientWidth < 560))""", arg=palette)


def check_selections(page):
    expected = {
        "age-parallel-profile": ["selectedAge", "75+"],
        "video-hours-bullet": ["videoFormat", "Paid streaming"],
        "audio-location-network": ["audioFocus", "FM radio"],
        "adii-cartogram": ["stateFocus", "TAS"],
        "radio-dot-map": ["mapRegion", "Sydney"],
    }
    assert page.evaluate("""expected => Object.entries(expected).every(
        ([name, [signal, value]]) => chartViews.get(name).signal(signal) === value)""", expected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path(".cache/palette-review"))
    options = parser.parse_args()
    options.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width in [1366, 390]:
            page = browser.new_page(viewport={"width": width, "height": 900})
            failures = []
            page.on("pageerror", lambda error: failures.append(str(error)))
            page.goto(options.url, wait_until="networkidle")
            for chart in page.locator(".chart").all():
                chart.scroll_into_view_if_needed()
                page.wait_for_function("element => element.dataset.status === 'ready'", arg=chart.element_handle())
            source_specs = page.evaluate("JSON.stringify([...chartSpecifications])")
            page.locator("#age-parallel-profile select").select_option("75+")
            page.locator("#video-hours-bullet select").select_option("Paid streaming")
            page.locator("#audio-location-network select").select_option("FM radio")
            page.locator("#state-focus").select_option("TAS")
            page.locator("#radio-dot-map select").select_option("Sydney")
            for palette in ["ocean", "editorial", "plum", "original"]:
                page.locator("#palette-choice").select_option(palette)
                wait_for_palette(page, palette)
                check_selections(page)
                assert page.locator(".chart svg.marks").count() == 16
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert page.evaluate("JSON.stringify([...chartSpecifications])") == source_specs
                assert page.evaluate("""() => {
                    const colour = document.createElement('span');
                    colour.style.color = palettes[activePalette].colours.primary;
                    return ['age-media-heatmap', 'adii-choropleth', 'adii-cartogram'].every(
                        name => chartViews.get(name).scale('color').range()[1] === colour.style.color);
                }""")
                assert page.evaluate("""() => {
                    const luminance = vega.expressionFunction('luminance');
                    return ['growth', 'fall'].every(direction => {
                        const levels = palettes[activePalette][direction].map(luminance);
                        return levels.slice(1).every((value, index) => direction === 'growth'
                            ? value < levels[index] : value > levels[index]);
                    });
                }"""), f"Unordered horizon bands: {palette}"
                contrast = page.evaluate("""() => {
                    const contrast = vega.expressionFunction('contrast');
                    const ratios = [];
                    for (const [name, field] of [['age-media-heatmap', 'percent'], ['adii-cartogram', 'score']]) {
                        const view = chartViews.get(name);
                        const inspect = item => {
                            if (item.mark?.marktype === 'text' && item.datum?.[field] !== undefined &&
                                (field === 'percent' || item.text === item.datum.state)) {
                                ratios.push(contrast(item.fill, view.scale('color')(item.datum[field])));
                            }
                            item.items?.forEach(inspect);
                        };
                        inspect(view.scenegraph().root);
                    }
                    return ratios;
                }""")
                assert len(contrast) == 64 and min(contrast) >= 4.5, (palette, len(contrast), min(contrast))
                if palette != "original":
                    assert page.evaluate("""() => {
                        const contrast = vega.expressionFunction('contrast');
                        const colours = palettes[activePalette].colours;
                        return ['ink', 'primary', 'accent', 'muted'].every(token =>
                            ['paper', 'paper-deep'].every(background => contrast(colours[token], colours[background]) >= 4.5));
                    }"""), f"Low-contrast page text: {palette}"
                page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                page.screenshot(path=str(options.output / f"{palette}-{width}.png"))
                for chart_id in ["media-horizon", "adii-cartogram"]:
                    page.locator(f"#{chart_id}").screenshot(path=str(options.output / f"{palette}-{chart_id}-{width}.png"))
                print(f"{width}px {palette}: all 16 charts; selections retained; 64 chart labels meet 4.5:1 contrast.")
            page.evaluate("""() => {
                const choice = document.getElementById('palette-choice');
                for (const palette of ['editorial', 'ocean', 'original', 'plum']) {
                    choice.value = palette;
                    choice.dispatchEvent(new Event('change'));
                }
            }""")
            page.set_viewport_size({"width": 390 if width == 1366 else 1366, "height": 900})
            wait_for_palette(page, "plum")
            check_selections(page)
            assert page.locator(".chart svg.marks").count() == 16
            page.reload(wait_until="networkidle")
            assert page.locator("#palette-choice").input_value() == "plum"
            page.locator("#hero-waffle").scroll_into_view_if_needed()
            page.wait_for_selector('#hero-waffle[data-status="ready"][data-palette="plum"]')
            assert not failures, failures
            page.close()
        page = browser.new_page()
        page.add_init_script("localStorage.setItem('different-feeds-palette', 'not-a-palette')")
        page.goto(options.url, wait_until="networkidle")
        assert page.locator("#palette-choice").input_value() == "ocean"
        page.close()
        page = browser.new_page()
        page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('Storage disabled');}})")
        page.goto(options.url, wait_until="networkidle")
        page.locator("#palette-choice").select_option("editorial")
        page.wait_for_selector('#hero-waffle[data-status="ready"][data-palette="editorial"]')
        for width in [320, 768]:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("""() => {
                const header = document.querySelector('.site-header').getBoundingClientRect();
                const story = document.querySelector('.hero-copy').getBoundingClientRect();
                return header.bottom <= story.top && document.documentElement.scrollWidth <= innerWidth;
            }"""), f"Header overlap at {width}px"
        page.close()
        browser.close()
        print("Rapid switching, live resizing, saved preferences and unavailable storage passed.")


if __name__ == "__main__":
    main()
