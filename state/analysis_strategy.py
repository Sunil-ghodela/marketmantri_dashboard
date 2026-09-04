"""Stage decision matrix + entry-tier cadence -> xlsx sheets (Stage_Map, Trade_Cadence).

Reads the daily state CSV + the JSON the pipeline just built, so numbers always
match the live dashboard. Output copies to Downloads/meeting_notes too.
"""
import os
import json
import shutil

import pandas as pd
import numpy as np

import scenario

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, 'nifty_daily_state.csv')
JSON = os.path.join(HERE, 'nifty_state_data.json')
XLSX = os.path.join(HERE, 'technical_parameters_full.xlsx')
COPY_TO = '/home/vaibhav/Downloads/meeting_notes/technical_parameters_full.xlsx'

df = pd.read_csv(CSV, parse_dates=['Date'])
d = json.load(open(JSON))
st = d['analysis']['stages']
meta = {m['name']: m for m in d['analysis']['stage_meta']}

# ---- Sheet 1: stage decision matrix ----
rows = []
for s in st['share']:
    m = meta[s['stage']]
    r = st['runs'][s['stage']]
    rows.append({
        'Stage': s['stage'], 'Action': m['action'], 'N_days': s['n'],
        'Pct_days': s['pct'], 'Avg_run_len': r['avg_len'], 'Max_run': r['max_len'],
        'Avg_+20d_pct': s['avg20'], 'Win_+20d_pct': s['win20'],
        'Kya_hai': m['desc'], 'Rule_v1': m['rule'],
    })
mat = pd.DataFrame(rows)

# ---- Sheet 2: trade cadence ----
tiers = []
for t in st['tiers']:
    tiers.append({'Tier': t['tier'], 'N_signals_12yr': t['n'],
                  'Per_year': t['per_year'], 'Gap_days_avg': t['gap_avg'],
                  'Avg_+10d_pct': t['avg_f10'], 'Win_+10d_pct': t['win_f10'],
                  'Avg_+20d_pct': t['avg_f20'], 'Win_+20d_pct': t['win_f20']})
cdf = pd.DataFrame(tiers)
qrow = {'Tier': 'QUALITY (T1+T2)', 'N_signals_12yr': st['quality_n'],
        'Per_year': st['quality_per_year'], 'Gap_days_avg': st['quality_gap_avg'],
        'Avg_+10d_pct': None, 'Win_+10d_pct': None,
        'Avg_+20d_pct': None, 'Win_+20d_pct': None}
cdf = pd.concat([cdf, pd.DataFrame([qrow])], ignore_index=True)

md = st['months_dist_pct']
dist = pd.DataFrame([
    {'Month_trades': k, 'Pct_months': v} for k, v in
    sorted(md.items(), key=lambda kv: (0 if kv[0] == '4+' else int(kv[0]), kv[0]))
])
# regime run context (why cadence is what it is)
runs = []
for k, r in d['analysis']['streaks'].items():
    runs.append({'Regime': k, 'Runs': r['n'], 'Avg_len': r['avg'],
                 'Max_len': r['max']})
rdf = pd.DataFrame(runs)

with pd.ExcelWriter(XLSX, engine='openpyxl', mode='a', if_sheet_exists='replace') as w:
    mat.to_excel(w, sheet_name='Stage_Map', index=False)
    cdf.to_excel(w, sheet_name='Trade_Cadence', index=False)
    dist.to_excel(w, sheet_name='Month_Cadence', index=False)
    rdf.to_excel(w, sheet_name='Regime_Runs', index=False)
try:
    shutil.copy(XLSX, COPY_TO)
    print('xlsx updated + copied to Downloads')
except Exception as e:
    print('copy failed:', e)

# ---- console summary ----
print('=== STAGE DECISION MATRIX (2015-2026, warmup ~200d excluded) ===')
print(mat[['Stage', 'Action', 'Pct_days', 'Avg_+20d_pct', 'Win_+20d_pct']].to_string(index=False))
print()
print('=== ENTRY TIER CADENCE — honest expectation ===')
print(cdf.to_string(index=False))
print()
print('=== Months: kitni quality entries mili (pct months) ===')
print(dist.to_string(index=False))
print()
print('=== Regime runs (kyun cadence aisi hai) ===')
print(rdf.to_string(index=False))
