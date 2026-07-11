#!/usr/bin/env python3
"""
Per-symbol news fetcher.

Primary: Finnhub company-news (set FINNHUB_KEY env var / repo secret to enable).
Fallback: yfinance .news (no key, US-centric, occasionally empty).

Writes data/news/<id>.json, deduped by URL, newest first, capped.
Only runs for equity/etf symbols (companies have news; indices/FX/futures don't).
"""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = os.path.join(ROOT, "data", "news")
os.makedirs(NEWS_DIR, exist_ok=True)
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "").strip()
CAP = 40

def load_symbols():
    with open(os.path.join(ROOT, "symbols.json"), encoding="utf-8") as f:
        return [s for s in json.load(f)["symbols"] if s["kind"] in ("equity", "etf")]

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "markets-dashboard"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def finnhub_news(yf_symbol):
    # Finnhub uses the plain ticker; strip exchange suffix for a best effort
    ticker = yf_symbol.split(".")[0].lstrip("^")
    to = datetime.now(timezone.utc).date()
    frm = to - timedelta(days=14)
    url = ("https://finnhub.io/api/v1/company-news?symbol=%s&from=%s&to=%s&token=%s"
           % (urllib.parse.quote(ticker), frm, to, FINNHUB_KEY))
    items = http_json(url)
    out = []
    for n in items[:CAP]:
        out.append({
            "datetime": datetime.fromtimestamp(n.get("datetime", 0), timezone.utc).isoformat(),
            "headline": n.get("headline", ""),
            "source": n.get("source", ""),
            "url": n.get("url", ""),
            "summary": (n.get("summary", "") or "")[:280],
        })
    return out

def yf_news(yf_symbol):
    import yfinance as yf
    raw = yf.Ticker(yf_symbol).news or []
    out = []
    for n in raw[:CAP]:
        c = n.get("content", n)  # yfinance changed shape over versions
        ts = c.get("pubDate") or c.get("providerPublishTime")
        try:
            dt = datetime.fromtimestamp(int(ts), timezone.utc).isoformat() if str(ts).isdigit() else str(ts)
        except Exception:
            dt = datetime.now(timezone.utc).isoformat()
        out.append({
            "datetime": dt,
            "headline": c.get("title", ""),
            "source": (c.get("provider", {}) or {}).get("displayName", "") if isinstance(c.get("provider"), dict) else c.get("publisher", ""),
            "url": (c.get("canonicalUrl", {}) or {}).get("url", "") if isinstance(c.get("canonicalUrl"), dict) else c.get("link", ""),
            "summary": (c.get("summary", "") or "")[:280],
        })
    return out

def merge(old, new):
    seen = {i["url"] for i in new if i.get("url")}
    merged = new + [o for o in old if o.get("url") and o["url"] not in seen]
    merged.sort(key=lambda x: x.get("datetime", ""), reverse=True)
    return merged[:CAP]

def main():
    errors = 0
    for sym in load_symbols():
        sid, yfs = sym["id"], sym["yf"]
        try:
            items = finnhub_news(yfs) if FINNHUB_KEY else []
            if not items:
                items = yf_news(yfs)
            path = os.path.join(NEWS_DIR, f"{sid}.json")
            old = json.load(open(path)) ["items"] if os.path.exists(path) else []
            merged = merge(old, items)
            json.dump({"id": sid, "updated": datetime.now(timezone.utc).isoformat(), "items": merged},
                      open(path, "w"), separators=(",", ":"))
            print(f"  ok   {sid:8s} {len(merged)} items")
        except Exception as e:
            errors += 1
            print(f"  FAIL {sid:8s} {e}", file=sys.stderr)
        time.sleep(0.3)
    print(f"News done. {errors} errors.")

if __name__ == "__main__":
    main()
