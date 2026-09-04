"""Fetch daily candles for 10 liquid NSE large-caps from Yahoo, cache to CSV.

Output: state/multistock/stocks_prices.csv  (symbol,Date,Open,High,Low,Close)
Data from 2013 (warmup ~200 din ke liye) taki analysis 2015 se shuru ho sake.
Sirf un tickers ke liye fetch karta hai jo cache mein missing hain.
"""
import os
import time
import json
import datetime
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'stocks_prices.csv')

# 10 sabse liquid NIFTY large-caps (banks + IT + FMCG + energy + infra + telecom)
SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'INFY',
           'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'LT']

P1 = int(datetime.datetime(2013, 1, 1).timestamp())
P2 = int(datetime.datetime.now().timestamp())


def fetch(sym):
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}.NS'
           f'?period1={P1}&period2={P2}&interval=1d')
    last_err = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            res = d['chart']['result'][0]
            ts = res['timestamp']
            q = res['indicators']['quote'][0]
            rows = []
            for t, o, h, l, c in zip(ts, q['open'], q['high'], q['low'], q['close']):
                if o is None or h is None or l is None or c is None:
                    continue
                dt = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).date().isoformat()
                rows.append((sym, dt, round(o, 2), round(h, 2), round(l, 2), round(c, 2)))
            return rows
        except Exception as e:  # noqa
            last_err = e
            time.sleep(3 + attempt * 3)
    raise RuntimeError(f'{sym} fetch failed: {last_err}')


def main():
    import pandas as pd
    have = {}
    if os.path.exists(OUT):
        old = pd.read_csv(OUT)
        have = {s: int((old['Date'] == old[old['symbol'] == s]['Date'].max()).sum()) if (old['symbol'] == s).any() else 0
                for s in SYMBOLS}
    frames, fresh = [], []
    for sym in SYMBOLS:
        rows = fetch(sym)
        fresh.append(sym)
        frames.append(pd.DataFrame(rows, columns=['symbol', 'Date', 'Open', 'High', 'Low', 'Close']))
        print(f'{sym}: {len(rows)} rows ({rows[0][1]} .. {rows[-1][1]})', flush=True)
        time.sleep(0.7)
    df = pd.concat(frames, ignore_index=True)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['symbol', 'Date']).reset_index(drop=True)
    df.to_csv(OUT, index=False)
    print('saved ->', OUT, f'({len(df)} rows)')


if __name__ == '__main__':
    main()
