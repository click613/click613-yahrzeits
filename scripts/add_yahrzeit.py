#!/usr/bin/env python3
"""Add one yahrzeit to data/yahrzeits.json (or data/unconfirmed.json with --unconfirmed).

Example:
  python scripts/add_yahrzeit.py --date 18-Cheshvan \
     --name-en "R' Nachum Partzovitz" --name-he "רבי נחום פרצוביץ" \
     --father-en "R' Aryeh Tzvi" --father-he "רבי אריה צבי" \
     --year-heb 5747 --year 1986 --who "Rosh Yeshivas Mir in Jerusalem" \
     --source "he.wikipedia date page" --source "https://www.torahtots.com/timecapsule/thismonth/cheshvan.htm"

A confirmed entry needs at least two --source values. Then run: python scripts/build.py --check
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import KEY_RE, MONTH_KEYS, MONTH_DAYS, DATA

ap = argparse.ArgumentParser()
ap.add_argument('--date', required=True, help='Hebrew date key, e.g. 18-Cheshvan, 7-Adar, 14-Adar-II')
ap.add_argument('--name-en'); ap.add_argument('--name-he')
ap.add_argument('--father-en'); ap.add_argument('--father-he')
ap.add_argument('--year-heb'); ap.add_argument('--year')
ap.add_argument('--who', help='one line: who he was')
ap.add_argument('--adar', choices=['I', 'II'])
ap.add_argument('--source', action='append', default=[], help='a source name or URL (repeat)')
ap.add_argument('--unconfirmed', action='store_true')
a = ap.parse_args()
m = KEY_RE.match(a.date)
if not m or not 1 <= int(m.group(1)) <= MONTH_DAYS[m.group(2)]:
    sys.exit(f'bad --date {a.date!r}; months: {", ".join(MONTH_KEYS)}')
if not (a.name_en or a.name_he): sys.exit('need --name-en or --name-he')
if not a.unconfirmed and len(a.source) < 2: sys.exit('a confirmed yahrzeit needs two --source values (or use --unconfirmed)')
p = {'name_he': a.name_he, 'name_en': a.name_en, 'father_he': a.father_he, 'father_en': a.father_en,
     'year_heb': a.year_heb, 'year': a.year, 'who': a.who, 'adar': a.adar,
     'sources': [{'name': s, 'url': s if s.startswith('http') else None} for s in a.source]}
p = {k: v for k, v in p.items() if v not in (None, '', [])}
fn = os.path.join(DATA, 'unconfirmed.json' if a.unconfirmed else 'yahrzeits.json')
doc = json.load(open(fn, encoding='utf-8'))
doc['dates'].setdefault(a.date, []).append(p)
order = lambda k: (MONTH_KEYS.index(k.split('-', 1)[1]), int(k.split('-')[0]))
doc['dates'] = dict(sorted(doc['dates'].items(), key=lambda kv: order(kv[0])))
doc['count'] = sum(len(v) for v in doc['dates'].values())
json.dump(doc, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'added to {os.path.basename(fn)} under {a.date}')
