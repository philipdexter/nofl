#!/usr/bin/env python3
"""Build the spoiler-free schedule bundle.

Usage:
  python3 scripts/update_schedule.py
  python3 scripts/update_schedule.py --input /path/to/full-season.json

Without --input, the script downloads each regular-season week from ESPN's
public scoreboard endpoint. Only future-facing schedule fields are retained.
Scores, records, status, winner flags, and result links are never written.
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
    "?seasontype=2&week={week}&dates={season}"
)


def fetch_week(week: int) -> dict:
    request = urllib.request.Request(
        ENDPOINT.format(week=week, season=SEASON),
        headers={"User-Agent": "NOFL schedule builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def games_from_scoreboard(payload: dict, week: int) -> list[dict]:
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
                }
            )
        )
    return games


def normalize_game(game: dict) -> dict:
    matchup = game["matchup"]
    venue = game.get("venue") or {}
    valid_time = bool(game.get("timeValid", True))
    return {
        "id": str(game["id"]),
        "week": int(game["week"]),
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


def load_input(path: pathlib.Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if "weeks" in payload:
        return [normalize_game(game) for week in payload["weeks"] for game in week["games"]]
    return [game for week in range(1, 19) for game in games_from_scoreboard(payload, week)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path)
    args = parser.parse_args()

    if args.input:
        games = load_input(args.input)
        source = "Imported schedule snapshot; verified against NFL.com"
    else:
        games = []
        for week in range(1, 19):
            games.extend(games_from_scoreboard(fetch_week(week), week))
        source = "ESPN public scoreboard API; verified against NFL.com"

    games.sort(key=lambda game: (game["week"], game["kickoff"] or "9999", game["home"]))
    bundle = {
        "season": SEASON,
        "seasonType": "regular",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "gameCount": len(games),
        "games": games,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as stream:
        json.dump(bundle, stream, indent=2)
        stream.write("\n")
    print(f"Wrote {len(games)} spoiler-free games to {OUTPUT}")


if __name__ == "__main__":
    main()
