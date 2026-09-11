#!/usr/bin/env python3

import argparse
import csv
import ipaddress
import re
import sys
from pathlib import Path
from typing import TextIO


COUNTRY_RE = re.compile(r"^[A-Za-z]{2}$")
REGION_RE = re.compile(r"^([A-Za-z]{2})-[A-Za-z0-9]{1,3}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an RFC 8805 geofeed CSV")
    parser.add_argument(
        "path",
        nargs="?",
        default="range.csv",
        help="geofeed CSV path, or - for standard input (default: range.csv)",
    )
    return parser.parse_args()


def canonical_prefix(value: str) -> str:
    return str(ipaddress.ip_network(value, strict=True))


def validate(stream: TextIO, source: str) -> list[str]:
    errors: list[str] = []
    prefixes: dict[str, int] = {}
    entries = 0

    for line_number, raw_line in enumerate(stream, start=1):
        if line_number == 1:
            raw_line = raw_line.removeprefix("\ufeff")
        line = raw_line.split("#", 1)[0]
        if not line.strip():
            continue

        try:
            fields = next(csv.reader([line], strict=True))
        except csv.Error as error:
            errors.append(f"{source}:{line_number}: invalid CSV: {error}")
            continue

        if len(fields) < 5:
            errors.append(
                f"{source}:{line_number}: expected at least 5 fields "
                f"(prefix,country,region,city,postal_code), got {len(fields)}"
            )
            continue

        prefix, country, region, city, postal_code = fields[:5]
        entries += 1

        try:
            normalized_prefix = canonical_prefix(prefix)
        except ValueError as error:
            errors.append(f"{source}:{line_number}: invalid IP prefix {prefix!r}: {error}")
        else:
            if normalized_prefix in prefixes:
                errors.append(
                    f"{source}:{line_number}: duplicate prefix {prefix!r}; "
                    f"first defined on line {prefixes[normalized_prefix]}"
                )
            else:
                prefixes[normalized_prefix] = line_number

        if country and not COUNTRY_RE.fullmatch(country):
            errors.append(
                f"{source}:{line_number}: country must be a 2-letter code, got {country!r}"
            )

        if region:
            match = REGION_RE.fullmatch(region)
            if not match:
                errors.append(
                    f"{source}:{line_number}: invalid ISO 3166-2 region code {region!r}"
                )
            elif not country:
                errors.append(
                    f"{source}:{line_number}: region {region!r} requires a country code"
                )
            elif match.group(1).upper() != country.upper():
                errors.append(
                    f"{source}:{line_number}: region {region!r} does not match "
                    f"country {country!r}"
                )

        for field_name, value in (("city", city), ("postal code", postal_code)):
            if "," in value:
                errors.append(
                    f"{source}:{line_number}: {field_name} must not contain a comma"
                )

    if entries == 0:
        errors.append(f"{source}: geofeed contains no entries")

    if not errors:
        print(f"Validated {entries} geofeed entries in {source}")
    return errors


def main() -> int:
    args = parse_args()

    try:
        if args.path == "-":
            errors = validate(sys.stdin, "range.csv (staged)")
        else:
            path = Path(args.path)
            with path.open(encoding="utf-8-sig", newline="") as stream:
                errors = validate(stream, str(path))
    except (OSError, UnicodeError) as error:
        print(f"Unable to read geofeed: {error}", file=sys.stderr)
        return 1

    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
