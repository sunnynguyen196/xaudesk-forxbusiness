"""Allowlisted MT5 market data adapter; no account or order APIs."""
import os
import sys
import json
import math
from pathlib import Path
import threading
import time
from contextlib import contextmanager

SYMBOL = "XAUUSD.c"
_LOCK = threading.Lock()


def file_mode():
    override=os.environ.get('XAU_MT5_MODE','').lower()
    if override: return override=='file'
    config=Path(__file__).with_name('.xau-mode')
    if config.exists(): return config.read_text(encoding='utf-8').strip()=='file'
    return sys.version_info[:2]>=(3,15)

def file_snapshot():
    default=Path(os.environ.get('APPDATA',''))/'MetaQuotes'/'Terminal'/'Common'/'Files'/'XAUDesk'/'snapshot.json'
    path=Path(os.environ.get('XAU_MT5_FILE',str(default)))
    try:
        if path.stat().st_size>50000:raise ValueError()
        x=json.loads(path.read_text(encoding='utf-8-sig'))
        finite=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
        if x.get('symbol')!=SYMBOL or not all(finite(x.get(k)) for k in ['bid','ask','quote_utc','sent_utc']):raise ValueError()
        if x['bid']<=0 or x['ask']<x['bid'] or not isinstance(x.get('candles'),list) or not 5<=len(x['candles'])<=80:raise ValueError()
        prev=0
        for b in x['candles']:
            if not all(finite(b.get(k)) for k in ['t','o','h','l','c']):raise ValueError()
            if b['t']<=prev or b['l']<=0 or b['h']<max(b['o'],b['c']) or b['l']>min(b['o'],b['c']) or b['t']+300>x['sent_utc']+5:raise ValueError()
            prev=b['t']
        return x
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        raise RuntimeError('No valid EA snapshot. Compile and attach XAUDeskFileBridge to XAUUSD.c M5; check README-315.md.') from None

@contextmanager
def terminal():
    import MetaTrader5 as mt5
    with _LOCK:
        path = os.environ.get("MT5_TERMINAL_PATH", "").strip()
        ok = mt5.initialize(path, timeout=10000) if path else mt5.initialize(timeout=10000)
        if not ok:
            raise RuntimeError("Cannot connect to MT5. Open FPG terminal; set MT5_TERMINAL_PATH if multiple terminals exist.")
        try:
            if not mt5.symbol_select(SYMBOL, True):
                raise RuntimeError("XAUUSD.c unavailable in this terminal.")
            yield mt5
        finally:
            mt5.shutdown()

def get_quote():
    if file_mode():
        x=file_snapshot();now=time.time()
        return {k:x[k] for k in ['symbol','bid','ask','quote_utc','sent_utc']} | {'stale':now-x['quote_utc']>30 or now-x['sent_utc']>30 or x['quote_utc']>now+60 or x['sent_utc']>now+60}
    with terminal() as mt5:
        t = mt5.symbol_info_tick(SYMBOL)
        if t is None or t.bid <= 0 or t.ask < t.bid:
            raise RuntimeError("No valid quote. Check Market Watch and network.")
        now = time.time()
        return {"symbol": SYMBOL, "bid": float(t.bid), "ask": float(t.ask),
                "quote_utc": int(t.time), "sent_utc": int(now),
                "stale": now - t.time > 30 or t.time > now + 60}

def get_candles(count=20):
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 80:
        raise ValueError("count must be an integer 1..80")
    if file_mode():
        x=file_snapshot();return {'symbol':SYMBOL,'timeframe':'M5','closed_only':True,'candles':x['candles'][-count:]}
    with terminal() as mt5:
        rows = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 1, count)
        if rows is None or len(rows) == 0:
            raise RuntimeError("M5 history unavailable. Open chart XAUUSD.c M5.")
        bars = [{"t": int(b["time"]), "o": float(b["open"]), "h": float(b["high"]),
                 "l": float(b["low"]), "c": float(b["close"])} for b in rows]
        return {"symbol": SYMBOL, "timeframe": "M5", "closed_only": True, "candles": sorted(bars, key=lambda b: b["t"])}

def snapshot():
    if file_mode():
        x=file_snapshot()
        if abs(time.time()-x['sent_utc'])>30:raise RuntimeError('EA snapshot is stale. Keep MT5 and the file bridge running.')
        return x
    quote = get_quote()
    quote["candles"] = get_candles(80)["candles"]
    if len(quote["candles"]) < 5:
        raise RuntimeError("Need at least 5 closed M5 bars.")
    return {k: v for k, v in quote.items() if k != "stale"}
