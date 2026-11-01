#!/usr/bin/env python3
"""Create address objects in Strata Cloud Manager (SCM).

Credentials are read from the .env file next to this script (or from environment variables):
    SCM_CLIENT_ID, SCM_CLIENT_SECRET, SCM_TSG_ID

Interactive (default):
    python3 create_address.py

The script asks for the folder, then accepts pasted addresses, one per line.
The type is detected from each value:

    10.1.1.0/23             ip-netmask
    10.1.1.10               ip-netmask (host, stored as /32)
    10.1.1.1-10.1.1.50      ip-range
    app.example.com         fqdn

Put a name before the value to override the generated object name:

    web-01 10.1.1.10/32

Single object without prompts:
    python3 create_address.py --name web-server-01 --ip-netmask 10.1.1.10/32 --folder Shared
"""
import argparse
import ipaddress
import os
import re
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple

import requests

AUTH_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
API_BASE = "https://api.sase.paloaltonetworks.com/sse/config/v1"

TYPE_LABELS = {
    "ip_netmask": "ip-netmask",
    "ip_range": "ip-range",
    "ip_wildcard": "ip-wildcard",
    "fqdn": "fqdn",
}

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
_FQDN = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"
)


class AddressEntry(NamedTuple):
    name: str
    kind: str
    value: str


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


def classify(raw: str) -> Tuple[str, str]:
    """Return the API field name and normalized value for one pasted address."""
    value = raw.strip().strip("\"'")
    if not value:
        raise ValueError("empty address")

    if "/" in value:
        return _classify_slash(value)

    left, sep, right = value.partition("-")
    if sep:
        try:
            start = ipaddress.ip_address(left)
            end = ipaddress.ip_address(right)
        except ValueError:
            start = end = None
        if start is not None and end is not None:
            if start.version != end.version:
                raise ValueError(f"range {value!r} mixes IPv4 and IPv6")
            if int(start) > int(end):
                raise ValueError(f"range start {start} is after {end}")
            return "ip_range", f"{start}-{end}"

    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        ip = None
    if ip is not None:
        prefix = 32 if ip.version == 4 else 128
        return "ip_netmask", f"{ip}/{prefix}"

    fqdn = _normalize_fqdn(value)
    if fqdn is not None:
        return "fqdn", fqdn

    raise ValueError(
        f"unrecognized address {raw!r}. "
        "Use a network (10.1.1.0/23), a range (10.1.1.1-10.1.1.50), or an FQDN."
    )


def _classify_slash(value: str) -> Tuple[str, str]:
    left, sep, right = value.partition("/")
    if not sep or not left or not right or "/" in right:
        raise ValueError(f"invalid network {value!r}")

    if right.isdigit():
        try:
            iface = ipaddress.ip_interface(value)
        except ValueError as e:
            raise ValueError(f"invalid network {value!r}") from e
        return "ip_netmask", f"{iface.ip}/{iface.network.prefixlen}"

    try:
        iface = ipaddress.ip_interface(value)
    except ValueError:
        iface = None
    if iface is not None:
        # Dotted netmask such as 10.1.1.0/255.255.254.0.
        return "ip_netmask", f"{iface.ip}/{iface.network.prefixlen}"

    try:
        address = ipaddress.ip_address(left)
        mask = ipaddress.ip_address(right)
    except ValueError as e:
        raise ValueError(f"invalid network {value!r}") from e
    if address.version != mask.version:
        raise ValueError(f"invalid wildcard {value!r}")
    return "ip_wildcard", f"{address}/{mask}"


def _normalize_fqdn(value: str) -> Optional[str]:
    wildcard = value.startswith("*.")
    candidate = value[2:] if wildcard else value
    candidate = candidate.lower().rstrip(".")
    if not _FQDN.match(candidate):
        return None
    return f"*.{candidate}" if wildcard else candidate


def auto_name(value: str) -> str:
    raw = value.replace("*", "wc").replace("/", "_")
    raw = re.sub(r"[^A-Za-z0-9._-]", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("._-")
    if raw and not raw[0].isalnum():
        raw = "addr-" + raw
    if not _NAME.match(raw):
        raise ValueError(
            f"cannot make an object name from {value!r}. Put a shorter name in front of it."
        )
    return raw


def validate_name(name: str) -> None:
    if not _NAME.match(name):
        raise ValueError(
            f"invalid object name {name!r}. Use letters, numbers, '.', '_' or '-', "
            "up to 63 characters, starting with a letter or number."
        )


def parse_line(line: str) -> Optional[AddressEntry]:
    text = line.strip()
    if not text or text.startswith("#"):
        return None

    try:
        kind, value = classify(text)
    except ValueError as first_error:
        parts = text.split()
        if len(parts) != 2:
            compact = re.sub(r"\s*-\s*", "-", text)
            if compact != text:
                kind, value = classify(compact)
                return AddressEntry(auto_name(value), kind, value)
            raise first_error
        name, raw = parts
        validate_name(name)
        kind, value = classify(raw)
        return AddressEntry(name, kind, value)
    return AddressEntry(auto_name(value), kind, value)


def parse_lines(lines: List[str]) -> List[AddressEntry]:
    entries: List[AddressEntry] = []
    errors: List[str] = []
    for lineno, line in enumerate(lines, start=1):
        try:
            entry = parse_line(line)
        except ValueError as e:
            errors.append(f"Line {lineno}: {e}")
            continue
        if entry is not None:
            entries.append(entry)

    if errors:
        sys.exit("\n".join(errors))
    if not entries:
        sys.exit("No addresses were pasted.")

    seen: Dict[str, str] = {}
    for entry in entries:
        previous = seen.get(entry.name)
        if previous is not None:
            sys.exit(
                f"Name {entry.name!r} is used more than once ({previous} and {entry.value}). "
                "Put a distinct name in front of one of them."
            )
        seen[entry.name] = entry.value
    return entries


def prompt_folder(preset: Optional[str]) -> str:
    if preset:
        return preset
    folder = input("Folder (for example All or Shared): ").strip()
    if not folder:
        sys.exit("Folder is required.")
    return folder


def prompt_objects() -> List[str]:
    print()
    print("Paste addresses, one per line. An empty line finishes.")
    print("  10.1.1.0/23              network")
    print("  10.1.1.1-10.1.1.50       range")
    print("  app.example.com          fqdn")
    print("  web-01 10.1.1.10         optional name, then the address")
    print()
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            print()
            break
        if not line.strip():
            break
        lines.append(line)
    return lines


def existing_names(token: str, folder: str) -> set:
    names = set()
    offset = 0
    limit = 500
    while True:
        resp = requests.get(
            f"{API_BASE}/addresses",
            params={"folder": folder, "limit": limit, "offset": offset},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if not resp.ok:
            print(
                f"Warning: could not list existing addresses (HTTP {resp.status_code}).",
                file=sys.stderr,
            )
            return set()
        payload = resp.json()
        batch = payload.get("data") or []
        for item in batch:
            name = item.get("name")
            if name:
                names.add(name)
        total = payload.get("total", 0)
        offset += len(batch)
        if not batch or offset >= total:
            break
    return names


def print_plan(folder: str, entries: List[AddressEntry], existing: set) -> int:
    rows = []
    create_count = 0
    for entry in entries:
        if entry.name in existing:
            action = "already exists"
        else:
            action = "create"
            create_count += 1
        rows.append((entry.name, TYPE_LABELS[entry.kind], entry.value, action))

    headers = ("name", "type", "value", "action")
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(row: Tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))

    print(f"\nFolder: {folder}\n")
    print(format_row(headers))
    print(format_row(tuple("-" * width for width in widths)))
    for row in rows:
        print(format_row(row))
    print()
    return create_count


def confirm(count: int, assume_yes: bool) -> bool:
    if count == 0:
        print("Nothing to create.")
        return False
    if assume_yes:
        return True
    noun = "address object" if count == 1 else "address objects"
    answer = input(f"Create {count} {noun}? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def create_one(
    token: str,
    folder: str,
    entry: AddressEntry,
    description: Optional[str],
    tags: Optional[List[str]],
) -> dict:
    body = {"name": entry.name, entry.kind: entry.value}
    if description:
        body["description"] = description
    if tags:
        body["tag"] = tags
    resp = requests.post(
        f"{API_BASE}/addresses",
        params={"folder": folder},
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def create_entries(
    token: str,
    folder: str,
    entries: List[AddressEntry],
    existing: set,
    description: Optional[str],
    tags: Optional[List[str]],
) -> int:
    created = 0
    for entry in entries:
        if entry.name in existing:
            print(f"Skipped {entry.name} (already exists)")
            continue
        try:
            create_one(token, folder, entry, description, tags)
        except RuntimeError as e:
            print(f"Failed {entry.name}: {e}")
            if created:
                print(f"Created {created} before this failure. Those objects are candidate config.")
            sys.exit(1)
        created += 1
        print(f"Created {entry.name} ({TYPE_LABELS[entry.kind]} {entry.value})")
    return created


def finish(created: int) -> None:
    if created:
        print("Note: changes are candidate config until you push them (Push Config in SCM).")


def run_single(args: argparse.Namespace) -> None:
    if args.ip_netmask:
        kind, value = classify(args.ip_netmask)
        if kind != "ip_netmask":
            sys.exit(f"--ip-netmask got {TYPE_LABELS[kind]} value {value!r}")
    elif args.ip_range:
        kind, value = classify(args.ip_range)
        if kind != "ip_range":
            sys.exit(f"--ip-range got {TYPE_LABELS[kind]} value {value!r}")
    elif args.fqdn:
        kind, value = classify(args.fqdn)
        if kind != "fqdn":
            sys.exit(f"--fqdn got {TYPE_LABELS[kind]} value {value!r}")
    else:
        sys.exit("Pass one of --ip-netmask, --ip-range, or --fqdn with --name.")

    validate_name(args.name)
    entry = AddressEntry(args.name, kind, value)
    folder = args.folder or "Shared"
    token = get_token()
    create_one(token, folder, entry, args.description, args.tag)
    print(f"Created {entry.name} ({TYPE_LABELS[kind]} {value}) in folder {folder}")
    finish(1)


def run_interactive(args: argparse.Namespace) -> None:
    if not sys.stdin.isatty():
        sys.exit("Run this in a terminal so it can ask for the folder and the addresses.")

    folder = prompt_folder(args.folder)
    entries = parse_lines(prompt_objects())
    token = get_token()
    existing = existing_names(token, folder)
    create_count = print_plan(folder, entries, existing)
    if not confirm(create_count, args.yes):
        if create_count:
            print("Cancelled. Nothing was created.")
        return

    created = create_entries(token, folder, entries, existing, args.description, args.tag)
    finish(created)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--folder", help="SCM folder. Prompted when omitted.")
    parser.add_argument("--name", help="Create one object and skip the paste prompt")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ip-netmask", help="e.g. 10.1.1.0/23 or 10.1.1.10/32")
    group.add_argument("--ip-range", help="e.g. 10.1.1.1-10.1.1.50")
    group.add_argument("--fqdn", help="e.g. app.example.com")
    parser.add_argument("--description", help="Applied to every object created in this run")
    parser.add_argument("--tag", action="append", help="Repeatable. The tag must already exist.")
    parser.add_argument("--yes", "-y", action="store_true", help="Create without the confirmation prompt")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.name or args.ip_netmask or args.ip_range or args.fqdn:
        if not args.name:
            sys.exit("--name is required when passing a single address on the command line.")
        run_single(args)
        return
    try:
        run_interactive(args)
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    main()
