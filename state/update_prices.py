"""
Daily updater — runs the whole state pipeline.

1. Ensure state/nifty_prices.csv exists (bootstraps from the 4,200-day xlsx on
   first run).
2. Fetch NIFTY daily candles from Yahoo Finance (^NSEI) and append every day
   newer than the last stored row (no overwrite of existing rows).
3. Re-run build_state.py so CSVs, JSON and both maps are rebuilt.

Usage:
    python3 state/update_prices.py        (add new days + rebuild)
    python3 state/update_prices.py --no-fetch   (rebuild only)
"""
import os
import sys
import json
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = '/home/vaibhav/AI/yr2026/dilvergence/data/Nifty-4200-Days-2015-2026-Full.xlsx'
PRICES = os.path.join(HERE, 'nifty_prices.csv')
YAHOO = 'https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=1y&interval=1d'


def bootstrap_from_xlsx():
    import openpyxl
    import pandas as pd
    print('bootstrap: reading xlsx ->', XLSX)
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()
    df = pd.DataFrame(rows).iloc[:, :7]
    df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Event', 'Category']
    df['Date'] = pd.to_datetime(df['Date'])
    for c in ['Open', 'High', 'Low', 'Close']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['Close']).sort_values('Date').reset_index(drop=True)
    df['Event'] = df['Event'].fillna('')
    df['Category'] = df['Category'].fillna('')
    df.to_csv(PRICES, index=False)
    print('prices saved ->', PRICES, f'({len(df)} rows)')


def fetch_yahoo():
    import datetime
    req = urllib.request.Request(YAHOO, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    res = d['chart']['result'][0]
    ts = res['timestamp']
    q = res['indicators']['quote'][0]
    rows = []
    for t, o, h, l, c in zip(ts, q['open'], q['high'], q['low'], q['close']):
        if c is None or h is None or l is None or o is None:
            continue
        dt = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).date().isoformat()
        rows.append((dt, round(o, 2), round(h, 2), round(l, 2), round(c, 2)))
    return rows


def main():
    import pandas as pd

    if not os.path.exists(PRICES):
        bootstrap_from_xlsx()

    df = pd.read_csv(PRICES)
    df['Date'] = pd.to_datetime(df['Date'])
    last = df['Date'].max().date()

    no_fetch = '--no-fetch' in sys.argv
    added = 0
    if not no_fetch:
        new_rows = []
        for dt, o, h, l, c in fetch_yahoo():
            d = __import__('datetime').date.fromisoformat(dt)
            if d > last:
                new_rows.append((dt, o, h, l, c))
        if new_rows:
            import datetime as _dt
            pad = pd.DataFrame(new_rows, columns=['Date', 'Open', 'High', 'Low', 'Close'])
            pad['Date'] = pd.to_datetime(pad['Date'])
            pad['Event'] = ''
            pad['Category'] = ''
            df = pd.concat([df, pad], ignore_index=True).sort_values('Date').reset_index(drop=True)
            df.to_csv(PRICES, index=False)
            added = len(new_rows)
            print(f'appended {added} new day(s): {new_rows[0][0]} .. {new_rows[-1][0]}')
        else:
            print('no new days (prices already current through', last, ')')
    else:
        print('no-fetch mode')

    # rebuild everything
    import subprocess
    code = subprocess.call([sys.executable, os.path.join(HERE, 'build_state.py')], cwd=HERE)
    sys.exit(code)


if __name__ == '__main__':
    main()