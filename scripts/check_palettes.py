#!/usr/bin/env python3
"""Check the final ocean palette, label contrast and obsolete saved preferences."""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


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
            page.add_init_script("localStorage.setItem('different-feeds-palette', 'plum')")
            page.goto(options.url, wait_until="networkidle")
            for chart in page.locator(".chart").all():
                chart.scroll_into_view_if_needed()
                page.wait_for_function("element => element.dataset.status === 'ready'", arg=chart.element_handle())
            assert page.locator("#palette-choice").count() == 0
            assert page.locator("html").get_attribute("data-palette") == "ocean"
            assert page.locator(".chart svg.marks").count() == 17
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.evaluate("""() => {
                const colour = document.createElement('span');
                colour.style.color = palette.colours.primary;
                return ['age-media-heatmap', 'audio-age-heatmap', 'adii-choropleth', 'adii-cartogram'].every(
                    name => chartViews.get(name).scale('color').range()[1] === colour.style.color);
            }""")
            assert page.evaluate("""() => {
                const luminance = vega.expressionFunction('luminance');
                return ['growth', 'fall'].every(direction => {
                    const levels = palette[direction].map(luminance);
                    return levels.slice(1).every((value, index) => direction === 'growth'
                        ? value < levels[index] : value > levels[index]);
                });
            }""")
            contrast = page.evaluate("""() => {
                const contrast = vega.expressionFunction('contrast');
                const ratios = [];
                for (const [name, field] of [['age-media-heatmap', 'percent'], ['audio-age-heatmap', 'percent'], ['adii-cartogram', 'score']]) {
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
            assert len(contrast) == 106 and min(contrast) >= 4.5, (width, len(contrast), min(contrast))
            assert page.evaluate("""() => {
                const contrast = vega.expressionFunction('contrast');
                const colours = palette.colours;
                return ['ink', 'primary', 'accent', 'muted'].every(token =>
                    ['paper', 'paper-deep'].every(background => contrast(colours[token], colours[background]) >= 4.5));
            }""")
            assert page.evaluate("""() => {
                const contrast = vega.expressionFunction('contrast');
                const backgrounds = [...document.querySelectorAll('.chapter')]
                    .map(section => getComputedStyle(section).backgroundColor);
                const textColours = ['ink', 'primary', 'accent', 'muted'].map(token => palette.colours[token]);
                const seriesColours = chartViews.get('video-service-bump').scale('color').range();
                return new Set(backgrounds).size === 4 && new Set(seriesColours).size === 8 &&
                    backgrounds.every(background => textColours.every(colour => contrast(colour, background) >= 4.5) &&
                        seriesColours.every(colour => contrast(colour, background) >= 3));
            }"""), 'Text or series colours lack contrast against a section background'
            assert page.locator('.story-bridge').evaluate_all("""bridges => bridges.every(bridge => {
                const style = getComputedStyle(bridge);
                return parseFloat(style.fontSize) >= 18 && parseInt(style.fontWeight) >= 600 &&
                    style.color === 'rgb(23, 42, 58)';
            })"""), 'Transitions should stand out from body text'
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            page.screenshot(path=str(options.output / f"ocean-{width}.png"))
            assert not failures, failures
            page.close()
        page = browser.new_page()
        page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('Storage disabled');}})")
        page.goto(options.url, wait_until="networkidle")
        page.wait_for_selector('#hero-waffle[data-status="ready"][data-palette="ocean"]')
        for width in [320, 768]:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("""() => {
                const header = document.querySelector('.site-header').getBoundingClientRect();
                const story = document.querySelector('.hero-copy').getBoundingClientRect();
                return header.bottom <= story.top && document.documentElement.scrollWidth <= innerWidth;
            }"""), f"Header overlap at {width}px"
        browser.close()
        print("Ocean palette, 106 label contrasts, obsolete preferences and unavailable storage passed.")


if __name__ == "__main__":
    main()
