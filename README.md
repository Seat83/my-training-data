[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

# Training Data Pipeline

![Sync Status](https://github.com/Seat83/my-training-data/actions/workflows/auto-sync.yml/badge.svg)

**Last successful sync:** 2026-04-23 09:09:07 UTC

Automated training data pipeline from [Intervals.icu](https://intervals.icu) for AI coaching analysis.
Built on the [Section 11 Protocol](https://github.com/CrankAddict/section-11).

## Sync Now

[🔄 Sync Now](../../actions/workflows/auto-sync.yml) — tap **Run workflow** to trigger a fresh sync. When the run completes, download the **training-data** artifact ZIP from the run page.

## Data URLs

| File | Description | Link |
|------|-------------|------|
| `latest.json` | Current 7-day snapshot + derived metrics | [View](https://github.com/Seat83/my-training-data/blob/main/latest.json) |
| `history.json` | Longitudinal data (daily/weekly/monthly) | [View](https://github.com/Seat83/my-training-data/blob/main/history.json) |
| `intervals.json` | Per-interval data for structured sessions | [View](https://github.com/Seat83/my-training-data/blob/main/intervals.json) |
| `routes.json` | Route/terrain data (when GPX/TCX attachments exist) | [View](https://github.com/Seat83/my-training-data/blob/main/routes.json) |

## Auto-Sync

Data syncs every 15 minutes via GitHub Actions. The pipeline pulls activities, wellness, and planned workouts from the Intervals.icu API, calculates derived metrics (ACWR, monotony, polarization, phase detection), and generates graduated alerts.

## AI Analysis

```
Analyze my training using these data files:
- Current: https://github.com/Seat83/my-training-data/blob/main/latest.json
- History: https://github.com/Seat83/my-training-data/blob/main/history.json
- Intervals: https://github.com/Seat83/my-training-data/blob/main/intervals.json
- Routes: https://github.com/Seat83/my-training-data/blob/main/routes.json
```

For best results, pair with the [Section 11 instruction set](https://github.com/CrankAddict/section-11).

## License

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — Free for personal and non-commercial use. Attribution required.
