"""CSV data availability helpers.

Dashboards should not display in-memory fake rows. When the configured CSV has
no usable rows, these helpers generate rows and write them to the CSV first;
the dashboard builders then read from those files normally.
"""

from pathlib import Path

import pandas as pd

from src.analytics import load_data
from src.data_generator import generate_facility_data, save_to_csv
from src.security_data_generator import (
    SECURITY_FIELDNAMES,
    generate_security_events,
    save_security_events,
)


SECURITY_REQUIRED_COLUMNS = SECURITY_FIELDNAMES


def ensure_facility_csv(path="facility_data.csv"):
    """
    Ensure the facility CSV contains usable dashboard rows.

    Returns True when new data was generated and written to the CSV, otherwise
    False. Existing usable CSV data is never overwritten.
    """

    csv_path = Path(path)
    df = load_data(csv_path)

    if not df.empty:
        return False

    records = generate_facility_data()
    save_to_csv(records, csv_path)
    return True


def ensure_security_csv(path="security_events.csv", facility_path="facility_data.csv"):
    """
    Ensure the security CSV contains usable dashboard rows.

    Returns True when new data was generated and written to the CSV, otherwise
    False. Existing usable CSV data is never overwritten.
    """

    csv_path = Path(path)

    if _security_csv_has_usable_rows(csv_path):
        return False

    building_rooms = _building_rooms_from_facility_csv(facility_path)
    rows = generate_security_events(building_rooms=building_rooms)
    save_security_events(rows, csv_path)
    return True


def _security_csv_has_usable_rows(path):
    if not Path(path).exists():
        return False

    try:
        df = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return False

    if df.empty:
        return False

    missing_columns = [
        column
        for column in SECURITY_REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        return False

    timestamps = pd.to_datetime(df["timestamp"], errors="coerce")

    return bool(timestamps.notna().any())


def _building_rooms_from_facility_csv(path):
    facility_path = Path(path)

    if not facility_path.exists():
        return None

    try:
        df = pd.read_csv(facility_path, usecols=["building_id", "room_id"])
    except (ValueError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return None

    df = df.dropna(subset=["building_id", "room_id"])

    if df.empty:
        return None

    building_rooms = {}

    for building_id, group in df.groupby("building_id"):
        rooms = sorted(str(room_id) for room_id in group["room_id"].dropna().unique())

        if rooms:
            building_rooms[str(building_id)] = rooms

    return building_rooms or None
