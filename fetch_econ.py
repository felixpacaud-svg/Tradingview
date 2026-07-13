#!/usr/bin/env python3
"""
Economic calendar + released-numbers archive.
Actuals + previous come from FRED (free key: set FRED_KEY env var / repo secret).
Each run MERGES into data/econ.json keyed by (code + reference date), so once a
number is published it is stored forever and never disappears.
Forecast (consensus) is left null unless a calendar source is wired in later.
FOMC meeting dates come from econ_config.json as scheduled events.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "econ.json")
FRED_KEY = os.environ.get("FRED_KEY", "").strip()

def cfg():
    with open(os.path.join(ROOT, "econ_config.json"), encoding="utf-8") as f:
        return json.load(f)

def fred_series(series_id, n=25):
    url = ("https://api.stlouisfed.org/fred/series/observations"
           "?series_id=%s&api_key=%s&file_type=json&sort_order=desc&limit=%d"
           % (series_id, FRED_KEY, n))
    req = urllib.request.Request(url, headers={"User-Agent": "markets-dashboard"})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.load(r)
    obs = [o for o in data.get("observations", []) if o["value"] not in (".", "")]
    return [{"date": o["date"], "value": float(o["value"])} for o in obs]

def build_events():
    c = cfg()
    events = []
    for ind in c["indicators"]:
        try:
            obs = fred_series(ind["series"])
            if len(obs) < 2:
                continue
            for i in range(min(12, len(obs) - 1)):
                cur, prev = obs[i], obs[i + 1]
                t = ind["transform"]
                if t == "mom_pct":
                    actual = round((cur["value"] / prev["value"] - 1) * 100, 2)
                    previous = round((prev["value"] / obs[i + 2]["value"] - 1) * 100, 2) if i + 2 < len(obs) else None
                elif t == "mom_chg":
                    actual = round(cur["value"] - prev["value"], 1)
                    previous = round(prev["value"] - obs[i + 2]["value"], 1) if i + 2 < len(obs) else None
                else:
                    actual = round(cur["value"], 2)
                    previous = round(prev["value"], 2)
                events.append({
                    "id": f"{ind['code']}_{cur['date']}",
                    "code": ind["code"], "name": ind["name"], "country": "US", "flag": "🇺🇸",
                    "importance": ind["importance"], "date": cur["date"], "time": "12:30",
                    "actual": actual, "forecast": None, "previous": previous, "unit": ind["unit"],
                })
            print(f"  ok   {ind['code']:8s}")
        except Exception as e:
            print(f"  FAIL {ind['code']:8s} {e}", file=sys.stderr)
    for d in c.get("fomc_2026", []):
        events.append({
            "id": f"FOMC_{d}", "code": "FOMC", "name": "FOMC Meeting", "country": "US", "flag": "🇺🇸",
            "importance": "high", "date": d, "time": "18:00",
            "actual": None, "forecast": None, "previous": None, "unit": "",
        })
    return events

def merge_persist(new_events):
    old = {}
    if os.path.exists(OUT):
        for e in json.load(ope
