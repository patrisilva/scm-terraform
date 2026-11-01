#!/usr/bin/env python3
"""Export Strata Cloud Manager security rules into the project CSV layout.

This script attempts to discover the live SCM rule endpoint using the tenant OAuth
credentials from .env, then writes the returned rules into:

    data/security policies/<folder>/pre-rules.csv
    data/security policies/<folder>/post-rules.csv

The CSV layout follows the project convention used by the Terraform modules.

Example:
    python3 export_security_rules.py --dry-run
    python3 export_security_rules.py
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional

import requests

AUTH_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
API_BASE = "https://api.sase.paloaltonetworks.com/sse/config/v1"
ALT_API_BASE = "https://api.strata.paloaltonetworks.com/sse/config/v1"

RULE_ENDPOINT_CANDIDATES = [
    "/security/rules",
    "/policies/security/rules",
    "/security/policies",
    "/rules",
    "/security/policies/rules",
    "/security-rule/rules",
]


def load_env(path: Optional[str] = None) -> None:
    if path is None:
        path = Path(__file__).with_name(".env")
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if value and key not in os.environ:
                os.environ[key] = value


def get_token() -> str:
    load_env()
    client_id = os.environ.get("SCM_CLIENT_ID")
    client_secret = os.environ.get("SCM_CLIENT_SECRET")
    tsg_id = os.environ.get("SCM_TSG_ID")
    if not client_id or not client_secret or not tsg_id:
        raise RuntimeError("Missing SCM_CLIENT_ID, SCM_CLIENT_SECRET, or SCM_TSG_ID in .env")

    resp = requests.post(
        AUTH_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials", "scope": f"tsg_id:{tsg_id}"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"OAuth failed ({resp.status_code}): {resp.text[:200]}")
    return resp.json()["access_token"]


def flatten_candidates(payload: Any) -> List[Any]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "rules", "policies", "security_rules", "result"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
            if key in payload and isinstance(payload[key], dict):
                nested = flatten_candidates(payload[key])
                if nested:
                    return nested
        if payload.get("error"):
            return []
        return [payload]
    return []


def get_rule_payload(token: str) -> tuple[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    candidates = []
    for base in (API_BASE, ALT_API_BASE):
        for suffix in RULE_ENDPOINT_CANDIDATES:
            candidates.append(base + suffix)

    last_error = "No candidate endpoints tried"
    for url in candidates:
        try:
            resp = requests.get(url, headers=headers, params={"limit": 200, "offset": 0}, timeout=30)
            if resp.status_code == 200:
                return url, resp.json()
            last_error = f"{url}: HTTP {resp.status_code} :: {resp.text[:180]}"
        except Exception as exc:  # pragma: no cover - network error handling
            last_error = f"{url}: {type(exc).__name__}: {exc}"

    raise RuntimeError(f"Unable to read SCM security rules. Last probe: {last_error}")


def as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None and str(v).strip()]
    if isinstance(value, tuple):
        return [str(v) for v in value if v is not None and str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def normalize_name(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def choose_position(rule: dict[str, Any]) -> str:
    pos = str(rule.get("position") or rule.get("rule_position") or rule.get("policy_position") or "").strip().lower()
    if pos in {"pre", "before"}:
        return "pre"
    if pos in {"post", "after"}:
        return "post"
    # If the SCM payload exposes this in a nested field, fall back to the common rule sequence field.
    if "pre" in str(rule).lower():
        return "pre"
    return "pre"


def normalize_rule(rule: dict[str, Any]) -> dict[str, Any]:
    folder = (
        rule.get("folder")
        or rule.get("folder_path")
        or rule.get("folderName")
        or rule.get("path")
        or rule.get("location")
        or "Global"
    )
    if isinstance(folder, list):
        folder = "/".join(str(x) for x in folder if str(x).strip())

    return {
        "folder": str(folder).strip() or "Global",
        "name": normalize_name(rule.get("name") or rule.get("rule_name") or rule.get("display_name") or rule.get("id")),
        "description": normalize_name(rule.get("description") or rule.get("comment") or ""),
        "action": normalize_name(rule.get("action") or "allow"),
        "position": choose_position(rule),
        "from": ",".join(as_list(rule.get("from") or rule.get("from_zone") or rule.get("from_zones") or rule.get("from_list") or [])),
        "to": ",".join(as_list(rule.get("to") or rule.get("to_zone") or rule.get("to_zones") or rule.get("to_list") or [])),
        "source": ",".join(as_list(rule.get("source") or rule.get("source_addresses") or rule.get("source_list") or [])),
        "destination": ",".join(as_list(rule.get("destination") or rule.get("destination_addresses") or rule.get("destination_list") or [])),
        "category": ",".join(as_list(rule.get("category") or rule.get("categories") or [])),
        "application": ",".join(as_list(rule.get("application") or rule.get("applications") or [])),
        "service": ",".join(as_list(rule.get("service") or rule.get("services") or [])),
        "source_user": ",".join(as_list(rule.get("source_user") or rule.get("source_users") or [])),
        "log_end": "true" if normalize_bool(rule.get("log_end") or rule.get("log_end_enabled")) else "false",
        "disabled": "true" if normalize_bool(rule.get("disabled") or rule.get("is_disabled") or rule.get("disable")) else "false",
    }


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    fieldnames = [
        "name",
        "description",
        "action",
        "from",
        "to",
        "source",
        "destination",
        "category",
        "application",
        "service",
        "source_user",
        "log_end",
        "disabled",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def export_rules(output_root: Path) -> None:
    token = get_token()
    _, payload = get_rule_payload(token)
    rules = flatten_candidates(payload)
    if not rules:
        raise RuntimeError(f"No rule items were returned by the live SCM API payload: {json.dumps(payload)[:600]}")

    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for item in rules:
        if not isinstance(item, dict):
            continue
        normalized = normalize_rule(item)
        folder_name = normalized["folder"]
        position = normalized["position"]
        grouped.setdefault(folder_name, {}).setdefault(position, []).append(normalized)

    if not grouped:
        raise RuntimeError("The rule payload was returned but did not contain parseable folder data.")

    for folder_name, positions in grouped.items():
        for position_name, rows in positions.items():
            folder_path = output_root / "security policies" / folder_name.replace("/", os.sep)
            write_csv(folder_path / f"{position_name}-rules.csv", rows)

    print(f"Exported {sum(len(v) for pos in grouped.values() for v in pos.values())} rules into {output_root / 'security policies'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Check connectivity without writing files")
    parser.add_argument("--output-root", default=str(Path(__file__).resolve().parent), help="Workspace root for export files")
    args = parser.parse_args()

    try:
        token = get_token()
        url, payload = get_rule_payload(token)
        print(f"Connected to SCM rule API: {url}")
        rules = flatten_candidates(payload)
        if args.dry_run:
            print(f"Found {len(rules)} rule entries in the live SCM response.")
            return
        export_rules(Path(args.output_root))
    except Exception as exc:  # pragma: no cover - runtime message path
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
