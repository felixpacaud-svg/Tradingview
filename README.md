# Terminal — personal markets dashboard

A self-hosted, free alternative to a TradingView watchlist. Nightly EOD data via
GitHub Actions, stored in the repo, rendered by a single static page using
TradingView's open-source Lightweight Charts.

## Features
- Fast, searchable, categorised watchlist with keyboard switching (↑/↓)
- Candles + volume, toggleable EMA 9/20/50/200 and RSI 14
- Per-stock **news** (right panel)
- **Economic calendar**: clickable event flags on the chart (Actual / Forecast / Previous),
  plus a Calendar view that **permanently archives every published number** — nothing
  disappears the day after release
- **Portfolio**: value, P&L and weight per holding, EUR-based with USD auto-converted at
  the live EUR/USD; your avg cost also draws as a line on each holding's chart

## Files
| File | Role |
|---|---|
| `index.html` | The whole app. Single file. |
| `symbols.json` | Your watchlist (single source of truth). |
| `econ_config.json` | Macro indicators → FRED series, plus FOMC dates. |
| `portfolio.json` | Your positions (edit these — examples included). |
| `fetch_data.py` | Daily OHLCV + fundamentals (yfinance). |
| `fetch_news.py` | Company news (Finnhub key optional, yfinance fallback). |
| `fetch_econ.py` | Macro numbers from FRED, merged into a permanent archive. |
| `gen_sample_data.py`, `gen_samples.py` | Fill `data/` with realistic **sample** data so the app renders before the first live run. |
| `.github/workflows/update.yml` | Runs all three fetchers nightly and commits the data. |

## Go live (one-time, ~5 min)
1. Push these files to a GitHub repo.
2. **Settings → Pages → Deploy from branch → `main` / root.** Site: `https://<you>.github.io/<repo>`.
3. (Optional but recommended) **Settings → Secrets and variables → Actions** → add:
   - `FRED_KEY` — free key from fred.stlouisfed.org (unlocks the real macro numbers)
   - `FINNHUB_KEY` — free key from finnhub.io (better company news)
   Without them, prices + fundamentals + sample macro/news still work; the archive just
   starts filling once `FRED_KEY` is set.
4. **Actions tab → enable workflows → run "Update market data" once** (▶ Run workflow).
   Replaces sample data with live data; the sample banner disappears.
5. Done — refreshes itself every weekday night (02:35 UTC, after the US close + after-hours).

## Everyday edits
- **Add a symbol:** one line in `symbols.json`, push.
- **Add a macro indicator:** one line in `econ_config.json` (any FRED series ID).
- **Update holdings:** edit `portfolio.json`.

## Notes
- yfinance is unofficial and can wobble; at ~25 symbols once a day the risk is tiny, and a
  failed symbol keeps its last committed data (stale beats empty). Swap in Twelve Data if needed.
- Fundamentals/news exist only for stocks/ETFs, not indices, FX, or futures.
- Consensus **forecast** is the one macro field that's hard to get free — Actual/Previous are
  always solid from FRED; forecast fills in only if you wire a calendar source.
- LQQ is 2× *daily* leveraged and flagged in the UI.
