#!/usr/bin/env python3
"""
Nightly market data fetcher.
Reads symbols.json, pulls daily OHLCV history (and, for equities/ETFs,
dividends + next earnings + key fundamentals) from Yahoo Finance via yfinance,
and writes one JSON file per symbol into data/.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import yfinance as yf

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
HISTORY_PERIOD = "3y"
os.makedirs(DATA_DIR, exist_ok=True)


def load_symbols():
    with open(os.path.join(ROOT, "symbols.json"), "r", encoding="utf-8") as f:
        return json.load(f)["symbols"]


def safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def fetch_prices(yf_symbol):
    tk = yf.Ticker(yf_symbol)
    hist = tk.history(period=HISTORY_PERIOD, interval="1d", auto_adjust=False)
    bars = []
    for idx, row in hist.iterrows():
        if row.isnull().any():
            continue
        bars.append({
            "t": idx.strftime("%Y-%m-%d"),
            "o": round(float(row["Open"]), 4),
            "h": round(float(row["High"]), 4),
            "l": round(float(row["Low"]), 4),
            "c": round(float(row["Close"]), 4),
            "v": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
        })
    return tk, bars


def fetch_fundamentals(tk):
    info = safe(lambda: tk.info, {}) or {}
    stats = {
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "dividendYield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
        "sector": info.get("sector"),
        "currency": info.get("currency"),
        "longName": info.get("longName") or info.get("shortName"),
    }
    divs = []
    dser = safe(lambda: tk.dividends, None)
    if dser is not None and len(dser) > 0:
        for idx, val in dser.tail(8).items():
            divs.append({"date": idx.strftime("%Y-%m-%d"), "amount": round(float(val), 4)})
    next_earnings = None
    cal = safe(lambda: tk.calendar, None)
    try:
        if cal is not None:
            if hasattr(cal, "get") and cal.get("Earnings Date"):
                ed = cal.get("Earnings Date")
                next_earnings = str(ed[0]) if isinstance(ed, list) and ed else str(ed)
            elif hasattr(cal, "loc") and "Earnings Date" in getattr(cal, "index", []):
                next_earnings = str(cal.loc["Earnings Date"][0])
    except Exception:
        next_earnings = None
    return {"stats": stats, "dividends": divs, "nextEarnings": next_earnings}


def write_symbol(sym, payload):
    path = os.path.join(DATA_DIR, f"{sym['id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))


def main():
    symbols = load_symbols()
    meta = {"updated": datetime.now(timezone.utc).isoformat(), "symbols": [], "errors": []}

    for sym in symbols:
        sid, yfs = sym["id"], sym["yf"]
        try:
            tk, bars = fetch_prices(yfs)
            if not bars:
                raise ValueError("no price data returned")
            payload = {
                "id": sid, "name": sym["name"], "kind": sym["kind"], "group": sym["group"],
                "yf": yfs, "leveraged": sym.get("leveraged", False),
                "bars": bars, "last": bars[-1]["c"],
                "prevClose": bars[-2]["c"] if len(bars) > 1 else bars[-1]["c"],
                "updated": datetime.now(timezone.utc).isoformat(),
            }
            if sym["kind"] in ("equity", "etf"):
                payload["fundamentals"] = fetch_fundamentals(tk)
            write_symbol(sym, payload)
            meta["symbols"].append({
                "id": sid, "name": sym["name"], "kind": sym["kind"], "group": sym["group"],
                "last": payload["last"], "prevClose": payload["prevClose"],
                "leveraged": sym.get("leveraged", False),
                "currency": "EUR" if yfs.endswith((".PA", ".DE")) else "USD",
            })
            print(f"  ok   {sid:8s} {len(bars)} bars")
        except Exception as e:
            meta["errors"].append({"id": sid, "yf": yfs, "error": str(e)})
            print(f"  FAIL {sid:8s} {e}", file=sys.stderr)
            prev = os.path.join(DATA_DIR, f"{sid}.json")
            if os.path.exists(prev):
                with open(prev, encoding="utf-8") as f:
                    old = json.load(f)
                meta["symbols"].append({
                    "id": sid, "name": sym["name"], "kind": sym["kind"], "group": sym["group"],
                    "last": old.get("last"), "prevClose": old.get("prevClose"),
                    "leveraged": sym.get("leveraged", False), "stale": True,
                    "currency": "EUR" if yfs.endswith((".PA", ".DE")) else "USD",
                })
        time.sleep(0.4)

    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, separators=(",", ":"))
    print(f"\nDone. {len(meta['symbols'])} symbols, {len(meta['errors'])} errors.")


if __name__ == "__main__":
    main()
