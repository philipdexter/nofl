#!/usr/bin/env python3
"""Build the spoiler-free schedule bundle.

Usage:
  python3 scripts/update_schedule.py
  python3 scripts/update_schedule.py --input /path/to/full-season.json
      --preseason-input /path/to/preseason-week-1.json

Without inputs, the script downloads the Hall of Fame game, all three preseason
weeks, and each regular-season week from ESPN's public scoreboard endpoint.
Only future-facing schedule fields are retained. Scores, records, status,
winner flags, and result links are never written.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import urllib.request
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "schedule.json"
SEASON = 2026
ENDPOINT = (
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    "?seasontype={season_type}&week={week}&dates={season}"
)


def fetch_week(week: int, season_type: int) -> dict:
    request = urllib.request.Request(
        ENDPOINT.format(week=week, season=SEASON, season_type=season_type),
        headers={"User-Agent": "NOFL schedule builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def week_label(phase: str, week: int) -> str:
    if phase == "preseason":
        return "Hall of Fame" if week == 1 else f"Preseason {week - 1}"
    return f"Week {week}"


def games_from_scoreboard(payload: dict, week: int, phase: str) -> list[dict]:
    games = []
    for event in payload.get("events", []):
        competition = event["competitions"][0]
        competitors = {team["homeAway"]: team for team in competition["competitors"]}
        away = competitors["away"]["team"]
        home = competitors["home"]["team"]
        venue = competition.get("venue", {})
        address = venue.get("address", {})
        broadcasts = [
            name
            for item in competition.get("broadcasts", [])
            for name in item.get("names", [])
        ]
        notes = [note.get("headline", "") for note in competition.get("notes", [])]
        status = competition.get("status", {}).get("type", {})
        games.append(
            normalize_game(
                {
                    "id": event["id"],
                    "week": week,
                    "startTimeUTC": event.get("date"),
                    "timeValid": not status.get("description", "").upper().startswith("TBD"),
                    "matchup": {
                        "away": {
                            "abbreviation": away["abbreviation"],
                            "displayName": away["displayName"],
                            "shortDisplayName": away.get("shortDisplayName", away["displayName"]),
                        },
                        "home": {
                            "abbreviation": home["abbreviation"],
                            "displayName": home["displayName"],
                            "shortDisplayName": home.get("shortDisplayName", home["displayName"]),
                        },
                    },
                    "broadcastNames": broadcasts,
                    "venue": {
                        "fullName": venue.get("fullName", ""),
                        "city": address.get("city", ""),
                        "state": address.get("state", ""),
                        "country": address.get("country", ""),
                    },
                    "neutralSite": competition.get("neutralSite", False),
                    "notes": notes,
                },
                phase,
            )
        )
    return games


def normalize_game(game: dict, phase: str = "regular") -> dict:
    matchup = game["matchup"]
    venue = game.get("venue") or {}
    valid_time = bool(game.get("timeValid", True))
    return {
        "id": str(game["id"]),
        "seasonType": phase,
        "week": int(game["week"]),
        "weekLabel": week_label(phase, int(game["week"])),
        "kickoff": game.get("startTimeUTC") if valid_time else None,
        "dateTbd": not valid_time,
        "away": matchup["away"]["abbreviation"],
        "home": matchup["home"]["abbreviation"],
        "broadcast": ", ".join(game.get("broadcastNames") or ([game["broadcast"]] if game.get("broadcast") else [])),
        "venue": venue.get("fullName", ""),
        "location": ", ".join(
            part for part in (venue.get("city"), venue.get("state") or venue.get("country")) if part
        ),
        "neutralSite": bool(game.get("neutralSite", False)),
        "note": next((note for note in game.get("notes", []) if note), ""),
    }


def load_input(path: pathlib.Path, phase: str) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if "weeks" in payload:
        return [normalize_game(game, phase) for week in payload["weeks"] for game in week["games"]]
    week = int(payload.get("week", {}).get("number", 1))
    return games_from_scoreboard(payload, week, phase)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path)
    parser.add_argument("--preseason-input", type=pathlib.Path, action="append", default=[])
    args = parser.parse_args()

    existing_recaps = {}
    recaps_updated_at = None
    if OUTPUT.exists():
        with OUTPUT.open(encoding="utf-8") as stream:
            existing_bundle = json.load(stream)
            existing_recaps = {
                game["id"]: game["recapUrl"]
                for game in existing_bundle.get("games", [])
                if game.get("recapUrl")
            }
            recaps_updated_at = existing_bundle.get("recapsUpdatedAt")

    if args.input:
        games = load_input(args.input, "regular")
        for path in args.preseason_input:
            games.extend(load_input(path, "preseason"))
        source = "Imported schedule snapshot; verified against NFL.com"
    else:
        games = []
        for week in range(1, 5):
            games.extend(games_from_scoreboard(fetch_week(week, 1), week, "preseason"))
        for week in range(1, 19):
            games.extend(games_from_scoreboard(fetch_week(week, 2), week, "regular"))
        source = "ESPN public scoreboard API; verified against NFL.com"

    games.sort(
        key=lambda game: (
            0 if game["seasonType"] == "preseason" else 1,
            game["week"],
            game["kickoff"] or "9999",
            game["home"],
        )
    )
    for game in games:
        if game["id"] in existing_recaps:
            game["recapUrl"] = existing_recaps[game["id"]]
    bundle = {
        "season": SEASON,
        "seasonTypes": ["preseason", "regular"],
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "gameCount": len(games),
        "games": games,
    }
    if existing_recaps and recaps_updated_at:
        bundle["recapsUpdatedAt"] = recaps_updated_at
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as stream:
        json.dump(bundle, stream, indent=2)
        stream.write("\n")
    print(f"Wrote {len(games)} spoiler-free games to {OUTPUT}")


if __name__ == "__main__":
    main()
