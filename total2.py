"""Download daily TOTAL2 (crypto market cap excluding BTC) from TradingView into total2.json."""
import json
import random
import re
import string
import time
from datetime import datetime, timezone

from websocket import create_connection


def frame(text):
    return f"~m~{len(text)}~m~{text}"


def msg(func, params):
    return frame(json.dumps({"m": func, "p": params}, separators=(",", ":")))


def tv_bars(symbol, interval="1D", n=1500):
    ws = create_connection("wss://data.tradingview.com/socket.io/websocket",
                           header=["Origin: https://data.tradingview.com"], timeout=30)
    cs = "cs_" + "".join(random.choices(string.ascii_lowercase, k=12))
    ws.send(msg("set_auth_token", ["unauthorized_user_token"]))
    ws.send(msg("chart_create_session", [cs, ""]))
    ws.send(msg("resolve_symbol", [cs, "sym1", '={"symbol":"%s","adjustment":"splits"}' % symbol]))
    ws.send(msg("create_series", [cs, "s1", "s1", "sym1", interval, n]))
    raw, deadline = "", time.time() + 40
    while time.time() < deadline:
        r = ws.recv()
        if re.fullmatch(r"~m~\d+~m~~h~\d+", r):
            ws.send(r)
            continue
        raw += r
        if "symbol_error" in r or "critical_error" in r:
            raise RuntimeError(r[:200])
        if "series_completed" in r:
            break
    ws.close()
    bars = {}
    for part in re.split(r"~m~\d+~m~", raw):
        if not part.startswith("{"):
            continue
        try:
            d = json.loads(part)
        except ValueError:
            continue
        if d.get("m") not in ("timescale_update", "du"):
            continue
        for it in d["p"][1].get("s1", {}).get("s", []):
            v = it["v"]
            bars[int(v[0])] = v
    return [bars[k] for k in sorted(bars)]


rows = []
for v in tv_bars("CRYPTOCAP:TOTAL2"):
    day = datetime.fromtimestamp(v[0], timezone.utc).strftime("%Y-%m-%d")
    if day >= "2024-01-01":
        rows.append([day, round(v[4] / 1e9, 1), round(v[3] / 1e9, 1)])   # date, close $B, low $B
assert len(rows) > 300, len(rows)
json.dump({"source": "TradingView CRYPTOCAP:TOTAL2, daily, US$ billions", "cols": ["date", "close", "low"], "rows": rows},
          open("total2.json", "w"), separators=(",", ":"))
print(len(rows), rows[-1])
