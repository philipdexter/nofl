# NOFL

A polished, spoiler-free view of the 2026 NFL preseason and regular-season schedule. It shows
matchups, kickoff times, broadcasts, venues, and official NFL YouTube recaps—but
never scores, winners, records, or live states.

## Features

- All 49 preseason and 272 regular-season games
- Single-week navigation or an all-weeks season view
- “Today” navigation to the next kickoff matching the active filters
- Follow multiple teams and highlight or isolate all of their games
- Visual 32-team picker with locally bundled team marks and a clear-all action
- Optional preseason checkbox that adds HOF and PW1–PW3 to the week strip
- Prime-time and international-game filters
- Automatic local-time conversion with an Eastern-time option
- Shareable filtered URLs and `.ics` calendar downloads
- Official NFL YouTube recap links for completed games
- Locally saved team preferences, compact mode, keyboard support, and responsive layouts
- Locally bundled fonts and no runtime dependencies

## Run locally

```sh
python3 -m http.server 4173
```

Then open <http://localhost:4173>. A server is needed because browsers usually
block `fetch()` for JSON when an HTML file is opened directly from disk.

## GitHub Pages

The site uses only relative asset paths, so it works at a project URL such as
`https://philipdexter.github.io/nofl/`. In the repository's **Settings → Pages**,
choose **Deploy from a branch**, select `main` and `/ (root)`, then save. No
build step or GitHub Actions workflow is required.

## Update the schedule

The updater uses Python's standard library and strips the source response down
to an allowlist of spoiler-safe fields:

```sh
python3 scripts/update_schedule.py
python3 scripts/check_spoilers.py
```

It can also normalize a saved full-season snapshot:

```sh
python3 scripts/update_schedule.py --input /path/to/snapshot.json
```

The schedule was checked against the [official NFL schedule](https://www.nfl.com/schedules/2026/).
Dates, times, and broadcasts remain subject to flex scheduling.

## Update recap links

Install [yt-dlp](https://github.com/yt-dlp/yt-dlp), then run:

```sh
python3 scripts/update_recaps.py
python3 scripts/update_recaps.py --team BUF --team NYG --team NE
python3 scripts/check_spoilers.py
```

The recap updater only accepts videos from the official NFL YouTube channel
that match both teams and the correct week; it verifies the season from the
title or upload date. Existing links are skipped, so it is safe to run every
Monday morning. Use `--dry-run` to search without changing the schedule,
`--team` (repeatable) to limit the teams, or `--refresh` to re-check existing
links.
