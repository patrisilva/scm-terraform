#!/usr/bin/env python3
"""Write a CSV of firewalls connected to Strata Cloud Manager (SCM).

Credentials are read from the .env file next to this script (or from environment variables):
    SCM_CLIENT_ID, SCM_CLIENT_SECRET, SCM_TSG_ID

Columns: report_date, hostname, ip, panos, model, serial, folder, uptime,
connected_since, ha_state, app_version, threat_version, antivirus, wildfire,
url_db, iot, synced_to_scm

Examples:
    python3 export_firewalls.py
    python3 export_firewalls.py --output firewalls.csv
    python3 export_firewalls.py --all
"""
import argparse
import csv
import os
import sys
from datetime import date

import requests

AUTH_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
DEVICES_URL = "https://api.strata.paloaltonetworks.com/config/setup/v1/devices"
COLUMNS = (
    "report_date",
    "hostname",
    "ip",
    "panos",
    "model",
    "serial",
    "folder",
    "uptime",
    "connected_since",
    "ha_state",
    "app_version",
    "threat_version",
    "antivirus",
    "wildfire",
    "url_db",
    "iot",
    "synced_to_scm",
)


def load_env(path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")) -> None:
    """Load KEY=VALUE lines from .env without overriding variables already set."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if value.strip():
                    os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def get_token() -> str:
    load_env()
    try:
        client_id = os.environ["SCM_CLIENT_ID"]
        client_secret = os.environ["SCM_CLIENT_SECRET"]
        tsg_id = os.environ["SCM_TSG_ID"]
    except KeyError as e:
        sys.exit(f"Missing environment variable: {e}")

    resp = requests.post(
        AUTH_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials", "scope": f"tsg_id:{tsg_id}"},
        timeout=30,
    )
    if not resp.ok:
        sys.exit(f"Authentication failed: HTTP {resp.status_code}: {resp.text}")
    return resp.json()["access_token"]


def list_devices(token: str) -> list:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    devices = []
    offset = 0
    limit = 200
    while True:
        resp = requests.get(
            DEVICES_URL,
            headers=headers,
            params={"limit": limit, "offset": offset},
            timeout=30,
        )
        if not resp.ok:
            sys.exit(f"HTTP {resp.status_code}: {resp.text}")
        payload = resp.json()
        batch = payload.get("data") or []
        devices.extend(batch)
        total = payload.get("total", 0)
        offset += len(batch)
        if not batch or offset >= total:
            return devices


def first_value(device: dict, *keys: str) -> str:
    for key in keys:
        value = device.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def flag(device: dict, key: str) -> str:
    value = device.get(key)
    if value is True:
        return "true"
    if value is False:
        return "false"
    return first_value(device, key)


def to_row(device: dict, report_date: str) -> dict:
    return {
        "report_date": report_date,
        "hostname": first_value(device, "hostname", "display_name", "name"),
        "ip": first_value(device, "ip_address", "ipV6_address"),
        "panos": first_value(device, "software_version", "installed_software_version"),
        "model": first_value(device, "model"),
        "serial": first_value(device, "serial_number", "id"),
        "folder": first_value(device, "folder"),
        "uptime": first_value(device, "uptime"),
        "connected_since": first_value(device, "connected_since"),
        "ha_state": first_value(device, "ha_state"),
        "app_version": first_value(device, "app_version"),
        "threat_version": first_value(device, "threat_version"),
        "antivirus": first_value(device, "anti_virus_version"),
        "wildfire": first_value(device, "wf_ver"),
        "url_db": first_value(device, "url_db_ver"),
        "iot": first_value(device, "iot_version"),
        "synced_to_scm": flag(device, "synced_to_scm"),
    }


def write_csv(path: str, rows: list) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--output",
        "-o",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewalls.csv"),
        help="CSV path (default: firewalls.csv next to this script)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include firewalls that are not currently connected",
    )
    args = parser.parse_args()

    devices = list_devices(get_token())
    selected = devices if args.all else [device for device in devices if device.get("is_connected") is True]
    report_date = date.today().strftime("%m/%d/%Y")
    rows = sorted(
        (to_row(device, report_date) for device in selected),
        key=lambda row: row["hostname"].lower(),
    )
    write_csv(args.output, rows)

    noun = "firewall" if len(rows) == 1 else "firewalls"
    scope = "known to SCM" if args.all else "connected to SCM"
    print(f"Wrote {len(rows)} {noun} {scope} to {args.output}")


if __name__ == "__main__":
    main()
