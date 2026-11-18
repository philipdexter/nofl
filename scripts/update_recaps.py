#!/usr/bin/env python3
"""Add official NFL YouTube recap links to completed games.

The script searches YouTube through yt-dlp, accepts results only from the
official NFL channel, and verifies the matchup, season, and week before writing
the URL to data/schedule.json. Existing links are left untouched by default.

Usage:
  python3 scripts/update_recaps.py
  python3 scripts/update_recaps.py --team BUF --team NYG --team NE
  python3 scripts/update_recaps.py --dry-run
  python3 scripts/update_recaps.py --refresh
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "data" / "schedule.json"
NFL_CHANNEL_ID = "UCDVYQ4Zhbm3S2dlz7P1GBDg"
YOUTUBE_URL = "https://www.youtube.com/watch?v={}"
RECAP_DELAY = timedelta(hours=4)

TEAM_NAMES = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WSH": "Washington Commanders",
}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def search_query(game: dict, season: int) -> str:
    away = TEAM_NAMES[game["away"]]
    home = TEAM_NAMES[game["home"]]
    if game["seasonType"] == "preseason":
        period = "Hall of Fame Game" if game["week"] == 1 else f"Preseason Week {game['week'] - 1}"
    else:
        period = f"NFL Season Week {game['week']}"
    return f"{away} {home} Game Highlights {season} {period}"


def normalized_words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def is_official_nfl(entry: dict) -> bool:
    return (
        entry.get("channel_id") == NFL_CHANNEL_ID
        or entry.get("uploader_id") == "@NFL"
    )


def looks_like_official_nfl(entry: dict) -> bool:
    channel = entry.get("channel", "")
    return is_official_nfl(entry) or channel == "NFL" or channel.startswith("NFL and ")


def is_matching_recap(entry: dict, game: dict, season: int) -> bool:
    if not is_official_nfl(entry):
        return False
    title = entry.get("title", "")
    folded = title.casefold()
    upload_date = entry.get("upload_date", "")
    if "preview" in folded or (str(season) not in title and not upload_date.startswith(str(season))):
        return False

    title_words = normalized_words(title)
    for code in (game["away"], game["home"]):
        nickname = TEAM_NAMES[code].split()[-1].casefold()
        if nickname not in title_words:
            return False

    if game["seasonType"] == "regular":
        if not re.search(rf"\bweek\s+{game['week']}\b", folded):
            return False
        return "highlight" in folded or "recap" in folded

    if game["week"] == 1:
        return "hall of fame" in folded and ("highlight" in folded or "recap" in folded)
    return bool(re.search(rf"\bpreseason\s+week\s+{game['week'] - 1}\b", folded))


def find_recap(game: dict, season: int) -> tuple[str | None, str | None]:
    query = search_query(game, season)
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
        f"ytsearch20:{query}",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, check=True)
        payload = json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        return None, detail.strip().splitlines()[-1]

    for entry in payload.get("entries", []):
        if is_matching_recap(entry, game, season):
            return YOUTUBE_URL.format(entry["id"]), entry.get("title", "")
        title_words = normalized_words(entry.get("title", ""))
        nicknames = [TEAM_NAMES[code].split()[-1].casefold() for code in (game["away"], game["home"])]
        if looks_like_official_nfl(entry) and all(nickname in title_words for nickname in nicknames):
            detail_command = [
                "yt-dlp",
                "--skip-download",
                "--dump-single-json",
                "--no-warnings",
                YOUTUBE_URL.format(entry["id"]),
            ]
            try:
                detail_result = subprocess.run(
                    detail_command, capture_output=True, text=True, timeout=45, check=True
                )
                detailed_entry = json.loads(detail_result.stdout)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
                continue
            if is_matching_recap(detailed_entry, game, season):
                return YOUTUBE_URL.format(entry["id"]), detailed_entry.get("title", "")
    return None, "no verified official-NFL result"


def game_label(game: dict) -> str:
    return f"{game['weekLabel']}: {game['away']} at {game['home']}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="search without changing schedule.json")
    parser.add_argument("--refresh", action="store_true", help="re-check games that already have links")
    parser.add_argument("--workers", type=int, default=6, help="parallel YouTube searches (default: 6)")
    parser.add_argument("--limit", type=int, help="only search the first N eligible games")
    parser.add_argument("--game-id", action="append", default=[], help="only search a specific game ID; repeatable")
    parser.add_argument(
        "--team",
        action="append",
        default=[],
        type=str.upper,
        choices=sorted(TEAM_NAMES),
        help="only update games involving this team abbreviation; repeatable",
    )
    args = parser.parse_args()

    if not shutil.which("yt-dlp"):
        parser.error("yt-dlp is required; install it with 'brew install yt-dlp' or 'pipx install yt-dlp'")
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    bundle = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    selected_ids = set(args.game_id)
    selected_teams = set(args.team)
    eligible = []
    for game in bundle["games"]:
        if selected_ids and game["id"] not in selected_ids:
            continue
        if selected_teams and not selected_teams.intersection((game["away"], game["home"])):
            continue
        if not game.get("kickoff") or parse_time(game["kickoff"]) + RECAP_DELAY > now:
            continue
        if game.get("recapUrl") and not args.refresh:
            continue
        eligible.append(game)
    if args.limit is not None:
        eligible = eligible[: args.limit]

    if not eligible:
        print("No completed games need recap links.")
        return

    print(f"Searching for {len(eligible)} recap link(s) from the official NFL YouTube channel...")
    found: dict[str, str] = {}
    missing = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(find_recap, game, bundle["season"]): game for game in eligible}
        for future in concurrent.futures.as_completed(futures):
            game = futures[future]
            url, detail = future.result()
            if url:
                found[game["id"]] = url
                print(f"FOUND   {game_label(game)} — {detail}")
            else:
                missing.append(game)
                print(f"MISSING {game_label(game)} — {detail}", file=sys.stderr)

    if found and not args.dry_run:
        for game in bundle["games"]:
            if game["id"] in found:
                game["recapUrl"] = found[game["id"]]
        bundle["recapsUpdatedAt"] = now.isoformat(timespec="seconds")
        SCHEDULE.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(found)} recap link(s) to {SCHEDULE}")
    elif args.dry_run:
        print(f"Dry run: found {len(found)} link(s); no files changed.")

    if missing:
        print(f"{len(missing)} game(s) still need a verified recap; rerun later.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
