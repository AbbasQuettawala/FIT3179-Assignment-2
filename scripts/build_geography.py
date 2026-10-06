#!/usr/bin/env python3
"""Build auditable radio-site data and a deterministic population cartogram."""

import csv
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from build_data import DATA, ROOT, XlsxWorkbook, download, write_csv


BROADCAST_URL = "https://www.acma.gov.au/sites/default/files/2026-07/BroadcastTransmitterExcel.zip"
POPULATION_URL = "https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/mar-2026"
POPULATION_WORKBOOK_URL = POPULATION_URL + "/310104.xlsx"
POPULATION_PERIOD = "2026-03"
STATES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}


def population_data(workbook):
    rows = workbook.rows("Data1")
    columns = {}
    for column, label in rows[0].items():
        parts = [part.strip() for part in label.split(";")]
        if parts[:2] == ["Estimated Resident Population", "Persons"]:
            columns[parts[2]] = column
    matches = []
    for row in rows:
        serial = str(row.get(0, ""))
        if serial.isdigit():
            period = (datetime(1899, 12, 30) + timedelta(days=int(serial))).strftime("%Y-%m")
            if period == POPULATION_PERIOD:
                matches.append(row)
    if len(matches) != 1 or len(columns) != 9:
        raise ValueError("Expected one March 2026 observation and nine persons series in ABS table 4")
    values = {name: int(matches[0][column]) for name, column in columns.items()}
    if any(value <= 0 for value in values.values()):
        raise ValueError("Population estimates must be positive")
    return values


def decimal_degrees(value):
    match = re.fullmatch(r"\s*(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)\s*([NSEW])\s*", str(value))
    if not match:
        raise ValueError(f"Invalid DMS coordinate: {value!r}")
    degrees, minutes, seconds = map(float, match.groups()[:3])
    if minutes >= 60 or seconds > 60:
        raise ValueError(f"Invalid minutes/seconds: {value}")
    return round((degrees + minutes / 60 + seconds / 3600) * (-1 if match[4] in "SW" else 1), 6)


def radio_data(workbook):
    sites = {}
    licences = []
    seen = set()
    for band in ["AM", "FM", "DR"]:
        rows = workbook.rows(band)
        headers = {str(value).lower(): column for column, value in rows[0].items()}
        for row in rows[1:]:
            record = {field: str(row.get(column, "")).strip() for field, column in headers.items()}
            if record["status"] != "Issued" or record["state"] not in STATES:
                continue
            key = (band, record["licence number"], record["technical specification number"], record["site id"])
            if key in seen:
                continue
            seen.add(key)
            longitude = decimal_degrees(record["longitude"])
            latitude = decimal_degrees(record["latitude"])
            if not (110 < longitude < 155 and -45 < latitude < -9):
                raise ValueError(f"Unexpected Australian coordinates: {key}")
            site_id = record["site id"]
            site = sites.setdefault(site_id, {
                "site_id": site_id, "name": record["site name"], "state": record["state"],
                "longitude": longitude, "latitude": latitude, "am": 0, "fm": 0, "dr": 0,
            })
            if (site["longitude"], site["latitude"], site["state"]) != (longitude, latitude, record["state"]):
                raise ValueError(f"Inconsistent coordinates/state for site {site_id}")
            site[band.lower()] += 1
            licences.append({
                "band": band, "licence": record["licence number"],
                "technical_specification": record["technical specification number"],
                "site_id": site_id, "state": record["state"], "status": record["status"],
                "source_id": "acma-radio",
            })
    conventional = []
    digital = []
    for site in sorted(sites.values(), key=lambda row: int(row["site_id"])):
        if site["am"] or site["fm"]:
            conventional.append({
                **site, "technology": "AM + FM" if site["am"] and site["fm"] else "AM" if site["am"] else "FM",
                "source_id": "acma-radio",
            })
        if site["dr"]:
            digital.append({**site, "source_id": "acma-radio"})
    write_csv("radio_licences.csv", licences)
    write_csv("radio_sites.csv", conventional)
    write_csv("digital_radio_sites.csv", digital)


def cartogram_data(populations):
    with (DATA / "adii_states.csv").open(encoding="utf-8") as handle:
        states = list(csv.DictReader(handle))
    for state in states:
        state["population"] = populations[state["state_name"]]
        state["population_period"] = POPULATION_PERIOD
        state["radius"] = math.sqrt(state["population"]) * 0.02
        state["anchor_x"] = (float(state["longitude"]) - 110) * 5
        state["anchor_y"] = (-float(state["latitude"]) - 10) * 5
        state["cartogram_x"] = state["anchor_x"]
        state["cartogram_y"] = state["anchor_y"]
    for iteration in range(1500):
        for state in states:
            if iteration < 1000:
                for axis in ["x", "y"]:
                    state[f"cartogram_{axis}"] += (state[f"anchor_{axis}"] - state[f"cartogram_{axis}"]) * 0.015
        for index, left in enumerate(states):
            for right in states[index + 1:]:
                delta_x = right["cartogram_x"] - left["cartogram_x"]
                delta_y = right["cartogram_y"] - left["cartogram_y"]
                distance = math.hypot(delta_x, delta_y)
                minimum = left["radius"] + right["radius"] + 5
                if distance < minimum:
                    shift = (minimum - distance) / (2 * distance)
                    for axis, delta in [("x", delta_x), ("y", delta_y)]:
                        left[f"cartogram_{axis}"] -= delta * shift
                        right[f"cartogram_{axis}"] += delta * shift
    for axis in ["x", "y"]:
        lower = min(state[f"cartogram_{axis}"] - state["radius"] for state in states) - 8
        extent = max(state[f"cartogram_{axis}"] + state["radius"] for state in states) + 8 - lower
        for state in states:
            state[f"cartogram_{axis}"] -= lower
            state[f"extent_{axis}"] = extent
    for state in states:
        del state["anchor_x"], state["anchor_y"]
        state["source_id"] = "adii;abs-population"
    write_csv("population_cartogram.csv", states)


def build_geography(workbook_path=None, population_path=None):
    workbook_path = workbook_path or ROOT / ".cache/BroadcastTransmitterExcel.xlsx"
    if not workbook_path.exists():
        archive_path = ROOT / ".cache/broadcast_transmitters.zip"
        download(BROADCAST_URL, archive_path)
        with ZipFile(archive_path) as archive:
            workbook_path.write_bytes(archive.read("BroadcastTransmitterExcel.xlsx"))
    radio_data(XlsxWorkbook(Path(workbook_path)))
    population_path = population_path or ROOT / ".cache/population-mar-2026.xlsx"
    if not population_path.exists():
        download(POPULATION_WORKBOOK_URL, population_path)
    cartogram_data(population_data(XlsxWorkbook(Path(population_path))))


if __name__ == "__main__":
    build_geography()
