#!/usr/bin/env python3
"""Build the small, auditable datasets used by the visual essay.

The ACMA workbooks are Office Open XML files.  This script intentionally uses
only Python's standard library so the project can be rebuilt without a data
science environment.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

WATCH_URL = (
    "https://www.acma.gov.au/sites/default/files/2026-02/"
    "How%20we%20watch%20and%20listen%20to%20content%20data%20tables.xlsx"
)
INTERNET_URL = (
    "https://www.acma.gov.au/sites/default/files/2026-02/"
    "How%20we%20use%20the%20internet%20data%20tables.xlsx"
)
ABS_URL = (
    "https://geo.abs.gov.au/arcgis/rest/services/ASGS2026/STE/MapServer/1/query?"
    "where=STATE_CODE_2026%3C%3E%279%27&outFields=STATE_CODE_2026%2CSTATE_NAME_2026"
    "&returnGeometry=true&outSR=4326&geometryPrecision=3&maxAllowableOffset=0.05&f=geojson"
)

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

AGE_ORDER = ["18–24", "25–34", "35–44", "45–54", "55–64", "65–74", "75+"]
AGE_LABELS = {
    "18-24": "18–24",
    "25-34": "25–34",
    "35-44": "35–44",
    "45-54": "45–54",
    "55-64": "55–64",
    "65-74": "65–74",
    "75 and older": "75+",
    "75+": "75+",
}


def column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def numeric(value):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


class XlsxWorkbook:
    def __init__(self, path: Path):
        self.archive = ZipFile(path)
        self.namespaces = {"m": NS_MAIN, "r": NS_REL}
        self.shared_strings = self._read_shared_strings()
        self.sheets = self._read_sheet_paths()

    def _read_shared_strings(self):
        try:
            root = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        return [
            "".join(node.text or "" for node in item.iter(f"{{{NS_MAIN}}}t"))
            for item in root.findall("m:si", self.namespaces)
        ]

    def _read_sheet_paths(self):
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        relation_map = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships.findall(f"{{{NS_PACKAGE_REL}}}Relationship")
        }
        result = {}
        for sheet in workbook.find("m:sheets", self.namespaces):
            target = relation_map[sheet.attrib[f"{{{NS_REL}}}id"]].lstrip("/")
            result[sheet.attrib["name"]] = target if target.startswith("xl/") else f"xl/{target}"
        return result

    def rows(self, sheet_name: str):
        root = ET.fromstring(self.archive.read(self.sheets[sheet_name]))
        rows = []
        for row_node in root.findall(".//m:row", self.namespaces):
            row = {}
            for cell in row_node.findall("m:c", self.namespaces):
                value_node = cell.find("m:v", self.namespaces)
                if value_node is None:
                    inline = cell.find("m:is", self.namespaces)
                    value = "" if inline is None else "".join(
                        node.text or "" for node in inline.iter(f"{{{NS_MAIN}}}t")
                    )
                else:
                    value = value_node.text or ""
                    if cell.attrib.get("t") == "s" and value:
                        value = self.shared_strings[int(value)]
                row[column_index(cell.attrib["r"])] = value
            rows.append(row)
        return rows


def download(url: str, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "FIT3179-data-builder/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def write_csv(filename: str, rows: list[dict], fields: list[str] | None = None):
    destination = DATA / filename
    if not rows:
        raise ValueError(f"No rows generated for {filename}")
    fields = fields or list(rows[0])
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def study_year_records(workbook: XlsxWorkbook, sheet_name: str):
    rows = workbook.rows(sheet_name)
    base_offset = str(rows[2][0]).splitlines().index("Column n")
    year_columns = {}
    for column, value in rows[2].items():
        number = numeric(value)
        if number and 2000 <= number <= 2100:
            year_columns[column] = int(number)

    records = []
    for index, row in enumerate(rows[3:], start=3):
        label = str(row.get(0, "")).strip()
        if not label or label.startswith(("Column ", "Filter:", "Multiple comparison")):
            continue
        base_row = rows[index + base_offset] if index + base_offset < len(rows) else {}
        for column, year in year_columns.items():
            value = numeric(row.get(column))
            if value is None:
                continue
            base = numeric(base_row.get(column))
            records.append({"category": label, "year": year, "value": value, "base_n": base})
    return records


def banner_records(workbook: XlsxWorkbook, sheet_name: str, groups=None, group_field="age"):
    groups = AGE_LABELS if groups is None else groups
    rows = workbook.rows(sheet_name)
    base_offset = str(rows[2][0]).splitlines().index("Column n")
    group_row = rows[3]
    year_row = rows[5]
    group_by_column = {}
    current_group = ""
    for column in range(max(year_row) + 1):
        if str(group_row.get(column, "")).strip():
            current_group = str(group_row[column]).strip()
        group_by_column[column] = current_group

    records = []
    for index, row in enumerate(rows[6:], start=6):
        label = str(row.get(0, "")).strip()
        if not label or label.startswith(("Column ", "Filter:", "Multiple comparison")):
            continue
        base_row = rows[index + base_offset] if index + base_offset < len(rows) else {}
        for column, year_value in year_row.items():
            year = numeric(year_value)
            value = numeric(row.get(column))
            group = groups.get(group_by_column.get(column, ""))
            if group and year and value is not None:
                records.append(
                    {
                        "category": label,
                        group_field: group,
                        "year": int(year),
                        "value": value,
                        "base_n": numeric(base_row.get(column)),
                    }
                )
    return records


def select(records, aliases: dict[str, str], years: set[int] | None = None):
    first_waves = {
        "User-generated or short-form online video service (e.g. YouTube, TikTok, Instagram)": 2022,
        "Online music streaming services (e.g. Spotify, Apple Music etc.)": 2021,
        "Podcasts (at least one)": 2021,
        "Disney+": 2020,
        "TikTok": 2020,
        "Kayo": 2020,
        "Binge": 2021,
        "Mobile phone": 2020,
        "Desktop or laptop computer": 2020,
        "Tablet": 2020,
    }
    selected = []
    for row in records:
        for source_label, display_label in aliases.items():
            if (
                row["category"] == source_label
                and (years is None or row["year"] in years)
                and (row.get("base_n") or 0) > 0
                and row["year"] >= first_waves.get(source_label, 2017)
            ):
                selected.append({**row, "metric": display_label})
    return selected


def percent_rows(records):
    result = []
    for row in records:
        result.append({**row, "percent": round(row["value"] * 100, 2)})
    return result


def first(records, category: str, year: int):
    return next(row for row in records if row["category"] == category and row["year"] == year)


def build_acma_data(watch: XlsxWorkbook, internet: XlsxWorkbook):
    viewing = study_year_records(watch, "QF4. Which of by Study year")
    viewing_age = banner_records(watch, "QF4. Which of by PBI BANNER")
    video_hours = study_year_records(watch, "QF5_ave. Hour by Study year")
    video_hours_age = banner_records(watch, "QF5_ave. Hour by PBI BANNER")
    services = study_year_records(watch, "QF7. Now, thi by Study year")
    devices = study_year_records(watch, "QF1. Which of by Study year")
    audio = study_year_records(watch, "QH3. Which of by Study year")
    audio_age = banner_records(watch, "QH3. Which of by PBI BANNER")
    music_services_age = banner_records(watch, "QH5a. Online  by PBI BANNER")

    trend_aliases = {
        "Paid subscription streaming service (e.g. Netflix, Stan, Binge)": "Paid streaming",
        "Free-to-air TV excluding catch-up TV (e.g. ABC, SBS, Channels 7, 9, 10) + Recorded free-to-air TV content (recorded by you) (UP TO 2021)": "Free-to-air TV",
        "User-generated or short-form online video service (e.g. YouTube, TikTok, Instagram)": "Short-form video",
        "Free-to-air catch-up TV and streaming services (e.g. ABC iview, 9Now, 7Plus)": "FTA catch-up",
    }
    trend = percent_rows(select(viewing, trend_aliases))
    write_csv(
        "media_trends.csv",
        [
            {"year": row["year"], "metric": row["metric"], "percent": row["percent"], "base_n": int(row["base_n"] or 0)}
            for row in trend
        ],
    )
    trend_by_key = {(row["year"], row["metric"]): row for row in trend}
    paired_years = sorted(
        {row["year"] for row in trend if row["metric"] == "Paid streaming"}
        & {row["year"] for row in trend if row["metric"] == "Free-to-air TV"}
    )
    write_csv(
        "streaming_fta.csv",
        [
            {
                "year": year,
                "paid_streaming": trend_by_key[(year, "Paid streaming")]["percent"],
                "free_to_air": trend_by_key[(year, "Free-to-air TV")]["percent"],
            }
            for year in paired_years
        ],
    )

    horizon_rows = []
    horizon_order = ["Paid streaming", "Short-form video", "FTA catch-up", "Free-to-air TV"]
    for metric_order, metric in enumerate(horizon_order):
        observations = sorted((row for row in trend if row["metric"] == metric), key=lambda row: row["year"])
        if not observations:
            continue
        baseline = observations[0]["percent"]
        for row in observations:
            change = round(row["percent"] - baseline, 2)
            for band in range(1, 5):
                band_value = max(0, min(10, abs(change) - (band - 1) * 10))
                y0 = metric_order * 13
                horizon_rows.append(
                    {
                        "year": row["year"],
                        "metric": metric,
                        "metric_order": metric_order,
                        "baseline": baseline,
                        "percent": row["percent"],
                        "change": change,
                        "direction": "increase" if change >= 0 else "decrease",
                        "band": band,
                        "band_value": round(band_value, 2),
                        "y0": y0,
                        "y1": round(y0 + band_value, 2),
                    }
                )
    write_csv("horizon_trends.csv", horizon_rows)
    age_metrics = []
    age_sources = [
        (
            viewing_age,
            {
                "Paid subscription streaming service (e.g. Netflix, Stan, Binge)": "Paid video",
                "User-generated or short-form online video service (e.g. YouTube, TikTok, Instagram)": "Short-form video",
                "Free-to-air TV excluding catch-up TV (e.g. ABC, SBS, Channels 7, 9, 10) + Recorded free-to-air TV content (recorded by you) (UP TO 2021)": "Free-to-air TV",
            },
        ),
        (
            audio_age,
            {
                "Online music streaming services (e.g. Spotify, Apple Music etc.)": "Music streaming",
                "Podcasts (at least one)": "Podcasts",
                "FM radio": "FM radio",
            },
        ),
    ]
    for records, aliases in age_sources:
        age_metrics.extend(percent_rows(select(records, aliases, {2025})))
    write_csv(
        "age_media.csv",
        [
            {
                "age": row["age"],
                "age_order": AGE_ORDER.index(row["age"]),
                "metric": row["metric"],
                "percent": row["percent"],
                "base_n": int(row["base_n"] or 0),
                "low_base": "yes" if (row["base_n"] or 0) < 100 else "no",
            }
            for row in age_metrics
        ],
    )

    service_aliases = {
        "YouTube": "YouTube",
        "Netflix": "Netflix",
        "Amazon Prime Video": "Prime Video",
        "Disney+": "Disney+",
        "TikTok": "TikTok",
        "Stan": "Stan",
        "Kayo": "Kayo",
        "Binge": "Binge",
    }
    service_rows = percent_rows(select(services, service_aliases, set(range(2021, 2026))))
    write_csv(
        "video_services.csv",
        [
            {"year": row["year"], "service": row["metric"], "percent": row["percent"], "base_n": int(row["base_n"] or 0)}
            for row in service_rows
        ],
    )
    service_age = percent_rows(select(
        banner_records(watch, "QF7. Now, thi by PBI BANNER"), service_aliases, {2025}
    ))
    write_csv("video_services_age.csv", [
        {"age": row["age"], "service": row["metric"], "percent": row["percent"],
         "base_n": int(row["base_n"]), "source_id": "acma-watch", "question": "QF7", "year": 2025}
        for row in service_age
    ])
    geography = {"Metro": "Metro", "Regional": "Regional"}
    regional_rows = []
    for sheet, aliases in [
        ("QF4. Which of by PBI BANNER", age_sources[0][1]),
        ("QH3. Which of by PBI BANNER", age_sources[1][1]),
    ]:
        observations = percent_rows(select(
            banner_records(watch, sheet, geography, "region"), aliases, {2025}
        ))
        for metric in aliases.values():
            paired = {row["region"]: row for row in observations if row["metric"] == metric}
            metro, regional = paired["Metro"], paired["Regional"]
            regional_rows.append({
                "metric": metric, "metro": metro["percent"], "regional": regional["percent"],
                "gap": round(regional["percent"] - metro["percent"], 2),
                "metro_base_n": int(metro["base_n"]), "regional_base_n": int(regional["base_n"]),
                "source_id": "acma-watch", "question": sheet.split(".")[0], "year": 2025,
            })
    write_csv("metro_regional.csv", regional_rows)
    news_age = percent_rows(select(
        banner_records(internet, "QD8. Internet by PBI BANNER"),
        {"Accessing news and information online": "Online news and information"}, {2025}
    ))
    write_csv("news_age.csv", [
        {"age": row["age"], "percent": row["percent"], "base_n": int(row["base_n"]),
         "source_id": "acma-internet", "question": "QD8", "year": 2025}
        for row in news_age
    ])

    device_aliases = {
        "Smart TV": "Smart TV",
        "Mobile phone": "Mobile phone",
        "Desktop or laptop computer": "Computer",
        "Tablet": "Tablet",
        "Google Chromecast/Google TV Streamer": "Chromecast / Google TV",
        "Games console (e.g. PlayStation, Xbox or Nintendo)": "Games console",
        "Apple TV box": "Apple TV",
    }
    device_rows = percent_rows(select(devices, device_aliases, {2021, 2025}))
    write_csv(
        "video_devices.csv",
        [
            {"year": row["year"], "device": row["metric"], "percent": row["percent"], "base_n": int(row["base_n"] or 0)}
            for row in device_rows
        ],
    )

    audio_aliases = {
        "AM radio": "AM radio",
        "FM radio": "FM radio",
        "Digital radio (DAB+)": "DAB+ radio",
        "Radio via the internet or an app (excluding podcasts)": "Internet radio",
        "Online music streaming services (e.g. Spotify, Apple Music etc.)": "Music streaming",
        "Podcasts (at least one)": "Podcasts",
    }
    audio_rows = percent_rows(select(audio, audio_aliases))
    write_csv(
        "audio_trends.csv",
        [
            {"year": row["year"], "metric": row["metric"], "percent": row["percent"], "base_n": int(row["base_n"] or 0)}
            for row in audio_rows
        ],
    )
    audio_age_rows = percent_rows(select(audio_age, audio_aliases, {2025}))
    write_csv(
        "audio_age.csv",
        [
            {
                "age": row["age"],
                "age_order": AGE_ORDER.index(row["age"]),
                "metric": row["metric"],
                "percent": row["percent"],
                "base_n": int(row["base_n"] or 0),
                "low_base": "yes" if (row["base_n"] or 0) < 100 else "no",
            }
            for row in audio_age_rows
        ],
    )

    music_aliases = {
        "Spotify": "Spotify",
        "YouTube (not YouTube Music)(BACKCODED) + YouTube Music": "YouTube Music",
        "Apple Music": "Apple Music",
        "ABC listen": "ABC listen",
        "Amazon Music": "Amazon Music",
    }
    music_rows = percent_rows(select(music_services_age, music_aliases, {2025}))
    write_csv(
        "music_services_age.csv",
        [
            {
                "age": row["age"],
                "age_order": AGE_ORDER.index(row["age"]),
                "service": row["metric"],
                "percent": row["percent"],
                "base_n": int(row["base_n"] or 0),
            }
            for row in music_rows
        ],
    )

    hours_aliases = {
        "Free-to-air TV excluding catch-up TV": "Free-to-air TV",
        "Free-to-air catch-up TV and streaming service (e.g. ABC iview, 9Now, 7Plus, SBS-on Demand)": "FTA catch-up",
        "Paid subscription streaming service (e.g. Netflix, Stan, Binge)": "Paid streaming",
        "Pay TV or other subscription TV channels (e.g. Foxtel, Fetch TV)": "Pay TV",
        "Pay-per-view service to rent/buy movie/TV show or live events such as sporting matches (e.g. Prime video stores, Telstra TV Box Office)": "Pay-per-view",
        "User-generated or short-form online video service (e.g. YouTube, TikTok, Instagram Reels)": "Short-form video",
    }
    national_hours = select(video_hours, hours_aliases, {2025})
    age_hour_rows = select(video_hours_age, hours_aliases, {2025})
    benchmarks = {row["metric"]: row["value"] for row in national_hours}
    write_csv(
        "video_hours_age.csv",
        [
            {
                "age": row["age"],
                "age_order": AGE_ORDER.index(row["age"]),
                "metric": row["metric"],
                "hours": round(row["value"], 2),
                "national_hours": round(benchmarks[row["metric"]], 2),
                "base_n": int(row["base_n"]),
            }
            for row in age_hour_rows
        ],
    )

    hero = first(services, "NET (excludes FTA-CATCH UP & FAST)", 2025)
    news = first(study_year_records(internet, "QD8. Internet by Study year"), "Accessing news and information online", 2025)
    with (DATA / "headline_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "online_video_past_six_months": round(hero["value"] * 100),
                "online_news_past_six_months": round(news["value"] * 100),
                "reference_year": 2025,
            },
            handle,
            indent=2,
        )


def build_audio_locations(workbook: XlsxWorkbook):
    rows = workbook.rows("QH16. Where l by Study year")
    group_row, year_row = rows[2], rows[3]
    group_by_column = {}
    current_group = ""
    for column in range(max(year_row) + 1):
        if str(group_row.get(column, "")).strip():
            current_group = str(group_row[column]).strip()
        group_by_column[column] = current_group
    format_aliases = {
        "online music streaming": "Music streaming",
        "Podcasts": "Podcasts",
        "radio via internet/app": "Internet radio",
        "AM radio": "AM radio",
        "FM radio": "FM radio",
        "DAB radio": "DAB+ radio",
    }
    location_aliases = {
        "At home": "Home",
        "In the car or another vehicle (including public transport)": "In transit",
        "Elsewhere": "Elsewhere",
    }
    output = []
    for index, row in enumerate(rows[4:], start=4):
        media_format = format_aliases.get(str(row.get(0, "")).strip())
        if not media_format:
            continue
        base_row = rows[index + str(rows[2][0]).splitlines().index("Column n")]
        for column, year_value in year_row.items():
            location = location_aliases.get(group_by_column.get(column, ""))
            value = numeric(row.get(column))
            if location and int(numeric(year_value) or 0) == 2025 and value is not None:
                output.append(
                    {
                        "format": media_format,
                        "location": location,
                        "percent": round(value * 100, 2),
                        "base_n": int(numeric(base_row.get(column)) or 0),
                    }
                )
    write_csv("audio_locations.csv", output)


def build_manual_data():
    state_scores = {
        "New South Wales": ("NSW", 74.0, 147.0, -32.5),
        "Victoria": ("VIC", 74.1, 144.9, -37.0),
        "Queensland": ("QLD", 72.9, 144.0, -22.0),
        "South Australia": ("SA", 71.3, 135.0, -30.0),
        "Western Australia": ("WA", 73.9, 121.0, -26.0),
        "Tasmania": ("TAS", 69.4, 146.5, -42.0),
        "Northern Territory": ("NT", 72.5, 133.5, -19.0),
        "Australian Capital Territory": ("ACT", 79.5, 149.1, -35.3),
    }
    state_rows = []
    for name, (code, score, longitude, latitude) in state_scores.items():
        state_rows.append(
            {
                "state_name": name,
                "state": code,
                "score": score,
                "national": 73.6,
                "gap": round(score - 73.6, 1),
                "absolute_gap": abs(round(score - 73.6, 1)),
                "direction": "above" if score >= 73.6 else "below",
                "longitude": longitude,
                "latitude": latitude,
            }
        )
    write_csv("adii_states.csv", state_rows)

    cohort_rows = [
        ("Age", "18–34", 80.9130), ("Age", "35–44", 80.2433),
        ("Age", "45–54", 76.1000), ("Age", "55–64", 70.8694),
        ("Age", "65–74", 62.9350), ("Age", "75+", 51.2379),
        ("Geography", "Capital cities", 75.4904), ("Geography", "Regional", 69.5696),
        ("Remoteness", "Major cities", 75.0933), ("Remoteness", "Inner regional", 69.6918),
        ("Remoteness", "Outer regional", 69.3614), ("Remoteness", "Remote", 70.6040),
        ("Remoteness", "Very remote", 62.5284),
    ]
    write_csv(
        "adii_cohorts.csv",
        [
            {"group": group, "cohort": cohort, "score": round(score, 1), "gap": round(score - 73.6, 1)}
            for group, cohort, score in cohort_rows
        ],
    )

    news_rows = [
        ("Heavy news use", "News consumers", 56, "Digital News Report Australia 2026"),
        ("Heavy news use", "Age 18–24", 49, "Digital News Report Australia 2026"),
        ("Trust", "News I use", 54, "Digital News Report Australia 2026"),
        ("Trust", "News on social media", 21, "Digital News Report Australia 2026"),
        ("Trust", "News from AI chatbots", 19, "Digital News Report Australia 2026"),
        ("Creator news", "News consumers", 43, "Digital News Report Australia 2026"),
        ("Never read print", "Age 18–24", 60, "Digital News Report Australia 2026"),
    ]
    write_csv(
        "news_indicators.csv",
        [{"topic": topic, "group": group, "percent": value, "source": source} for topic, group, value, source in news_rows],
    )


def write_provenance():
    from build_geography import BROADCAST_URL, POPULATION_WORKBOOK_URL

    sources = [
        {
            "dataset": "How we watch and listen to content — data tables",
            "publisher": "Australian Communications and Media Authority",
            "vintage": "2025 survey; report released 5 March 2026; workbook URL dated February",
            "url": WATCH_URL,
            "use": "Viewing, service, device, audio and age comparisons",
            "notes": "Weighted survey percentages; multiple-response questions are not totals.",
        },
        {
            "dataset": "How we use the internet — data tables",
            "publisher": "Australian Communications and Media Authority",
            "vintage": "2025 survey; published February 2026",
            "url": INTERNET_URL,
            "use": "National and age-group six-month online news and information reach",
            "notes": "Weighted survey percentages.",
        },
        {
            "dataset": "Australian Digital Inclusion Index 2025",
            "publisher": "ARC Centre of Excellence for Automated Decision-Making and Society / RMIT / Swinburne / Telstra",
            "vintage": "2025 report; data collected in 2024",
            "url": "https://digitalinclusionindex.org.au/wp-content/uploads/2025/10/ADII-Report-2025_V6-Remediated.pdf",
            "use": "State, age and remoteness digital inclusion scores",
            "notes": "Score is an index, not a percentage. Values transcribed from the report and public dashboard.",
        },
        {
            "dataset": "Digital News Report: Australia 2026",
            "publisher": "News and Media Research Centre, University of Canberra",
            "vintage": "2026",
            "url": "https://www.canberra.edu.au/research/centres/nmrc/digital-news-report-australia",
            "use": "Separate supporting news-trust prose, not charted with ACMA reach",
            "notes": "Selected headline indicators transcribed from the report landing page; a different survey base from ACMA.",
        },
        {
            "dataset": "ASGS 2026 State and Territory Boundaries",
            "publisher": "Australian Bureau of Statistics",
            "vintage": "2026 edition; released 22 July 2026",
            "url": "https://geo.abs.gov.au/arcgis/rest/services/ASGS2026/STE/MapServer",
            "use": "State choropleth geometry",
            "notes": "ABS generalised geometry, 0.05-degree service simplification; Mapshaper 0.6.113 rewinds malformed service polygon rings by containment (preserving NSW and the ACT hole), cleans slivers, retains 30% of vertices with keep-shapes and exports TopoJSON. Cartographic display only.",
        },
    ]
    sources.extend([
        {
            "dataset": "Broadcast Transmitter Excel",
            "publisher": "Australian Communications and Media Authority",
            "vintage": "13 July 2026 snapshot",
            "url": BROADCAST_URL,
            "use": "Issued AM/FM physical sites and digital-radio licence records per site",
            "notes": "AM/FM/DR sheets; Issued only, excluding Temporary Licences. Repeated day/night assignments deduplicated by band/licence/technical specification/Site Id, then grouped by site. GDA94 DMS to decimal degrees, carrying rounded 60-second entries; display only. Licences do not establish operation, coverage or audiences. CC BY 2.5 AU.",
        },
        {
            "dataset": "National, state and territory population, March 2026 — table 4",
            "publisher": "Australian Bureau of Statistics",
            "vintage": "31 March 2026; released 17 September 2026",
            "url": POPULATION_WORKBOOK_URL,
            "use": "Dorling cartogram areas show latest resident estimates; colour separately shows ADII 2024 fieldwork",
            "notes": "Table 4, Data1, persons series for March 2026, read directly from XLSX. Estimates are subject to revision. Eight states/territories; all ages; excludes Other Territories. Different periods: population is not multiplied by ADII or interpreted as a media audience count. CC BY 4.0.",
        },
    ])
    source_ids = ["acma-watch", "acma-internet", "adii", "news-report", "abs-boundaries", "acma-radio", "abs-population"]
    for source, source_id in zip(sources, source_ids):
        source["source_id"] = source_id
        source["checked_date"] = "2026-10-06"
    write_csv("sources.csv", sources)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch-workbook", type=Path)
    parser.add_argument("--internet-workbook", type=Path)
    parser.add_argument("--geojson", type=Path)
    parser.add_argument("--broadcast-workbook", type=Path)
    parser.add_argument("--population-workbook", type=Path)
    arguments = parser.parse_args()

    cache = ROOT / ".cache"
    watch_path = arguments.watch_workbook or cache / "watch_listen.xlsx"
    internet_path = arguments.internet_workbook or cache / "internet.xlsx"
    geojson_path = arguments.geojson or cache / "au_states_2026.geojson"
    if not watch_path.exists():
        print("Downloading ACMA watch/listen workbook …")
        download(WATCH_URL, watch_path)
    if not internet_path.exists():
        print("Downloading ACMA internet workbook …")
        download(INTERNET_URL, internet_path)
    if not geojson_path.exists():
        print("Downloading ABS state geometry …")
        download(ABS_URL, geojson_path)

    DATA.mkdir(exist_ok=True)
    watch = XlsxWorkbook(watch_path)
    internet = XlsxWorkbook(internet_path)
    build_acma_data(watch, internet)
    build_audio_locations(watch)
    build_manual_data()
    from build_geography import build_geography
    build_geography(arguments.broadcast_workbook, arguments.population_workbook)
    write_provenance()
    with geojson_path.open(encoding="utf-8") as handle:
        boundaries = json.load(handle)
    boundaries["features"] = [
        feature
        for feature in boundaries["features"]
        if str(feature.get("properties", {}).get("STATE_CODE_2026")) in set("12345678")
        and feature.get("geometry")
    ]
    if len(boundaries["features"]) != 8:
        raise ValueError("Expected eight jurisdictions from the ASGS 2026 boundary source")
    for feature in boundaries["features"]:
        properties = feature["properties"]
        feature["properties"] = {
            "state_code": properties["STATE_CODE_2026"],
            "state_name": properties["STATE_NAME_2026"],
            "boundary_edition": 2026,
        }
    with (DATA / "au_states.geojson").open("w", encoding="utf-8") as handle:
        json.dump(boundaries, handle, separators=(",", ":"))
    print(f"Built {len(list(DATA.glob('*')))} data files in {DATA}")


if __name__ == "__main__":
    main()
