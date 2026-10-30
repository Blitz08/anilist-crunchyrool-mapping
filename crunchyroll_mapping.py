#!/usr/bin/env python3
"""Normalize saved Crunchyroll CMS responses into a mapping database."""

import argparse
import json
import sys
from pathlib import Path


def _value(record, *keys):
    for key in keys:
        value = record.get(key)
        if value is not None:
            return value
    return None


def _record_type(record):
    if any(
        key in record
        for key in ("episode_number", "duration_ms", "next_episode_id", "streams_link")
    ):
        return "episodes"
    if any(key in record for key in ("episode_count", "season_count", "media_count")):
        return "series"
    if "season_number" in record or "season_id" in record:
        return "seasons"
    if "series_id" in record and any(key in record for key in ("title", "name")):
        return "seasons"
    raise ValueError("could not identify record as a series, season, or episode")


def _normalize_version(version):
    if not isinstance(version, dict):
        return None
    fields = {
        "audio_locale": _value(version, "audio_locale"),
        "subtitle_locale": _value(version, "subtitle_locale"),
        "is_subbed": _value(version, "is_subbed"),
        "is_dubbed": _value(version, "is_dubbed"),
    }
    return {key: value for key, value in fields.items() if value is not None}


def _normalize(record, kind):
    if kind == "series":
        fields = {
            "id": _value(record, "id", "series_id"),
            "title": _value(record, "title", "series_title", "name"),
            "episode_count": _value(record, "episode_count"),
            "season_count": _value(record, "season_count"),
            "media_count": _value(record, "media_count"),
            "year": _value(record, "year", "start_year"),
            "is_subbed": _value(record, "is_subbed"),
            "is_dubbed": _value(record, "is_dubbed"),
        }
    elif kind == "seasons":
        fields = {
            "id": _value(record, "id", "season_id"),
            "series_id": _value(record, "series_id"),
            "title": _value(record, "title", "season_title", "name"),
            "season_number": _value(record, "season_number"),
            "sequence_number": _value(record, "sequence_number"),
            "episode_count": _value(record, "episode_count"),
        }
    else:
        fields = {
            "id": _value(record, "id", "episode_id"),
            "external_id": _value(record, "identifier", "external_id"),
            "series_id": _value(record, "series_id"),
            "season_id": _value(record, "season_id"),
            "season_title": _value(record, "season_title"),
            "season_number": _value(record, "season_number"),
            "season_sequence_number": _value(
                record, "season_sequence_number", "season_sequence"
            ),
            "episode_number": _value(record, "episode_number"),
            "sequence_number": _value(record, "sequence_number"),
            "title": _value(record, "title", "episode_title", "name"),
            "slug": _value(record, "slug"),
            "air_date": _value(record, "episode_air_date", "air_date"),
            "duration_ms": _value(record, "duration_ms"),
            "next_episode_id": _value(record, "next_episode_id"),
            "streams_link": _value(record, "streams_link"),
            "is_subbed": _value(record, "is_subbed"),
            "is_dubbed": _value(record, "is_dubbed"),
            "audio_locale": _value(record, "audio_locale"),
            "subtitle_locale": _value(record, "subtitle_locale"),
        }
        versions = record.get("versions")
        if isinstance(versions, list):
            fields["versions"] = [
                normalized
                for version in versions
                if (normalized := _normalize_version(version))
            ]
    return {key: value for key, value in fields.items() if value is not None}


def _response_records(document):
    if isinstance(document, dict):
        records = document.get("data", document)
        cursor = document.get("next_cursor")
    else:
        records = document
        cursor = None
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        raise ValueError("response data must be an object or an array")
    return records, cursor


def _sort_key(kind, record):
    sequence = record.get("sequence_number")
    if sequence is None:
        sequence = record.get("episode_number" if kind == "episodes" else "season_number")
    if isinstance(sequence, (int, float)):
        return (sequence is None, 0, sequence, str(record["id"]))
    return (sequence is None, 1, str(sequence), str(record["id"]))


def build_database(documents):
    """Build a deterministic database from decoded Crunchyroll API responses."""
    database = {"series": {}, "seasons": {}, "episodes": {}, "next_cursors": []}
    for document in documents:
        records, cursor = _response_records(document)
        if cursor is not None and cursor not in database["next_cursors"]:
            database["next_cursors"].append(cursor)
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("response data entries must be objects")
            record_id = _value(record, "id", "episode_id", "season_id")
            kind = next(
                (
                    existing_kind
                    for existing_kind in ("series", "seasons", "episodes")
                    if record_id in database[existing_kind]
                ),
                None,
            )
            if kind is None:
                kind = _record_type(record)
            normalized = _normalize(record, kind)
            record_id = normalized.get("id")
            if record_id is None:
                raise ValueError(f"{kind[:-1]} record is missing its ID")
            existing = database[kind].setdefault(record_id, {})
            existing.update(normalized)
    result = {
        kind: sorted(records.values(), key=lambda record: _sort_key(kind, record))
        for kind, records in database.items()
        if kind != "next_cursors"
    }
    result["next_cursors"] = database["next_cursors"]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Normalize saved Crunchyroll CMS JSON responses."
    )
    parser.add_argument(
        "responses",
        nargs="+",
        type=Path,
        help="JSON response files (episode, series, season, or paginated episode list)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("mapping.json"), help="output JSON file"
    )
    args = parser.parse_args(argv)

    try:
        documents = [
            json.loads(path.read_text(encoding="utf-8")) for path in args.responses
        ]
        database = build_database(documents)
        args.output.write_text(
            json.dumps(database, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
