#!/usr/bin/env python3
"""Audit source denominators, known values, joins and chart asset references."""

import csv
import json
import math
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from build_data import XlsxWorkbook, banner_records, select, study_year_records
from build_geography import STATES, POPULATION_PERIOD, decimal_degrees, population_data


ROOT = Path(__file__).resolve().parents[1]


def records(filename):
    with (ROOT / "data" / filename).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    watch = XlsxWorkbook(ROOT / ".cache/watch_listen.xlsx")
    national = study_year_records(watch, "QF4. Which of by Study year")
    paid = next(row for row in national if row["year"] == 2025 and row["category"].startswith("Paid subscription"))
    assert paid["base_n"] == 5990, "Base must use Column n (5990), not positive responses (4046)"
    assert round(paid["value"] * 100, 2) == 67.64
    age_audio = banner_records(watch, "QH3. Which of by PBI BANNER")
    young_am = next(row for row in age_audio if row["age"] == "18–24" and row["category"] == "AM radio" and row["year"] == 2025)
    assert young_am["base_n"] == 525, "Age denominator must not be the 43 AM-radio users"
    assert select([{"category": "AM radio", "year": 2025, "base_n": 525, "value": 0}], {"AM radio": "AM radio"}), "Preserve genuine measured zeroes"
    trends = records("media_trends.csv")
    assert min(int(row["year"]) for row in trends if row["metric"] == "Short-form video") == 2022
    horizon = records("horizon_trends.csv")
    for metric, year in {(row["metric"], row["year"]) for row in horizon}:
        bands = [row for row in horizon if row["metric"] == metric and row["year"] == year]
        assert {int(row["band"]) for row in bands} == {1, 2, 3, 4}
        assert math.isclose(sum(float(row["band_value"]) for row in bands), abs(float(bands[0]["change"])), abs_tol=0.01)
    weekly = records("age_media.csv")
    assert len(weekly) == 42 and all(row["metric"] != "Online news" for row in weekly)
    hours = records("video_hours_age.csv")
    assert len(hours) == 42 and len({row["metric"] for row in hours}) == 6
    assert all(float(row["national_hours"]) == 5.12 for row in hours if row["metric"] == "Free-to-air TV")
    assert next(row for row in records("news_indicators.csv") if row["topic"] == "Creator news")["group"] == "News consumers"
    services = records("video_services.csv")
    assert len(services) == 40 and {int(row["year"]) for row in services} == set(range(2021, 2026))
    service_ages = records("video_services_age.csv")
    assert len(service_ages) == 56
    assert {row["service"] for row in service_ages} == {row["service"] for row in services}
    internet = XlsxWorkbook(ROOT / ".cache/internet.xlsx")
    expected_news = {
        row["age"]: row for row in banner_records(internet, "QD8. Internet by PBI BANNER")
        if row["year"] == 2025 and row["category"] == "Accessing news and information online"
    }
    assert len(records("news_age.csv")) == len(expected_news) == 7
    for row in records("news_age.csv"):
        assert float(row["percent"]) == round(expected_news[row["age"]]["value"] * 100, 2)
        assert float(row["base_n"]) == expected_news[row["age"]]["base_n"]
    regional = records("metro_regional.csv")
    assert len(regional) == 6
    for row in regional:
        assert float(row["gap"]) == round(float(row["regional"]) - float(row["metro"]), 2)
        assert int(row["metro_base_n"]) == 4107 and int(row["regional_base_n"]) == 1880
    assert next(row for row in regional if row["metric"] == "FM radio")["gap"] == "8.06"
    assert decimal_degrees("35 12 60S") == -35.216667
    assert decimal_degrees("138 30 0E") == 138.5
    assert decimal_degrees("35 0 0N") == 35
    assert decimal_degrees("138 30 0W") == -138.5
    for invalid in ["unknown", "35 61 0S", "35 12 61S"]:
        try:
            decimal_degrees(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid coordinate accepted: {invalid}")
    licences = records("radio_licences.csv")
    keys = {(row["band"], row["licence"], row["technical_specification"], row["site_id"]) for row in licences}
    assert len(keys) == len(licences) and all(row["status"] == "Issued" for row in licences)
    radio = records("radio_sites.csv")
    digital = records("digital_radio_sites.csv")
    transmitter_book = XlsxWorkbook(ROOT / ".cache/BroadcastTransmitterExcel.xlsx")
    source_sites = {"AM": set(), "FM": set(), "DR": set()}
    for band in source_sites:
        rows = transmitter_book.rows(band)
        columns = {str(value).lower(): key for key, value in rows[0].items()}
        for row in rows[1:]:
            if row.get(columns["status"]) == "Issued" and row.get(columns["state"]) in STATES:
                source_sites[band].add(row[columns["site id"]])
    assert {row["site_id"] for row in radio} == source_sites["AM"] | source_sites["FM"]
    assert {row["site_id"] for row in digital} == source_sites["DR"]
    assert len(radio) == len({row["site_id"] for row in radio}) == 1574
    assert len(digital) == len({row["site_id"] for row in digital}) == 29
    assert sum(int(row["dr"]) for row in digital) == 63
    assert {row["site_id"] for row in radio} == {row["site_id"] for row in licences if row["band"] in {"AM", "FM"}}
    for band, field, sites in [("AM", "am", radio), ("FM", "fm", radio), ("DR", "dr", digital)]:
        counts = Counter(row["site_id"] for row in licences if row["band"] == band)
        assert all(int(row[field]) == counts[row["site_id"]] for row in sites)
    assert all(110 < float(row["longitude"]) < 155 and -45 < float(row["latitude"]) < -9 for row in radio + digital)
    cartogram = records("population_cartogram.csv")
    populations = population_data(XlsxWorkbook(ROOT / ".cache/population-mar-2026.xlsx"))
    assert populations["New South Wales"] == 8670105
    assert populations["Northern Territory"] == 268899
    assert len(cartogram) == 8
    for index, left in enumerate(cartogram):
        assert int(left["population"]) == populations[left["state_name"]]
        assert left["population_period"] == POPULATION_PERIOD
        assert math.isclose(float(left["radius"]) ** 2 / int(left["population"]), 0.0004)
        for right in cartogram[index + 1:]:
            distance = math.hypot(float(left["cartogram_x"]) - float(right["cartogram_x"]),
                                  float(left["cartogram_y"]) - float(right["cartogram_y"]))
            assert distance >= float(left["radius"]) + float(right["radius"]), "Cartogram circles overlap"
    topology = json.loads((ROOT / "data/au_states.topojson").read_text())
    geometries = topology["objects"]["states"]["geometries"]
    assert all(geometry["properties"]["boundary_edition"] == 2026 for geometry in geometries)
    names = {geometry["properties"]["state_name"] for geometry in geometries}
    assert len(geometries) == 8 and names == {row["state_name"] for row in records("adii_states.csv")}
    manifest = json.loads((ROOT / "specs/manifest.json").read_text())
    assert len(manifest) == 16 and len(set(manifest)) == 16
    assert set(manifest) == {path.stem for path in (ROOT / "specs").glob("*.json") if path.stem != "manifest"}
    sources = {row["source_id"] for row in records("sources.csv")}
    assert len(sources) == 7
    for filename in ["news_age.csv", "video_services_age.csv", "metro_regional.csv", "radio_sites.csv", "digital_radio_sites.csv", "population_cartogram.csv"]:
        assert all(set(row["source_id"].split(";")) <= sources for row in records(filename))
    class PageParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids, self.references, self.charts = [], [], []

        def handle_starttag(self, tag, attributes):
            attributes = dict(attributes)
            if "id" in attributes:
                self.ids.append(attributes["id"])
            if tag == "a" and attributes.get("href", "").startswith("#"):
                self.references.append(attributes["href"][1:])
            if "chart" in attributes.get("class", "").split():
                self.charts.append(attributes["id"])

    page = PageParser()
    page.feed((ROOT / "index.html").read_text())
    assert len(page.ids) == len(set(page.ids)), "Duplicate HTML IDs"
    assert set(page.references) <= set(page.ids), "Broken internal footnote/navigation links"
    assert set(page.charts) == set(manifest), "Manifest and page charts disagree"
    assets = set()

    def find_assets(node):
        if isinstance(node, dict):
            if str(node.get("url", "")).startswith("data/"):
                assets.add(node["url"])
            for value in node.values():
                find_assets(value)
        elif isinstance(node, list):
            for value in node:
                find_assets(value)

    for name in manifest:
        find_assets(json.loads((ROOT / "specs" / f"{name}.json").read_text()))
    assert all((ROOT / path).is_file() for path in assets)
    size = sum((ROOT / path).stat().st_size for path in assets)
    assert size < 1_000_000, "Chart data should stay well below a few megabytes"
    print(f"Data audit passed: source denominators, 16 specs, 8 state joins, radio sites, cartogram areas and footnotes; {size:,} bytes of unique chart data.")


if __name__ == "__main__":
    main()
