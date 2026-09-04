"""Fetch daily candles for the full momentum universe (90 names) from Yahoo.

Output: state/multistock/universe_prices.csv  (symbol,Date,Open,High,Low,Close)
Incremental: sirf wahi symbols fetch karta hai jo cache mein missing hain.
"""
import os
import time
import json
import datetime
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'universe_prices.csv')

SYMBOLS = [
    'RELIANCE','HDFCBANK','ICICIBANK','INFY','TCS','ITC','SBIN','KOTAKBANK','BHARTIARTL','LT',
    'AXISBANK','BAJFINANCE','BAJAJFINSV','MARUTI','ASIANPAINT','HINDUNILVR','SUNPHARMA','TITAN',
    'ULTRACEMCO','NESTLEIND','WIPRO','HCLTECH','TATASTEEL','TMPV','MM','POWERGRID','NTPC','ONGC',
    'COALINDIA','JSWSTEEL','ADANIPORTS','GRASIM','CIPLA','TECHM','HAL','CHOLAFIN','MUTHOOTFIN',
    'MAZDOCK','DMART','MOTHERSON','TVSMOTOR','SIEMENS','ABB','BOSCHLTD','CUMMINSIND','DLF','GODREJCP',
    'AMBUJACEM','PIDILITIND','TORNTPHARM','INDHOTEL','PFC','RECLTD','BANKBARODA','INDIGO',
    'APOLLOHOSP','DIVISLAB','DRREDDY','ZYDUSLIFE','BRITANNIA','TATACONSUM','UNITDSPR','VBL',
    'EICHERMOT','BAJAJ-AUTO','HYUNDAI','BPCL','IOC','GAIL','TATAPOWER','ADANIPOWER','ADANIGREEN',
    'ADANIENT','ADANIENSOL','VEDL','HINDALCO','HINDZINC','JINDALSTEL','SHREECEM','MAXHEALTH',
    'CANBK','PNB','UNIONBANK','SHRIRAMFIN','BAJAJHLDNG','HDFCAMC','JIOFIN','TATACAP','LODHA',
    'ETERNAL',
]

# symbols whose Yahoo ticker differs from "{sym}.NS"
_YMAP = {'TMPV': 'TATAMOTORS', 'MM': 'M&M'}

P1 = int(datetime.datetime(2013, 1, 1).timestamp())
P2 = int(datetime.datetime.now().timestamp())


def yahoo(sym: str) -> str:
    return _YMAP.get(sym, sym) + '.NS'


def fetch(sym):
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{yahoo(sym)}'
           f'?period1={P1}&period2={P2}&interval=1d')
    last_err = None
    for attempt in range(6):
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
                rows.append(f"{sym},{dt},{o:.2f},{h:.2f},{l:.2f},{c:.2f}")
            return rows
        except Exception as e:
            last_err = e
            time.sleep(3 + attempt * 2)
    print(f'  FAIL {sym} ({yahoo(sym)}): {last_err}')
    return None


def main():
    # already-fetched symbols
    have = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                if line.startswith('symbol,'):
                    continue
                have.add(line.split(',')[0])
    todo = [s for s in SYMBOLS if s not in have]
    if not todo:
        print('Sab symbols already cached — kuch fetch nahi.')
        return
    print(f'{len(todo)}/{len(SYMBOLS)} symbols fetch honge...')
    with open(OUT, 'a') as f:
        for i, sym in enumerate(todo):
            rows = fetch(sym)
            if rows:
                for r in rows:
                    f.write(r + '\n')
                f.flush()
                print(f'  [{i+1}/{len(todo)}] {sym} -> {len(rows)} rows')
            time.sleep(1.2)  # polite rate limit
    print('Done.')


if __name__ == '__main__':
    main()